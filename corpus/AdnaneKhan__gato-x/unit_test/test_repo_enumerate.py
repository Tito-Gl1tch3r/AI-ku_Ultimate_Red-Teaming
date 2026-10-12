import json
import os
import pathlib
from unittest.mock import AsyncMock

import pytest

from gatox.cli.output import Output
from gatox.enumerate.repository import RepositoryEnum
from gatox.models.repository import Repository

TEST_REPO_DATA = None
TEST_WORKFLOW_YML = None

Output(True)


@pytest.fixture(scope="session", autouse=True)
def load_test_files(request):
    global TEST_REPO_DATA
    global TEST_WORKFLOW_YML
    curr_path = pathlib.Path(__file__).parent.resolve()
    test_repo_path = os.path.join(curr_path, "files/example_repo.json")
    test_wf_path = os.path.join(curr_path, "files/main.yaml")

    with open(test_repo_path) as repo_data:
        TEST_REPO_DATA = json.load(repo_data)

    with open(test_wf_path) as wf_data:
        TEST_WORKFLOW_YML = wf_data.read()


async def test_enumerate_repo():
    """Test constructor for enumerator."""
    mock_api = AsyncMock()

    gh_enumeration_runner = RepositoryEnum(mock_api, False)

    mock_api.user.check_user.return_value = {
        "user": "testUser",
        "scopes": ["repo", "workflow"],
    }

    mock_api.action.retrieve_run_logs.return_value = [
        {
            "machine_name": "unittest1",
            "runner_name": "much_unit_such_test",
            "runner_type": "organization",
            "non_ephemeral": False,
            "token_permissions": {"Actions": "write"},
            "runner_group": "Default",
            "requested_labels": ["self-hosted", "Linux", "X64"],
        }
    ]

    repo_data = json.loads(json.dumps(TEST_REPO_DATA))
    test_repo = Repository(repo_data)
    test_repo.add_self_hosted_workflows(["build.yaml"])

    await gh_enumeration_runner.enumerate_repository(test_repo)

    assert test_repo.sh_runner_access is True
    assert len(test_repo.accessible_runners) > 0
    assert test_repo.accessible_runners[0].runner_name == "much_unit_such_test"


async def test_enumerate_repo_admin():
    """Test constructor for enumerator."""
    mock_api = AsyncMock()

    gh_enumeration_runner = RepositoryEnum(mock_api, False)

    mock_api.user.check_user.return_value = {
        "user": "testUser",
        "scopes": ["repo", "workflow"],
    }

    mock_api.action.retrieve_run_logs.return_value = [
        {
            "machine_name": "unittest1",
            "runner_name": "much_unit_such_test",
            "runner_type": "organization",
            "non_ephemeral": False,
            "token_permissions": {"Actions": "write"},
            "runner_group": "Default",
            "requested_labels": ["self-hosted", "Linux", "X64"],
        }
    ]

    repo_data = json.loads(json.dumps(TEST_REPO_DATA))
    repo_data["permissions"]["admin"] = True
    test_repo = Repository(repo_data)

    await gh_enumeration_runner.enumerate_repository(test_repo)

    assert test_repo.is_admin()


async def test_enumerate_repo_secrets():
    """Test constructor for enumerator."""
    mock_api = AsyncMock()

    gh_enumeration_runner = RepositoryEnum(mock_api, False)

    mock_api.user.check_user.return_value = {
        "user": "testUser",
        "scopes": ["repo", "workflow"],
    }

    mock_api.repo.get_secrets.return_value = [
        {
            "name": "GIST_ID",
            "created_at": "2019-08-10T14:59:22Z",
            "updated_at": "2020-01-10T14:59:22Z",
            "visibility": "private",
        },
        {
            "name": "DEPLOY_TOKEN",
            "created_at": "2019-08-10T14:59:22Z",
            "updated_at": "2020-01-10T14:59:22Z",
            "visibility": "all",
        },
        {
            "name": "GH_TOKEN",
            "created_at": "2019-08-10T14:59:22Z",
            "updated_at": "2020-01-10T14:59:22Z",
            "visibility": "selected",
            "selected_repositories_url": "https://api.github.com/orgs/octo-org/actions/secrets/SUPER_SECRET/repositories",
        },
    ]

    repo_data = json.loads(json.dumps(TEST_REPO_DATA))
    test_repo = Repository(repo_data)

    await gh_enumeration_runner.enumerate_repository_secrets(test_repo)

    assert len(test_repo.secrets) > 0


# ---------------------------------------------------------------------------
# Repository.toJSON() — new fields
# ---------------------------------------------------------------------------


def test_toJSON_includes_description():
    """Repository.toJSON() should emit the 'description' field from repo_data."""
    repo_data = json.loads(json.dumps(TEST_REPO_DATA))
    repo_data["description"] = "This your first repo!"
    repo = Repository(repo_data)
    result = repo.toJSON()

    assert result["description"] == "This your first repo!"


def test_toJSON_includes_pushed_at():
    """Repository.toJSON() should emit the 'pushed_at' field from repo_data."""
    repo_data = json.loads(json.dumps(TEST_REPO_DATA))
    repo_data["pushed_at"] = "2011-01-26T19:06:43Z"
    repo = Repository(repo_data)
    result = repo.toJSON()

    assert result["pushed_at"] == "2011-01-26T19:06:43Z"


def test_toJSON_includes_workflow_count():
    """Repository.toJSON() should emit the 'workflow_count' attribute."""
    repo_data = json.loads(json.dumps(TEST_REPO_DATA))
    repo = Repository(repo_data)
    repo.workflow_count = 5
    result = repo.toJSON()

    assert result["workflow_count"] == 5


def test_toJSON_workflow_count_defaults_to_zero():
    """workflow_count defaults to 0 when not explicitly set."""
    repo_data = json.loads(json.dumps(TEST_REPO_DATA))
    repo = Repository(repo_data)
    result = repo.toJSON()

    assert result["workflow_count"] == 0


def test_toJSON_description_defaults_to_empty_string():
    """description defaults to '' when repo_data has no 'description' key."""
    repo_data = {
        "full_name": "testOrg/testRepo",
        "html_url": "https://github.com/testOrg/testRepo",
        "visibility": "public",
        "default_branch": "main",
        "fork": False,
        "stargazers_count": 0,
        "permissions": {"pull": True, "push": False, "admin": False},
        "archived": False,
        "isFork": False,
        "environments": [],
    }
    repo = Repository(repo_data)
    result = repo.toJSON()

    assert result["description"] == ""


def test_toJSON_pushed_at_defaults_to_empty_string():
    """pushed_at defaults to '' when repo_data has no 'pushed_at' key."""
    repo_data = {
        "full_name": "testOrg/testRepo",
        "html_url": "https://github.com/testOrg/testRepo",
        "visibility": "public",
        "default_branch": "main",
        "fork": False,
        "stargazers_count": 0,
        "permissions": {"pull": True, "push": False, "admin": False},
        "archived": False,
        "isFork": False,
        "environments": [],
    }
    repo = Repository(repo_data)
    result = repo.toJSON()

    assert result["pushed_at"] == ""


def test_toJSON_all_new_fields_present():
    """Verify that all new fields appear in the toJSON() dictionary keys."""
    repo_data = json.loads(json.dumps(TEST_REPO_DATA))
    repo = Repository(repo_data)
    result = repo.toJSON()

    assert "description" in result
    assert "pushed_at" in result
    assert "workflow_count" in result


# ---------------------------------------------------------------------------
# RepositoryEnum.enumerate_repository_secrets — skip_secrets flag
# ---------------------------------------------------------------------------


async def test_skip_secrets_skips_api_calls():
    """When skip_secrets=True, enumerate_repository_secrets returns immediately
    without making any API calls."""
    mock_api = AsyncMock()
    gh_enumeration_runner = RepositoryEnum(mock_api, False, skip_secrets=True)

    repo_data = json.loads(json.dumps(TEST_REPO_DATA))
    test_repo = Repository(repo_data)

    await gh_enumeration_runner.enumerate_repository_secrets(test_repo)

    # API should never be called
    mock_api.repo.get_secrets.assert_not_called()
    mock_api.repo.get_environment_secrets.assert_not_called()
    mock_api.repo.get_repo_org_secrets.assert_not_called()
    # Secrets list should still be empty (default)
    assert len(test_repo.secrets) == 0


async def test_skip_secrets_false_enumerates_normally():
    """When skip_secrets=False (default), secrets are enumerated as expected."""
    mock_api = AsyncMock()

    mock_api.repo.get_secrets.return_value = [
        {
            "name": "GIST_ID",
            "created_at": "2019-08-10T14:59:22Z",
            "updated_at": "2020-01-10T14:59:22Z",
            "visibility": "private",
        },
    ]
    mock_api.repo.get_repo_org_secrets.return_value = []

    gh_enumeration_runner = RepositoryEnum(mock_api, False, skip_secrets=False)

    repo_data = json.loads(json.dumps(TEST_REPO_DATA))
    test_repo = Repository(repo_data)

    await gh_enumeration_runner.enumerate_repository_secrets(test_repo)

    # API should have been called
    mock_api.repo.get_secrets.assert_called_once_with(test_repo.name)
    assert len(test_repo.secrets) == 1
    assert test_repo.secrets[0].name == "GIST_ID"
