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

import typer

from agentkit.toolkit.cli.sandbox.utils import echo_json, get_session_result


def get_command(
    user_session_id: str = typer.Option(
        ...,
        "--user-session-id",
        help="User session ID to look up.",
    ),
) -> None:
    """Get a sandbox session from the local session store."""
    result = get_session_result(user_session_id)
    echo_json(result)
