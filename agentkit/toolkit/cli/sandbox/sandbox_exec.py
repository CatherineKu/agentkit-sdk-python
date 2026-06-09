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

"""Exec command for sandbox CLI."""

from __future__ import annotations

from typing import Optional

import requests
import typer

from agentkit.toolkit.cli.sandbox.utils import (
    SANDBOX_EXEC_TIMEOUT_SECONDS,
    build_exec_url,
    echo_json,
    error,
    get_session_result,
    rename_exec_session_id,
)


def exec_command(
    user_session_id: str = typer.Option(
        ...,
        "--user-session-id",
        help="User session ID to execute against.",
    ),
    command: str = typer.Option(
        ...,
        "--command",
        help="Command to execute.",
    ),
    exec_dir: Optional[str] = typer.Option(
        None,
        "--exec-dir",
        help="Execution directory.",
    ),
    shell_id: Optional[str] = typer.Option(
        None,
        "--shell-id",
        help="Shell terminal ID for re-entering an existing shell.",
    ),
) -> None:
    """Execute a command in a sandbox shell."""
    session = get_session_result(user_session_id)
    url = build_exec_url(session.get("endpoint"))
    body = {
        "id": shell_id or "",
        "exec_dir": exec_dir or "",
        "command": command,
    }

    try:
        response = requests.post(
            url,
            json=body,
            timeout=SANDBOX_EXEC_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        error(str(exc))

    try:
        payload = response.json()
    except ValueError:
        error(f"Invalid sandbox exec response: {response.text}")

    echo_json(rename_exec_session_id(payload))
