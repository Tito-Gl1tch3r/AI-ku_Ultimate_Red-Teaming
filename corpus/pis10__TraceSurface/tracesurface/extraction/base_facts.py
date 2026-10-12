from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from tree_sitter import Node

from tracesurface.extraction.resolve import (
    ResolveCtx,
    _single_return_expr,
    client_ref_for,
    render_prod_url,
    resolve_template,
)
from tracesurface.jsast import get_object_props, node_text, walk_pre_iter
from tracesurface.models import (
    BaseFact,
    BaseSourceKind,
    ClientRef,
    Lit,
    SourceLocation,
)
from tracesurface.urls import combine_urls

_BASE_KEY_CLIENT = {
    "baseURL": "axios",
    "baseUrl": "axios",
    "prefixUrl": "ky",
    "prefix": "umi",
}
_FACTORY_PROPS = {"create", "extend"}
_FACTORY_FUNCS = {"createAlova"}
_FACTORY_FN_NODES = frozenset(
    {
        "function_declaration",
        "function_expression",
        "arrow_function",
    }
)


def _base_string(node: Node | None, ctx: ResolveCtx) -> str | None:
    if node is None:
        return None
    rendered = render_prod_url(resolve_template(node, ctx))
    return rendered or None


def _instance_decl_node(call_node: Node) -> Node | None:
    parent = call_node.parent
    while parent is not None and parent.type in (
        "member_expression",
        "call_expression",
        "parenthesized_expression",
        "sequence_expression",
    ):
        parent = parent.parent

    if parent is not None and parent.type == "variable_declarator":
        name = parent.child_by_field_name("name")
        return name if name is not None and name.type == "identifier" else None

    if parent is not None and parent.type == "assignment_expression":
        left = parent.child_by_field_name("left")
        return left if left is not None and left.type == "identifier" else None
    return None


def _defaults_instance_node(left: Node) -> Node | None:
    obj = left.child_by_field_name("object")
    if obj is None or obj.type != "member_expression":
        return None
    prop = obj.child_by_field_name("property")
    if prop is None or node_text(prop) != "defaults":
        return None
    inst = obj.child_by_field_name("object")
    return inst if inst is not None and inst.type == "identifier" else None


def _wrapper_base(obj: Node, ctx: ResolveCtx) -> str | None:
    props = get_object_props(obj)
    if "urlPrefix" not in props and "apiUrl" not in props:
        return None
    prefix = _base_string(props.get("urlPrefix"), ctx)
    api = _base_string(props.get("apiUrl"), ctx)

    if prefix:
        norm = "/" + prefix.lstrip("/")
        return combine_urls(api, norm) if api else norm

    if api and (api.startswith("http") or api.startswith("/")):
        return api
    return None


def _resolve_base_in_config(cfg: Node, ctx: ResolveCtx) -> tuple[str, str] | None:
    props = get_object_props(cfg)
    for key, client in _BASE_KEY_CLIENT.items():
        if key in props:
            val = _base_string(props[key], ctx)
            if val:
                return val, client
    return None


def _base_suffix(node: Node | None, ctx: ResolveCtx) -> str | None:
    if node is None:
        return None

    inner = _single_return_expr(node)
    if inner is not None:
        node = inner
    tmpl = resolve_template(node, ctx)
    full = render_prod_url(tmpl)

    if full is not None:
        return full or None

    tail: list[str] = []
    for seg in reversed(tmpl.segments):
        if isinstance(seg, Lit):
            tail.append(seg.value)
        else:
            break
    suffix = "".join(reversed(tail))

    return "/" + suffix.lstrip("/") if suffix.strip("/") else None


def _factory_config_base(ret: Node, ctx: ResolveCtx) -> str | None:
    obj: Node | None = None

    if ret.type == "call_expression":
        args = ret.child_by_field_name("arguments")
        if args is not None:
            obj = next((a for a in args.named_children if a.type == "object"), None)
    elif ret.type == "object":
        obj = ret
    if obj is None:
        return None

    props = get_object_props(obj)
    for key in _BASE_KEY_CLIENT:
        if key in props:
            base = _base_suffix(props[key], ctx)
            if base:
                return base
    return None


def _factory_function_base(fn_node: Node, ctx: ResolveCtx) -> str | None:
    ret = _single_return_expr(fn_node)
    return _factory_config_base(ret, ctx) if ret is not None else None


def _factory_identity_node(fn_node: Node) -> Node | None:
    if fn_node.type == "function_declaration":
        name = fn_node.child_by_field_name("name")
        return name if name is not None and name.type == "identifier" else None

    parent = fn_node.parent
    if parent is not None and parent.type == "variable_declarator":
        value = parent.child_by_field_name("value")
        if value is not None and value.id == fn_node.id:
            name = parent.child_by_field_name("name")
            return name if name is not None and name.type == "identifier" else None
    return None


def _module_id_for(node: Node, js_url: str, ctx: ResolveCtx) -> str:
    if not ctx.is_webpack:
        return js_url
    from tracesurface.extraction.caller import find_module_id_webpack

    return find_module_id_webpack(node) or js_url


def _require_id_for(module_id: str, js_url: str, ctx: ResolveCtx) -> str:
    return module_id if ctx.is_webpack else js_url.rsplit("/", 1)[-1]


def _interceptors_receiver_node(obj: Node | None) -> Node | None:
    if obj is None or obj.type != "member_expression":
        return None
    prop = obj.child_by_field_name("property")
    if prop is None or node_text(prop) != "request":
        return None
    mid = obj.child_by_field_name("object")
    if mid is None or mid.type != "member_expression":
        return None
    mid_prop = mid.child_by_field_name("property")
    if mid_prop is None or node_text(mid_prop) != "interceptors":
        return None
    inst = mid.child_by_field_name("object")
    return inst if inst is not None and inst.type == "identifier" else None


def _interceptor_instance_node(node: Node) -> Node | None:
    parent = node.parent
    depth = 0
    while parent is not None and depth < 80:
        if parent.type == "call_expression":
            func = parent.child_by_field_name("function")

            if func is not None and func.type == "member_expression":
                prop = func.child_by_field_name("property")
                if prop is not None and node_text(prop) == "use":
                    inst = _interceptors_receiver_node(
                        func.child_by_field_name("object")
                    )
                    if inst is not None:
                        return inst
        parent = parent.parent
        depth += 1
    return None


def _url_concat_prefix(rhs: Node | None, ctx: ResolveCtx) -> str | None:
    if rhs is None or rhs.type != "binary_expression":
        return None
    op = rhs.child_by_field_name("operator")
    if op is None or node_text(op) != "+":
        return None

    right = rhs.child_by_field_name("right")
    if right is None or right.type != "member_expression":
        return None
    prop = right.child_by_field_name("property")
    if prop is None or node_text(prop) != "url":
        return None

    prefix = _base_string(rhs.child_by_field_name("left"), ctx)
    return prefix if prefix and prefix.strip("/") else None


@dataclass(frozen=True, slots=True)
class BaseFinding:
    value: str
    inst_node: Node | None
    kind: BaseSourceKind
    client: str


BaseStrategy = Callable[[Node, ResolveCtx], "BaseFinding | None"]


def _try_factory_return(node: Node, ctx: ResolveCtx) -> BaseFinding | None:
    if node.type not in _FACTORY_FN_NODES:
        return None
    base = _factory_function_base(node, ctx)
    if not base:
        return None
    return BaseFinding(base, _factory_identity_node(node), "static_config", "axios")


def _try_vben_wrapper(node: Node, ctx: ResolveCtx) -> BaseFinding | None:
    if node.type != "object":
        return None
    base = _wrapper_base(node, ctx)
    if not base:
        return None
    return BaseFinding(base, None, "inline_host", "wrapper")


def _try_sdk_factory(node: Node, ctx: ResolveCtx) -> BaseFinding | None:
    if node.type != "call_expression":
        return None
    func = node.child_by_field_name("function")
    if func is None:
        return None

    is_factory = (
        func.type == "member_expression"
        and (prop := func.child_by_field_name("property")) is not None
        and node_text(prop) in _FACTORY_PROPS
    ) or (func.type == "identifier" and node_text(func) in _FACTORY_FUNCS)
    if not is_factory:
        return None

    args = node.child_by_field_name("arguments")
    cfg = (
        next((a for a in args.named_children if a.type == "object"), None)
        if args
        else None
    )
    resolved = _resolve_base_in_config(cfg, ctx) if cfg is not None else None
    if not resolved:
        return None
    base, client = resolved
    return BaseFinding(base, _instance_decl_node(node), "static_config", client)


def _try_axios_defaults(node: Node, ctx: ResolveCtx) -> BaseFinding | None:
    if node.type != "assignment_expression":
        return None
    left = node.child_by_field_name("left")
    if left is None or left.type != "member_expression":
        return None
    prop = left.child_by_field_name("property")
    if prop is None or node_text(prop) not in ("baseURL", "baseUrl"):
        return None
    base = _base_string(node.child_by_field_name("right"), ctx)
    if not base:
        return None

    inst = _defaults_instance_node(left) or _interceptor_instance_node(node)
    return BaseFinding(base, inst, "sdk_init", "axios")


def _try_interceptor_url(node: Node, ctx: ResolveCtx) -> BaseFinding | None:
    if node.type != "assignment_expression":
        return None
    left = node.child_by_field_name("left")
    if left is None or left.type != "member_expression":
        return None
    prop = left.child_by_field_name("property")
    if prop is None or node_text(prop) != "url":
        return None
    base = _url_concat_prefix(node.child_by_field_name("right"), ctx)
    if not base:
        return None
    return BaseFinding(base, _interceptor_instance_node(node), "interceptor", "axios")


BASE_STRATEGIES: tuple[tuple[str, BaseStrategy], ...] = (
    ("factory-return", _try_factory_return),
    ("vben-wrapper", _try_vben_wrapper),
    ("sdk-factory", _try_sdk_factory),
    ("axios-defaults", _try_axios_defaults),
    ("interceptor-url", _try_interceptor_url),
)


def extract_base_facts(root: Node, js_url: str, ctx: ResolveCtx) -> list[BaseFact]:
    facts: list[BaseFact] = []
    counter = 0

    for node in walk_pre_iter(root):
        for _name, strategy in BASE_STRATEGIES:
            finding = strategy(node, ctx)
            if finding is None:
                continue

            inst_node = finding.inst_node
            module_id = (
                _module_id_for(node, js_url, ctx) if inst_node is not None else ""
            )
            local_var = node_text(inst_node) if inst_node is not None else ""
            refs: tuple[ClientRef, ...] = (
                (client_ref_for(inst_node, ctx),) if inst_node is not None else ()
            )
            facts.append(
                BaseFact(
                    base_id=f"{js_url}#base{counter}",
                    base_value=Lit(finding.value),
                    client_refs=refs,
                    source_kind=finding.kind,
                    location=SourceLocation(
                        url=js_url,
                        line=node.start_point[0],
                        col_start=node.start_point[1],
                        col_end=node.end_point[1],
                    ),
                    client=finding.client,
                    require_id=_require_id_for(module_id, js_url, ctx)
                    if local_var
                    else "",
                    module_id=module_id,
                    local_var=local_var,
                    js_url=js_url,
                )
            )
            counter += 1
            break

    return facts
