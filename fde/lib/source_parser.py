"""Parse source design HTML into structured data for diffing against produced artifacts."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

from bs4 import BeautifulSoup, Tag


@dataclass
class CssVariable:
    name: str  # e.g. "--bg-raised"
    value: str  # raw value, exact
    line: int  # source line number


@dataclass
class InlineSvg:
    raw: str  # full <svg>...</svg> outerHTML
    paths: list[str]  # path `d` attributes
    viewbox: str | None
    line: int


@dataclass
class TextString:
    text: str  # the visible string
    line: int
    context: str  # parent tag name + class for disambiguation


@dataclass
class ParsedSource:
    html_path: Path
    raw: str
    css_variables: list[CssVariable] = field(default_factory=list)
    css_rules_raw: str = ""
    inline_svgs: list[InlineSvg] = field(default_factory=list)
    text_strings: list[TextString] = field(default_factory=list)
    media_queries: list[str] = field(default_factory=list)
    keyframes: list[str] = field(default_factory=list)


# strings that are noise — designer annotations, debug ui, dev-only chrome
NOISE_CLASSES = {"annot", "phone-label", "phone-hint", "tweaks", "spec-strip", "mast-r"}
NOISE_PARENTS = {"script", "style", "noscript"}


def parse_source(path: Path) -> ParsedSource:
    raw = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(raw, "html.parser")
    parsed = ParsedSource(html_path=path, raw=raw)

    parsed.css_variables = _extract_css_variables(raw)
    parsed.css_rules_raw = _extract_css_block(soup)
    parsed.inline_svgs = _extract_svgs(soup, raw)
    parsed.text_strings = _extract_text_strings(soup, raw)
    parsed.media_queries = _extract_media_queries(parsed.css_rules_raw)
    parsed.keyframes = _extract_keyframes(parsed.css_rules_raw)
    return parsed


def _line_of(needle: str, raw: str) -> int:
    idx = raw.find(needle)
    if idx < 0:
        return -1
    return raw[:idx].count("\n") + 1


def _extract_css_block(soup: BeautifulSoup) -> str:
    parts = []
    for s in soup.find_all("style"):
        if s.string:
            parts.append(s.string)
    return "\n".join(parts)


_VAR_RE = re.compile(r"(--[a-zA-Z0-9_-]+)\s*:\s*([^;}\n]+);")


def _extract_css_variables(raw: str) -> list[CssVariable]:
    out: list[CssVariable] = []
    for m in _VAR_RE.finditer(raw):
        name = m.group(1)
        value = m.group(2).strip()
        line = raw[: m.start()].count("\n") + 1
        out.append(CssVariable(name=name, value=value, line=line))
    return out


_PATH_D_RE = re.compile(r'\bd\s*=\s*["\']([^"\']+)["\']')
_VIEWBOX_RE = re.compile(r'\bviewBox\s*=\s*["\']([^"\']+)["\']')


def _extract_svgs(soup: BeautifulSoup, raw: str) -> list[InlineSvg]:
    out: list[InlineSvg] = []
    seen_signatures: set[str] = set()
    for svg in soup.find_all("svg"):
        s = str(svg)
        # skip annotation arrows and dev chrome
        parent_classes = set()
        for ancestor in svg.parents:
            if isinstance(ancestor, Tag) and ancestor.get("class"):
                parent_classes.update(ancestor.get("class"))
        if parent_classes & NOISE_CLASSES:
            continue
        paths = _PATH_D_RE.findall(s)
        if not paths:
            if "stroke" not in s and "fill" not in s:
                continue
        vb_m = _VIEWBOX_RE.search(s)

        # dedup: same path data == same icon. The wireframe repeats icons across sections,
        # but for catalog/validation purposes each unique icon counts once.
        sig = "|".join(paths) if paths else s[:200]
        if sig in seen_signatures:
            continue
        seen_signatures.add(sig)

        # find line via the first path's distinctive prefix; fall back to the svg open tag with class
        line = -1
        if paths:
            line = _line_of(f'd="{paths[0][:30]}', raw)
            if line < 0:
                line = _line_of(f"d='{paths[0][:30]}", raw)
        if line < 0:
            # try matching on a stable substring of the svg open tag
            open_match = re.search(r"<svg[^>]{0,100}", s)
            if open_match:
                line = _line_of(open_match.group(0), raw)

        out.append(
            InlineSvg(
                raw=s,
                paths=paths,
                viewbox=vb_m.group(1) if vb_m else None,
                line=line,
            )
        )
    return out


_WHITESPACE_RE = re.compile(r"\s+")


def _extract_text_strings(soup: BeautifulSoup, raw: str) -> list[TextString]:
    out: list[TextString] = []
    seen: set[str] = set()
    for el in soup.find_all(string=True):
        parent = el.parent
        if not isinstance(parent, Tag):
            continue
        if parent.name in NOISE_PARENTS:
            continue
        # filter doctype, html declarations, and meta-ish noise
        if parent.name in {"[document]", "html", "head", "meta", "link", "title"}:
            continue

        # walk up to check noise classes
        skip = False
        for anc in parent.parents:
            if isinstance(anc, Tag) and anc.get("class"):
                if set(anc.get("class")) & NOISE_CLASSES:
                    skip = True
                    break
        if skip:
            continue

        text = _WHITESPACE_RE.sub(" ", str(el)).strip()
        if not text:
            continue
        # filter pure punctuation, single chars, line numbers
        if len(text) < 2 and text not in {"·", "—", "¶"}:
            continue
        # filter trivial markup leftovers
        if text in {">", "<", "/", "{", "}"}:
            continue

        key = (parent.name, text)
        if key in seen:
            continue
        seen.add(key)

        ctx = parent.name
        if parent.get("class"):
            ctx += "." + ".".join(parent.get("class"))
        out.append(TextString(text=text, line=_line_of(text[:30], raw), context=ctx))
    return out


_MEDIA_RE = re.compile(r"@media\s+([^{]+)\{")


def _extract_media_queries(css: str) -> list[str]:
    return [m.group(1).strip() for m in _MEDIA_RE.finditer(css)]


_KEYFRAMES_RE = re.compile(r"@keyframes\s+([a-zA-Z_-]+)\s*\{")


def _extract_keyframes(css: str) -> list[str]:
    return [m.group(1) for m in _KEYFRAMES_RE.finditer(css)]
