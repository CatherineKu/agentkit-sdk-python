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

"""Mount command for sandbox CLI."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
from typing import Optional
from urllib.parse import urljoin
from urllib.request import urlopen

import typer

from agentkit.toolkit.cli.sandbox.tool_resolve import (
    READY_TOOL_STATUS,
    SandboxToolType,
    find_tool_result,
)
from agentkit.toolkit.cli.sandbox.utils import echo_json, error

SANDBOX_DISCOVERY_PATH = Path(".agentkit") / "sandbox" / "agentkit-cli"
USER_POOL_PATTERN = re.compile(r"userpool-([^.]+)\.userpool")


def _get_discovery_store_path() -> Path:
    return Path.cwd() / SANDBOX_DISCOVERY_PATH


def _resolve_required(value: str, option_name: str) -> str:
    resolved = (value or "").strip()
    if not resolved:
        error(f"{option_name} must not be empty")
    return resolved


def _record_string(record: dict[str, object], *keys: str) -> str | None:
    for key in keys:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _resolve_mount_tool_id(
    *,
    tool_id: Optional[str],
    tool_type: SandboxToolType,
) -> str:
    explicit_tool_id = (tool_id or "").strip()
    if explicit_tool_id:
        return explicit_tool_id

    resolved_tool_type = tool_type.value
    record = find_tool_result(resolved_tool_type)
    if not record:
        error(
            f"Sandbox tool ID not found in local cache for tool type: "
            f"{resolved_tool_type}. Pass --tool-id or run sandbox create first."
        )

    cached_tool_id = _record_string(record, "ToolId", "tool_id")
    if not cached_tool_id:
        error(f"Cached sandbox tool record missing ToolId: {resolved_tool_type}")

    status = _record_string(record, "Status", "status")
    if status != READY_TOOL_STATUS:
        error(
            f"Cached sandbox tool is not available: {cached_tool_id}. "
            f"Status: {status or 'Unknown'}. Expected: {READY_TOOL_STATUS}"
        )

    return cached_tool_id


def _build_discovery_url(oauth_url: str) -> str:
    return urljoin(f"{oauth_url.rstrip('/')}/", ".well-known/agentkit-cli")


def _download_discovery(oauth_url: str) -> dict[str, object]:
    discovery_url = _build_discovery_url(oauth_url)
    path = _get_discovery_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    with urlopen(discovery_url) as response:
        content = response.read()
    path.write_bytes(content)

    try:
        data = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        error(f"Invalid sandbox mount discovery file {path}: {exc}")

    if not isinstance(data, dict):
        error(f"Invalid sandbox mount discovery file {path}: expected JSON object")
    return data


def _required_discovery_field(
    discovery: dict[str, object],
    field_name: str,
) -> str:
    value = discovery.get(field_name)
    if not isinstance(value, str) or not value.strip():
        error(f"Sandbox mount discovery missing {field_name}")
    return value.strip()


def _extract_user_pool_id(issuer: str) -> str:
    match = USER_POOL_PATTERN.search(issuer)
    if not match:
        error("Sandbox mount discovery issuer missing user pool ID")
    return match.group(1)


def _build_tosbrowser_command(
    *,
    tos_bucket: str,
    tool_id: str,
    session_id: str,
    role_trn: str,
    user_pool_id: str,
    client_id: str,
) -> str:
    return (
        "tosbrowser://open?"
        f"path=tos://{tos_bucket}/sandbox-session/tool-{tool_id}/"
        f"session-{session_id}/"
        f"&type=oAuthLogin"
        f"&role={role_trn}"
        f"&userPool={user_pool_id}"
        f"&clientId={client_id}"
    )


def _open_tosbrowser(command: str) -> None:
    subprocess.run(["open", command], check=True)


def mount_command(
    session_id: str = typer.Option(
        ...,
        "--session-id",
        "--sid",
        "-s",
        help="Sandbox session ID to mount.",
    ),
    oauth_url: str = typer.Option(
        ...,
        "--oauth-url",
        help="OAuth discovery base URL.",
    ),
    tos_bucket: str = typer.Option(
        ...,
        "--tos-bucket",
        help="TOS bucket to mount.",
    ),
    tool_id: Optional[str] = typer.Option(
        None,
        "--tool-id",
        help=(
            "Sandbox tool ID. Defaults to the local cached tool for --tool-type."
        ),
    ),
    tool_type: SandboxToolType = typer.Option(
        SandboxToolType.CODE_ENV,
        "--tool-type",
        help="Sandbox tool type used for local tool cache lookup.",
    ),
) -> None:
    """Open the sandbox session TOS path in TOS Browser."""
    try:
        resolved_session_id = _resolve_required(session_id, "--session-id")
        resolved_oauth_url = _resolve_required(oauth_url, "--oauth-url")
        resolved_tos_bucket = _resolve_required(tos_bucket, "--tos-bucket")
        resolved_tool_id = _resolve_mount_tool_id(
            tool_id=tool_id,
            tool_type=tool_type,
        )
        discovery = _download_discovery(resolved_oauth_url)
        issuer = _required_discovery_field(discovery, "issuer")
        role_trn = _required_discovery_field(discovery, "role_trn")
        client_id = _required_discovery_field(discovery, "client_id")
        user_pool_id = _extract_user_pool_id(issuer)
        command = _build_tosbrowser_command(
            tos_bucket=resolved_tos_bucket,
            tool_id=resolved_tool_id,
            session_id=resolved_session_id,
            role_trn=role_trn,
            user_pool_id=user_pool_id,
            client_id=client_id,
        )
        _open_tosbrowser(command)
    except typer.Exit:
        raise
    except Exception as exc:
        error(str(exc))

    echo_json(
        {
            "tool_id": resolved_tool_id,
            "session_id": resolved_session_id,
            "command": command,
        }
    )
