"""Title cleaning, broadcast indicator stripping, and normalization pipeline."""

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Optional, Tuple


@dataclass
class SanitizedTitleResult:
    """Structured output from title sanitization and parsing."""

    cleaned_title: str
    raw_title: str
    release_year: Optional[int] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    is_live: bool = False
    is_repeat: bool = False


class MetadataSanitizer:
    """Sanitizes raw broadcast titles, extracting release years, episodic tags, and removing noise."""

    _QUALITY_TAGS = re.compile(
        r"\b(?:4K|UHD|FHD|HD|SD|1080[pi]|720p|576[pi]|480p|HDR|Dolby(?:\s*Digital)?|5\.1|HEVC|x26[45])\b",
        re.IGNORECASE,
    )

    _BROADCAST_INDICATORS = re.compile(
        r"\[(?:1st\s+Broadcast|Live|R|Replica|New|Prima\s+TV|1\^?\s*TV|Diretta|1a\s+TV)\]|\((?:Repeat|New|R|Live)\)",
        re.IGNORECASE,
    )

    _SEASON_EPISODE_REGEX = re.compile(
        r"\b(?:S(\d{1,2})\s*E(\d{1,2})|(\d{1,2})x(\d{1,2})|Season\s+(\d+)\s+Episode\s+(\d+))\b",
        re.IGNORECASE,
    )

    _YEAR_REGEX = re.compile(r"\(?(\b(?:19\d{2}|20\d{2})\b)\)?")

    _EMPTY_BRACKETS = re.compile(r"\[\s*\]|\(\s*\)")
    _MULTISPACE = re.compile(r"\s+")
    _TRAILING_PUNCT = re.compile(r"^[^\w]+|[^\w]+$")

    @classmethod
    def strip_diacritics(cls, text: str) -> str:
        """Removes unicode accents and diacritical marks from text.

        Args:
            text (str): Input text string.

        Returns:
            str: Plain ASCII text with accents removed.
        """
        if not text:
            return ""
        normalized = unicodedata.normalize("NFD", text)
        return "".join(c for c in normalized if unicodedata.category(c) != "Mn")

    @classmethod
    def calculate_similarity(cls, title1: str, title2: str, auto_sanitize: bool = True) -> float:
        """Calculates normalized fuzzy string similarity ratio between two titles.

        Args:
            title1 (str): First title string.
            title2 (str): Second title string.
            auto_sanitize (bool): Whether to strip quality and broadcast tags before comparing.

        Returns:
            float: SequenceMatcher similarity score between 0.0 and 1.0.
        """
        if auto_sanitize:
            t1 = cls.sanitize(title1).cleaned_title
            t2 = cls.sanitize(title2).cleaned_title
        else:
            t1 = title1
            t2 = title2

        s1 = cls.strip_diacritics(t1).lower().strip()
        s2 = cls.strip_diacritics(t2).lower().strip()
        if not s1 or not s2:
            return 0.0
        if s1 == s2:
            return 1.0
        return SequenceMatcher(None, s1, s2).ratio()

    @classmethod
    def sanitize(cls, raw_title: str) -> SanitizedTitleResult:
        """Parses and normalizes a noisy broadcast title.

        Args:
            raw_title (str): Original raw EPG programme title.

        Returns:
            SanitizedTitleResult: Parsed metadata fields and cleaned title.
        """
        if not raw_title:
            return SanitizedTitleResult(cleaned_title="", raw_title="")

        original = raw_title.strip()
        working = original

        is_live = bool(re.search(r"\[(?:Live|Diretta)\]|\(Live\)", working, re.IGNORECASE))
        is_repeat = bool(re.search(r"\[(?:R|Replica)\]|\((?:Repeat|R)\)", working, re.IGNORECASE))

        working = cls._BROADCAST_INDICATORS.sub(" ", working)

        season: Optional[int] = None
        episode: Optional[int] = None
        se_match = cls._SEASON_EPISODE_REGEX.search(working)
        if se_match:
            g = se_match.groups()
            if g[0] is not None and g[1] is not None:
                season, episode = int(g[0]), int(g[1])
            elif g[2] is not None and g[3] is not None:
                season, episode = int(g[2]), int(g[3])
            elif g[4] is not None and g[5] is not None:
                season, episode = int(g[4]), int(g[5])
            working = cls._SEASON_EPISODE_REGEX.sub(" ", working)

        year: Optional[int] = None
        year_match = cls._YEAR_REGEX.search(working)
        if year_match:
            try:
                candidate_year = int(year_match.group(1))
                if 1900 <= candidate_year <= 2100:
                    year = candidate_year
                    working = cls._YEAR_REGEX.sub(" ", working)
            except ValueError:
                pass

        working = cls._QUALITY_TAGS.sub(" ", working)
        working = cls._EMPTY_BRACKETS.sub(" ", working)
        working = cls._MULTISPACE.sub(" ", working).strip()
        working = cls._TRAILING_PUNCT.sub("", working).strip()

        if not working:
            working = original

        return SanitizedTitleResult(
            cleaned_title=working,
            raw_title=original,
            release_year=year,
            season=season,
            episode=episode,
            is_live=is_live,
            is_repeat=is_repeat,
        )
