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
from agentkit.toolkit.cli.sandbox.utils import echo_json, error, save_session_result

DEFAULT_SANDBOX_TTL = 28800
SANDBOX_TOOL_ID_ENV = "AGENTKIT_SANDBOX_TOOL_ID"
SANDBOX_TTL_ENV = "AGENTKIT_SANDBOX_TTL"


def _resolve_tool_id(tool_id: Optional[str]) -> str:
    resolved = (tool_id or os.getenv(SANDBOX_TOOL_ID_ENV) or "").strip()
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
    resolved_tool_id = _resolve_tool_id(tool_id)
    resolved_ttl = _resolve_ttl(ttl)

    try:
        client = AgentkitToolsClient()
        request = tools_types.CreateSessionRequest(
            tool_id=resolved_tool_id,
            ttl=resolved_ttl,
            ttl_unit="second",
            user_session_id=resolved_user_session_id,
        )
        response = client.create_session(request)
    except typer.Exit:
        raise
    except Exception as exc:
        error(str(exc))

    result = {
        "user_session_id": response.user_session_id or resolved_user_session_id,
        "tool_id": resolved_tool_id,
        "session_id": response.session_id,
        "endpoint": response.endpoint,
    }
    save_session_result(result)
    echo_json(result)
