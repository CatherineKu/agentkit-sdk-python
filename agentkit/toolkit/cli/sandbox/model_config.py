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

"""Model and runtime configuration helpers for sandbox CLI."""

from __future__ import annotations

import json

MODEL_NAME_ENV_KEYS = ("OPENCODE_MODEL", "CODEX_MODEL", "ANTHROPIC_MODEL")
MODEL_API_KEY_ENV_KEYS = (
    "OPENCODE_API_KEY",
    "CODEX_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
)
MODEL_BASE_URL_ENV_KEYS = (
    "OPENCODE_BASE_URL",
    "CODEX_BASE_URL",
    "MODEL_BASE_URL",
)
ANTHROPIC_BASE_URL_ENV_KEYS = ("ANTHROPIC_BASE_URL",)
MODEL_API_KEY_ENV = "MODEL_API_KEY"

CODE_ENV_HOME = "/home/gem"
CODE_ENV_CODEX_HOME = "/home/gem/.codex"
CODEX_CONFIG_TOML_ENV = "CODEX_CONFIG_TOML"
CODEX_MODEL_CATALOG_JSON_ENV = "CODEX_MODEL_CATALOG_JSON"
CODEX_MODEL_CATALOG_PATH = f"{CODE_ENV_CODEX_HOME}/model-catalog.json"
DEFAULT_MODEL_NAME = "deepseek-v4-flash-260425"
DEFAULT_MODEL_NAME_LIST = (
    DEFAULT_MODEL_NAME,
    "deepseek-v4-pro-260425",
    "doubao-seed-2-0-pro-260215",
)
DEFAULT_MODEL_CONTEXT_WINDOW = 1000000
MODEL_CONTEXT_WINDOW_OVERRIDES = {
    "doubao-seed-2-0-pro-260215": 256000,
}
DEFAULT_MODEL_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_ANTHROPIC_BASE_URL = "https://ark.cn-beijing.volces.com/api/compatible"


def _toml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def build_codex_config_toml(model_name: str) -> str:
    quoted_model = _toml_quote(model_name)
    return "\n".join(
        [
            'model_provider = "codex"',
            f"model = {quoted_model}",
            f"review_model = {quoted_model}",
            'approval_policy = "never"',
            'sandbox_mode = "danger-full-access"',
            'model_reasoning_effort = "medium"',
            'personality = "pragmatic"',
            "check_for_update_on_startup = false",
            'web_search = "disabled"',
            f"model_catalog_json = {_toml_quote(CODEX_MODEL_CATALOG_PATH)}",
            'developer_instructions = """',
            (
                "When the user asks for simple browser operation tasks, "
                "you can use xdg-open to complete them."
            ),
            '"""',
            "",
            "[model_providers.codex]",
            'name = "codex"',
            f"base_url = {_toml_quote(DEFAULT_MODEL_BASE_URL)}",
            'wire_api = "responses"',
            'env_key = "CODEX_API_KEY"',
            "",
            "[tui]",
            "show_tooltips = false",
            "",
            '[projects."/home/gem"]',
            'trust_level = "trusted"',
            "",
            "[mcp_servers.browser-use]",
            'url = "http://localhost:8100/mcp"',
            "",
        ]
    )


def _build_model_catalog_item(model_name: str, max_context_window: int) -> dict:
    return {
        "slug": model_name,
        "display_name": model_name,
        "supported_reasoning_levels": [
            {
                "effort": "low",
                "description": "Fast responses with lighter reasoning",
            },
            {
                "effort": "medium",
                "description": "Balances speed and reasoning depth",
            },
            {
                "effort": "high",
                "description": "Greater reasoning depth",
            },
        ],
        "max_context_window": max_context_window,
        "shell_type": "shell_command",
        "visibility": "list",
        "supported_in_api": True,
        "priority": 100,
        "base_instructions": "",
        "supports_reasoning_summaries": True,
        "support_verbosity": False,
        "truncation_policy": {"mode": "tokens", "limit": 10000},
        "supports_parallel_tool_calls": False,
        "experimental_supported_tools": [],
    }


def model_catalog_context_window(model_name: str) -> int:
    return MODEL_CONTEXT_WINDOW_OVERRIDES.get(
        model_name,
        DEFAULT_MODEL_CONTEXT_WINDOW,
    )


def build_codex_model_catalog_json(model_name: str) -> str:
    deduped_model_names = list(
        dict.fromkeys((model_name, *DEFAULT_MODEL_NAME_LIST))
    )
    payload = {
        "models": [
            _build_model_catalog_item(
                name,
                model_catalog_context_window(name),
            )
            for name in deduped_model_names
        ]
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
