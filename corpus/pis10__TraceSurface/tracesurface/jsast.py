from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from typing import TypeVar, cast

import tree_sitter_javascript as tsjs
from tree_sitter import Language, Node, Parser

JS_LANGUAGE = Language(tsjs.language())
T = TypeVar("T")


class JsParser:
    def __init__(self) -> None:
        self._parser = Parser(JS_LANGUAGE)

    def normalize(self, source: str) -> str:
        return source.replace("\r\n", "\n").replace("\r", "\n")

    def parse(self, source: str):
        normalized = self.normalize(source)
        return self._parser.parse(normalized.encode("utf-8"))


def parse_js(source: str):
    return JsParser().parse(source)


def node_text(node: Node | None) -> str:
    return node.text.decode("utf-8") if node and node.text else ""


def extract_string(node: Node | None) -> str | None:
    if not node or node.type != "string":
        return None
    raw = node_text(node)

    if len(raw) >= 2 and raw[0] in ('"', "'"):
        return raw[1:-1]
    return raw


def get_object_props(node: Node | None) -> dict[str, Node]:
    if not node or node.type != "object":
        return {}
    props: dict[str, Node] = {}

    for child in node.named_children:
        if child.type == "pair":
            key_node = child.child_by_field_name("key")
            val_node = child.child_by_field_name("value")
            if key_node and val_node:
                key = extract_string(key_node) or node_text(key_node)
                props[key] = val_node
    return props


def extract_literal_value(node: Node | None):
    if not node:
        return "?"
    if node.type == "string":
        return extract_string(node) or "?"
    if node.type == "number":
        text = node_text(node)
        try:
            return int(text) if "." not in text else float(text)
        except ValueError:
            return "?"
    if node.type == "true":
        return True
    if node.type == "false":
        return False
    if node.type == "null":
        return None
    if node.type == "object":
        result = {}
        for child in node.named_children:
            if child.type == "pair":
                key_node = child.child_by_field_name("key")
                val_node = child.child_by_field_name("value")
                if key_node:
                    key = extract_string(key_node) or node_text(key_node)
                    result[key] = extract_literal_value(val_node)
        return result
    if node.type == "array":
        return [extract_literal_value(c) for c in node.named_children]

    return "?"


def walk_pre_iter(root: T) -> Iterator[T]:
    stack = [root]
    while stack:
        node = stack.pop()
        yield node

        children = _children_of(node)
        for index in range(len(children) - 1, -1, -1):
            stack.append(children[index])


def walk_first_match(root: T, predicate: Callable[[T], bool]) -> T | None:
    for node in walk_pre_iter(root):
        if predicate(node):
            return node
    return None


def walk_pre_iter_json(root: object) -> Iterator[object]:
    stack = [root]
    while stack:
        node = stack.pop()
        yield node

        if isinstance(node, dict):
            values = list(node.values())
            for index in range(len(values) - 1, -1, -1):
                stack.append(values[index])
        elif isinstance(node, list):
            for index in range(len(node) - 1, -1, -1):
                stack.append(node[index])


def _children_of(node: T) -> list[T]:
    children = getattr(node, "children", None)
    if children is None:
        return []
    return list(cast(Iterable[T], children))
