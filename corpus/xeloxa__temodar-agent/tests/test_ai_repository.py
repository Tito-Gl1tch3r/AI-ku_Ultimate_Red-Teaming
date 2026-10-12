import json
import sqlite3

from ai.repository import AIRepository
from database.models import init_db


def test_init_db_migrates_unique_ai_threads_scope_without_leaving_legacy_table(tmp_path):
    db_path = tmp_path / "ai_state.db"

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE ai_threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plugin_slug TEXT NOT NULL,
                is_theme INTEGER NOT NULL DEFAULT 0,
                title TEXT,
                last_scan_session_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(plugin_slug, is_theme)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE ai_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (thread_id) REFERENCES ai_threads(id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE ai_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                model TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (thread_id) REFERENCES ai_threads(id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            "INSERT INTO ai_threads (plugin_slug, is_theme, title) VALUES (?, ?, ?)",
            ("akismet", 0, "Akismet"),
        )
        cursor.execute(
            "INSERT INTO ai_messages (thread_id, role, content) VALUES (?, ?, ?)",
            (1, "user", "hello"),
        )
        cursor.execute(
            "INSERT INTO ai_runs (thread_id, provider, model, status) VALUES (?, ?, ?, ?)",
            (1, "anthropic", "claude-3-7-sonnet", "completed"),
        )
        conn.commit()

    init_db(db_path)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'ai_threads_legacy'"
        )
        assert cursor.fetchone() is None
        cursor.execute("PRAGMA index_list(ai_threads)")
        assert all(not row[2] for row in cursor.fetchall())
        cursor.execute("SELECT plugin_slug, is_theme, title FROM ai_threads")
        assert cursor.fetchall() == [("akismet", 0, "Akismet")]
        cursor.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'ai_messages'")
        assert 'ai_threads_legacy' not in (cursor.fetchone()[0] or "")
        cursor.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'ai_runs'")
        assert 'ai_threads_legacy' not in (cursor.fetchone()[0] or "")
        cursor.execute("SELECT thread_id, role, content FROM ai_messages")
        assert cursor.fetchall() == [(1, "user", "hello")]
        cursor.execute("SELECT thread_id, provider, model, status FROM ai_runs")
        assert cursor.fetchall() == [(1, "anthropic", "claude-3-7-sonnet", "completed")]


def test_init_db_rebuilds_run_event_tables_that_reference_ai_runs_legacy(tmp_path):
    db_path = tmp_path / "ai_state.db"

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE ai_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                model TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE ai_run_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                agent_name TEXT,
                task_id TEXT,
                payload_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES ai_runs_legacy(id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE ai_run_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                task_id TEXT NOT NULL,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                assignee TEXT,
                depends_on_json TEXT,
                result_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(run_id, task_id),
                FOREIGN KEY (run_id) REFERENCES ai_runs_legacy(id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            "INSERT INTO ai_runs (id, thread_id, provider, model, status) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "anthropic", "claude-3-7-sonnet", "completed"),
        )
        cursor.execute(
            "INSERT INTO ai_run_events (run_id, event_type) VALUES (?, ?)",
            (1, "agent_started"),
        )
        cursor.execute(
            "INSERT INTO ai_run_tasks (run_id, task_id, title, status) VALUES (?, ?, ?, ?)",
            (1, "task-1", "Inspect plugin", "completed"),
        )
        conn.commit()

    init_db(db_path)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'ai_run_events'")
        assert 'ai_runs_legacy' not in (cursor.fetchone()[0] or "")
        cursor.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'ai_run_tasks'")
        assert 'ai_runs_legacy' not in (cursor.fetchone()[0] or "")
        cursor.execute("SELECT run_id, event_type FROM ai_run_events")
        assert cursor.fetchall() == [(1, "agent_started")]
        cursor.execute("SELECT run_id, task_id, title, status FROM ai_run_tasks")
        assert cursor.fetchall() == [(1, "task-1", "Inspect plugin", "completed")]




def test_get_thread_pending_approval_ignores_completed_run(tmp_path):
    db_path = tmp_path / "ai_state.db"
    repository = AIRepository(db_path=db_path)

    thread = repository.create_thread(plugin_slug="akismet", is_theme=False)
    run = repository.create_run(
        thread_id=int(thread["id"]),
        provider="anthropic",
        model="claude-3-7-sonnet",
        status="running",
    )

    repository.upsert_run_approval(
        run_id=int(run["id"]),
        thread_id=int(thread["id"]),
        status="pending",
        mode="manual",
        request_payload={"nextTasks": [{"id": "task-1", "title": "Inspect files"}]},
    )

    assert repository.get_thread_pending_approval(int(thread["id"])) is not None

    repository.finish_run(int(run["id"]), "completed")

    assert repository.get_thread_pending_approval(int(thread["id"])) is None


def test_upsert_provider_settings_deactivates_previous_active_provider(tmp_path):
    db_path = tmp_path / "ai_state.db"
    repository = AIRepository(db_path=db_path)

    repository.upsert_provider_settings(
        provider="claude",
        api_key="claude-key",
        model="claude-3-7-sonnet",
        base_url="https://api.anthropic.com",
        is_active=True,
    )

    repository.upsert_provider_settings(
        provider="openai",
        api_key="openai-key",
        model="gpt-4.1",
        base_url="https://api.openai.com",
        is_active=True,
    )

    active_provider = repository.get_active_provider()
    claude_settings = repository.get_provider_by_profile_key("claude-claude-3-7-sonnet")

    assert active_provider is not None
    assert active_provider["provider"] == "openai"
    assert active_provider["is_active"] == 1
    assert claude_settings["is_active"] == 0
    assert claude_settings["api_key"] == "claude-key"


def test_upsert_provider_settings_preserves_existing_optional_fields_on_partial_update(tmp_path):
    db_path = tmp_path / "ai_state.db"
    repository = AIRepository(db_path=db_path)

    repository.upsert_provider_settings(
        provider="claude",
        api_key="test-key",
        model="claude-3-7-sonnet",
        base_url="https://api.anthropic.com",
        is_active=True,
    )

    updated_provider = repository.upsert_provider_settings(
        provider="claude",
        profile_key="claude-claude-3-7-sonnet",
        is_active=False,
    )

    assert updated_provider["provider"] == "claude"
    assert updated_provider["api_key"] == "test-key"
    assert updated_provider["model"] == "claude-3-7-sonnet"
    assert updated_provider["base_url"] == "https://api.anthropic.com"
    assert updated_provider["is_active"] == 0
    assert updated_provider["profile_key"] == "claude-claude-3-7-sonnet"


def test_ai_repository_does_not_expose_removed_alias_only_methods(tmp_path):
    repository = AIRepository(db_path=tmp_path / "ai_state.db")

    removed_aliases = [
        "upsert_thread",
        "list_scope_threads",
        "create_scope_thread",
        "get_scope_thread",
        "get_latest_scope_thread",
        "get_thread_messages",
        "list_messages_for_thread",
        "get_thread_record",
        "get_run_record",
        "get_provider_record",
        "get_message_record",
        "get_scoped_thread",
        "set_thread_scan_session",
        "set_thread_name",
        "add_tool_audit",
        "mark_run_completed",
        "mark_run_failed",
        "create_or_get_thread",
        "get_active_provider_settings",
        "get_sanitized_active_provider_settings",
        "get_sanitized_active_provider",
        "list_tool_activity",
        "get_tool_activity",
        "create_structured_tool_audit",
        "set_run_failed_with_message",
        "mark_provider_active",
        "get_thread_runs",
        "create_run_for_message",
        "complete_run",
        "get_sanitized_settings",
        "sanitize_settings_response",
        "create_run_record",
        "complete_run_record",
        "get_masked_active_provider",
        "provider_label_for",
        "set_active_provider",
        "set_run_error_message",
        "set_run_workspace",
        "set_run_message",
        "get_thread_events",
        "list_thread_events",
        "create_assistant_message",
        "create_user_message",
        "create_failed_assistant_message",
        "get_provider_label",
        "get_active_provider_name",
        "get_active_provider_model",
        "get_active_provider_base_url",
        "get_active_provider_api_key",
        "get_active_provider_label",
        "get_active_provider_tuple",
        "get_active_provider_id",
        "set_provider_settings",
        "get_provider_settings",
        "get_sanitized_provider_settings",
        "set_run_status",
        "get_thread_by_scope",
        "fail_run",
        "set_thread_updated",
        "create_message_with_audit",
        "get_thread_last_scan",
        "get_thread_metadata",
        "mask_settings",
        "get_run_workspace",
        "get_scoped_thread_id",
        "list_all_provider_settings",
        "set_run_completed",
        "get_thread_id_by_scope",
        "has_active_provider",
        "thread_exists",
        "provider_exists",
        "run_exists",
        "message_exists",
        "count_messages",
        "count_runs",
        "count_providers",
        "get_run_provider_label",
        "get_run_message_id",
        "get_run_error",
        "get_thread_plugin_slug",
        "get_thread_title",
        "get_last_scan_session_id",
        "get_masked_api_key",
        "list_thread_message_ids",
        "list_thread_roles",
        "list_thread_contents",
        "get_sanitized_provider",
        "count_tool_calls",
        "count_tool_results",
        "get_run_provider",
        "get_thread_is_theme",
        "list_all_threads",
        "list_all_runs",
        "list_all_messages",
        "get_thread_count",
        "get_provider_count",
        "get_message_count",
        "get_run_count",
        "get_tool_activity_count",
        "get_any_provider",
        "get_any_thread",
        "get_any_run",
        "get_any_message",
        "get_thread_lookup_key",
        "get_thread_summary",
        "get_run_summary",
        "get_message_summary",
        "get_provider_summary",
        "get_thread_scope_key",
        "get_thread_last_updated",
        "get_provider_updated_at",
        "get_run_completed_at",
        "get_message_created_at",
        "has_messages",
        "has_runs",
        "has_tool_activity",
        "has_title",
        "has_last_scan",
        "has_workspace_path",
        "has_error_message",
        "is_provider_active",
        "is_message_assistant",
        "is_message_user",
        "is_run_completed",
        "is_run_failed",
        "is_provider_configured",
        "get_thread_scope_tuple",
        "get_run_tuple",
        "get_message_tuple",
        "get_tool_audit_tuple",
        "provider_requires_key",
        "get_provider_api_key_suffix",
        "list_thread_ids",
        "list_provider_names",
        "list_run_ids",
        "list_message_ids",
        "get_provider_id",
        "get_run_id",
        "get_message_id",
    ]

    assert all(not hasattr(repository, alias_name) for alias_name in removed_aliases)



def test_ai_repository_persists_provider_threads_messages_and_runs(tmp_path):
    db_path = tmp_path / "ai_state.db"
    repository = AIRepository(db_path=db_path)

    repository.upsert_provider_settings(
        provider="anthropic",
        api_key="test-key",
        model="claude-3-7-sonnet",
        base_url="https://api.anthropic.com",
        is_active=True,
    )

    active_provider = repository.get_active_provider()
    assert active_provider is not None
    assert active_provider["provider"] == "anthropic"
    assert active_provider["provider_label"] == "Anthropic"
    assert active_provider["api_key"] == "test-key"
    assert active_provider["model"] == "claude-3-7-sonnet"
    assert active_provider["base_url"] == "https://api.anthropic.com"
    assert active_provider["is_active"] == 1

    thread = repository.get_or_create_thread(
        plugin_slug="akismet",
        is_theme=False,
        title="Akismet",
        last_scan_session_id=33,
    )
    same_thread = repository.get_or_create_thread(
        plugin_slug="akismet",
        is_theme=False,
        title="Akismet updated",
        last_scan_session_id=34,
    )
    second_thread = repository.create_thread(
        plugin_slug="akismet",
        is_theme=False,
        title="Akismet follow-up",
        last_scan_session_id=35,
    )
    theme_thread = repository.get_or_create_thread(
        plugin_slug="akismet",
        is_theme=True,
        title="Akismet Theme",
    )
    fetched_thread = repository.get_thread(thread["id"])
    scoped_threads = repository.list_threads_for_scope("akismet", False)

    assert same_thread["id"] == thread["id"]
    assert second_thread["id"] != thread["id"]
    assert theme_thread["id"] != thread["id"]
    assert fetched_thread is not None
    assert fetched_thread["plugin_slug"] == "akismet"
    assert fetched_thread["is_theme"] == 0
    assert fetched_thread["title"] == "Akismet"
    assert fetched_thread["last_scan_session_id"] == 33
    assert [item["id"] for item in scoped_threads] == [second_thread["id"], thread["id"]]
    assert scoped_threads[0]["title"] == "Akismet follow-up Chat 2"
    latest_thread = repository.get_latest_thread_for_scope("akismet", False)
    scoped_second_thread = repository.get_thread_for_scope(second_thread["id"], "akismet", False)
    assert latest_thread is not None
    assert scoped_second_thread is not None
    assert latest_thread["id"] == second_thread["id"]
    assert scoped_second_thread["id"] == second_thread["id"]
    assert repository.get_thread_for_scope(second_thread["id"], "akismet", True) is None

    first_message = repository.create_message(
        thread_id=thread["id"],
        role="user",
        content="Summarize this plugin.",
        tool_calls=[{"name": "read", "path": "source/plugin.php"}],
    )
    second_message = repository.create_message(
        thread_id=thread["id"],
        role="assistant",
        content="This plugin provides spam filtering.",
        tool_results=[{"name": "read", "status": "ok"}],
    )

    messages = repository.list_messages(thread["id"])
    assert [message["id"] for message in messages] == [
        first_message["id"],
        second_message["id"],
    ]
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert json.loads(messages[0]["tool_calls_json"]) == [{"name": "read", "path": "source/plugin.php"}]
    assert json.loads(messages[1]["tool_results_json"]) == [{"name": "read", "status": "ok"}]
    assert messages[1]["content"] == "This plugin provides spam filtering."

    run = repository.create_run(
        thread_id=thread["id"],
        provider="anthropic",
        provider_label="Anthropic",
        model="claude-3-7-sonnet",
        status="pending",
        message_id=first_message["id"],
        workspace_path="/tmp/workspace/source",
    )
    assert run["status"] == "pending"
    assert run["provider_label"] == "Anthropic"
    assert run["message_id"] == first_message["id"]
    assert run["workspace_path"] == "/tmp/workspace/source"

    repository.finish_run(run_id=run["id"], status="completed")
    finished_run = repository.get_run(run["id"])

    assert finished_run is not None
    assert finished_run["thread_id"] == thread["id"]
    assert finished_run["provider"] == "anthropic"
    assert finished_run["provider_label"] == "Anthropic"
    assert finished_run["model"] == "claude-3-7-sonnet"
    assert finished_run["status"] == "completed"
    assert finished_run["message_id"] == first_message["id"]
    assert finished_run["workspace_path"] == "/tmp/workspace/source"
    assert finished_run["completed_at"] is not None


def test_thread_memory_roundtrip_persists_structured_context(tmp_path):
    db_path = tmp_path / "ai_state.db"
    repository = AIRepository(db_path=db_path)
    thread = repository.get_or_create_thread(plugin_slug="akismet", is_theme=False)

    repository.update_thread_memory(
        thread["id"],
        conversation_summary="User greeted and then requested analysis.",
        analysis_summary="The plugin registers one main entry file.",
        important_files=["plugin.php", "includes/admin.php"],
        findings_summary="No confirmed vulnerability yet.",
        architecture_notes="Main bootstrap is plugin.php.",
        last_source_path="/tmp/workspace/source",
    )

    memory = repository.get_thread_memory(thread["id"])
    thread_row = repository.get_thread(thread["id"])

    assert memory["conversation_summary"] == "User greeted and then requested analysis."
    assert memory["analysis_summary"] == "The plugin registers one main entry file."
    assert memory["important_files"] == ["plugin.php", "includes/admin.php"]
    assert memory["findings_summary"] == "No confirmed vulnerability yet."
    assert memory["architecture_notes"] == "Main bootstrap is plugin.php."
    assert memory["last_source_path"] == "/tmp/workspace/source"
    assert thread_row["important_files"] == ["plugin.php", "includes/admin.php"]


def test_fail_run_with_assistant_message_persists_error_and_structured_tool_audit(tmp_path):
    db_path = tmp_path / "ai_state.db"
    repository = AIRepository(db_path=db_path)
    thread = repository.get_or_create_thread(plugin_slug="akismet", is_theme=False)
    user_message = repository.create_message(thread_id=thread["id"], role="user", content="Analyze")
    run = repository.create_run(
        thread_id=thread["id"],
        provider="anthropic",
        provider_label="Anthropic",
        model="claude-3-7-sonnet",
        status="running",
        message_id=user_message["id"],
        workspace_path="/tmp/workspace/source",
    )

    assistant_message = repository.fail_run_with_assistant_message(
        run_id=run["id"],
        thread_id=thread["id"],
        content="AI agent bridge failed.",
        error_message="AI agent bridge failed.",
        tool_calls=[{"name": "read", "path": "source/plugin.php"}],
        tool_results=[{"name": "read", "status": "failed"}],
    )

    assert assistant_message["role"] == "assistant"
    assert json.loads(assistant_message["tool_calls_json"]) == [{"name": "read", "path": "source/plugin.php"}]
    assert json.loads(assistant_message["tool_results_json"]) == [{"name": "read", "status": "failed"}]

    failed_run = repository.get_run(run["id"])
    assert failed_run is not None
    assert failed_run["status"] == "failed"
    assert failed_run["error_message"] == "AI agent bridge failed."
    assert repository.list_thread_tool_audit(thread["id"]) == [
        {"name": "read", "path": "source/plugin.php"},
        {"name": "read", "status": "failed"},
    ]



def test_repository_persists_run_events_and_tasks(tmp_path):
    db_path = tmp_path / "ai_state.db"
    repository = AIRepository(db_path=db_path)
    thread = repository.get_or_create_thread(plugin_slug="akismet", is_theme=False)
    message = repository.create_message(thread_id=thread["id"], role="user", content="Analyze")
    run = repository.create_run(
        thread_id=thread["id"],
        provider="anthropic",
        provider_label="Anthropic",
        model="claude-3-7-sonnet",
        status="running",
        message_id=message["id"],
        workspace_path="/tmp/workspace/source",
    )

    event = repository.create_run_event(
        run_id=run["id"],
        event_type="agent_started",
        agent_name="plugin_analyst",
        task_id="task-1",
        payload={"name": "plugin_analyst", "taskId": "task-1"},
    )
    task = repository.upsert_run_task(
        run_id=run["id"],
        task_id="task-1",
        title="Inspect plugin",
        status="completed",
        assignee="plugin_analyst",
        depends_on=["task-0"],
        result_text="done",
    )

    assert event["event_type"] == "agent_started"
    assert event["payload"] == {"name": "plugin_analyst", "taskId": "task-1"}
    assert repository.list_run_events(run["id"])[0]["agent_name"] == "plugin_analyst"

    assert task["task_id"] == "task-1"
    assert task["depends_on"] == ["task-0"]
    assert repository.list_run_tasks(run["id"])[0]["status"] == "completed"


def test_sanitize_provider_settings_omits_raw_api_key_and_masks_suffix(tmp_path):
    db_path = tmp_path / "ai_state.db"
    repository = AIRepository(db_path=db_path)
    repository.upsert_provider_settings(
        provider="anthropic",
        api_key="sk-ant-api-key-1234",
        model="claude-3-7-sonnet",
        base_url="https://api.anthropic.com",
        is_active=True,
    )

    settings = repository.get_active_provider()
    assert settings is not None
    sanitized = repository.sanitize_provider_settings(settings)

    assert sanitized is not None
    assert sanitized["api_key"] is None
    assert sanitized["api_key_masked"] == "••••1234"
    assert settings["api_key"] == "sk-ant-api-key-1234"




def test_get_or_create_thread_scopes_plugin_and_theme_independently(tmp_path):
    db_path = tmp_path / "ai_state.db"
    repository = AIRepository(db_path=db_path)

    plugin_thread = repository.get_or_create_thread(
        plugin_slug="hello-dolly",
        is_theme=False,
        title="Plugin Thread",
        last_scan_session_id=11,
    )
    plugin_second_thread = repository.create_thread(
        plugin_slug="hello-dolly",
        is_theme=False,
        title="Plugin Thread",
        last_scan_session_id=13,
    )
    theme_thread = repository.get_or_create_thread(
        plugin_slug="hello-dolly",
        is_theme=True,
        title="Theme Thread",
        last_scan_session_id=12,
    )

    scoped_theme_thread = repository.get_thread_for_scope(
        theme_thread["id"], "hello-dolly", True
    )
    scoped_original_plugin_thread = repository.get_thread_for_scope(
        plugin_thread["id"], "hello-dolly", False
    )

    assert plugin_thread["id"] != theme_thread["id"]
    assert plugin_thread["is_theme"] == 0
    assert theme_thread["is_theme"] == 1
    assert scoped_theme_thread is not None
    assert scoped_theme_thread["id"] == theme_thread["id"]
    assert [thread["id"] for thread in repository.list_threads_for_scope("hello-dolly", False)] == [plugin_second_thread["id"], plugin_thread["id"]]
    assert repository.has_thread_scope("hello-dolly", False) is True
    assert repository.has_thread_scope("missing", False) is False
    assert scoped_original_plugin_thread is not None
    assert scoped_original_plugin_thread["id"] == plugin_thread["id"]
    scoped_latest_plugin_thread = repository.get_thread_for_scope(
        plugin_second_thread["id"], "hello-dolly", False
    )
    assert scoped_latest_plugin_thread is not None
    assert scoped_latest_plugin_thread["id"] == plugin_second_thread["id"]
    assert repository.get_thread_for_scope(plugin_thread["id"], "hello-dolly", True) is None
