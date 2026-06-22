# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd. and/or its affiliates.
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

"""AgentKit CLI - register deployed Runtime Agents to A2A registry."""

from typing import Optional

import typer

from agentkit.toolkit.cli.cli_add import (
    _REGISTER_DEFAULT_VERSION,
    _register_a2a_runtime_agent,
)


def register_command(
    space_id: str = typer.Option(
        ...,
        "--space-id",
        "--register-space-id",
        help="A2A registry space id.",
    ),
    runtime_id: str = typer.Option(
        ...,
        "--runtime-id",
        "--register-runtime-id",
        help="Runtime id to register.",
    ),
    network_type: str = typer.Option(
        "public",
        "--network-type",
        "--register-network-type",
        help="Runtime network address to register: public or private.",
    ),
    project_name: Optional[str] = typer.Option(
        None,
        "--project-name",
        "--register-project-name",
        help="A2A registry project name.",
    ),
    tag: list[str] = typer.Option(
        [],
        "--tag",
        "--register-tag",
        help="A2A agent tag in KEY=VALUE form. Can be repeated.",
    ),
    set_default_version: bool = typer.Option(
        True,
        "--set-default-version/--no-set-default-version",
        "--register-set-default-version/--register-no-set-default-version",
        help="Whether to set this runtime registration as the default version.",
    ),
    endpoint: Optional[str] = typer.Option(
        None,
        "--endpoint",
        "--register-endpoint",
        help="AgentKit OpenAPI endpoint for CreateA2aAgent.",
    ),
    region: Optional[str] = typer.Option(
        None,
        "--region",
        "--register-region",
        help="AgentKit OpenAPI region. Defaults to AGENTKIT_REGION/VOLCENGINE_REGION/cn-beijing.",
    ),
    version: str = typer.Option(
        _REGISTER_DEFAULT_VERSION,
        "--version",
        "--register-version",
        help="AgentKit OpenAPI version for CreateA2aAgent.",
    ),
    raw: bool = typer.Option(
        False,
        "--raw",
        "--register-raw",
        help="Print raw A2A registration result.",
    ),
) -> None:
    """Register any deployed Runtime Agent to the A2A registry."""
    _register_a2a_runtime_agent(
        subject="runtime agent",
        space_id=space_id,
        runtime_id=runtime_id,
        network_type=network_type,
        project_name=project_name,
        tags=tag,
        set_default_version=set_default_version,
        endpoint=endpoint,
        region=region,
        version=version,
        raw=raw,
    )
