"""The parts of Markdown that Menairos checks: headings, anchors and sections.

This is not a full CommonMark parser. It reads what the method's documents
use, as GitHub renders it (checked against GitHub's API in T-06, see the
annex of ``hito-0.md``):

* ATX headings (``#`` to ``######`` with up to three spaces in front) outside
  fenced code blocks. Setext headings and headings inside lists or block
  quotes get an anchor on GitHub but are not counted here (``hito-0.md`` 2.3).
* The anchor of a heading, computed as GitHub does from its visible text.

Files are read as UTF-8 with an optional BOM; any line ending (LF, CRLF or
CR) is accepted.
"""

import html
import re
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

_LINE_BREAK = re.compile(r"\r\n|\r|\n")
_FENCE_OPEN = re.compile(r" {0,3}(`{3,}|~{3,})(.*)")
_ATX = re.compile(r" {0,3}(#{1,6})(?:[ \t](.*))?")
_CLOSING_HASHES = re.compile(r"(?:^|[ \t]+)#+[ \t]*$")
_ENTITY = re.compile(
    r"&(?:#[0-9]{1,7}|#[xX][0-9a-fA-F]{1,6}|[A-Za-z][A-Za-z0-9]{1,31});"
)
_AUTOLINK = re.compile(r"<([A-Za-z][A-Za-z0-9+.-]{1,31}:[^\s<>]*|[^\s<>@]+@[^\s<>@]+)>")
_HTML_TAG = re.compile(
    r"<(?:/?[A-Za-z][A-Za-z0-9-]*(?:\s[^<>]*)?/?|!--.*?--)>", flags=re.DOTALL
)
_ASCII_PUNCTUATION = frozenset("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")
_EMPHASIS = "*_"


@dataclass(frozen=True)
class Line:
    """A line of the document, numbered from 1, and whether it is code."""

    number: int
    text: str
    in_code: bool


@dataclass(frozen=True)
class Heading:
    """An ATX heading: level, visible text, line and GitHub anchor.

    ``anchor`` is ``""`` when nothing is left of the text after removing
    punctuation and symbols (``## ✅``): GitHub gives it no anchor.
    """

    level: int
    text: str
    line: int
    anchor: str


@dataclass(frozen=True)
class Document:
    """A Markdown document: its lines and its headings, in order."""

    lines: tuple[Line, ...]
    headings: tuple[Heading, ...]

    @property
    def anchors(self) -> frozenset[str]:
        """The anchors a link can point to (without the ``#``)."""
        return frozenset(h.anchor for h in self.headings if h.anchor)

    def section(self, heading: Heading) -> tuple[Line, ...]:
        """The lines under ``heading``, up to the next heading of its level or above."""
        start = heading.line  # the line after the heading (lines are 1-based)
        end = len(self.lines)
        for other in self.headings:
            if other.line > heading.line and other.level <= heading.level:
                end = other.line - 1
                break
        return self.lines[start:end]


def read(path: Path) -> Document:
    """Read and parse a Markdown file (UTF-8, BOM allowed)."""
    return parse(path.read_text(encoding="utf-8-sig"))


def parse(text: str) -> Document:
    """Parse Markdown text into lines and headings."""
    text = text.removeprefix("\ufeff")
    raw = _LINE_BREAK.split(text)
    if raw and raw[-1] == "":
        raw.pop()
    lines: list[Line] = []
    headings: list[Heading] = []
    slugger = _Slugger()
    fence: str | None = None
    for number, line in enumerate(raw, start=1):
        if fence is not None:
            if _closes(line, fence):
                fence = None
            lines.append(Line(number, line, in_code=True))
            continue
        opened = _FENCE_OPEN.fullmatch(line)
        if opened and not (opened[1][0] == "`" and "`" in opened[2]):
            fence = opened[1]
            lines.append(Line(number, line, in_code=True))
            continue
        lines.append(Line(number, line, in_code=False))
        heading = _ATX.fullmatch(line)
        if heading:
            content = _CLOSING_HASHES.sub("", heading[2] or "").strip()
            visible = visible_text(content)
            if visible:
                anchor = slugger.slug(visible)
                headings.append(Heading(len(heading[1]), visible, number, anchor))
    return Document(tuple(lines), tuple(headings))


def github_slug(text: str) -> str:
    """The anchor GitHub derives from a heading's visible text, before deduplication.

    Lowercase; keep letters, marks, decimal digits, connector punctuation
    (``_``), ``-`` and spaces (Ruby's ``\\p{Word}``); each space becomes ``-``.
    """
    out: list[str] = []
    for char in text.lower():
        if char == " ":
            out.append("-")
        elif char == "-" or _is_word(char):
            out.append(char)
    return "".join(out)


def visible_text(content: str) -> str:
    """The text a heading shows: code without backticks, links as their text…

    Backslash escapes and entities are resolved; images, HTML tags and
    emphasis markers are dropped.
    """
    chars: list[tuple[str, bool]] = []
    _inline(content, chars)
    return _drop_emphasis(chars).strip()


class _Slugger:
    """Deduplicate anchors as GitHub does (``x``, ``x-1``, and ``x-1-1`` on a clash)."""

    def __init__(self) -> None:
        self._count: dict[str, int] = {}

    def slug(self, text: str) -> str:
        base = slug = github_slug(text)
        while slug in self._count:
            self._count[base] += 1
            slug = f"{base}-{self._count[base]}"
        self._count[slug] = 0
        return slug


def _is_word(char: str) -> bool:
    category = unicodedata.category(char)
    return category[0] in "LM" or category in ("Nd", "Pc")


def _closes(line: str, fence: str) -> bool:
    """A closing fence: the same character, at least as long, and nothing after."""
    stripped = line.lstrip(" ")
    if len(line) - len(stripped) > 3:
        return False
    run = len(stripped) - len(stripped.lstrip(fence[0]))
    return run >= len(fence) and stripped[run:].strip(" \t") == ""


def _inline(text: str, out: list[tuple[str, bool]]) -> None:
    """Append (char, literal) pairs; literal chars never act as emphasis markers."""
    i = 0
    while i < len(text):
        char = text[i]
        if char == "\\" and i + 1 < len(text) and text[i + 1] in _ASCII_PUNCTUATION:
            out.append((text[i + 1], True))
            i += 2
        elif char == "`":
            i = _code_span(text, i, out)
        elif char == "&" and (entity := _ENTITY.match(text, i)):
            out.extend((c, True) for c in html.unescape(entity[0]))
            i = entity.end()
        elif char == "!" and (link := _link(text, i + 1)):
            i = link[1]  # images show nothing
        elif char == "[" and (link := _link(text, i)):
            _inline(link[0], out)
            i = link[1]
        elif char == "<" and (auto := _AUTOLINK.match(text, i)):
            out.extend((c, True) for c in auto[1])
            i = auto.end()
        elif char == "<" and (tag := _HTML_TAG.match(text, i)):
            i = tag.end()
        else:
            out.append((char, False))
            i += 1


def _code_span(text: str, start: int, out: list[tuple[str, bool]]) -> int:
    """Handle a backtick run at ``start``; return the index after it."""
    end = start
    while end < len(text) and text[end] == "`":
        end += 1
    ticks = end - start
    search = end
    while (found := text.find("`" * ticks, search)) != -1:
        after = found + ticks
        if (after < len(text) and text[after] == "`") or text[found - 1] == "`":
            search = after
            while search < len(text) and text[search] == "`":
                search += 1
            continue
        code = text[end:found]
        if len(code) >= 2 and code[0] == " " and code[-1] == " " and code.strip(" "):
            code = code[1:-1]
        out.extend((c, True) for c in code)
        return after
    out.extend(("`", False) for _ in range(ticks))
    return end


def _link(text: str, start: int) -> tuple[str, int] | None:
    """An inline link ``[text](destination)`` at ``start``: (text, index after)."""
    if start >= len(text) or text[start] != "[":
        return None
    depth = 0
    i = start
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
            if depth == 0:
                break
        i += 1
    else:
        return None
    label_end = i
    if label_end + 1 >= len(text) or text[label_end + 1] != "(":
        return None
    depth = 0
    j = label_end + 1
    while j < len(text):
        if text[j] == "\\":
            j += 2
            continue
        if text[j] == "(":
            depth += 1
        elif text[j] == ")":
            depth -= 1
            if depth == 0:
                return text[start + 1 : label_end], j + 1
        j += 1
    return None


def _drop_emphasis(chars: list[tuple[str, bool]]) -> str:
    """Remove matched ``*`` and ``_`` delimiter runs (CommonMark flanking rules)."""
    runs = list(_delimiter_runs(chars))
    removed: set[int] = set()
    openers: list[list[int]] = []  # [marker index in runs, start, length left]
    for index, (marker, start, length, can_open, can_close) in enumerate(runs):
        left = length
        if can_close:
            k = len(openers) - 1
            while left and k >= 0:
                opener = openers[k]
                if runs[opener[0]][0] != marker:
                    k -= 1
                    continue
                used = min(opener[2], left)
                removed.update(
                    range(opener[1] + opener[2] - used, opener[1] + opener[2])
                )
                removed.update(
                    range(start + length - left, start + length - left + used)
                )
                opener[2] -= used
                left -= used
                del openers[k + 1 :]
                if opener[2] == 0:
                    openers.pop()
                k = len(openers) - 1
        if can_open and left:
            openers.append([index, start + length - left, left])
    return "".join(c for i, (c, _) in enumerate(chars) if i not in removed)


def _delimiter_runs(
    chars: list[tuple[str, bool]],
) -> Iterator[tuple[str, int, int, bool, bool]]:
    """Yield (marker, start, length, can_open, can_close) for each emphasis run."""
    i = 0
    while i < len(chars):
        char, literal = chars[i]
        if literal or char not in _EMPHASIS:
            i += 1
            continue
        start = i
        while i < len(chars) and chars[i] == (char, False):
            i += 1
        before = chars[start - 1][0] if start else " "
        after = chars[i][0] if i < len(chars) else " "
        left = not after.isspace() and (
            not _is_punctuation(after) or before.isspace() or _is_punctuation(before)
        )
        right = not before.isspace() and (
            not _is_punctuation(before) or after.isspace() or _is_punctuation(after)
        )
        if char == "_":
            can_open = left and (not right or _is_punctuation(before))
            can_close = right and (not left or _is_punctuation(after))
        else:
            can_open, can_close = left, right
        yield char, start, i - start, can_open, can_close


def _is_punctuation(char: str) -> bool:
    return unicodedata.category(char)[0] in "PS"
