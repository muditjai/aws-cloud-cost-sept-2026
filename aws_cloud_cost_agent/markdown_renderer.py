from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit

import markdown


ALLOWED_TAGS = {
    "a",
    "blockquote",
    "br",
    "code",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "li",
    "ol",
    "p",
    "pre",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
}
VOID_TAGS = {"br", "hr"}
SAFE_LINK_SCHEMES = {"", "http", "https", "mailto"}
LANGUAGE_CLASS = re.compile(r"^language-[a-zA-Z0-9_+-]+$")


class MarkdownSanitizer(HTMLParser):
    """Keep only the HTML emitted for supported Markdown constructs."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.output: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in ALLOWED_TAGS:
            return
        safe_attrs = self._safe_attrs(tag, attrs)
        rendered_attrs = "".join(
            f' {name}="{html.escape(value, quote=True)}"' for name, value in safe_attrs
        )
        self.output.append(f"<{tag}{rendered_attrs}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag in ALLOWED_TAGS and tag not in VOID_TAGS:
            self.output.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        self.output.append(html.escape(data))

    def handle_entityref(self, name: str) -> None:
        self.output.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.output.append(f"&#{name};")

    def _safe_attrs(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> list[tuple[str, str]]:
        values = {name: value for name, value in attrs if value is not None}
        if tag == "a" and "href" in values:
            href = values["href"]
            if urlsplit(href).scheme.lower() in SAFE_LINK_SCHEMES:
                result = [("href", href), ("rel", "noopener noreferrer")]
                if "title" in values:
                    result.append(("title", values["title"]))
                return result
        if tag == "code" and LANGUAGE_CLASS.fullmatch(values.get("class", "")):
            return [("class", values["class"])]
        return []


def render_markdown(source: str) -> str:
    """Render Markdown to sanitized HTML suitable for the local artifact viewer."""
    rendered = markdown.markdown(
        source,
        extensions=["fenced_code", "sane_lists", "tables"],
        output_format="html",
    )
    sanitizer = MarkdownSanitizer()
    sanitizer.feed(rendered)
    sanitizer.close()
    return "".join(sanitizer.output)
