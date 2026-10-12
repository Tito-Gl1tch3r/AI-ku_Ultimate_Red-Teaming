from __future__ import annotations

import re
from dataclasses import dataclass
from importlib.resources import files

import yaml


@dataclass(frozen=True, slots=True)
class Rule:
    rule_id: str
    rule_group: str
    sensitive: bool
    pattern: re.Pattern[str]
    s_pattern: re.Pattern[str] | None = None


def _load_rules() -> list[Rule]:
    raw = files(__package__).joinpath("rules.yml").read_text(encoding="utf-8")
    doc = yaml.safe_load(raw) or {}
    rules: list[Rule] = []
    for entry in doc.get("rules", []):
        if entry.get("loaded", True) is False:
            continue
        name = (entry.get("name") or "").strip()
        f_regex = entry.get("f_regex")

        if not name or not f_regex:
            continue

        pattern = re.compile(f_regex)
        s_regex = entry.get("s_regex")
        s_pattern = re.compile(s_regex) if s_regex else None
        rules.append(
            Rule(
                rule_id=name,
                rule_group=(entry.get("group") or "Other").strip(),
                sensitive=bool(entry.get("sensitive")),
                pattern=pattern,
                s_pattern=s_pattern,
            )
        )
    return rules


RULES: list[Rule] = _load_rules()
