# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd. and/or its affiliates.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Create command for sandbox CLI."""

from __future__ import annotations

import os
import uuid
from typing import Optional

import typer

from agentkit.sdk.tools.client import AgentkitToolsClient
from agentkit.sdk.tools import types as tools_types
from agentkit.toolkit.cli.sandbox.utils import (
    echo_json,
    error,
    find_session_result,
    save_session_result,
)

DEFAULT_SANDBOX_TTL = 28800
SANDBOX_TOOL_ID_ENV = "AGENTKIT_SANDBOX_TOOL_ID"
SANDBOX_TTL_ENV = "AGENTKIT_SANDBOX_TTL"


def _resolve_tool_id(
    tool_id: Optional[str],
    default_tool_id: object = None,
) -> str:
    default = default_tool_id if isinstance(default_tool_id, str) else ""
    resolved = (tool_id or os.getenv(SANDBOX_TOOL_ID_ENV) or default).strip()
    if not resolved:
        error(f"--tool-id or {SANDBOX_TOOL_ID_ENV} is required")
    return resolved


def _resolve_ttl(ttl: Optional[int]) -> int:
    if ttl is not None:
        return ttl

    raw = (os.getenv(SANDBOX_TTL_ENV) or "").strip()
    if not raw:
        return DEFAULT_SANDBOX_TTL

    try:
        return int(raw)
    except ValueError:
        error(f"{SANDBOX_TTL_ENV} must be an integer")


def _is_session_missing_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(
        token in message
        for token in (
            "not found",
            "not exist",
            "notfound",
            "not_found",
            "不存在",
        )
    )


def _build_result(
    *,
    user_session_id: str,
    tool_id: str,
    session_id: object,
    endpoint: object,
) -> dict[str, object]:
    return {
        "user_session_id": user_session_id,
        "tool_id": tool_id,
        "session_id": session_id,
        "endpoint": endpoint,
    }


def _build_create_result(
    response: tools_types.CreateSessionResponse,
    user_session_id: str,
    tool_id: str,
) -> dict[str, object]:
    return _build_result(
        user_session_id=response.user_session_id or user_session_id,
        tool_id=tool_id,
        session_id=response.session_id,
        endpoint=response.endpoint,
    )


def _build_get_result(
    response: tools_types.GetSessionResponse,
    existing: dict[str, object],
    user_session_id: str,
    tool_id: str,
) -> dict[str, object]:
    return _build_result(
        user_session_id=response.user_session_id or user_session_id,
        tool_id=tool_id,
        session_id=response.session_id or existing.get("session_id"),
        endpoint=response.endpoint or existing.get("endpoint"),
    )


def _get_existing_remote_session(
    client: AgentkitToolsClient,
    existing: dict[str, object],
    user_session_id: str,
    tool_id: str,
) -> dict[str, object] | None:
    session_id = existing.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        return None

    try:
        response = client.get_session(
            tools_types.GetSessionRequest(
                tool_id=tool_id,
                session_id=session_id,
            )
        )
    except Exception as exc:
        if _is_session_missing_error(exc):
            return None
        raise

    return _build_get_result(response, existing, user_session_id, tool_id)


def _create_session(
    client: AgentkitToolsClient,
    user_session_id: str,
    tool_id: str,
    ttl: int,
) -> dict[str, object]:
    request = tools_types.CreateSessionRequest(
        tool_id=tool_id,
        ttl=ttl,
        ttl_unit="second",
        user_session_id=user_session_id,
    )
    response = client.create_session(request)
    return _build_create_result(response, user_session_id, tool_id)


def create_command(
    user_session_id: Optional[str] = typer.Option(
        None,
        "--user-session-id",
        help="User session ID. Defaults to a generated UUID.",
    ),
    ttl: Optional[int] = typer.Option(
        None,
        "--ttl",
        help=(
            "Session TTL in seconds. Defaults to "
            f"{SANDBOX_TTL_ENV} or {DEFAULT_SANDBOX_TTL}."
        ),
    ),
    tool_id: Optional[str] = typer.Option(
        None,
        "--tool-id",
        help=f"Sandbox tool ID. Defaults to {SANDBOX_TOOL_ID_ENV}.",
    ),
) -> None:
    """Create a sandbox session."""
    resolved_user_session_id = user_session_id or str(uuid.uuid4())
    existing = (
        find_session_result(resolved_user_session_id) if user_session_id else None
    )
    existing_tool_id = (
        _resolve_tool_id(None, default_tool_id=existing.get("tool_id"))
        if existing
        else None
    )
    resolved_tool_id = _resolve_tool_id(
        tool_id,
        default_tool_id=existing.get("tool_id") if existing else None,
    )

    try:
        client = AgentkitToolsClient()
        if existing:
            result = _get_existing_remote_session(
                client,
                existing,
                resolved_user_session_id,
                existing_tool_id or resolved_tool_id,
            )
            if result:
                save_session_result(result)
                echo_json(result)
                return

        result = _create_session(
            client,
            resolved_user_session_id,
            resolved_tool_id,
            _resolve_ttl(ttl),
        )
    except typer.Exit:
        raise
    except Exception as exc:
        error(str(exc))

    save_session_result(result)
    echo_json(result)
