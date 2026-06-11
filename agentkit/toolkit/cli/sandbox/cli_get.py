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

"""Get command for sandbox CLI."""

from __future__ import annotations

from typing import Optional

import typer

from agentkit.sdk.tools.client import AgentkitToolsClient
from agentkit.toolkit.cli.sandbox.session_create import SANDBOX_TOOL_ID_ENV
from agentkit.toolkit.cli.sandbox.session_sync import sync_remote_sessions
from agentkit.toolkit.cli.sandbox.tool_resolve import SandboxToolType
from agentkit.toolkit.cli.sandbox.utils import (
    echo_json,
    error,
    get_session_result,
)


def get_command(
    session_id: str = typer.Option(
        ...,
        "--session-id",
        help="Sandbox session ID to look up.",
    ),
    tool_id: Optional[str] = typer.Option(
        None,
        "--tool-id",
        help=f"Sandbox tool ID. Defaults to {SANDBOX_TOOL_ID_ENV}.",
    ),
    tool_type: SandboxToolType = typer.Option(
        SandboxToolType.CODE_ENV,
        "--tool-type",
        help="Sandbox tool type to resolve when --tool-id is omitted.",
    ),
) -> None:
    """Get a sandbox session after syncing remote sessions for the current tool."""
    try:
        resolved_tool_id = sync_remote_sessions(
            session_id=session_id,
            tool_id=tool_id,
            tool_type=tool_type,
            client=AgentkitToolsClient(),
            env_var_name=SANDBOX_TOOL_ID_ENV,
        )
        result = get_session_result(session_id)
    except typer.Exit:
        raise
    except Exception as exc:
        error(str(exc))

    if resolved_tool_id and result.get("tool_id") != resolved_tool_id:
        error(f"Sandbox session not found: {session_id}")

    echo_json(result)
