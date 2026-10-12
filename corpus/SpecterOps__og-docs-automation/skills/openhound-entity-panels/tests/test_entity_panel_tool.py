# ruff: noqa: E501

from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "entity_panel_tool.py"
SPEC = importlib.util.spec_from_file_location("entity_panel_tool", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


def panel(title: str, position: int, content: str) -> dict[str, object]:
    return {
        "title": title,
        "position": position,
        "markdown": {"content": content},
    }


def valid_schema() -> dict[str, object]:
    return {
        "schema": {"namespace": "Example"},
        "node_kinds": [
            {
                "name": "Example_Role",
                "info": {
                    "description": panel(
                        "Description",
                        1,
                        "## Overview\n\nAn example role.\n\n"
                        "## Relationships\n\nRoles connect principals "
                        "to resources.",
                    ),
                    "inbound_traversable_relationships": panel(
                        "Inbound Traversable Example Relationships",
                        2,
                        dynamic_template(
                            "MATCH p = (principal)-[:Example_HasRole]->"
                            "(selected:Example_Role {objectid: '%s'})\n"
                            "RETURN p\n"
                            "LIMIT 500",
                            "View direct inbound relationships in Explore",
                        ),
                    ),
                    "outbound_traversable_relationships": panel(
                        "Outbound Traversable Example Relationships",
                        3,
                        dynamic_template(
                            "MATCH p = (selected:Example_Role "
                            "{objectid: '%s'})"
                            "-[:Example_AllowsAccess]->(resource)\n"
                            "RETURN p\n"
                            "LIMIT 500",
                            "View direct outbound relationships in Explore",
                        ),
                    ),
                    "who_has_this_role": panel(
                        "Role Assignments and Grant Sources",
                        4,
                        dynamic_template(
                            "MATCH p = (principal)-[:Example_HasRole]->"
                            "(selected:Example_Role {objectid: '%s'})\n"
                            "RETURN p\n"
                            "LIMIT 500",
                            "View principals that receive this permission set "
                            "in Explore",
                        ),
                    ),
                    "what_can_this_role_access": panel(
                        "Accessible Resources",
                        5,
                        dynamic_template(
                            "MATCH p = (selected:Example_Role "
                            "{objectid: '%s'})"
                            "-[:Example_AllowsAccess]->(resource)\n"
                            "RETURN p\n"
                            "LIMIT 500",
                            "View resources reachable through this permission "
                            "set in Explore",
                        ),
                    ),
                },
            }
        ],
        "relationship_kinds": [
            {
                "name": "Example_HasRole",
                "is_traversable": True,
                "info": {
                    "general": panel(
                        "General", 1, "A principal holds a role."
                    )
                },
            },
            {
                "name": "Example_AllowsAccess",
                "is_traversable": True,
                "info": {
                    "general": panel(
                        "General", 1, "A role grants access to a resource."
                    )
                },
            },
            {
                "name": "Example_Observed",
                "is_traversable": False,
                "info": {
                    "general": panel(
                        "General", 1, "A descriptive relationship."
                    )
                },
            },
        ],
    }


def dynamic_template(query: str, link_text: str) -> str:
    query_source = query.replace("\n", r"\n")
    return "\n".join(
        (
            '{{ $objectID := .Properties.objectid | default "" | trim }}',
            r'''{{ $escapedObjectID := $objectID | replace "\\" "\\\\" | replace "'" "\\'" }}''',
            '{{ if ne $objectID "" }}',
            f'{{{{ $query := printf "{query_source}" $escapedObjectID }}}}',
            "{{ $encodedQuery := $query | b64enc | urlquery }}",
            f"[{link_text}](/ui/explore?exploreSearchTab=cypher&"
            "searchType=cypher&cypherSearch={{ $encodedQuery }})",
            "{{ else }}",
            "Explore navigation is unavailable because this object has no "
            "stable identifier.",
            "{{ end }}",
        )
    )


def dynamic_role_template() -> str:
    return dynamic_template(
        "MATCH p = (principal)-[:Example_HasRole]->"
        "(selected:Example_Role {objectid: '%s'})\n"
        "RETURN p\n"
        "LIMIT 500",
        "View principals that receive this permission set in Explore",
    )


def valid_node_fragment() -> dict[str, object]:
    schema = valid_schema()
    return {
        "entity_type": "node",
        "kind": "Example_Role",
        "platform": "Example",
        "info": copy.deepcopy(schema["node_kinds"][0]["info"]),
        "relationship_summary_panels": [
            {
                "section_key": "inbound_traversable_relationships",
                "direction": "inbound",
                "relationship_kinds": ["Example_HasRole"],
                "evidence": [
                    "extension/schema.json",
                    "src/example/models/roles.py",
                ],
            },
            {
                "section_key": "outbound_traversable_relationships",
                "direction": "outbound",
                "relationship_kinds": ["Example_AllowsAccess"],
                "evidence": [
                    "extension/schema.json",
                    "src/example/models/roles.py",
                ],
            },
        ],
        "query_panels": [
            {
                "section_key": "who_has_this_role",
                "purpose": "Show principals that hold the selected role.",
                "relationship_kinds": ["Example_HasRole"],
                "evidence": [
                    "descriptions/nodes/Example_Role.md",
                    "extension/saved_searches/principals-with-roles.json",
                ],
            },
            {
                "section_key": "what_can_this_role_access",
                "purpose": "Show resources reachable through the selected role.",
                "relationship_kinds": ["Example_AllowsAccess"],
                "evidence": [
                    "descriptions/nodes/Example_Role.md",
                    "extension/saved_searches/role-access.json",
                ],
            },
        ],
        "assumptions": [],
        "evidence": ["extension/schema.json"],
    }


def valid_relationship_fragment() -> dict[str, object]:
    return {
        "entity_type": "relationship",
        "kind": "Example_HasRole",
        "info": {
            "general": panel("General", 1, "A principal holds this role."),
            "abuse_info": panel(
                "Abuse Info",
                2,
                "The assignment conveys the role's access.\n\n"
                "### Reverting Abuse Actions\n\nRestore the assignment.",
            ),
            "opsec_considerations": panel(
                "Opsec Considerations", 3, "Review assignment changes."
            ),
            "references": panel(
                "References",
                4,
                "- [Role reference](https://example.com/roles)",
            ),
        },
        "description_sections": [
            {
                "source_heading": "General Information",
                "section_key": "general",
            },
            {"source_heading": "Abuse Info", "section_key": "abuse_info"},
            {
                "source_heading": "Opsec Considerations",
                "section_key": "opsec_considerations",
            },
            {"source_heading": "References", "section_key": "references"},
        ],
        "assumptions": [],
        "evidence": ["descriptions/edges/Example_HasRole.md"],
    }


class MarkdownUploadErrorsTests(unittest.TestCase):
    def messages(self, content: str) -> str:
        return "\n".join(TOOL.markdown_upload_errors(content))

    def test_accepts_portable_markdown_and_inline_code(self) -> None:
        content = """Use `<account-name>` as the placeholder.

1. First step
2. Second step

| Name | Value |
| --- | --- |
| one | two |

```
example-cli inspect
```
"""
        self.assertEqual(TOOL.markdown_upload_errors(content), [])

    def test_rejects_raw_html_and_tag_shaped_placeholder(self) -> None:
        messages = self.messages(
            "<!-- internal note -->\nUse <account-name> as the placeholder."
        )
        self.assertIn("raw HTML", messages)
        self.assertEqual(messages.count("raw HTML"), 2)

    def test_rejects_code_fence_info_string(self) -> None:
        messages = self.messages("```shell\nexample-cli inspect\n```")
        self.assertIn("language class", messages)

    def test_rejects_task_list_and_aligned_table(self) -> None:
        content = """- [ ] Review the entity

| Name | Value |
| :--- | ---: |
| one | two |
"""
        messages = self.messages(content)
        self.assertIn("task-list", messages)
        self.assertIn("aligned GFM table", messages)

    def test_rejects_ordered_list_restarted_after_top_level_fence(self) -> None:
        content = """1. First step

```
example-cli inspect
```

2. Second step
"""
        self.assertIn("ordered-list block begins at 2", self.messages(content))

    def test_accepts_fence_nested_inside_ordered_list(self) -> None:
        content = """1. First step

   ```
   example-cli inspect
   ```

2. Second step
"""
        self.assertEqual(TOOL.markdown_upload_errors(content), [])

    def test_rejects_unsafe_markdown_link_scheme(self) -> None:
        messages = self.messages("[Run this](javascript:alert(1))")
        self.assertIn("unsafe URI scheme", messages)

    def test_splits_relationship_h2_and_preserves_deeper_headings(self) -> None:
        source = """## General Information

General prose with <object-id>.

```mermaid
graph LR
```

## Abuse Info

Use the relationship.

### Reverting Abuse Actions

Restore it with [Related edge](Example_Other.md).

```bash
example-cli restore
```

2. Verify the restoration.
"""
        sections = TOOL.relationship_description_sections(source)
        self.assertEqual(
            [section["section_key"] for section in sections],
            ["general", "abuse_info"],
        )
        self.assertEqual(sections[0]["title"], "General")
        self.assertIn("[object-id]", sections[0]["content"])
        self.assertNotIn("mermaid", sections[0]["content"])
        self.assertIn("### Reverting Abuse Actions", sections[1]["content"])
        self.assertIn("Related edge", sections[1]["content"])
        self.assertNotIn("Example_Other.md", sections[1]["content"])
        self.assertIn("\n```\nexample-cli restore", sections[1]["content"])
        self.assertIn(
            "- **Step 2:** Verify the restoration.", sections[1]["content"]
        )
        for section in sections:
            self.assertEqual(
                TOOL.markdown_upload_errors(section["content"]), []
            )


class PanelContractTests(unittest.TestCase):
    def validate(
        self,
        schema: dict[str, object],
    ) -> list[str]:
        errors, _warnings, _checked = TOOL.validate_schema(
            schema,
            require_all_panels=True,
        )
        return errors

    def fragment_messages(
        self,
        fragment: dict[str, object],
    ) -> str:
        return "\n".join(
            TOOL.fragment_errors(
                Path("fragment.json"),
                fragment,
                relationship_traversability={
                    "Example_HasRole": True,
                    "Example_AllowsAccess": True,
                    "Example_Observed": False,
                },
            )
        )

    def test_accepts_node_specific_dynamic_query_panels(self) -> None:
        self.assertEqual(self.validate(valid_schema()), [])

    def test_requires_consolidated_description_headers(self) -> None:
        schema = valid_schema()
        description = schema["node_kinds"][0]["info"]["description"]
        description["markdown"]["content"] = "An unstructured description."
        self.assertIn(
            "level-two Markdown headers", "\n".join(self.validate(schema))
        )

    def test_requires_at_least_one_node_specific_query_panel(self) -> None:
        schema = valid_schema()
        info = schema["node_kinds"][0]["info"]
        schema["node_kinds"][0]["info"] = {
            key: info[key]
            for key in (
                "description",
                "inbound_traversable_relationships",
                "outbound_traversable_relationships",
            )
        }
        self.assertIn(
            "at least one node-specific Cypher accordion",
            "\n".join(self.validate(schema)),
        )

    def test_rejects_question_investigation_title(self) -> None:
        schema = valid_schema()
        section = schema["node_kinds"][0]["info"]["who_has_this_role"]
        section["title"] = "Who Has This Role?"
        self.assertIn(
            "concise non-question labels",
            "\n".join(self.validate(schema)),
        )

    def test_requires_exact_relationship_summary_title(self) -> None:
        schema = valid_schema()
        info = schema["node_kinds"][0]["info"]
        info["inbound_traversable_relationships"]["title"] = (
            "Inbound Relationships"
        )
        self.assertIn(
            "Inbound Traversable Example Relationships",
            "\n".join(self.validate(schema)),
        )

    def test_requires_both_relationship_summaries(self) -> None:
        schema = valid_schema()
        del schema["node_kinds"][0]["info"][
            "outbound_traversable_relationships"
        ]
        self.assertIn(
            "missing required sections: outbound_traversable_relationships",
            "\n".join(self.validate(schema)),
        )

    def test_rejects_prose_only_empty_relationship_summary(self) -> None:
        fragment = valid_node_fragment()
        fragment["info"]["inbound_traversable_relationships"]["markdown"][
            "content"
        ] = (
            "The current extension schema defines no direct inbound "
            "traversable Example relationships for this node kind."
        )
        fragment["relationship_summary_panels"][0]["relationship_kinds"] = []
        self.assertIn(
            "require a guarded dynamic Explore link",
            self.fragment_messages(fragment),
        )

    def test_accepts_link_only_dynamic_summary_without_bullets(self) -> None:
        self.assertEqual(
            self.fragment_messages(valid_node_fragment()),
            "",
        )

    def test_accepts_dynamic_empty_relationship_summary(self) -> None:
        fragment = valid_node_fragment()
        fragment["info"]["inbound_traversable_relationships"]["markdown"][
            "content"
        ] = dynamic_template(
            "MATCH p = (selected:Example_Role {objectid: '%s'})\n"
            "WHERE false\n"
            "RETURN p\n"
            "LIMIT 500",
            "View direct inbound relationships in Explore",
        )
        fragment["relationship_summary_panels"][0]["relationship_kinds"] = []
        self.assertEqual(self.fragment_messages(fragment), "")

    def test_rejects_non_traversable_relationship_in_summary(self) -> None:
        fragment = valid_node_fragment()
        content = fragment["info"]["inbound_traversable_relationships"][
            "markdown"
        ]["content"]
        fragment["info"]["inbound_traversable_relationships"]["markdown"][
            "content"
        ] = content.replace("Example_HasRole", "Example_Observed")
        fragment["relationship_summary_panels"][0]["relationship_kinds"] = [
            "Example_Observed"
        ]
        self.assertIn(
            "includes non-traversable relationship kind Example_Observed",
            self.fragment_messages(fragment),
        )

    def test_rejects_related_entities_for_nodes_and_relationships(self) -> None:
        schema = valid_schema()
        node_info = schema["node_kinds"][0]["info"]
        node_info["related_entities"] = panel(
            "Related Entities",
            6,
            node_info["who_has_this_role"]["markdown"]["content"],
        )
        edge_info = schema["relationship_kinds"][0]["info"]
        edge_info["related_entities"] = panel(
            "Related Entities", 2, "Legacy section."
        )
        messages = "\n".join(self.validate(schema))
        self.assertGreaterEqual(
            messages.count("must not contain related_entities"), 2
        )

    def test_relationship_h2_must_be_its_own_panel(self) -> None:
        schema = valid_schema()
        schema["relationship_kinds"][0]["info"]["general"]["markdown"][
            "content"
        ] += "\n\n## Abuse Info\n\nDo not leave this nested."
        self.assertIn(
            "each level-two source heading must be its own relationship panel",
            "\n".join(self.validate(schema)),
        )

    def test_relationship_h2_inside_fence_is_not_a_section(self) -> None:
        schema = valid_schema()
        schema["relationship_kinds"][0]["info"]["general"]["markdown"][
            "content"
        ] += "\n\n```\n## shell comment\n```"
        self.assertEqual(self.validate(schema), [])

    def test_dynamic_query_must_anchor_selected_node(self) -> None:
        schema = valid_schema()
        content = schema["node_kinds"][0]["info"]["who_has_this_role"][
            "markdown"
        ]["content"]
        schema["node_kinds"][0]["info"]["who_has_this_role"]["markdown"][
            "content"
        ] = content.replace("(selected:Example_Role ", "(role:Example_Missing ")
        self.assertIn(
            "anchor the selected Example_Role",
            "\n".join(self.validate(schema)),
        )

    def test_dynamic_query_must_return_a_bounded_path(self) -> None:
        schema = valid_schema()
        content = schema["node_kinds"][0]["info"]["who_has_this_role"][
            "markdown"
        ]["content"]
        schema["node_kinds"][0]["info"]["who_has_this_role"]["markdown"][
            "content"
        ] = content.replace(r"\nRETURN p\nLIMIT 500", " RETURN principal")
        messages = "\n".join(self.validate(schema))
        self.assertIn("positive LIMIT", messages)

    def test_rejects_unknown_relationship_kind(self) -> None:
        schema = valid_schema()
        content = schema["node_kinds"][0]["info"]["who_has_this_role"][
            "markdown"
        ]["content"]
        schema["node_kinds"][0]["info"]["who_has_this_role"]["markdown"][
            "content"
        ] = content.replace("Example_HasRole", "Example_Missing")
        self.assertIn(
            "unknown relationship Example_Missing",
            "\n".join(self.validate(schema)),
        )

    def test_allows_evidence_backed_non_traversable_relationship_query(
        self,
    ) -> None:
        schema = valid_schema()
        content = schema["node_kinds"][0]["info"]["who_has_this_role"][
            "markdown"
        ]["content"]
        schema["node_kinds"][0]["info"]["who_has_this_role"]["markdown"][
            "content"
        ] = content.replace("Example_HasRole", "Example_Observed")
        self.assertEqual(self.validate(schema), [])

    def test_accepts_saved_search_style_optional_path_context(self) -> None:
        schema = valid_schema()
        schema["node_kinds"][0]["info"]["who_has_this_role"]["markdown"][
            "content"
        ] = dynamic_template(
            "MATCH assignment = (principal)"
            "-[grant:Example_HasRole]->(selected:Example_Role "
            "{objectid: '%s'})\n"
            "OPTIONAL MATCH reach = (selected)"
            "-[:Example_AllowsAccess]->(resource)\n"
            "RETURN assignment, reach\n"
            "LIMIT 500",
            "View assignments and optional access context in Explore",
        )
        self.assertEqual(self.validate(schema), [])

    def test_rejects_static_fenced_query_panel(self) -> None:
        schema = valid_schema()
        schema["node_kinds"][0]["info"]["who_has_this_role"]["markdown"][
            "content"
        ] = (
            "```\nMATCH p = (principal)-[:Example_HasRole]->"
            "(selected:Example_Role {objectid: '[selected-objectid]'})\n"
            "RETURN p\nLIMIT 200\n```"
        )
        self.assertIn(
            "require a guarded dynamic Explore link",
            "\n".join(self.validate(schema)),
        )

    def test_rejects_graph_node_id_as_property_lookup(self) -> None:
        schema = valid_schema()
        schema["node_kinds"][0]["info"]["who_has_this_role"]["markdown"][
            "content"
        ] = dynamic_role_template().replace(
            ".Properties.objectid", ".NodeID"
        )
        self.assertIn(
            "do not use graph NodeID",
            "\n".join(self.validate(schema)),
        )

    def test_requires_every_node_query_dynamic(self) -> None:
        schema = valid_schema()
        static_content = (
            "```\nMATCH p = (selected:Example_Role "
            "{objectid: '[selected-objectid]'})"
            "-[:Example_AllowsAccess]->(resource)\n"
            "RETURN p\nLIMIT 200\n```"
        )
        schema["node_kinds"][0]["info"]["what_can_this_role_access"][
            "markdown"
        ]["content"] = static_content
        self.assertIn(
            "node Cypher panels require a guarded dynamic Explore link",
            "\n".join(self.validate(schema)),
        )

    def test_dynamic_query_requires_limit_500(self) -> None:
        schema = valid_schema()
        content = schema["node_kinds"][0]["info"]["who_has_this_role"][
            "markdown"
        ]["content"]
        schema["node_kinds"][0]["info"]["who_has_this_role"]["markdown"][
            "content"
        ] = content.replace("LIMIT 500", "LIMIT 200")
        self.assertIn(
            "LIMIT must be exactly 500",
            "\n".join(self.validate(schema)),
        )

    def test_dynamic_query_requires_operation_newlines(self) -> None:
        schema = valid_schema()
        content = schema["node_kinds"][0]["info"]["who_has_this_role"][
            "markdown"
        ]["content"]
        schema["node_kinds"][0]["info"]["who_has_this_role"]["markdown"][
            "content"
        ] = content.replace(r"\nRETURN", " RETURN")
        self.assertIn(
            "each Cypher operation must start on a new line",
            "\n".join(self.validate(schema)),
        )

    def test_dynamic_success_body_contains_only_link(self) -> None:
        schema = valid_schema()
        content = schema["node_kinds"][0]["info"]["who_has_this_role"][
            "markdown"
        ]["content"]
        schema["node_kinds"][0]["info"]["who_has_this_role"]["markdown"][
            "content"
        ] = content.replace(
            "[View principals", "Extra explanation.\n[View principals"
        )
        self.assertIn(
            "no visible text except the Explore link",
            "\n".join(self.validate(schema)),
        )

    def test_dynamic_link_text_uses_words_not_graph_identifiers(self) -> None:
        schema = valid_schema()
        content = schema["node_kinds"][0]["info"]["who_has_this_role"][
            "markdown"
        ]["content"]
        schema["node_kinds"][0]["info"]["who_has_this_role"]["markdown"][
            "content"
        ] = content.replace(
            "View principals that receive this permission set",
            "View Example_HasRole relationships",
        )
        self.assertIn(
            "ordinary words, not graph identifiers",
            "\n".join(self.validate(schema)),
        )

    def test_dynamic_link_allows_platform_product_name(self) -> None:
        schema = valid_schema()
        section = schema["node_kinds"][0]["info"][
            "inbound_traversable_relationships"
        ]["markdown"]
        section["content"] = section["content"].replace(
            "(principal)", "(principal:Example)"
        ).replace(
            "View direct inbound relationships",
            "View direct inbound Example relationships",
        )
        self.assertEqual(self.validate(schema), [])

    def test_accepts_complete_query_panel_metadata(self) -> None:
        self.assertEqual(self.fragment_messages(valid_node_fragment()), "")

    def test_requires_relationship_summary_metadata(self) -> None:
        fragment = valid_node_fragment()
        del fragment["relationship_summary_panels"]
        self.assertIn(
            "relationship_summary_panels must contain exactly",
            self.fragment_messages(fragment),
        )

    def test_requires_query_panel_metadata(self) -> None:
        fragment = valid_node_fragment()
        del fragment["query_panels"]
        self.assertIn(
            "query_panels must be a non-empty array",
            self.fragment_messages(fragment),
        )

    def test_query_kinds_must_match_metadata(self) -> None:
        fragment = valid_node_fragment()
        fragment["query_panels"][0]["relationship_kinds"] = [
            "Example_AllowsAccess"
        ]
        messages = self.fragment_messages(fragment)
        self.assertIn("do not exactly match query_panels metadata", messages)

    def test_query_metadata_requires_evidence(self) -> None:
        fragment = valid_node_fragment()
        fragment["query_panels"][0]["evidence"] = []
        self.assertIn(
            "evidence must be a non-empty array",
            self.fragment_messages(fragment),
        )

    def test_rejects_legacy_direction_metadata(self) -> None:
        fragment = valid_node_fragment()
        fragment["inbound_traversable_kinds"] = ["Example_HasRole"]
        self.assertIn(
            "replace legacy inbound_traversable_kinds",
            self.fragment_messages(fragment),
        )

    def test_accepts_relationship_description_section_metadata(self) -> None:
        self.assertEqual(
            self.fragment_messages(valid_relationship_fragment()), ""
        )

    def test_relationship_fragment_requires_description_sections(self) -> None:
        fragment = valid_relationship_fragment()
        del fragment["description_sections"]
        self.assertIn(
            "description_sections must be a non-empty array",
            self.fragment_messages(fragment),
        )

    def test_relationship_fragment_preserves_h2_title_and_order(self) -> None:
        fragment = valid_relationship_fragment()
        fragment["info"]["abuse_info"]["title"] = "Abuse"
        fragment["info"]["opsec_considerations"]["position"] = 4
        messages = self.fragment_messages(fragment)
        self.assertIn("title must be 'Abuse Info'", messages)
        self.assertIn("position must be 3", messages)


if __name__ == "__main__":
    unittest.main()
