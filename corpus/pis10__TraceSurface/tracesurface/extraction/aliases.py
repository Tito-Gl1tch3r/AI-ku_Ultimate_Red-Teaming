from __future__ import annotations

from tree_sitter import Node

from tracesurface.extraction.resolve import (
    ResolveCtx,
    _single_return_expr,
    client_ref_for,
)
from tracesurface.jsast import node_text, walk_pre_iter
from tracesurface.models import ClientAliasFact, ClientRef


def module_export_ref(require_id: str, export_name: str = "") -> ClientRef:
    return ClientRef(
        module_id=f"<mod:{require_id}>",
        scope_id=0,
        decl_node_id=0,
        symbol_name=export_name or "<default>",
    )


def _require_id_of(value_node: Node | None) -> str | None:
    if value_node is None or value_node.type != "call_expression":
        return None
    from tracesurface.extraction.resolve import _is_require_call

    if not _is_require_call(value_node):
        return None
    args = value_node.child_by_field_name("arguments")
    if args is None or not args.named_children:
        return None

    arg = args.named_children[0]
    if arg.type == "string":
        from tracesurface.jsast import extract_string

        s = extract_string(arg)
        return s if s else None
    if arg.type == "number":
        return f"#{node_text(arg)}"
    return None


def _factory_callee(value: Node | None, ctx: ResolveCtx) -> Node | None:
    if value is None or value.type != "call_expression":
        return None
    func = value.child_by_field_name("function")
    if func is None or func.type != "identifier":
        return None

    b = ctx.scope_index.resolve_binding(func)
    if b is None or b.decl_value is None:
        return None
    return func if _single_return_expr(b.decl_value) is not None else None


def build_aliases(
    root: Node,
    ctx: ResolveCtx,
) -> list[ClientAliasFact]:
    edges: list[ClientAliasFact] = []

    if not ctx.is_webpack:
        for local, (req_id, orig) in ctx.esm_imports.items():
            edges.append(
                ClientAliasFact(
                    left_ref=ClientRef(
                        module_id=ctx.js_url,
                        scope_id=0,
                        decl_node_id=0,
                        symbol_name=local,
                    ),
                    right_ref=module_export_ref(req_id, orig),
                    edge_kind="import",
                )
            )

    for node in walk_pre_iter(root):
        if node.type == "variable_declarator":
            name = node.child_by_field_name("name")
            value = node.child_by_field_name("value")
            if name is None or name.type != "identifier" or value is None:
                continue

            req_id = _require_id_of(value)
            if req_id is not None:
                edges.append(
                    ClientAliasFact(
                        left_ref=client_ref_for(name, ctx),
                        right_ref=module_export_ref(req_id),
                        edge_kind="require",
                    )
                )

            elif value.type == "identifier":
                edges.append(
                    ClientAliasFact(
                        left_ref=client_ref_for(name, ctx),
                        right_ref=client_ref_for(value, ctx),
                        edge_kind="assign",
                    )
                )

            elif (fac := _factory_callee(value, ctx)) is not None:
                edges.append(
                    ClientAliasFact(
                        left_ref=client_ref_for(name, ctx),
                        right_ref=client_ref_for(fac, ctx),
                        edge_kind="wrapper_return",
                    )
                )

        elif node.type == "assignment_expression":
            left = node.child_by_field_name("left")
            right = node.child_by_field_name("right")
            if left is None or left.type != "identifier":
                continue
            if right is not None and right.type == "identifier":
                edges.append(
                    ClientAliasFact(
                        left_ref=client_ref_for(left, ctx),
                        right_ref=client_ref_for(right, ctx),
                        edge_kind="assign",
                    )
                )
            elif (fac := _factory_callee(right, ctx)) is not None:
                edges.append(
                    ClientAliasFact(
                        left_ref=client_ref_for(left, ctx),
                        right_ref=client_ref_for(fac, ctx),
                        edge_kind="wrapper_return",
                    )
                )

    return edges
