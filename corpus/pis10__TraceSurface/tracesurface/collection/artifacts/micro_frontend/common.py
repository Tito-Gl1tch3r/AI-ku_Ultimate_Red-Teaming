from __future__ import annotations

import re

from tree_sitter import Node

from tracesurface.jsast import node_text


def _is_valid_app_name(val: str) -> bool:
    if len(val) <= 2:
        return False

    if val.isdigit():
        return False

    if re.fullmatch(r"[a-f0-9]{6,}", val):
        return False

    if "." in val:
        return False
    return True


_STRICT_IDENT_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{2,}$")


def is_strict_identifier(val: str) -> bool:
    return bool(_STRICT_IDENT_PATTERN.match(val))


_FUNCTION_NODE_TYPES = frozenset(
    {
        "function_declaration",
        "function_expression",
        "arrow_function",
        "method_definition",
        "generator_function",
        "generator_function_declaration",
    }
)


def _find_enclosing_function(node: Node) -> Node | None:
    cur = node.parent
    while cur:
        if cur.type in _FUNCTION_NODE_TYPES:
            return cur
        cur = cur.parent
    return None


def _get_function_params(func_node: Node) -> list[str]:
    params_node = func_node.child_by_field_name("parameters")
    if not params_node:
        for c in func_node.children:
            if c.type == "identifier":
                return [node_text(c)]
        return []
    out: list[str] = []
    for child in params_node.named_children:
        if child.type == "identifier":
            out.append(node_text(child))

        elif child.type in ("assignment_pattern", "required_parameter"):
            left = child.child_by_field_name("left") or (
                child.named_children[0] if child.named_children else None
            )
            if left and left.type == "identifier":
                out.append(node_text(left))
    return out


def _is_src_assignment(node: Node) -> bool:
    if node.type != "assignment_expression":
        return False
    left = node.child_by_field_name("left")
    if not left or left.type != "member_expression":
        return False
    prop = left.child_by_field_name("property")
    return bool(prop and node_text(prop) == "src")
