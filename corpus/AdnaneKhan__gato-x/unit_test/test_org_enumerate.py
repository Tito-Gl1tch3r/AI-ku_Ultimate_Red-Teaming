import json
import os
import pathlib
from unittest.mock import AsyncMock

import pytest

from gatox.enumerate.organization import OrganizationEnum
from gatox.models.organization import Organization

TEST_ORG_DATA = None
TEST_REPO_DATA = None


@pytest.fixture(scope="session", autouse=True)
def load_test_files(request):
    global TEST_REPO_DATA
    global TEST_ORG_DATA
    global TEST_WORKFLOW_YML
    curr_path = pathlib.Path(__file__).parent.resolve()
    test_repo_path = os.path.join(curr_path, "files/example_repo.json")
    test_org_path = os.path.join(curr_path, "files/example_org.json")
    test_wf_path = os.path.join(curr_path, "files/main.yaml")

    with open(test_repo_path) as repo_data:
        TEST_REPO_DATA = json.load(repo_data)

    with open(test_org_path) as repo_data:
        TEST_ORG_DATA = json.load(repo_data)

    with open(test_wf_path) as wf_data:
        TEST_WORKFLOW_YML = wf_data.read()


async def test_assemble_repo_list():
    """Test getting a list of repos to scan from org."""

    mock_api = AsyncMock()

    test_private_repodata = TEST_REPO_DATA.copy()
    test_private_repodata["visibility"] = "private"
    test_private_repodata["private"] = True

    mock_api.org.check_org_repos.side_effect = [
        [test_private_repodata],
        [],
        [TEST_REPO_DATA],
    ]

    mock_api.org.validate_sso.return_value = True

    gh_enumeration_runner = OrganizationEnum(mock_api)

    organization = Organization(TEST_ORG_DATA, user_scopes=["repo", "workflow"])

    repos = await gh_enumeration_runner.construct_repo_enum_list(organization)

    assert len(repos) == 2
    assert repos[0].is_public() is False
    assert repos[1].is_public() is True


async def test_admin_enum():
    """Test checks that Gato performs if the user is an org admin and has an
    appropriately scoped token."""

    mock_api = AsyncMock()

    organization = Organization(
        TEST_ORG_DATA, user_scopes=["repo", "workflow", "admin:org"]
    )

    mock_api.org.check_org_runners.return_value = {
        "total_count": 1,
        "runners": [
            {
                "id": 21,
                "name": "ghrunner-test",
                "os": "Linux",
                "status": "online",
                "busy": False,
                "labels": [
                    {"id": 1, "name": "self-hosted", "type": "read-only"},
                    {"id": 2, "name": "Linux", "type": "read-only"},
                    {"id": 3, "name": "X64", "type": "read-only"},
                ],
            }
        ],
    }

    mock_api.org.get_org_secrets.return_value = [
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
            "selected_repositories_url": "https://api.github.com/orgs/testOrg/actions/secrets/GH_TOKEN/repositories",
        },
    ]
    gh_enumeration_runner = OrganizationEnum(mock_api)

    await gh_enumeration_runner.admin_enum(organization)

    assert len(organization.secrets) == 2
    assert len(organization.runners) == 1


# ---------------------------------------------------------------------------
# OrganizationEnum.admin_enum — skip flags
# ---------------------------------------------------------------------------


async def test_admin_enum_skip_runners():
    """When skip_runners=True, runner enumeration is skipped but secrets
    are still enumerated."""
    mock_api = AsyncMock()

    organization = Organization(
        TEST_ORG_DATA, user_scopes=["repo", "workflow", "admin:org"]
    )

    mock_api.org.get_org_secrets.return_value = [
        {
            "name": "DEPLOY_TOKEN",
            "created_at": "2019-08-10T14:59:22Z",
            "updated_at": "2020-01-10T14:59:22Z",
            "visibility": "all",
        },
    ]

    gh_enumeration_runner = OrganizationEnum(mock_api)

    await gh_enumeration_runner.admin_enum(
        organization, skip_runners=True, skip_secrets=False
    )

    # Runners should NOT have been queried
    mock_api.org.check_org_runners.assert_not_called()
    assert len(organization.runners) == 0

    # Secrets SHOULD have been queried
    mock_api.org.get_org_secrets.assert_called_once_with(organization.name)
    assert len(organization.secrets) == 1


async def test_admin_enum_skip_secrets():
    """When skip_secrets=True, secrets enumeration is skipped but runners
    are still enumerated."""
    mock_api = AsyncMock()

    organization = Organization(
        TEST_ORG_DATA, user_scopes=["repo", "workflow", "admin:org"]
    )

    mock_api.org.check_org_runners.return_value = {
        "total_count": 1,
        "runners": [
            {
                "id": 21,
                "name": "ghrunner-test",
                "os": "Linux",
                "status": "online",
                "busy": False,
                "labels": [
                    {"id": 1, "name": "self-hosted", "type": "read-only"},
                    {"id": 2, "name": "Linux", "type": "read-only"},
                    {"id": 3, "name": "X64", "type": "read-only"},
                ],
            }
        ],
    }

    gh_enumeration_runner = OrganizationEnum(mock_api)

    await gh_enumeration_runner.admin_enum(
        organization, skip_runners=False, skip_secrets=True
    )

    # Runners SHOULD have been queried
    mock_api.org.check_org_runners.assert_called_once_with(organization.name)
    assert len(organization.runners) == 1

    # Secrets should NOT have been queried
    mock_api.org.get_org_secrets.assert_not_called()
    assert len(organization.secrets) == 0


async def test_admin_enum_skip_both():
    """When both skip_runners=True and skip_secrets=True, neither runners
    nor secrets are enumerated."""
    mock_api = AsyncMock()

    organization = Organization(
        TEST_ORG_DATA, user_scopes=["repo", "workflow", "admin:org"]
    )

    gh_enumeration_runner = OrganizationEnum(mock_api)

    await gh_enumeration_runner.admin_enum(
        organization, skip_runners=True, skip_secrets=True
    )

    # Neither API should be called
    mock_api.org.check_org_runners.assert_not_called()
    mock_api.org.get_org_secrets.assert_not_called()
    assert len(organization.runners) == 0
    assert len(organization.secrets) == 0
