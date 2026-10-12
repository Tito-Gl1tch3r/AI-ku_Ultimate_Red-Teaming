from __future__ import annotations

from dataclasses import dataclass, field

from tree_sitter import Node

from tracesurface.extraction.scope import ScopeIndex
from tracesurface.jsast import extract_string, get_object_props, node_text
from tracesurface.models import (
    ClientRef,
    DynamicHole,
    EnvChoice,
    Lit,
    RefHole,
    ResolvedValue,
    RouteChoice,
    UrlTemplate,
)

_MAX_DEPTH = 6
_MAX_EXPAND = 12

_ENV_SOURCE_NAMES = frozenset(
    {
        "env",
        "NODE_ENV",
        "APP_ENV",
        "MODE",
        "BUILD_ENV",
        "RUNTIME_ENV",
        "DEPLOY_ENV",
        "VITE_MODE",
    }
)
_PROD_TOKENS = frozenset(
    {
        "prod",
        "production",
        "online",
        "release",
        "master",
        "prd",
        "live",
        "default",
    }
)
_NONPROD_TOKENS = frozenset(
    {
        "pre",
        "prepub",
        "prepublish",
        "gray",
        "daily",
        "dev",
        "development",
        "test",
        "sit",
        "uat",
        "local",
        "localhost",
        "staging",
        "stage",
        "qa",
        "beta",
    }
)
_ENV_VOCAB = _PROD_TOKENS | _NONPROD_TOKENS


@dataclass(slots=True)
class ResolveCtx:
    scope_index: ScopeIndex
    is_webpack: bool = False
    js_url: str = ""
    module_requires: dict[str, dict[str, str]] = field(default_factory=dict)
    esm_imports: dict[str, tuple[str, str]] = field(default_factory=dict)


def resolve_template(node: Node | None, ctx: ResolveCtx) -> UrlTemplate:
    if node is None:
        return UrlTemplate((DynamicHole("none"),))
    return UrlTemplate(tuple(_segments(node, ctx, 0, set())))


def _segments(
    node: Node, ctx: ResolveCtx, depth: int, seen: set[int]
) -> list[ResolvedValue]:
    if depth > _MAX_DEPTH or node.id in seen:
        return [DynamicHole("depth")]
    seen = seen | {node.id}
    t = node.type

    if t == "string":
        s = extract_string(node)
        return [Lit(s)] if s is not None else [DynamicHole("string")]
    if t == "template_string":
        return _template_segments(node, ctx, depth, seen)
    if t == "parenthesized_expression":
        inner = node.named_children[0] if node.named_children else None
        return _segments(inner, ctx, depth, seen) if inner else [DynamicHole("paren")]
    if t == "sequence_expression":
        last = node.named_children[-1] if node.named_children else None
        return _segments(last, ctx, depth, seen) if last else [DynamicHole("seq")]
    if t == "binary_expression":
        op = node.child_by_field_name("operator")
        ops = node_text(op)

        if ops == "+":
            left = node.child_by_field_name("left")
            right = node.child_by_field_name("right")
            out: list[ResolvedValue] = []
            if left:
                out += _segments(left, ctx, depth, seen)
            if right:
                out += _segments(right, ctx, depth, seen)
            return out or [DynamicHole("binary")]

        if ops in ("||", "??"):
            return [_resolve_logical(node, ctx, depth, seen)]

        return [DynamicHole("binary")]
    if t == "ternary_expression":
        return [_resolve_choice(node, ctx, depth, seen)]
    if t == "call_expression":
        return _call_segments(node, ctx, depth, seen)
    if t == "subscript_expression":
        return [_resolve_index(node, ctx, depth, seen)]
    if t == "member_expression":
        return [_resolve_member(node, ctx, depth, seen)]
    if t == "identifier":
        return _identifier_segments(node, ctx, depth, seen)
    return [DynamicHole(t)]


def _template_segments(
    node: Node, ctx: ResolveCtx, depth: int, seen: set[int]
) -> list[ResolvedValue]:
    out: list[ResolvedValue] = []

    for child in node.children:
        if child.type in ("string_fragment", "template_content"):
            out.append(Lit(node_text(child)))
        elif child.type == "template_substitution":
            inner = child.named_children[0] if child.named_children else None
            if inner is not None:
                out += _segments(inner, ctx, depth, seen)
            else:
                out.append(DynamicHole("subst"))
        elif child.type == "`":
            continue
    return out or [DynamicHole("template")]


def _call_segments(
    node: Node, ctx: ResolveCtx, depth: int, seen: set[int]
) -> list[ResolvedValue]:
    func = node.child_by_field_name("function")

    if func is not None and func.type == "member_expression":
        prop = func.child_by_field_name("property")
        if prop is not None and node_text(prop) == "concat":
            obj = func.child_by_field_name("object")
            out: list[ResolvedValue] = []
            if obj is not None:
                out += _segments(obj, ctx, depth, seen)
            args = node.child_by_field_name("arguments")
            if args is not None:
                for a in args.named_children:
                    out += _segments(a, ctx, depth, seen)
            return out or [DynamicHole("concat")]
    return [_resolve_call(node, ctx, depth, seen)]


def _identifier_segments(
    node: Node, ctx: ResolveCtx, depth: int, seen: set[int]
) -> list[ResolvedValue]:
    name = node_text(node)

    ref = _alias_ref(node, name, ctx)
    if ref is not None:
        return [RefHole(client_ref=ref, display=name)]

    b = ctx.scope_index.resolve_binding(node)
    if b is None or b.decl_value is None:
        return [DynamicHole(f"ident:{name}")]
    return _segments(b.decl_value, ctx, depth, seen)


def _is_require_call(node: Node | None) -> bool:
    if node is None or node.type != "call_expression":
        return False
    callee = node.child_by_field_name("function")
    if callee is None or callee.type != "identifier":
        return False
    args = node.child_by_field_name("arguments")
    if args is None or len(args.named_children) != 1:
        return False
    return args.named_children[0].type in ("number", "string")


def _value_of(node: Node, ctx: ResolveCtx, depth: int, seen: set[int]) -> ResolvedValue:
    segs = _segments(node, ctx, depth, seen)
    if len(segs) == 1:
        return segs[0]
    if segs and all(isinstance(s, Lit) for s in segs):
        return Lit("".join(s.value for s in segs if isinstance(s, Lit)))
    return DynamicHole("multiseg")


def _resolve_choice(
    node: Node, ctx: ResolveCtx, depth: int, seen: set[int]
) -> ResolvedValue:
    cond = node.child_by_field_name("condition")
    cons = node.child_by_field_name("consequence")
    alt = node.child_by_field_name("alternative")
    if cons is None or alt is None:
        return DynamicHole("ternary")
    cons_v = _value_of(cons, ctx, depth, seen)
    alt_v = _value_of(alt, ctx, depth, seen)

    verdict = _classify_condition(cond)
    if verdict is None:
        return RouteChoice((cons_v, alt_v))

    prod_is_consequence = verdict
    if prod_is_consequence:
        return EnvChoice(prod=cons_v, alternates=(alt_v,))
    return EnvChoice(prod=alt_v, alternates=(cons_v,))


def _classify_condition(cond: Node | None) -> bool | None:
    if cond is None or cond.type != "binary_expression":
        return None
    op = node_text(cond.child_by_field_name("operator"))
    if op not in ("===", "==", "!==", "!="):
        return None
    left = cond.child_by_field_name("left")
    right = cond.child_by_field_name("right")

    token = _env_token(left, right)
    if token is None:
        return None
    if token not in _ENV_VOCAB:
        return None

    is_prod_token = token in _PROD_TOKENS
    op_is_eq = op in ("===", "==")
    return is_prod_token == op_is_eq


def _env_token(left: Node | None, right: Node | None) -> str | None:
    for src, other in ((left, right), (right, left)):
        if _is_env_source(src) and other is not None and other.type == "string":
            return extract_string(other)
    return None


def _is_env_source(node: Node | None) -> bool:
    if node is None or node.type != "member_expression":
        return False
    prop = node.child_by_field_name("property")
    return prop is not None and node_text(prop) in _ENV_SOURCE_NAMES


def _resolve_logical(
    node: Node, ctx: ResolveCtx, depth: int, seen: set[int]
) -> ResolvedValue:
    left = node.child_by_field_name("left")
    right = node.child_by_field_name("right")
    lv = _value_of(left, ctx, depth, seen) if left else DynamicHole("logical")

    if isinstance(lv, Lit) and lv.value:
        return lv
    return _value_of(right, ctx, depth, seen) if right else lv


def _resolve_index(
    node: Node, ctx: ResolveCtx, depth: int, seen: set[int]
) -> ResolvedValue:
    obj = node.child_by_field_name("object")
    idx = node.child_by_field_name("index")

    props = _object_props_of(obj, ctx)
    if props is None:
        return DynamicHole("index")

    if _is_env_source(idx):
        prod_v: ResolvedValue | None = None
        alts: list[ResolvedValue] = []
        for k, vnode in props.items():
            v = _value_of(vnode, ctx, depth, seen)
            if k in _PROD_TOKENS and prod_v is None:
                prod_v = v
            else:
                alts.append(v)
        if prod_v is not None:
            return EnvChoice(prod=prod_v, alternates=tuple(alts))

        return (
            RouteChoice(tuple(_value_of(v, ctx, depth, seen) for v in props.values()))
            if props
            else DynamicHole("index")
        )

    key_v = _value_of(idx, ctx, depth, seen) if idx else DynamicHole("key")
    if isinstance(key_v, Lit) and key_v.value in props:
        return _value_of(props[key_v.value], ctx, depth, seen)

    if 0 < len(props) <= _MAX_EXPAND:
        return RouteChoice(
            tuple(_value_of(v, ctx, depth, seen) for v in props.values())
        )
    return DynamicHole("index")


def _object_props_of(node: Node | None, ctx: ResolveCtx) -> dict[str, Node] | None:
    if node is None:
        return None

    if node.type == "object":
        return get_object_props(node)

    if node.type == "identifier":
        b = ctx.scope_index.resolve_binding(node)
        if b is not None and b.decl_value is not None and b.decl_value.type == "object":
            return get_object_props(b.decl_value)
    return None


def _resolve_member(
    node: Node, ctx: ResolveCtx, depth: int, seen: set[int]
) -> ResolvedValue:
    obj = node.child_by_field_name("object")
    prop = node.child_by_field_name("property")
    if prop is None:
        return DynamicHole("member")
    pname = node_text(prop)

    props = _object_props_of(obj, ctx)
    if props is not None and pname in props:
        return _value_of(props[pname], ctx, depth, seen)

    if obj is not None and obj.type == "identifier":
        ref = _alias_ref(obj, node_text(obj), ctx)
        if ref is not None:
            return RefHole(client_ref=ref, display=f"{node_text(obj)}.{pname}")
    return DynamicHole("member")


def _resolve_call(
    node: Node, ctx: ResolveCtx, depth: int, seen: set[int]
) -> ResolvedValue:
    func = node.child_by_field_name("function")
    if func is None:
        return DynamicHole("call")

    inner = func
    while inner.type in ("parenthesized_expression", "sequence_expression"):
        kids = inner.named_children
        inner = kids[-1] if kids else inner
        if inner is func:
            break
    if inner.type == "identifier":
        ref = _alias_ref(inner, node_text(inner), ctx)
        if ref is not None:
            return RefHole(client_ref=ref, display=f"{node_text(inner)}()")

        b = ctx.scope_index.resolve_binding(inner)
        if b is not None and b.decl_value is not None:
            ret = _single_return_expr(b.decl_value)
            if ret is not None:
                return _value_of(ret, ctx, depth + 1, seen)
        return DynamicHole(f"call:{node_text(inner)}")
    if inner.type == "member_expression":
        v = _resolve_member(inner, ctx, depth, seen)
        return v
    return DynamicHole("call")


def _single_return_expr(fn_node: Node) -> Node | None:
    if fn_node.type not in (
        "function_declaration",
        "function_expression",
        "arrow_function",
        "generator_function",
        "generator_function_declaration",
    ):
        return None
    body = fn_node.child_by_field_name("body")
    if body is None:
        return None

    if body.type != "statement_block":
        return body

    stmts = [c for c in body.named_children if c.type not in ("comment",)]
    if len(stmts) == 1 and stmts[0].type == "return_statement":
        ret = stmts[0]
        return ret.named_children[0] if ret.named_children else None
    return None


def _alias_ref(use_node: Node, name: str, ctx: ResolveCtx) -> ClientRef | None:
    b = ctx.scope_index.resolve_binding(use_node)

    if b is not None and b.decl_value is not None:
        if ctx.is_webpack and _is_require_call(b.decl_value):
            return _client_ref_at(use_node, name, ctx)
        return None

    if not ctx.is_webpack and name in ctx.esm_imports:
        return _client_ref_at(use_node, name, ctx)
    return None


def _module_id_of(node: Node, ctx: ResolveCtx) -> str:
    if not ctx.is_webpack:
        return ctx.js_url
    from tracesurface.extraction.caller import find_module_id_webpack

    return find_module_id_webpack(node) or ctx.js_url


def _client_ref_at(use_node: Node, name: str, ctx: ResolveCtx) -> ClientRef:
    module_id = _module_id_of(use_node, ctx)
    b = ctx.scope_index.resolve_binding(use_node)
    scope_id = b.scope.node_id if b is not None else 0
    decl_id = b.decl_value.id if (b is not None and b.decl_value is not None) else 0
    return ClientRef(
        module_id=module_id, scope_id=scope_id, decl_node_id=decl_id, symbol_name=name
    )


def client_ref_for(use_node: Node, ctx: ResolveCtx) -> ClientRef:
    return _client_ref_at(use_node, node_text(use_node), ctx)


def _receiver_identifier(call_node: Node) -> Node | None:
    if call_node.type != "call_expression":
        return None
    func = call_node.child_by_field_name("function")
    if func is None:
        return None

    if func.type == "identifier":
        return func

    if func.type == "member_expression":
        root = func.child_by_field_name("object")
        while root is not None and root.type == "member_expression":
            root = root.child_by_field_name("object")
        if root is not None and root.type == "identifier":
            return root
    return None


def request_client_ref(call_node: Node, ctx: ResolveCtx) -> ClientRef | None:
    recv = _receiver_identifier(call_node)
    if recv is None:
        return None
    return client_ref_for(recv, ctx)


EXPR = "EXPR"


def _prod_str(v: ResolvedValue) -> str | None:
    if isinstance(v, Lit):
        return v.value
    if isinstance(v, EnvChoice):
        return _prod_str(v.prod)
    return None


def render_prod_url(template: UrlTemplate) -> str | None:
    parts: list[str] = []
    for seg in template.segments:
        if isinstance(seg, Lit):
            parts.append(seg.value)
        elif isinstance(seg, EnvChoice):
            r = _prod_str(seg.prod)
            if r is None:
                return None
            parts.append(r)
        else:
            return None
    return "".join(parts)


def template_to_expr_path(template: UrlTemplate) -> str:
    parts: list[str] = []
    for seg in template.segments:
        s = _prod_str(seg)
        parts.append(s if s is not None else EXPR)
    out = "".join(parts)

    while EXPR + EXPR in out:
        out = out.replace(EXPR + EXPR, EXPR)
    return out
