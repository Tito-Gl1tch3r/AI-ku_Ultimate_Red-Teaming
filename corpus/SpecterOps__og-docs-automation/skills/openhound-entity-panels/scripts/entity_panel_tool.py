#!/usr/bin/env python3
"""Inventory, assemble, and structurally validate OpenGraph entity panels.

This tool deliberately does not render Go templates or execute Cypher. Those
checks require the target BloodHound release.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

URL_COMPATIBLE_KEY = re.compile(r"^[a-z0-9][a-z0-9_-]{0,127}$")
RELATIVE_MARKDOWN_LINK = re.compile(r"\]\((?!https?://|/)[^)]+\.md(?:#[^)]+)?\)")
RELATIVE_MARKDOWN_LINK_CAPTURE = re.compile(
    r"\[(?P<label>[^\]\r\n]+)\]"
    r"\((?!https?://|/)(?P<target>[^)]+\.md(?:#[^)]+)?)\)"
)
FENCE_LINE = re.compile(
    r"^(?P<indent> *)(?P<fence>`{3,}|~{3,})(?P<info>[^\r\n]*)$"
)
ORDERED_LIST_ITEM = re.compile(
    r"^(?P<indent> *)(?P<number>\d{1,9})[.)](?P<spacing>[ \t]+)"
)
TASK_LIST_ITEM = re.compile(
    r"^\s*(?:>\s*)*(?:[-+*]|\d+[.)])\s+\[[ xX]\](?:\s+|$)"
)
TABLE_DELIMITER_CELL = re.compile(r"^:?-{3,}:?$")
RAW_HTML = re.compile(
    r"<!--|-->|<![A-Za-z]|<\?|</?[A-Za-z][A-Za-z0-9-]*"
    r"(?:\s[^<>]*?)?\s*/?>"
)
UNSAFE_MARKDOWN_LINK = re.compile(
    r"\]\(\s*<?\s*(?:javascript|vbscript|data):", re.IGNORECASE
)
BACKSLASH_ESCAPE = r'''replace "\\" "\\\\"'''
SINGLE_QUOTE_ESCAPE = r'''replace "'" "\\'"'''
SUMMARY_SECTION_SPECS = {
    "inbound_traversable_relationships": ("Inbound", "inbound", 2),
    "outbound_traversable_relationships": ("Outbound", "outbound", 3),
}
QUESTION_TITLE = re.compile(
    r"^(?:Who|What|Which|Where|When|Why|How|Can|Could|Does|Do|Is|Are|Should|Would)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class EntitySpec:
    entity_type: str
    schema_key: str
    description_subdir: str
    required_sections: tuple[str, ...]


ENTITY_SPECS = (
    EntitySpec(
        "node",
        "node_kinds",
        "nodes",
        (
            "description",
            "inbound_traversable_relationships",
            "outbound_traversable_relationships",
        ),
    ),
    EntitySpec(
        "relationship", "relationship_kinds", "edges", ("general",)
    ),
)
SPEC_BY_TYPE = {spec.entity_type: spec for spec in ENTITY_SPECS}


class PanelToolError(Exception):
    """A user-facing input or validation error."""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PanelToolError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PanelToolError(
            f"invalid JSON in {path}: line {exc.lineno}, column {exc.colno}: "
            f"{exc.msg}"
        ) from exc


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def strip_inline_code_spans(line: str) -> str:
    """Remove complete backtick code spans before scanning rendered Markdown."""

    result: list[str] = []
    cursor = 0
    while cursor < len(line):
        opening = line.find("`", cursor)
        if opening < 0:
            result.append(line[cursor:])
            break
        result.append(line[cursor:opening])
        opening_end = opening
        while opening_end < len(line) and line[opening_end] == "`":
            opening_end += 1
        delimiter = line[opening:opening_end]
        search_from = opening_end
        closing = -1
        while True:
            candidate = line.find(delimiter, search_from)
            if candidate < 0:
                break
            before_is_tick = candidate > 0 and line[candidate - 1] == "`"
            after = candidate + len(delimiter)
            after_is_tick = after < len(line) and line[after] == "`"
            if not before_is_tick and not after_is_tick:
                closing = candidate
                break
            search_from = candidate + 1
        if closing < 0:
            result.append(line[opening:])
            break
        cursor = closing + len(delimiter)
    return "".join(result)


def has_aligned_table_delimiter(line: str) -> bool:
    """Return whether a GFM table delimiter asks for cell alignment."""

    stripped = line.strip()
    if "|" not in stripped:
        return False
    cells = [cell.strip() for cell in stripped.split("|")]
    if cells and not cells[0]:
        cells.pop(0)
    if cells and not cells[-1]:
        cells.pop()
    return bool(cells) and all(
        TABLE_DELIMITER_CELL.fullmatch(cell) for cell in cells
    ) and any(":" in cell for cell in cells)


def markdown_upload_errors(content: str) -> list[str]:
    """Find Markdown constructs known to fail sanitizer equality checks.

    BloodHound's target renderer and sanitizer remain authoritative. This
    scanner intentionally enforces a conservative subset without attempting to
    reimplement either component.
    """

    errors: list[str] = []
    fence: tuple[str, int] | None = None
    ordered_lists: list[tuple[int, int]] = []
    blank_since_content = False

    for line_number, source_line in enumerate(content.splitlines(), start=1):
        line = source_line.expandtabs(4)

        if fence is not None:
            fence_char, fence_length = fence
            closing = line.lstrip(" ")
            closing_run = len(closing) - len(closing.lstrip(fence_char))
            if (
                closing_run >= fence_length
                and not closing[closing_run:].strip()
            ):
                fence = None
            continue

        fence_match = FENCE_LINE.fullmatch(line)
        if fence_match:
            indent = len(fence_match.group("indent"))
            container_indent = max(
                (
                    content_indent
                    for _, content_indent in ordered_lists
                    if content_indent <= indent
                ),
                default=0,
            )
            if indent - container_indent <= 3:
                while ordered_lists and indent < ordered_lists[-1][1]:
                    ordered_lists.pop()
                fence_text = fence_match.group("fence")
                info = fence_match.group("info").strip()
                if info:
                    errors.append(
                        f"line {line_number}: fenced code block has info "
                        "text that renders a sanitizer-stripped language class"
                    )
                fence = (fence_text[0], len(fence_text))
                blank_since_content = False
                continue

        visible_line = strip_inline_code_spans(line)
        stripped = visible_line.strip()
        if not stripped:
            blank_since_content = True
            continue

        ordered_match = ORDERED_LIST_ITEM.match(line)
        if ordered_match:
            indent = len(ordered_match.group("indent"))
            while ordered_lists and indent < ordered_lists[-1][0]:
                ordered_lists.pop()
            continuing = bool(
                ordered_lists and indent == ordered_lists[-1][0]
            )
            if not continuing:
                while ordered_lists and indent < ordered_lists[-1][1]:
                    ordered_lists.pop()
                continuing = bool(
                    ordered_lists and indent == ordered_lists[-1][0]
                )
            if not continuing:
                number = int(ordered_match.group("number"))
                if number != 1:
                    errors.append(
                        f"line {line_number}: ordered-list block begins at "
                        f"{number}, which renders a sanitizer-stripped start "
                        "attribute"
                    )
                marker_width = len(ordered_match.group("number")) + 1
                spacing_width = len(ordered_match.group("spacing"))
                ordered_lists.append(
                    (indent, indent + marker_width + spacing_width)
                )
            blank_since_content = False
        else:
            indent = len(line) - len(line.lstrip(" "))
            if blank_since_content:
                while ordered_lists and indent < ordered_lists[-1][1]:
                    ordered_lists.pop()
            blank_since_content = False

        if RAW_HTML.search(visible_line):
            errors.append(
                f"line {line_number}: raw HTML, an HTML comment, or a "
                "tag-shaped placeholder is not upload-safe"
            )
        if TASK_LIST_ITEM.match(visible_line):
            errors.append(
                f"line {line_number}: GFM task-list markup renders a "
                "sanitizer-stripped checkbox"
            )
        if has_aligned_table_delimiter(visible_line):
            errors.append(
                f"line {line_number}: aligned GFM table delimiters render "
                "sanitizer-stripped style attributes"
            )
        if UNSAFE_MARKDOWN_LINK.search(visible_line):
            errors.append(
                f"line {line_number}: Markdown link uses an unsafe URI scheme"
            )

    return errors


def markdown_h2_headings(content: str) -> list[str]:
    """Return level-two ATX headings outside fenced code blocks."""

    headings: list[str] = []
    fence: tuple[str, int] | None = None
    for source_line in content.splitlines():
        line = source_line.expandtabs(4)
        if fence is not None:
            fence_char, fence_length = fence
            closing = line.lstrip(" ")
            closing_run = len(closing) - len(closing.lstrip(fence_char))
            if (
                closing_run >= fence_length
                and not closing[closing_run:].strip()
            ):
                fence = None
            continue

        fence_match = FENCE_LINE.fullmatch(line)
        if fence_match and len(fence_match.group("indent")) <= 3:
            fence_text = fence_match.group("fence")
            fence = (fence_text[0], len(fence_text))
            continue

        heading = re.match(r"^ {0,3}##[ \t]+(.+?)\s*#*\s*$", line)
        if heading:
            headings.append(heading.group(1).strip())
    return headings


def relationship_panel_title(source_heading: str) -> str:
    """Map the canonical general heading to its compact panel title."""

    if source_heading.strip().casefold() in {"general", "general information"}:
        return "General"
    return source_heading.strip()


def relationship_panel_key(source_heading: str) -> str:
    """Derive a lowercase URL-compatible key from an H2 heading."""

    if relationship_panel_title(source_heading) == "General":
        return "general"
    key = re.sub(r"[^a-z0-9]+", "_", source_heading.casefold()).strip("_")
    return key


def normalize_ordered_list_markers(content: str) -> str:
    """Keep step numbers visible without sanitizer-sensitive list starts."""

    normalized: list[str] = []
    fence: tuple[str, int] | None = None
    for source_line in content.splitlines():
        line = source_line.expandtabs(4)
        if fence is not None:
            normalized.append(line)
            fence_char, fence_length = fence
            closing = line.lstrip(" ")
            closing_run = len(closing) - len(closing.lstrip(fence_char))
            if (
                closing_run >= fence_length
                and not closing[closing_run:].strip()
            ):
                fence = None
            continue

        fence_match = FENCE_LINE.fullmatch(line)
        if fence_match:
            fence_text = fence_match.group("fence")
            fence = (fence_text[0], len(fence_text))
            normalized.append(line)
            continue

        ordered_match = ORDERED_LIST_ITEM.match(line)
        if ordered_match:
            prefix_end = ordered_match.end()
            line = (
                ordered_match.group("indent")
                + f"- **Step {ordered_match.group('number')}:** "
                + line[prefix_end:]
            )
        normalized.append(line)
    return "\n".join(normalized)


def relationship_description_sections(content: str) -> list[dict[str, str]]:
    """Split and portably normalize a relationship description by H2."""

    sections: list[tuple[str, list[str]]] = []
    preamble: list[str] = []
    current_heading: str | None = None
    current_lines: list[str] = []
    fence: tuple[str, int, bool] | None = None

    def append_line(line: str) -> None:
        if current_heading is None:
            preamble.append(line)
        else:
            current_lines.append(line)

    def flush_section() -> None:
        nonlocal current_lines
        if current_heading is not None:
            sections.append((current_heading, current_lines))
            current_lines = []

    for source_line in content.splitlines():
        line = source_line.expandtabs(4)
        if fence is not None:
            fence_char, fence_length, skip = fence
            closing = line.lstrip(" ")
            closing_run = len(closing) - len(closing.lstrip(fence_char))
            is_closing = (
                closing_run >= fence_length
                and not closing[closing_run:].strip()
            )
            if not skip:
                append_line(line)
            if is_closing:
                fence = None
            continue

        fence_match = FENCE_LINE.fullmatch(line)
        if fence_match:
            fence_text = fence_match.group("fence")
            info = fence_match.group("info").strip()
            skip = bool(info and info.split(maxsplit=1)[0].casefold() == "mermaid")
            fence = (fence_text[0], len(fence_text), skip)
            if not skip:
                append_line(fence_match.group("indent") + fence_text)
            continue

        heading_match = re.match(r"^ {0,3}##[ \t]+(.+?)\s*#*\s*$", line)
        if heading_match:
            flush_section()
            current_heading = heading_match.group(1).strip()
            if not sections and preamble:
                current_lines.extend(preamble)
                preamble = []
            continue
        append_line(line)
    flush_section()

    result: list[dict[str, str]] = []
    seen_keys: set[str] = set()
    for source_heading, lines in sections:
        section_content = "\n".join(lines).strip()
        section_content = RELATIVE_MARKDOWN_LINK_CAPTURE.sub(
            lambda match: match.group("label"), section_content
        )
        section_content = re.sub(
            r"<([A-Za-z][A-Za-z0-9_-]*)>", r"[\1]", section_content
        )
        section_content = normalize_ordered_list_markers(section_content)
        section_key = relationship_panel_key(source_heading)
        if not section_key or section_key in seen_keys:
            raise PanelToolError(
                f"relationship H2 heading {source_heading!r} does not produce "
                "a unique URL-compatible section key"
            )
        seen_keys.add(section_key)
        result.append(
            {
                "source_heading": source_heading,
                "section_key": section_key,
                "title": relationship_panel_title(source_heading),
                "content": section_content,
            }
        )
    return result


def iter_entities(schema: dict[str, Any]) -> Iterable[tuple[EntitySpec, Any]]:
    for spec in ENTITY_SPECS:
        entries = schema.get(spec.schema_key)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            yield spec, entry


def get_extension_label(schema: dict[str, Any]) -> str:
    metadata = schema.get("schema")
    if isinstance(metadata, dict):
        for field in ("namespace", "display_name", "name"):
            value = metadata.get(field)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return "Extension"


def get_relationship_traversability(schema: dict[str, Any]) -> dict[str, bool]:
    result: dict[str, bool] = {}
    relationships = schema.get("relationship_kinds")
    if not isinstance(relationships, list):
        return result
    for relationship in relationships:
        if not isinstance(relationship, dict):
            continue
        name = relationship.get("name")
        if isinstance(name, str) and name:
            result[name] = relationship.get("is_traversable") is True
    return result


def schema_shape_errors(schema: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(schema, dict):
        return ["schema root must be a JSON object"]

    for spec in ENTITY_SPECS:
        entries = schema.get(spec.schema_key)
        if not isinstance(entries, list):
            errors.append(f"{spec.schema_key} must be an array")
            continue

        seen: set[str] = set()
        for index, entry in enumerate(entries):
            location = f"{spec.schema_key}[{index}]"
            if not isinstance(entry, dict):
                errors.append(f"{location} must be an object")
                continue
            kind = entry.get("name")
            if not isinstance(kind, str) or not kind.strip():
                errors.append(f"{location}.name must be a non-empty string")
                continue
            if kind in seen:
                errors.append(f"duplicate {spec.entity_type} kind: {kind}")
            seen.add(kind)
    return errors


def panel_errors(
    spec: EntitySpec,
    kind: str,
    info: Any,
    *,
    relationship_traversability: dict[str, bool],
    platform_label: str,
) -> tuple[list[str], list[str]]:
    prefix = f"{spec.entity_type} {kind}"
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(info, dict) or not info:
        return [f"{prefix}: info must be a non-empty object"], warnings

    required_sections = set(spec.required_sections)
    missing = sorted(required_sections - set(info))
    if missing:
        errors.append(f"{prefix}: missing required sections: {', '.join(missing)}")

    if "related_entities" in info:
        errors.append(
            f"{prefix}: panels must not contain related_entities"
        )

    positions: dict[int, str] = {}
    for section_key, section in info.items():
        section_prefix = f"{prefix} info.{section_key}"
        if not isinstance(section_key, str) or not URL_COMPATIBLE_KEY.fullmatch(
            section_key
        ):
            errors.append(
                f"{section_prefix}: section key is not URL-compatible"
            )
        if not isinstance(section, dict):
            errors.append(f"{section_prefix}: section must be an object")
            continue

        allowed_section_keys = {"title", "position", "markdown"}
        unsupported = sorted(set(section) - allowed_section_keys)
        if unsupported:
            errors.append(
                f"{section_prefix}: unsupported section fields: "
                f"{', '.join(unsupported)}"
            )

        title = section.get("title")
        if not isinstance(title, str) or not title.strip():
            errors.append(f"{section_prefix}.title must be a non-empty string")

        position = section.get("position")
        if (
            not isinstance(position, int)
            or isinstance(position, bool)
            or position < 1
        ):
            errors.append(
                f"{section_prefix}.position must be a positive integer"
            )
        elif position in positions:
            errors.append(
                f"{section_prefix}.position duplicates info."
                f"{positions[position]} at {position}"
            )
        else:
            positions[position] = section_key

        markdown = section.get("markdown")
        if not isinstance(markdown, dict):
            errors.append(f"{section_prefix}.markdown must be an object")
            continue
        unsupported_markdown = sorted(set(markdown) - {"content"})
        if unsupported_markdown:
            errors.append(
                f"{section_prefix}.markdown has unsupported fields: "
                f"{', '.join(unsupported_markdown)}"
            )
        content = markdown.get("content")
        if not isinstance(content, str) or not content.strip():
            errors.append(
                f"{section_prefix}.markdown.content must be a non-empty string"
            )
            continue
        if RELATIVE_MARKDOWN_LINK.search(content):
            errors.append(
                f"{section_prefix}: contains a repository-relative .md link"
            )
        if re.search(r"```\s*mermaid\b", content, re.IGNORECASE):
            errors.append(
                f"{section_prefix}: contains an unsupported Mermaid block"
            )
        for markdown_error in markdown_upload_errors(content):
            errors.append(f"{section_prefix}: {markdown_error}")
    if positions:
        ordered = sorted(positions)
        expected = list(range(1, len(positions) + 1))
        if ordered != expected:
            warnings.append(
                f"{prefix}: section positions are not contiguous from 1: {ordered}"
            )

    if spec.entity_type == "node":
        description = info.get("description")
        if isinstance(description, dict):
            if description.get("title") != "Description":
                errors.append(
                    f"{prefix} info.description.title must be 'Description'"
                )
            if description.get("position") != 1:
                errors.append(
                    f"{prefix} info.description.position must be 1"
                )
            markdown = description.get("markdown")
            content = (
                markdown.get("content") if isinstance(markdown, dict) else None
            )
            if isinstance(content, str) and not re.search(
                r"(?m)^##\s+\S", content
            ):
                errors.append(
                    f"{prefix} info.description: preserve description "
                    "sections as level-two Markdown headers"
                )

        for section_key, (title_prefix, _direction, position) in (
            SUMMARY_SECTION_SPECS.items()
        ):
            section = info.get(section_key)
            if not isinstance(section, dict):
                continue
            expected_title = (
                f"{title_prefix} Traversable {platform_label} Relationships"
            )
            if section.get("title") != expected_title:
                errors.append(
                    f"{prefix} info.{section_key}.title must be "
                    f"{expected_title!r}"
                )
            if section.get("position") != position:
                errors.append(
                    f"{prefix} info.{section_key}.position must be {position}"
                )
            markdown = section.get("markdown")
            content = (
                markdown.get("content") if isinstance(markdown, dict) else None
            )
            if not isinstance(content, str):
                continue
            if "{{" not in content or "}}" not in content:
                errors.append(
                    f"{prefix} info.{section_key}: node Cypher panels require "
                    "a guarded dynamic Explore link"
                )
                continue
            errors.extend(
                node_query_panel_errors(
                    prefix=prefix,
                    section_key=section_key,
                    node_kind=kind,
                    content=content,
                    relationship_kinds={
                        name
                        for name, traversable in (
                            relationship_traversability.items()
                        )
                        if traversable
                    },
                    platform_label=platform_label,
                    allow_no_relationship_kinds=True,
                )
            )

        reserved_node_sections = {"description", *SUMMARY_SECTION_SPECS}
        query_section_keys = [
            key for key in info if key not in reserved_node_sections
        ]
        if not query_section_keys:
            errors.append(
                f"{prefix}: add at least one node-specific Cypher accordion "
                "for a distinct investigation goal"
            )
        for section_key in query_section_keys:
            section = info.get(section_key)
            if not isinstance(section, dict):
                continue
            if section_key in {"overview", "relationships"}:
                errors.append(
                    f"{prefix} info.{section_key}: use a semantic key for a "
                    "node-specific investigation"
                )
            title = section.get("title")
            if isinstance(title, str) and (
                title.rstrip().endswith("?") or QUESTION_TITLE.match(title)
            ):
                errors.append(
                    f"{prefix} info.{section_key}: investigation titles must "
                    "be concise non-question labels"
                )
            position = section.get("position")
            if isinstance(position, int) and position <= 3:
                errors.append(
                    f"{prefix} info.{section_key}.position must follow "
                    "the three required leading node sections"
                )
            markdown = (
                section.get("markdown")
                if isinstance(section, dict)
                else None
            )
            content = (
                markdown.get("content") if isinstance(markdown, dict) else None
            )
            if not isinstance(content, str):
                continue
            if "{{" not in content or "}}" not in content:
                errors.append(
                    f"{prefix} info.{section_key}: node Cypher panels require "
                    "a guarded dynamic Explore link"
                )
                continue
            errors.extend(
                node_query_panel_errors(
                    prefix=prefix,
                    section_key=section_key,
                    node_kind=kind,
                    content=content,
                    relationship_kinds=set(relationship_traversability),
                    platform_label=platform_label,
                    allow_no_relationship_kinds=False,
                )
            )
    else:
        general = info.get("general")
        if isinstance(general, dict):
            if general.get("title") != "General":
                errors.append(
                    f"{prefix} info.general.title must be 'General'"
                )
            if general.get("position") != 1:
                errors.append(
                    f"{prefix} info.general.position must be 1"
                )
        for section_key, section in info.items():
            if not isinstance(section, dict):
                continue
            markdown = section.get("markdown")
            content = (
                markdown.get("content") if isinstance(markdown, dict) else None
            )
            if not isinstance(content, str):
                continue
            headings = markdown_h2_headings(content)
            if headings:
                errors.append(
                    f"{prefix} info.{section_key}: each level-two source "
                    "heading must be its own relationship panel; nested H2 "
                    f"headings remain: {headings}"
                )

    return errors, warnings


DYNAMIC_QUERY_ASSIGNMENT = re.compile(
    r"\$(?P<variable>query|cypherQuery)\s*:=\s*printf\s+"
    r'"(?P<query>(?:\\.|[^"\\\r\n])+)"\s+\$escapedObjectID'
)
TEMPLATE_ACTION = re.compile(r"{{-?.*?-?}}", re.DOTALL)
TEMPLATE_SUCCESS = re.compile(
    r'{{-?\s*if\s+ne\s+\$objectID\s+""\s*-?}}'
    r"(?P<body>.*?)"
    r"{{-?\s*else\s*-?}}",
    re.DOTALL,
)
EXPLORE_LINK = re.compile(
    r"\[(?P<label>[^\]\r\n]+)\]"
    r"\((?P<url>/ui/explore\?[^)\r\n]+)\)"
)


def extract_dynamic_query(content: str) -> tuple[str, str] | None:
    match = DYNAMIC_QUERY_ASSIGNMENT.search(content)
    if not match:
        return None
    return match.group("variable"), match.group("query")


def extract_query_relationship_kinds(query: str) -> set[str]:
    result: set[str] = set()
    for match in re.finditer(
        r"\[(?:[A-Za-z_][A-Za-z0-9_]*)?:"
        r"(?P<kinds>[A-Za-z0-9_|]+)",
        query,
    ):
        result.update(match.group("kinds").split("|"))
    return result


def extract_query_node_kinds(query: str) -> set[str]:
    return set(
        re.findall(
            r"\((?:[A-Za-z_][A-Za-z0-9_]*)?:"
            r"([A-Za-z][A-Za-z0-9_]*)",
            query,
        )
    )


def dynamic_query_text(query_source: str) -> str:
    return query_source.replace(r"\n", "\n")


def cypher_clause_line_errors(section_prefix: str, query: str) -> list[str]:
    errors: list[str] = []
    clause_pattern = re.compile(
        r"(?i)\b(?:OPTIONAL\s+MATCH|MATCH|WHERE|WITH|UNWIND|RETURN|"
        r"ORDER\s+BY|SKIP|LIMIT|UNION(?:\s+ALL)?)\b"
    )
    for match in clause_pattern.finditer(query):
        line_start = query.rfind("\n", 0, match.start()) + 1
        if query[line_start : match.start()].strip():
            errors.append(
                f"{section_prefix}: each Cypher operation must start on a "
                "new line in the printf query"
            )
            break
    return errors


def dynamic_link_errors(
    section_prefix: str,
    content: str,
    query: str,
    *,
    platform_label: str,
) -> list[str]:
    errors: list[str] = []
    success = TEMPLATE_SUCCESS.search(content)
    if not success:
        return [f"{section_prefix}: dynamic template has no guarded success body"]
    body = success.group("body")
    links = list(EXPLORE_LINK.finditer(body))
    if len(links) != 1:
        errors.append(
            f"{section_prefix}: dynamic success body must contain exactly "
            "one Explore link"
        )
        return errors
    visible = TEMPLATE_ACTION.sub("", body).strip()
    link_visible = TEMPLATE_ACTION.sub("", links[0].group(0))
    if visible != link_visible:
        errors.append(
            f"{section_prefix}: dynamic success body must contain no visible "
            "text except the Explore link"
        )
    label = links[0].group("label")
    identifiers = extract_query_relationship_kinds(query)
    identifiers.update(extract_query_node_kinds(query))
    identifiers.update(
        token for token in re.findall(r"\b[A-Za-z]+_[A-Za-z0-9_]+\b", query)
    )
    named_identifiers = sorted(
        identifier
        for identifier in identifiers
        if identifier != platform_label and identifier in label
    )
    if named_identifiers:
        errors.append(
            f"{section_prefix}: Explore link text must describe the result "
            "in ordinary words, not graph identifiers "
            f"{named_identifiers}"
        )
    return errors


def cypher_query_shape_errors(
    section_prefix: str,
    node_kind: str,
    query: str,
    *,
    objectid_placeholder: str,
    relationship_kinds: set[str],
    required_limit: int | None = None,
    allow_no_relationship_kinds: bool = False,
) -> list[str]:
    errors: list[str] = []
    query = dynamic_query_text(query)
    normalized = re.sub(r"\s+", " ", query.strip()).rstrip(";")
    selected_pattern = (
        rf"\((?:[A-Za-z_][A-Za-z0-9_]*)?:{re.escape(node_kind)}\s*"
        rf"\{{\s*objectid\s*:\s*'{re.escape(objectid_placeholder)}'\s*\}}\)"
    )
    if not re.search(selected_pattern, normalized):
        errors.append(
            f"{section_prefix}: Cypher must anchor the selected {node_kind} "
            f"by objectid {objectid_placeholder!r} and its exact node label"
        )
    if query.count(objectid_placeholder) != 1:
        errors.append(
            f"{section_prefix}: Cypher must use the selected objectid "
            "placeholder exactly once"
        )

    path_variables = set(
        re.findall(
            r"(?i)\b(?:OPTIONAL\s+)?MATCH\s+([A-Za-z_][A-Za-z0-9_]*)\s*=",
            normalized,
        )
    )
    if not path_variables:
        errors.append(
            f"{section_prefix}: Cypher must bind at least one path variable"
        )
    return_match = re.search(
        r"(?i)\bRETURN\s+(?P<values>.+?)\s+LIMIT\s+(?P<limit>[1-9][0-9]*)$",
        normalized,
    )
    if not return_match:
        errors.append(
            f"{section_prefix}: Cypher must end with RETURN and a positive LIMIT"
        )
    elif path_variables and not any(
        re.search(rf"\b{re.escape(variable)}\b", return_match.group("values"))
        for variable in path_variables
    ):
        errors.append(
            f"{section_prefix}: RETURN must include a bound path variable"
        )
    elif required_limit is not None and (
        int(return_match.group("limit")) != required_limit
    ):
        errors.append(
            f"{section_prefix}: Cypher LIMIT must be exactly {required_limit}"
        )

    query_relationship_kinds = extract_query_relationship_kinds(query)
    if not query_relationship_kinds and not allow_no_relationship_kinds:
        errors.append(
            f"{section_prefix}: Cypher must name at least one relationship kind"
        )
    for query_kind in sorted(query_relationship_kinds - relationship_kinds):
        errors.append(
            f"{section_prefix}: Cypher names unknown relationship {query_kind}"
        )
    return errors


def node_query_panel_errors(
    *,
    prefix: str,
    section_key: str,
    node_kind: str,
    content: str,
    relationship_kinds: set[str],
    platform_label: str,
    allow_no_relationship_kinds: bool = False,
) -> list[str]:
    section_prefix = f"{prefix} info.{section_key}"
    errors: list[str] = []

    required_tokens = (
        ".Properties.objectid",
        'default ""',
        "trim",
        "$escapedObjectID",
        'if ne $objectID ""',
        "/ui/explore",
        "exploreSearchTab=cypher",
        "searchType=cypher",
        "cypherSearch=",
        "$encodedQuery",
        "b64enc",
        "urlquery",
    )
    for token in required_tokens:
        if token not in content:
            errors.append(
                f"{section_prefix}: missing required dynamic-link token "
                f"{token!r}"
            )

    escape_pipeline = (
        f"$escapedObjectID := $objectID | {BACKSLASH_ESCAPE} | "
        f"{SINGLE_QUOTE_ESCAPE}"
    )
    if escape_pipeline not in content:
        errors.append(
            f"{section_prefix}: escape backslashes and single quotes in "
            "objectid, in that order, before interpolation"
        )
    if ".NodeID" in content or re.search(r"\{(?:id|node_id)\s*:", content):
        errors.append(
            f"{section_prefix}: do not use graph NodeID as an id, node_id, "
            "or objectid property value"
        )

    dynamic_query = extract_dynamic_query(content)
    if not dynamic_query:
        errors.append(
            f"{section_prefix}: construct the complete query with printf and "
            "$escapedObjectID"
        )
    else:
        query_variable, query = dynamic_query
        encoding_pattern = (
            rf"\$encodedQuery\s*:=\s*\${query_variable}\s*\|\s*"
            r"b64enc\s*\|\s*urlquery"
        )
        if not re.search(encoding_pattern, content):
            errors.append(
                f"{section_prefix}: encode the complete query variable with "
                "b64enc before urlquery"
            )
        errors.extend(
            cypher_query_shape_errors(
                section_prefix,
                node_kind,
                query,
                objectid_placeholder="%s",
                relationship_kinds=relationship_kinds,
                required_limit=500,
                allow_no_relationship_kinds=allow_no_relationship_kinds,
            )
        )
        query_text = dynamic_query_text(query)
        errors.extend(cypher_clause_line_errors(section_prefix, query_text))
        errors.extend(
            dynamic_link_errors(
                section_prefix,
                content,
                query_text,
                platform_label=platform_label,
            )
        )

    if not re.search(r"{{-?\s*else\s*-?}}", content):
        errors.append(
            f"{section_prefix}: include a useful missing-objectid fallback"
        )
    return errors


def query_panel_relationship_kinds(content: str) -> set[str]:
    dynamic_query = extract_dynamic_query(content)
    if dynamic_query:
        return extract_query_relationship_kinds(dynamic_query[1])
    return set()


def validate_schema(
    schema: Any,
    *,
    require_all_panels: bool,
) -> tuple[list[str], list[str], int]:
    errors = schema_shape_errors(schema)
    warnings: list[str] = []
    checked = 0
    if errors or not isinstance(schema, dict):
        return errors, warnings, checked

    relationship_traversability = get_relationship_traversability(schema)
    for spec, entry in iter_entities(schema):
        if not isinstance(entry, dict):
            continue
        kind = entry.get("name")
        if not isinstance(kind, str) or not kind:
            continue
        if "info" not in entry and not require_all_panels:
            continue
        checked += 1
        current_errors, current_warnings = panel_errors(
            spec,
            kind,
            entry.get("info"),
            relationship_traversability=relationship_traversability,
            platform_label=get_extension_label(schema),
        )
        errors.extend(current_errors)
        warnings.extend(current_warnings)

    return errors, warnings, checked


def resolve_schema_path(repo_root: Path, schema_arg: Path) -> Path:
    if schema_arg.is_absolute():
        return schema_arg
    return repo_root / schema_arg


def inventory_saved_searches(
    repo_root: Path,
    directory: Path,
    schema: dict[str, Any],
) -> list[dict[str, Any]]:
    search_root = directory if directory.is_absolute() else repo_root / directory
    if not search_root.is_dir():
        return []
    node_kinds = {
        entry["name"]
        for entry in schema.get("node_kinds", [])
        if isinstance(entry, dict) and isinstance(entry.get("name"), str)
    }
    relationship_kinds = set(get_relationship_traversability(schema))
    searches: list[dict[str, Any]] = []
    for search_path in sorted(search_root.rglob("*.json")):
        search = load_json(search_path)
        if not isinstance(search, dict):
            continue
        searchable = "\n".join(
            str(search.get(field, ""))
            for field in ("name", "description", "query")
        )
        try:
            display_path = str(search_path.relative_to(repo_root))
        except ValueError:
            display_path = str(search_path)
        searches.append(
            {
                "path": display_path,
                "name": search.get("name", search_path.stem),
                "referenced_node_kinds": sorted(
                    kind
                    for kind in node_kinds
                    if re.search(
                        rf"(?<![A-Za-z0-9_]){re.escape(kind)}"
                        r"(?![A-Za-z0-9_])",
                        searchable,
                    )
                ),
                "referenced_relationship_kinds": sorted(
                    kind
                    for kind in relationship_kinds
                    if re.search(
                        rf"(?<![A-Za-z0-9_]){re.escape(kind)}"
                        r"(?![A-Za-z0-9_])",
                        searchable,
                    )
                ),
            }
        )
    return searches


def inventory_command(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    schema_path = resolve_schema_path(repo_root, args.schema)
    schema = load_json(schema_path)
    errors = schema_shape_errors(schema)
    if errors:
        raise PanelToolError("; ".join(errors))

    description_roots = {
        "node": repo_root / args.node_descriptions_dir,
        "relationship": repo_root / args.relationship_descriptions_dir,
    }
    saved_searches = inventory_saved_searches(
        repo_root, args.saved_searches_dir, schema
    )
    entities: list[dict[str, Any]] = []
    for spec, entry in iter_entities(schema):
        kind = entry["name"]
        description_path = description_roots[spec.entity_type] / f"{kind}.md"
        try:
            display_path = str(description_path.relative_to(repo_root))
        except ValueError:
            display_path = str(description_path)
        entities.append(
            {
                "entity_type": spec.entity_type,
                "kind": kind,
                "schema_description": entry.get("description", ""),
                "description_path": display_path,
                "description_exists": description_path.is_file(),
                "direct_saved_searches": [
                    search["path"]
                    for search in saved_searches
                    if kind
                    in (
                        search["referenced_node_kinds"]
                        + search["referenced_relationship_kinds"]
                    )
                ],
                "has_info": isinstance(entry.get("info"), dict)
                and bool(entry["info"]),
            }
        )

    result = {
        "repo_root": str(repo_root),
        "schema": str(schema_path),
        "extension_label": get_extension_label(schema),
        "traversable_relationship_kinds": sorted(
            name
            for name, traversable in get_relationship_traversability(
                schema
            ).items()
            if traversable
        ),
        "counts": {
            "nodes": sum(e["entity_type"] == "node" for e in entities),
            "relationships": sum(
                e["entity_type"] == "relationship" for e in entities
            ),
            "missing_descriptions": sum(
                not e["description_exists"] for e in entities
            ),
            "existing_panels": sum(e["has_info"] for e in entities),
            "saved_searches": len(saved_searches),
        },
        "saved_searches": saved_searches,
        "entities": entities,
    }

    if args.output:
        write_json(args.output.resolve(), result)
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def read_fragments(directory: Path) -> list[tuple[Path, dict[str, Any]]]:
    if not directory.is_dir():
        raise PanelToolError(f"fragment directory not found: {directory}")
    fragment_paths = sorted(directory.rglob("*.json"))
    if not fragment_paths:
        raise PanelToolError(f"no JSON fragments found under {directory}")

    fragments: list[tuple[Path, dict[str, Any]]] = []
    for path in fragment_paths:
        value = load_json(path)
        if not isinstance(value, dict):
            raise PanelToolError(f"fragment must be a JSON object: {path}")
        fragments.append((path, value))
    return fragments


def fragment_errors(
    path: Path,
    fragment: dict[str, Any],
    *,
    relationship_traversability: dict[str, bool],
) -> list[str]:
    errors: list[str] = []
    entity_type = fragment.get("entity_type")
    kind = fragment.get("kind")
    if entity_type not in SPEC_BY_TYPE:
        errors.append(
            f"{path}: entity_type must be 'node' or 'relationship'"
        )
        return errors
    if not isinstance(kind, str) or not kind.strip():
        errors.append(f"{path}: kind must be a non-empty string")
        return errors
    for optional_list in ("assumptions", "evidence"):
        value = fragment.get(optional_list)
        if value is not None and (
            not isinstance(value, list)
            or not all(isinstance(item, str) for item in value)
        ):
            errors.append(f"{path}: {optional_list} must be an array of strings")
    platform = fragment.get("platform")
    if entity_type == "node" and (
        not isinstance(platform, str) or not platform.strip()
    ):
        errors.append(f"{path}: platform must be a non-empty string")
    platform_label = (
        platform.strip()
        if isinstance(platform, str) and platform.strip()
        else kind.split("_", 1)[0]
    )
    current_errors, _ = panel_errors(
        SPEC_BY_TYPE[entity_type],
        kind,
        fragment.get("info"),
        relationship_traversability=relationship_traversability,
        platform_label=platform_label,
    )
    errors.extend(f"{path}: {error}" for error in current_errors)

    if entity_type == "node":
        info = fragment.get("info")
        for legacy_key in (
            "inbound_traversable_kinds",
            "outbound_traversable_kinds",
        ):
            if legacy_key in fragment:
                errors.append(
                    f"{path}: replace legacy {legacy_key} metadata with "
                    "relationship_summary_panels metadata"
                )

        summary_panels = fragment.get("relationship_summary_panels")
        summary_metadata_keys: list[str] = []
        summary_directions: list[str] = []
        if not isinstance(summary_panels, list) or len(summary_panels) != 2:
            errors.append(
                f"{path}: relationship_summary_panels must contain exactly "
                "the inbound and outbound summary metadata entries"
            )
            summary_panels = []
        for index, metadata in enumerate(summary_panels):
            metadata_prefix = f"{path}: relationship_summary_panels[{index}]"
            if not isinstance(metadata, dict):
                errors.append(f"{metadata_prefix} must be an object")
                continue
            section_key = metadata.get("section_key")
            direction = metadata.get("direction")
            relationship_kinds = metadata.get("relationship_kinds")
            evidence = metadata.get("evidence")
            expected = SUMMARY_SECTION_SPECS.get(section_key)
            if expected is None:
                errors.append(
                    f"{metadata_prefix}.section_key must name one of the "
                    "two required relationship summaries"
                )
                continue
            summary_metadata_keys.append(section_key)
            summary_directions.append(direction)
            if direction != expected[1]:
                errors.append(
                    f"{metadata_prefix}.direction must be {expected[1]!r}"
                )
            if not isinstance(evidence, list) or not evidence or not all(
                isinstance(item, str) and item for item in evidence
            ):
                errors.append(
                    f"{metadata_prefix}.evidence must be a non-empty array "
                    "of repository paths"
                )
            if not isinstance(relationship_kinds, list) or not all(
                isinstance(item, str) and item for item in relationship_kinds
            ):
                errors.append(
                    f"{metadata_prefix}.relationship_kinds must be an array "
                    "of relationship-kind strings"
                )
                continue
            if len(relationship_kinds) != len(set(relationship_kinds)):
                errors.append(
                    f"{metadata_prefix}.relationship_kinds contains duplicates"
                )
            for relationship_kind in relationship_kinds:
                traversable = relationship_traversability.get(relationship_kind)
                if traversable is None:
                    errors.append(
                        f"{metadata_prefix} names unknown relationship kind "
                        f"{relationship_kind}"
                    )
                elif not traversable:
                    errors.append(
                        f"{metadata_prefix} includes non-traversable "
                        f"relationship kind {relationship_kind}"
                    )
            section = info.get(section_key) if isinstance(info, dict) else None
            markdown = (
                section.get("markdown") if isinstance(section, dict) else None
            )
            content = (
                markdown.get("content")
                if isinstance(markdown, dict)
                else None
            )
            if isinstance(content, str):
                expected_kinds = set(relationship_kinds)
                actual_query_kinds = query_panel_relationship_kinds(content)
                if actual_query_kinds != expected_kinds:
                    errors.append(
                        f"{path}: info.{section_key} Cypher kinds "
                        f"{sorted(actual_query_kinds)} do not exactly match "
                        f"relationship_summary_panels metadata "
                        f"{sorted(expected_kinds)}"
                    )
        if set(summary_metadata_keys) != set(SUMMARY_SECTION_SPECS):
            errors.append(
                f"{path}: relationship_summary_panels must cover exactly "
                f"{sorted(SUMMARY_SECTION_SPECS)}"
            )
        if set(summary_directions) != {"inbound", "outbound"}:
            errors.append(
                f"{path}: relationship_summary_panels must include inbound "
                "and outbound directions exactly once"
            )

        query_panels = fragment.get("query_panels")
        if not isinstance(query_panels, list) or not query_panels:
            errors.append(
                f"{path}: query_panels must be a non-empty array of "
                "node-specific query metadata"
            )
            return errors

        metadata_keys: list[str] = []
        for index, metadata in enumerate(query_panels):
            metadata_prefix = f"{path}: query_panels[{index}]"
            if not isinstance(metadata, dict):
                errors.append(f"{metadata_prefix} must be an object")
                continue
            section_key = metadata.get("section_key")
            purpose = metadata.get("purpose")
            relationship_kinds = metadata.get("relationship_kinds")
            evidence = metadata.get("evidence")
            if (
                not isinstance(section_key, str)
                or not URL_COMPATIBLE_KEY.fullmatch(section_key)
            ):
                errors.append(
                    f"{metadata_prefix}.section_key must be a lowercase "
                    "URL-compatible string"
                )
                continue
            metadata_keys.append(section_key)
            if not isinstance(purpose, str) or not purpose.strip():
                errors.append(
                    f"{metadata_prefix}.purpose must explain the "
                    "investigation goal"
                )
            if not isinstance(evidence, list) or not evidence or not all(
                isinstance(item, str) and item for item in evidence
            ):
                errors.append(
                    f"{metadata_prefix}.evidence must be a non-empty array "
                    "of repository paths"
                )
            if (
                not isinstance(relationship_kinds, list)
                or not relationship_kinds
                or not all(
                    isinstance(item, str) and item
                    for item in relationship_kinds
                )
            ):
                errors.append(
                    f"{metadata_prefix}.relationship_kinds must be a "
                    "non-empty array of relationship-kind strings"
                )
                continue
            if len(relationship_kinds) != len(set(relationship_kinds)):
                errors.append(
                    f"{metadata_prefix}.relationship_kinds contains duplicates"
                )
            for relationship_kind in relationship_kinds:
                if relationship_kind not in relationship_traversability:
                    errors.append(
                        f"{metadata_prefix} names unknown relationship "
                        f"kind {relationship_kind}"
                    )
            section = info.get(section_key) if isinstance(info, dict) else None
            markdown = (
                section.get("markdown") if isinstance(section, dict) else None
            )
            content = (
                markdown.get("content")
                if isinstance(markdown, dict)
                else None
            )
            if isinstance(content, str):
                actual_kinds = query_panel_relationship_kinds(content)
                expected_kinds = set(relationship_kinds)
                if actual_kinds != expected_kinds:
                    errors.append(
                        f"{path}: info.{section_key} Cypher kinds "
                        f"{sorted(actual_kinds)} do not exactly match "
                        f"query_panels metadata {sorted(expected_kinds)}"
                    )

        if len(metadata_keys) != len(set(metadata_keys)):
            errors.append(f"{path}: query_panels contains duplicate section keys")
        info_keys = (
            set(info) - {"description", *SUMMARY_SECTION_SPECS}
            if isinstance(info, dict)
            else set()
        )
        if set(metadata_keys) != info_keys:
            errors.append(
                f"{path}: query_panels section keys {sorted(set(metadata_keys))} "
                f"do not exactly match node query sections {sorted(info_keys)}"
            )
    else:
        if "query_panels" in fragment:
            errors.append(
                f"{path}: query_panels metadata is only valid for node fragments"
            )
        if "relationship_summary_panels" in fragment:
            errors.append(
                f"{path}: relationship_summary_panels metadata is only valid "
                "for node fragments"
            )

        description_sections = fragment.get("description_sections")
        if not isinstance(description_sections, list) or not description_sections:
            errors.append(
                f"{path}: description_sections must be a non-empty array "
                "covering every relationship source H2 section"
            )
            description_sections = []

        metadata_keys: list[str] = []
        source_headings: list[str] = []
        info = fragment.get("info")
        for index, metadata in enumerate(description_sections):
            metadata_prefix = f"{path}: description_sections[{index}]"
            if not isinstance(metadata, dict):
                errors.append(f"{metadata_prefix} must be an object")
                continue
            unsupported = sorted(
                set(metadata) - {"source_heading", "section_key"}
            )
            if unsupported:
                errors.append(
                    f"{metadata_prefix} has unsupported fields: "
                    f"{', '.join(unsupported)}"
                )
            source_heading = metadata.get("source_heading")
            section_key = metadata.get("section_key")
            if not isinstance(source_heading, str) or not source_heading.strip():
                errors.append(
                    f"{metadata_prefix}.source_heading must be non-empty"
                )
                continue
            source_heading = source_heading.strip()
            source_headings.append(source_heading)
            if (
                not isinstance(section_key, str)
                or not URL_COMPATIBLE_KEY.fullmatch(section_key)
            ):
                errors.append(
                    f"{metadata_prefix}.section_key must be a lowercase "
                    "URL-compatible string"
                )
                continue
            metadata_keys.append(section_key)
            section = info.get(section_key) if isinstance(info, dict) else None
            if not isinstance(section, dict):
                errors.append(
                    f"{metadata_prefix}.section_key does not name an info panel"
                )
                continue
            expected_title = relationship_panel_title(source_heading)
            if section.get("title") != expected_title:
                errors.append(
                    f"{path}: info.{section_key}.title must be "
                    f"{expected_title!r} for source heading {source_heading!r}"
                )
            if section.get("position") != index + 1:
                errors.append(
                    f"{path}: info.{section_key}.position must be {index + 1} "
                    "to preserve relationship source H2 order"
                )

        if metadata_keys and metadata_keys[0] != "general":
            errors.append(
                f"{path}: the first relationship description section must "
                "map to info.general"
            )
        if len(metadata_keys) != len(set(metadata_keys)):
            errors.append(f"{path}: description_sections has duplicate section keys")
        if len(source_headings) != len(set(source_headings)):
            errors.append(f"{path}: description_sections has duplicate H2 headings")
        info_keys = list(info) if isinstance(info, dict) else []
        if metadata_keys != info_keys:
            errors.append(
                f"{path}: description_sections keys {metadata_keys} do not "
                f"exactly match relationship info panels in source order "
                f"{info_keys}"
            )
    return errors


def assemble_command(args: argparse.Namespace) -> int:
    schema_path = args.schema.resolve()
    output_path = args.output.resolve()
    if output_path == schema_path:
        raise PanelToolError(
            "refusing to overwrite the source schema; choose a candidate output path"
        )

    schema = load_json(schema_path)
    shape_errors = schema_shape_errors(schema)
    if shape_errors:
        raise PanelToolError("; ".join(shape_errors))
    assert isinstance(schema, dict)
    relationship_traversability = get_relationship_traversability(schema)

    schema_entities: dict[tuple[str, str], dict[str, Any]] = {}
    for spec, entry in iter_entities(schema):
        if isinstance(entry, dict) and isinstance(entry.get("name"), str):
            schema_entities[(spec.entity_type, entry["name"])] = entry

    fragments = read_fragments(args.fragments.resolve())
    fragment_map: dict[tuple[str, str], dict[str, Any]] = {}
    all_fragment_errors: list[str] = []
    for path, fragment in fragments:
        all_fragment_errors.extend(
            fragment_errors(
                path,
                fragment,
                relationship_traversability=relationship_traversability,
            )
        )
        entity_type = fragment.get("entity_type")
        kind = fragment.get("kind")
        if entity_type in SPEC_BY_TYPE and isinstance(kind, str):
            key = (entity_type, kind)
            if key in fragment_map:
                all_fragment_errors.append(
                    f"duplicate fragment for {entity_type} {kind}: {path}"
                )
            elif key not in schema_entities:
                all_fragment_errors.append(
                    f"{path}: no matching {entity_type} kind in schema: {kind}"
                )
            else:
                fragment_map[key] = fragment

    if all_fragment_errors:
        raise PanelToolError("\n".join(all_fragment_errors))

    missing = sorted(set(schema_entities) - set(fragment_map))
    if missing and not args.allow_partial:
        formatted = ", ".join(f"{entity_type} {kind}" for entity_type, kind in missing)
        raise PanelToolError(f"missing fragments for: {formatted}")

    candidate = copy.deepcopy(schema)
    candidate_entities: dict[tuple[str, str], dict[str, Any]] = {}
    for spec, entry in iter_entities(candidate):
        if isinstance(entry, dict) and isinstance(entry.get("name"), str):
            candidate_entities[(spec.entity_type, entry["name"])] = entry
    for key, fragment in fragment_map.items():
        candidate_entities[key]["info"] = copy.deepcopy(fragment["info"])

    errors, warnings, checked = validate_schema(
        candidate,
        require_all_panels=not args.allow_partial,
    )
    if errors:
        raise PanelToolError("candidate validation failed:\n" + "\n".join(errors))
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)

    write_json(output_path, candidate)
    print(
        f"assembled {len(fragment_map)} fragments into {output_path}; "
        f"validated {checked} panel definitions"
    )
    return 0


def validate_command(args: argparse.Namespace) -> int:
    schema_path = args.schema.resolve()
    schema = load_json(schema_path)
    errors, warnings, checked = validate_schema(
        schema,
        require_all_panels=not args.allow_missing_panels,
    )
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        print(
            f"validation failed with {len(errors)} error(s) and "
            f"{len(warnings)} warning(s)",
            file=sys.stderr,
        )
        return 1
    print(
        f"validated {checked} panel definitions in {schema_path} "
        f"with {len(warnings)} warning(s)"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inventory, assemble, and structurally validate OpenGraph "
            "entity-panel definitions."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory = subparsers.add_parser(
        "inventory", help="list node and relationship kinds"
    )
    inventory.add_argument(
        "--repo-root", type=Path, default=Path("."), help="extension repo root"
    )
    inventory.add_argument(
        "--schema",
        type=Path,
        default=Path("extension/schema.json"),
        help="schema path, relative to --repo-root unless absolute",
    )
    inventory.add_argument(
        "--node-descriptions-dir",
        type=Path,
        default=Path("descriptions/nodes"),
    )
    inventory.add_argument(
        "--relationship-descriptions-dir",
        type=Path,
        default=Path("descriptions/edges"),
    )
    inventory.add_argument(
        "--saved-searches-dir",
        type=Path,
        default=Path("extension/saved_searches"),
    )
    inventory.add_argument(
        "--output", type=Path, help="optional JSON output path"
    )
    inventory.set_defaults(handler=inventory_command)

    assemble = subparsers.add_parser(
        "assemble", help="merge isolated fragments into a candidate schema"
    )
    assemble.add_argument("--schema", type=Path, required=True)
    assemble.add_argument("--fragments", type=Path, required=True)
    assemble.add_argument("--output", type=Path, required=True)
    assemble.add_argument(
        "--allow-partial",
        action="store_true",
        help="permit a deliberately scoped subset of fragment kinds",
    )
    assemble.set_defaults(handler=assemble_command)

    validate = subparsers.add_parser(
        "validate",
        help="validate panel structure and node-query invariants",
    )
    validate.add_argument("--schema", type=Path, required=True)
    validate.add_argument(
        "--allow-missing-panels",
        action="store_true",
        help="validate existing info objects without requiring every kind",
    )
    validate.set_defaults(handler=validate_command)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.handler(args)
    except PanelToolError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
