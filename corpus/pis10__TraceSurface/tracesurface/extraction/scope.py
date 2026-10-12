from __future__ import annotations

from dataclasses import dataclass, field

from tree_sitter import Node

from tracesurface.jsast import node_text

_FUNCTION_NODES = frozenset(
    {
        "function_declaration",
        "function_expression",
        "arrow_function",
        "method_definition",
        "generator_function",
        "generator_function_declaration",
        "function",
    }
)
_BLOCK_NODES = frozenset(
    {
        "statement_block",
        "for_statement",
        "for_in_statement",
        "catch_clause",
        "class_body",
        "switch_body",
    }
)


@dataclass(slots=True)
class Scope:
    node_id: int
    kind: str
    parent: Scope | None
    decls: dict[str, Node | None] = field(default_factory=dict)
    multi: set[str] = field(default_factory=set)
    assigns: set[str] = field(default_factory=set)

    def add_decl(self, name: str, value: Node | None) -> None:
        if name in self.multi:
            return
        if name in self.decls:
            existing = self.decls[name]

            if existing is None and value is None:
                return

            if existing is None or value is None or existing.id != value.id:
                del self.decls[name]
                self.multi.add(name)
            return
        self.decls[name] = value


@dataclass(frozen=True, slots=True)
class Binding:
    name: str
    decl_value: Node | None
    scope: Scope


def _register_params(fn_node: Node, scope: Scope) -> None:
    params = fn_node.child_by_field_name("parameters")
    targets: list[Node] = []
    if params is not None:
        targets = list(params.named_children)
    else:
        single = fn_node.child_by_field_name("parameter")
        if single is not None:
            targets = [single]

    for p in targets:
        if p.type == "identifier":
            scope.add_decl(node_text(p), None)


def _register_fn_name(fn_node: Node, enclosing_fn: Scope) -> None:
    if fn_node.type not in ("function_declaration", "generator_function_declaration"):
        return
    name = fn_node.child_by_field_name("name")
    if name is not None and name.type == "identifier":
        enclosing_fn.add_decl(node_text(name), fn_node)


def _record_declarator(node: Node, cur_fn: Scope, cur_block: Scope) -> None:
    parent = node.parent
    is_var = parent is not None and parent.type == "variable_declaration"
    owner = cur_fn if is_var else cur_block
    name_node = node.child_by_field_name("name")
    value = node.child_by_field_name("value")
    if name_node is None:
        return

    if name_node.type == "identifier":
        owner.add_decl(node_text(name_node), value)
    else:
        for ident in _pattern_identifiers(name_node):
            owner.add_decl(ident, None)


def _pattern_identifiers(node: Node) -> list[str]:
    out: list[str] = []
    for child in node.named_children:
        if child.type == "shorthand_property_identifier_pattern":
            out.append(node_text(child))
        elif child.type == "identifier":
            out.append(node_text(child))

        elif child.type in (
            "pair_pattern",
            "object_pattern",
            "array_pattern",
            "rest_pattern",
        ):
            out.extend(_pattern_identifiers(child))
    return out


class ScopeIndex:
    def __init__(self, scopes_by_id: dict[int, Scope]) -> None:
        self._by_id = scopes_by_id

    def scope_of(self, node: Node) -> Scope | None:
        n: Node | None = node
        while n is not None:
            sc = self._by_id.get(n.id)
            if sc is not None:
                return sc
            n = n.parent
        return None

    def _fn_owner(self, scope: Scope) -> Scope:
        sc = scope
        while sc.kind == "block" and sc.parent is not None:
            sc = sc.parent
        return sc

    def resolve_binding(self, use_node: Node) -> Binding | None:
        if use_node.type != "identifier":
            return None
        name = node_text(use_node)
        if not name:
            return None

        sc = self.scope_of(use_node)
        while sc is not None:
            if name in sc.multi:
                return Binding(name, None, sc)
            if name in sc.decls:
                fn = self._fn_owner(sc)
                if name in fn.assigns:
                    return Binding(name, None, sc)
                return Binding(name, sc.decls[name], sc)
            sc = sc.parent
        return None


def build_scope_index(root: Node) -> ScopeIndex:
    module_scope = Scope(node_id=root.id, kind="module", parent=None)
    by_id: dict[int, Scope] = {root.id: module_scope}
    stack: list[tuple[Node, Scope, Scope]] = [(root, module_scope, module_scope)]
    while stack:
        node, cur_fn, cur_block = stack.pop()
        t = node.type
        new_fn, new_block = cur_fn, cur_block

        if t in _FUNCTION_NODES:
            sc = by_id.get(node.id)
            if sc is None:
                sc = Scope(node_id=node.id, kind="function", parent=cur_block)
                by_id[node.id] = sc
                _register_fn_name(node, cur_fn)
                _register_params(node, sc)
            new_fn = sc
            new_block = sc

        elif t in _BLOCK_NODES:
            sc = by_id.get(node.id)
            if sc is None:
                sc = Scope(node_id=node.id, kind="block", parent=cur_block)
                by_id[node.id] = sc
            new_block = sc
        elif t == "variable_declarator":
            _record_declarator(node, cur_fn, cur_block)

        elif t == "assignment_expression":
            left = node.child_by_field_name("left")
            if left is not None and left.type == "identifier":
                cur_fn.assigns.add(node_text(left))

        children = node.children
        for i in range(len(children) - 1, -1, -1):
            stack.append((children[i], new_fn, new_block))

    return ScopeIndex(by_id)
