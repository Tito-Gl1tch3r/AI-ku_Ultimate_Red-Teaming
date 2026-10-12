import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import BotoCoreError, ClientError
from iam_principal_enumerator.aws.sts import get_current_account_id
from mypy_boto3_sts import STSClient


def test_get_current_account_id_success():
    client = Mock(spec=STSClient)
    client.get_caller_identity.return_value = {"Account": "123456789012"}
    account_id = get_current_account_id(client)
    assert account_id == "123456789012"
    client.get_caller_identity.assert_called_once()


def test_get_current_account_id_botocore_error():
    client = Mock(spec=STSClient)
    client.get_caller_identity.side_effect = BotoCoreError()

    with pytest.raises(BotoCoreError):
        get_current_account_id(client)
    client.get_caller_identity.assert_called_once()


def test_get_current_account_id_client_error():
    client = Mock(spec=STSClient)
    client.get_caller_identity.side_effect = ClientError(
        {"Error": {"Code": "ClientError", "Message": "An error occurred"}},
        "GetCallerIdentity",
    )

    with pytest.raises(ClientError):
        get_current_account_id(client)
    client.get_caller_identity.assert_called_once()
