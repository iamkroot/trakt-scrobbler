"""
This module contains a parser and applier for mediainfo remap rules.

It should be called at the end of get_media_info.
"""

import re
from copy import deepcopy
from enum import Enum
from pathlib import Path
from typing import List, Optional, Union

import toml
from pydantic import BaseModel, Extra, Field, root_validator, validator
from trakt_scrobbler import logger
from trakt_scrobbler.app_dirs import CFG_DIR

REMAP_FILE_PATH = CFG_DIR / "remap_rules.toml"


class NumOrRange:
    """Single number, or a range (inclusive on both ends)"""

    __slots__ = ("start", "end")
    RANGE_REGEX = re.compile(r"(?P<start>\d+)(:(?P<end>\d+))?")

    def __init__(self, start: int, end: Optional[int] = None) -> None:
        self.start = start
        if end is not None:
            self.end = end
        else:
            self.end = start

    def match(self, val: int) -> bool:
        return self.start <= val and val <= self.end

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def __modify_schema__(cls, field_schema):
        # field_schema.update(pattern=)
        # TODO: Update schema
        # this class is a union of int and string "(\d+(:\d+)?)"
        pass

    @classmethod
    def validate(cls, v):
        if isinstance(v, int):
            return cls(v, v)
        elif isinstance(v, str):
            m = cls.RANGE_REGEX.fullmatch(v)
            if not m:
                raise ValueError("Invalid range")
            start = int(m.group("start"))
            try:
                end = int(m["end"])
            except KeyError:
                end = start
            return cls(start, end)
        else:
            raise TypeError("Expected int or string range")


class RemapMatch(BaseModel):
    path: Optional[re.Pattern]
    episode: Optional[NumOrRange]
    season: Optional[NumOrRange]
    title: Optional[str]
    year: Optional[int]

    @root_validator
    def check_atleast_one(cls, values):
        assert any(
            values.get(k) is not None for k in ("path", "title")
        ), f"Expected either path or title in match. Got {values}"
        return values

    @validator('path')
    def path_regex(cls, path):
        if isinstance(path, str):
            return re.compile(path)
        return path

    def match(self, path: str, guess):
        path_match = None
        if self.path is not None:
            path_match = self.path.fullmatch(path)
            if not path_match:
                return None

        if self.title is not None:
            title = guess.get("title")
            if title is not None:
                if self.title != title:
                    return None

        if self.year is not None:
            year = guess.get("year")
            if year is not None:
                if self.year != year:
                    return None

        if self.episode is not None:
            episode = guess.get("episode")
            if episode is not None:
                if not self.episode.match(episode):
                    return None

        if self.season is not None:
            season = guess.get("season")
            if season is not None:
                if not self.season.match(season):
                    return None

        return path_match.groupdict() if path_match is not None else {}


class TraktId(BaseModel):
    trakt_id: str


class TraktSlug(BaseModel):
    trakt_slug: str


class Title(BaseModel):
    title: str


MediaId = Union[TraktId, TraktSlug, Title]


def format(media_id: MediaId, *args, **kwargs) -> MediaId:
    if isinstance(media_id, TraktId):
        return TraktId(trakt_id=media_id.trakt_id.format(*args, **kwargs))
    elif isinstance(media_id, TraktSlug):
        return TraktSlug(trakt_slug=media_id.trakt_slug.format(*args, **kwargs))
    elif isinstance(media_id, Title):
        return Title(title=media_id.title.format(*args, **kwargs))


class MediaType(str, Enum):
    episode = "episode"
    movie = "movie"

    def __str__(self) -> str:
        return "episode" if self == MediaType.episode else "movie"


class RemapRule(BaseModel, extra=Extra.forbid):
    match: RemapMatch
    media_type: MediaType = Field(alias="type")
    media_id: MediaId = Field(alias="id")
    season: Optional[int]
    episode_delta: int = 0

    @root_validator
    def check_no_ep_with_movie(cls, values):
        if values["media_type"] == MediaType.movie:
            assert values.get("season") is None, "Got season in movie rule"
        return values

    def apply(self, path: str, media_info: dict):
        """If the rule matches, apply it to guess"""
        orig = deepcopy(media_info)
        match = self.match.match(path, media_info)
        if match is None:
            return False

        media_info.update(match)
        media_info['type'] = str(self.media_type)
        if self.media_type == MediaType.episode:
            media_info['season'] = (
                self.season if self.season is not None else int(media_info['season'])
            )
            media_info['episode'] = int(media_info['episode']) + self.episode_delta
            if media_info['episode'] < 0:
                raise ValueError(
                    f"Negative episode {media_info['episode']}! delta={self.episode_delta}"
                )

        new_id = format(self.media_id, media_info)
        if isinstance(new_id, TraktId):
            media_info['trakt_id'] = new_id.trakt_id
        elif isinstance(new_id, TraktSlug):
            media_info['trakt_slug'] = new_id.trakt_slug
        elif isinstance(new_id, Title):
            media_info['title'] = new_id.title

        logger.debug(f"Applied remap rule {self} on {orig} to get {media_info}")
        return True


class RemapFile(BaseModel):
    rules: List[RemapRule]


def read_file(file: Path) -> List[RemapRule]:
    try:
        data = toml.load(file)
    except FileNotFoundError:
        return []
    except toml.TomlDecodeError:
        logger.exception("Invalid TOML in remap_rules file. Ignoring.")
        return []
    return RemapFile.parse_obj(data).rules


rules = read_file(REMAP_FILE_PATH)


def apply_remap_rules(path, media_info):
    for rule in rules:
        if rule.apply(path, media_info):
            break
