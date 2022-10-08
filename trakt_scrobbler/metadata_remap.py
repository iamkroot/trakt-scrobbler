"""
This module contains a parser and applier for metadata remap rules.

It should be called at the end of get_media_info.
"""

from enum import Enum
import re
from typing import Literal, Optional, Union
from pydantic import BaseModel, Field, root_validator, validator, Extra


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
        assert any(k in values for k in ("path", "title"))
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


class MediaId(Union[TraktId, TraktSlug, Title]):
    def format(self, *args, **kwargs):
        if isinstance(self, TraktId):
            return TraktId(trakt_id=self.trakt_id.format(*args, **kwargs))
        elif isinstance(self, TraktSlug):
            return TraktSlug(trakt_slug=self.trakt_slug.format(*args, **kwargs))
        elif isinstance(self, Title):
            return Title(title=self.title.format(*args, **kwargs))


class MediaType(str, Enum):
    episode = "episode"
    movie = "movie"


class RemapRule(BaseModel, extra=Extra.forbid):
    match: RemapMatch
    media_type: MediaType = Field(alias="type")
    media_id: MediaId = Field(alias="id")
    season: Optional[int]
    episode_delta: int = 0

    @root_validator
    def check_no_ep_with_movie(cls, values):
        if values["media_id"] == MediaId.movie:
            assert "season" not in values
            assert "episode_delta" not in values
        return values
