"""Tests for hosted Prefect Cloud OAuth support."""

from unittest.mock import AsyncMock, PropertyMock, patch

import pytest

from prefect_mcp_server import cloud_oauth
from prefect_mcp_server._prefect_client.client import get_prefect_client


async def test_get_prefect_client_uses_oauth_workspace() -> None:
    workspace = cloud_oauth.WorkspaceRef(
        account_id="account-1",
        account_handle="acme",
        workspace_id="workspace-1",
        workspace_handle="prod",
    )

    with (
        patch(
            "prefect_mcp_server._prefect_client.client.cloud_oauth.current_oauth_access_token",
            return_value="oauth-token",
        ),
        patch(
            "prefect_mcp_server._prefect_client.client.cloud_oauth.require_authorized_workspace",
            AsyncMock(return_value=workspace),
        ),
        patch(
            "prefect_mcp_server.cloud_oauth.CloudOAuthSettings.resolved_api_base_url",
            new_callable=PropertyMock,
            return_value="https://api.prefect.cloud",
        ),
        patch(
            "prefect_mcp_server._prefect_client.client.PrefectClient",
        ) as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        async with get_prefect_client(workspace_id="workspace-1") as client:
            assert client is mock_client

    mock_client_cls.assert_called_once_with(
        api=(
            "https://api.prefect.cloud/api/accounts/account-1/"
            "workspaces/workspace-1"
        ),
        api_key="oauth-token",
    )


async def test_get_prefect_client_requires_oauth_token_for_workspace() -> None:
    with patch(
        "prefect_mcp_server._prefect_client.client.cloud_oauth.current_oauth_access_token",
        return_value=None,
    ):
        with pytest.raises(RuntimeError, match="requires a Prefect Cloud OAuth"):
            async with get_prefect_client(workspace_id="workspace-1"):
                pass


async def test_get_prefect_client_requires_workspace_in_oauth_mode() -> None:
    with (
        patch(
            "prefect_mcp_server._prefect_client.client.cloud_oauth.current_oauth_access_token",
            return_value="oauth-token",
        ),
        patch(
            "prefect_mcp_server.cloud_oauth.CloudOAuthSettings.enabled",
            new_callable=PropertyMock,
            return_value=True,
        ),
    ):
        with pytest.raises(RuntimeError, match="workspace_id is required"):
            async with get_prefect_client():
                pass


def test_workspace_ref_display_name_prefers_handles() -> None:
    workspace = cloud_oauth.WorkspaceRef(
        account_id="account-1",
        account_handle="acme",
        workspace_id="workspace-1",
        workspace_handle="prod",
        workspace_name="Production",
    )

    assert workspace.display_name == "acme/prod"
    assert workspace.as_dict()["display_name"] == "acme/prod"
