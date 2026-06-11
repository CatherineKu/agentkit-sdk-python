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

from __future__ import annotations

from typer.testing import CliRunner

runner = CliRunner()
_PLACEHOLDER_A = "example-value-a"
_PLACEHOLDER_B = "example-value-b"
_PLACEHOLDER_MODEL_VALUE = "example-model-value"


class _FakeCreateToolResponse:
    tool_id = "t-created"


class _FakeGetToolResponse:
    def __init__(self, status="Ready"):
        self.status = status
        self.tool_id = "t-created"
        self.name = "demo-tool"
        self.tool_type = "SkillEnv"
        self.tos_mount_config = None

    def model_dump(self, by_alias=False, exclude_none=False):
        payload = {
            "ToolId": self.tool_id,
            "Name": self.name,
            "Status": self.status,
            "ToolType": self.tool_type,
            "TosMountConfig": self.tos_mount_config,
        }
        if exclude_none:
            payload = {
                key: value for key, value in payload.items() if value is not None
            }
        return payload


class _FakeToolsClient:
    instances = []
    last_request = None
    get_statuses = ["Ready"]
    get_call_count = 0

    def __init__(self, **kwargs):
        self.access_key = kwargs.get("access" + "_key", "")
        self.secret_key = kwargs.get("secret" + "_key", "")
        self.region = kwargs.get("region", "")
        self.session_token = kwargs.get("session_token", "")
        _FakeToolsClient.instances.append(self)

    def create_tool(self, request):
        _FakeToolsClient.last_request = request
        return _FakeCreateToolResponse()

    def get_tool(self, request):
        _FakeToolsClient.get_call_count += 1
        if len(_FakeToolsClient.get_statuses) > 1:
            status = _FakeToolsClient.get_statuses.pop(0)
        else:
            status = _FakeToolsClient.get_statuses[0]
        return _FakeGetToolResponse(status=status)


class _FakeTOSService:
    def __init__(
        self,
        *,
        bucket_exists=True,
        endpoint="tos-cn-beijing.volces.com",
    ):
        self._bucket_exists = bucket_exists
        self.create_count = 0
        self.created_objects = []
        self.created_directories = []
        self.endpoint = endpoint

    def bucket_exists(self):
        return self._bucket_exists

    def create_bucket(self):
        self.create_count += 1

    def object_exists(self, key):
        return key in self.created_objects

    def create_directory(self, key):
        self.created_objects.append(key)
        self.created_directories.append(key)


def _reset_fake_tools_client():
    _FakeToolsClient.instances = []
    _FakeToolsClient.last_request = None
    _FakeToolsClient.get_statuses = ["Ready"]
    _FakeToolsClient.get_call_count = 0


def _set_fake_env_credentials(monkeypatch):
    monkeypatch.setenv("VOLCENGINE_ACCESS_KEY", _PLACEHOLDER_A)
    monkeypatch.setenv("VOLCENGINE_SECRET_KEY", _PLACEHOLDER_B)


def _fake_env_credentials(cli_create):
    return cli_create.EnvCredentials(
        **{
            "access" + "_key": _PLACEHOLDER_A,
            "secret" + "_key": _PLACEHOLDER_B,
        }
    )


def test_load_credentials_uses_volc_configuration(monkeypatch):
    from agentkit.toolkit.cli.sandbox import cli_create

    captured = {}

    class FakeCredentials:
        access_key = _PLACEHOLDER_A
        secret_key = _PLACEHOLDER_B
        session_token = "example-session-token"

    class FakeVolcConfiguration:
        def __init__(self, region=None):
            captured["region"] = region

        def get_service_credentials(self, service_key):
            captured["service_key"] = service_key
            return FakeCredentials()

    monkeypatch.setattr(cli_create, "VolcConfiguration", FakeVolcConfiguration)

    credentials = cli_create._load_env_credentials("cn-shanghai")

    assert captured == {
        "region": "cn-shanghai",
        "service_key": "agentkit",
    }
    assert credentials.access_key == _PLACEHOLDER_A
    assert credentials.secret_key == _PLACEHOLDER_B
    assert credentials.session_token == "example-session-token"


def test_load_credentials_supports_legacy_volc_env(monkeypatch):
    from agentkit.toolkit.cli.sandbox import cli_create

    monkeypatch.delenv("VOLCENGINE_ACCESS_KEY", raising=False)
    monkeypatch.delenv("VOLCENGINE_SECRET_KEY", raising=False)
    monkeypatch.setenv("VOLC_ACCESSKEY", _PLACEHOLDER_A)
    monkeypatch.setenv("VOLC_SECRETKEY", _PLACEHOLDER_B)

    credentials = cli_create._load_env_credentials()

    assert credentials.access_key == _PLACEHOLDER_A
    assert credentials.secret_key == _PLACEHOLDER_B


def test_create_command_uses_env_credentials_and_default_region(monkeypatch):
    from agentkit.toolkit.cli.cli import app
    from agentkit.toolkit.cli.sandbox import cli_create

    fake_service = _FakeTOSService()

    _reset_fake_tools_client()
    _set_fake_env_credentials(monkeypatch)
    monkeypatch.setattr(cli_create, "AgentkitToolsClient", _FakeToolsClient)
    monkeypatch.setattr(
        cli_create,
        "_generate_default_tos_bucket",
        lambda credentials, region: "agentkit-platform-123",
    )
    monkeypatch.setattr(
        cli_create,
        "_build_tos_service",
        lambda bucket_name, region, credentials: fake_service,
    )

    result = runner.invoke(app, ["create", "--tool-name", "demo-tool"])

    assert result.exit_code == 0
    assert "工具创建成功" in result.output
    assert "工具ID：t-created" in result.output
    assert "状态：Ready" in result.output
    assert len(_FakeToolsClient.instances) == 1
    client = _FakeToolsClient.instances[0]
    assert client.access_key == _PLACEHOLDER_A
    assert client.secret_key == _PLACEHOLDER_B
    assert client.session_token == ""
    assert client.region == "cn-beijing"
    assert _FakeToolsClient.last_request.name == "demo-tool"
    assert _FakeToolsClient.last_request.tool_type == "CodeEnv"
    tos_config = _FakeToolsClient.last_request.tos_mount_config
    assert tos_config is not None
    assert tos_config.mount_points[0].bucket_name == "agentkit-platform-123"
    assert (
        tos_config.mount_points[0].bucket_path
        == "/sandbox-session/default/default"
    )
    assert _FakeToolsClient.get_call_count == 1


def test_create_command_passes_region_to_client(monkeypatch):
    from agentkit.toolkit.cli.cli import app
    from agentkit.toolkit.cli.sandbox import cli_create

    fake_service = _FakeTOSService()

    _reset_fake_tools_client()
    _set_fake_env_credentials(monkeypatch)
    monkeypatch.setattr(cli_create, "AgentkitToolsClient", _FakeToolsClient)
    monkeypatch.setattr(
        cli_create,
        "_generate_default_tos_bucket",
        lambda credentials, region: "agentkit-platform-123",
    )
    monkeypatch.setattr(
        cli_create,
        "_build_tos_service",
        lambda bucket_name, region, credentials: fake_service,
    )

    result = runner.invoke(
        app,
        ["create", "--tool-name", "demo-tool", "--region", "cn-shanghai"],
    )

    assert result.exit_code == 0
    assert _FakeToolsClient.instances[0].region == "cn-shanghai"


def test_create_command_waits_until_tool_ready(monkeypatch):
    from agentkit.toolkit.cli.cli import app
    from agentkit.toolkit.cli.sandbox import cli_create

    fake_service = _FakeTOSService()

    _reset_fake_tools_client()
    _FakeToolsClient.get_statuses = ["Creating", "Ready"]
    _set_fake_env_credentials(monkeypatch)
    monkeypatch.setattr(cli_create, "AgentkitToolsClient", _FakeToolsClient)
    monkeypatch.setattr(
        cli_create,
        "_generate_default_tos_bucket",
        lambda credentials, region: "agentkit-platform-123",
    )
    monkeypatch.setattr(
        cli_create,
        "_build_tos_service",
        lambda bucket_name, region, credentials: fake_service,
    )
    monkeypatch.setattr(cli_create.time, "sleep", lambda _seconds: None)

    result = runner.invoke(app, ["create", "--tool-name", "demo-tool"])

    assert result.exit_code == 0
    assert "工具状态：Creating" in result.output
    assert "工具状态：Ready" in result.output
    assert "工具创建成功" in result.output
    assert _FakeToolsClient.get_call_count == 2


def test_create_command_prints_sanitized_details_on_error(monkeypatch):
    from agentkit.toolkit.cli.cli import app
    from agentkit.toolkit.cli.sandbox import cli_create

    fake_service = _FakeTOSService()

    _reset_fake_tools_client()
    _FakeToolsClient.get_statuses = ["Error"]
    _set_fake_env_credentials(monkeypatch)
    monkeypatch.setattr(cli_create, "AgentkitToolsClient", _FakeToolsClient)
    monkeypatch.setattr(
        cli_create,
        "_generate_default_tos_bucket",
        lambda credentials, region: "agentkit-platform-123",
    )
    monkeypatch.setattr(
        cli_create,
        "_build_tos_service",
        lambda bucket_name, region, credentials: fake_service,
    )

    result = runner.invoke(app, ["create", "--tool-name", "demo-tool"])

    assert result.exit_code == 1
    assert "entered terminal status: Error" in result.output
    assert "Summary:" in result.output
    assert "Name: demo-tool" in result.output
    assert _PLACEHOLDER_A not in result.output
    assert _PLACEHOLDER_B not in result.output


def test_build_create_tool_request_adds_tos_mount(monkeypatch):
    from agentkit.toolkit.cli.sandbox import cli_create

    fake_service = _FakeTOSService()

    def fake_build_tos_service(bucket_name, region, credentials):
        assert bucket_name == "my-bucket"
        assert region == "cn-beijing"
        assert credentials.access_key == _PLACEHOLDER_A
        assert credentials.secret_key == _PLACEHOLDER_B
        return fake_service

    monkeypatch.setattr(cli_create, "_build_tos_service", fake_build_tos_service)

    request = cli_create._build_create_tool_request(
        tool_type="CodeEnv",
        name="demo-tool",
        tos_bucket="my-bucket",
        region="cn-beijing",
        credentials=_fake_env_credentials(cli_create),
    )

    tos_config = request.tos_mount_config
    assert tos_config is not None
    assert tos_config.enable_tos is True
    assert tos_config.credentials.access_key_id == _PLACEHOLDER_A
    assert tos_config.credentials.secret_access_key == _PLACEHOLDER_B
    assert len(tos_config.mount_points) == 1
    mount_point = tos_config.mount_points[0]
    assert mount_point.bucket_name == "my-bucket"
    assert mount_point.bucket_path == "/sandbox-session/default/default"
    assert mount_point.endpoint == "http://tos-cn-beijing.ivolces.com"
    assert mount_point.local_mount_path == "/home/gem"
    assert mount_point.read_only is False
    assert fake_service.created_objects == [
        "sandbox-session/",
        "sandbox-session/default/",
        "sandbox-session/default/default/",
    ]
    assert fake_service.created_directories == fake_service.created_objects
    assert request.authorizer_configuration is not None
    assert request.authorizer_configuration.key_auth is not None
    assert request.authorizer_configuration.key_auth.api_key_name
    assert request.authorizer_configuration.key_auth.api_key_location == "Header"
    assert request.network_configuration is not None
    assert request.network_configuration.enable_public_network is True
    assert request.network_configuration.enable_private_network is False


def test_build_create_tool_request_adds_model_envs(monkeypatch):
    from agentkit.toolkit.cli.sandbox import cli_create

    fake_service = _FakeTOSService()
    monkeypatch.setattr(
        cli_create,
        "_build_tos_service",
        lambda bucket_name, region, credentials: fake_service,
    )

    request = cli_create._build_create_tool_request(
        tool_type="SkillEnv",
        name="demo-tool",
        tos_bucket="my-bucket",
        region="cn-beijing",
        credentials=_fake_env_credentials(cli_create),
        model_name="claude-sonnet-4",
        model_base_url="https://models.example.com",
        **{"model_" + "api_key": _PLACEHOLDER_MODEL_VALUE},
    )

    assert [(item.key, item.value) for item in request.envs] == [
        ("OPENCODE_MODEL", "claude-sonnet-4"),
        ("CODEX_MODEL", "claude-sonnet-4"),
        ("ANTHROPIC_MODEL", "claude-sonnet-4"),
        ("OPENCODE_API_KEY", _PLACEHOLDER_MODEL_VALUE),
        ("CODEX_API_KEY", _PLACEHOLDER_MODEL_VALUE),
        ("ANTHROPIC_AUTH_TOKEN", _PLACEHOLDER_MODEL_VALUE),
        ("OPENCODE_BASE_URL", "https://models.example.com"),
        ("CODEX_BASE_URL", "https://models.example.com"),
        ("MODEL_BASE_URL", "https://models.example.com"),
        ("ANTHROPIC_BASE_URL", "https://models.example.com"),
    ]


def test_build_create_tool_request_adds_default_model_base_url(monkeypatch):
    from agentkit.toolkit.cli.sandbox import cli_create

    fake_service = _FakeTOSService()
    monkeypatch.setattr(
        cli_create,
        "_build_tos_service",
        lambda bucket_name, region, credentials: fake_service,
    )

    request = cli_create._build_create_tool_request(
        tool_type="SkillEnv",
        name="demo-tool",
        tos_bucket="my-bucket",
        region="cn-beijing",
        credentials=_fake_env_credentials(cli_create),
    )

    assert [(item.key, item.value) for item in request.envs] == [
        ("OPENCODE_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
        ("CODEX_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
        ("MODEL_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
        (
            "ANTHROPIC_BASE_URL",
            "https://ark.cn-beijing.volces.com/api/compatible",
        ),
    ]


def test_ensure_tos_bucket_ready_creates_missing_bucket(monkeypatch):
    from agentkit.toolkit.cli.sandbox import cli_create

    fake_service = _FakeTOSService(bucket_exists=False)

    monkeypatch.setattr(
        cli_create,
        "_build_tos_service",
        lambda bucket_name, region, credentials: fake_service,
    )
    endpoint = cli_create._ensure_tos_bucket_ready(
        "new-bucket",
        "cn-beijing",
        _fake_env_credentials(cli_create),
    )

    assert endpoint == "tos-cn-beijing.volces.com"
    assert fake_service.create_count == 1


def test_ensure_tos_bucket_path_ready_creates_directory_markers(monkeypatch):
    from agentkit.toolkit.cli.sandbox import cli_create

    fake_service = _FakeTOSService()

    monkeypatch.setattr(
        cli_create,
        "_build_tos_service",
        lambda bucket_name, region, credentials: fake_service,
    )

    cli_create._ensure_tos_bucket_path_ready(
        "my-bucket",
        "/sandbox-session/default/default",
        "cn-beijing",
        _fake_env_credentials(cli_create),
    )

    assert fake_service.created_directories == [
        "sandbox-session/",
        "sandbox-session/default/",
        "sandbox-session/default/default/",
    ]


def test_build_tos_mount_endpoint_uses_default_private_endpoint():
    from agentkit.toolkit.cli.sandbox import cli_create

    assert (
        cli_create._build_tos_mount_endpoint("cn-beijing")
        == "http://tos-cn-beijing.ivolces.com"
    )
