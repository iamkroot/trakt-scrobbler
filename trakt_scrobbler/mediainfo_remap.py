"""
This module contains a parser and applier for mediainfo remap rules.

It should be called at the end of get_media_info.
"""

import re
import sys
from copy import deepcopy
from enum import Enum
from pathlib import Path
from typing import List, Optional, Union
from pydantic_core import CoreSchema, core_schema
from pydantic import GetCoreSchemaHandler, field_validator, model_validator

from trakt_scrobbler.utils import pluralize

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib
from pydantic import BaseModel, Field
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

    def to_val(self) -> Union[int, List[int]]:
        """Convert to either a bare int, or a list of ints"""
        if self.end != self.start:
            return list(range(self.start, self.end + 1))
        else:
            return self.start

    def apply_delta(self, delta: int) -> "NumOrRange":
        return NumOrRange(self.start + delta, self.end + delta)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type, _handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        int_or_str = core_schema.union_schema([
            core_schema.int_schema(ge=0),
            core_schema.str_schema(pattern="^[0-9]+(:[0-9]+)?$"),
        ])
        return core_schema.no_info_after_validator_function(
            cls.validate,
            int_or_str,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda v: v.start if v.start == v.end else f"{v.start}:{v.end}",
                info_arg=False,
                return_schema=int_or_str
            )
        )

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
                end = int(m["end"]) if m["end"] != None else start
            except KeyError:
                end = start
            assert start <= end, f"Got start={start} > end={end}"
            return cls(start, end)
        else:
            raise TypeError("Expected int or string range")

    def __str__(self) -> str:
        if self.start == self.end:
            return str(self.start)
        else:
            return f"{self.start}:{self.end}"

    def __repr__(self) -> str:
        return f"NumOrRange(start={self.start},end={self.end})"        


class RemapMatch(BaseModel):
    path: Optional[re.Pattern] = None
    episode: Optional[NumOrRange] = None
    season: Optional[NumOrRange] = None
    title: Optional[str] = None
    year: Optional[int] = None

    @model_validator(mode='before')
    @classmethod
    def check_atleast_one(cls, values):
        if isinstance(values, dict):
            assert any(
                values.get(k) is not None for k in ("path", "title")
            ), f"Expected either path or title in match. Got {values}"
        return values

    @field_validator('path')
    @classmethod
    def path_regex(cls, path):
        if isinstance(path, str):
            return re.compile(path)
        return path

    def match(self, path: Optional[str], guess):
        path_match = None
        if self.path is not None:
            if path is None:
                # If match.path is provided, the path _has_ to be present
                return None
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

    def __str__(self):
        s = []
        if self.path is not None:
            s.append(f"path={self.path.pattern!r}")
        if self.title is not None:
            s.append(f"title={self.title}")
        if self.episode is not None:
            s.append(f"episode={self.episode}")
        if self.season is not None:
            s.append(f"season={self.season}")
        if self.year is not None:
            s.append(f"year={self.year}")
        return f"RemapMatch({' && '.join(s)})"


class TraktId(BaseModel):
    trakt_id: int

    def __str__(self):
        return f"trakt_id={self.trakt_id}"


class TraktSlug(BaseModel):
    trakt_slug: str

    def __str__(self):
        return f"trakt_slug={self.trakt_slug}"


class Title(BaseModel):
    title: str

    def __str__(self):
        return f"title={self.title}"


MediaId = Union[TraktId, TraktSlug, Title]


def format(media_id: MediaId, mediainfo) -> MediaId:
    if isinstance(media_id, TraktId):
        return TraktId(trakt_id=int(media_id.trakt_id))
    elif isinstance(media_id, TraktSlug):
        return TraktSlug(trakt_slug=media_id.trakt_slug.format(**mediainfo))
    elif isinstance(media_id, Title):
        return Title(title=media_id.title.format(**mediainfo))


class MediaType(str, Enum):
    episode = "episode"
    movie = "movie"

    def __str__(self) -> str:
        return "episode" if self == MediaType.episode else "movie"


class RemapRule(BaseModel, extra='forbid'):
    match: RemapMatch
    media_type: MediaType = Field(alias="type")
    media_id: MediaId = Field(alias="id")
    season: Optional[int] = None
    episode: Optional[NumOrRange] = None
    episode_delta: int = 0

    @model_validator(mode='before')
    @classmethod
    def check_no_ep_with_movie(cls, values):
        if isinstance(values, dict):
            if values.get("media_type") == MediaType.movie:
                assert values.get("season") is None, "Got season in movie rule"
        return values

    def apply(self, path: Optional[str], orig_info: dict):
        """If the rule matches, apply it to orig_info and return modified media_info"""
        media_info = deepcopy(orig_info)
        match = self.match.match(path, media_info)
        if match is None:
            return None

        media_info.update(match)
        media_info['type'] = str(self.media_type)
        if self.media_type == MediaType.episode:
            media_info['season'] = (
                self.season if self.season is not None else int(media_info['season'])
            )
            if self.episode is not None:
                # completely override the episode
                ep = self.episode.apply_delta(self.episode_delta).to_val()
            elif isinstance(media_info['episode'], list):
                # got multi-episode file, apply delta to each one
                ep = [
                    int(epnum) + self.episode_delta for epnum in media_info['episode']
                ]
            else:
                # single episode, directly apply delta
                ep = int(media_info['episode']) + self.episode_delta

            if (isinstance(ep, int) and ep < 0) or (
                isinstance(ep, list) and any(epnum < 0 for epnum in ep)
            ):
                logger.error(f"Negative episode {ep} in {media_info}! rule={self}")
                return None
            media_info['episode'] = ep

        new_id = format(self.media_id, media_info)
        if isinstance(new_id, TraktId):
            media_info['trakt_id'] = new_id.trakt_id
        elif isinstance(new_id, TraktSlug):
            media_info['trakt_slug'] = new_id.trakt_slug
        elif isinstance(new_id, Title):
            media_info['title'] = new_id.title

        logger.debug(f"Applied remap rule {self} on {orig_info} to get {media_info}")
        return media_info

    def __str__(self):
        s = [f"type={self.media_type}", f"id.{self.media_id}"]
        if self.season is not None:
            s.append(f"season={self.season}")
        if self.episode_delta:
            s.append(f"episode_delta={self.episode_delta}")

        return f"RemapRule({self.match} -> {{{', '.join(s)}}})"


class RemapFile(BaseModel):
    rules: List[RemapRule] = Field(default_factory=list)


def read_file(file: Path) -> List[RemapRule]:
    try:
        with open(file, "rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError:
        return []
    except tomllib.TOMLDecodeError:
        logger.exception(f"Invalid TOML in remap_rules file at {file}. Ignoring.")
        return []
    return RemapFile.model_validate(data).rules


_rules: Optional[List[RemapRule]] = None


def apply_remap_rules(path: Optional[str], media_info: dict):
    global _rules
    if _rules is None:
        # read from file on first use
        _rules = read_file(REMAP_FILE_PATH)
        if _rules:
            logger.debug(f"Read {len(_rules)} remap {pluralize(len(_rules), 'rule')} from {REMAP_FILE_PATH}")

    for rule in _rules:
        upd = rule.apply(path, media_info)
        if upd is not None:
            return upd
    return media_info  # unchanged
