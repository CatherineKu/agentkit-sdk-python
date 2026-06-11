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

"""Minimal signed Volcengine OpenAPI client for the auth ADMIN commands.

Stdlib-only SigV4 (reusing :mod:`agentkit.auth._sigv4`) so the admin path that
provisions the UserPool client / IAM OIDC provider / STS role carries no
third-party dependency. Used only by ``agentkit auth admin`` — the end-user login
path never touches it. A mandatory ``GetCallerIdentity`` guard runs before any write.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from agentkit.auth._sigv4 import sign_headers
from agentkit.auth.errors import AuthError
from agentkit.auth.ssl_trust import harden_default_ssl_context

_HOST = "open.volcengineapi.com"
# Services whose OpenAPI reads parameters from the query string, not a JSON body.
_QUERY_PARAM_SERVICES = {"iam"}


class ApiError(AuthError):
    """A Volcengine OpenAPI call returned an error. Subclasses AuthError so the CLI's
    ``except AuthError`` handlers surface it as a clean message, not a traceback."""

    def __init__(self, action: str, code: str, message: str) -> None:
        super().__init__(f"{action}: {code}: {message}")
        self.action = action
        self.code = code
        self.message = message


class OpenApiClient:
    """Signed Volcengine OpenAPI caller with an account guard (admin use only)."""

    def __init__(
        self,
        *,
        access_key: str | None = None,
        secret_key: str | None = None,
        session_token: str | None = None,
        region: str = "cn-beijing",
        expect_account: str | None = None,
        harden_ssl: bool = True,
    ) -> None:
        if harden_ssl:
            harden_default_ssl_context()
        self.ak = access_key or os.getenv("VOLCENGINE_ACCESS_KEY") or os.getenv("VOLC_ACCESSKEY")
        self.sk = secret_key or os.getenv("VOLCENGINE_SECRET_KEY") or os.getenv("VOLC_SECRETKEY")
        self.token = session_token or os.getenv("VOLCENGINE_SESSION_TOKEN")
        if not (self.ak and self.sk):
            raise AuthError(
                "admin provisioning needs Volcengine credentials.",
                hint="export VOLCENGINE_ACCESS_KEY / VOLCENGINE_SECRET_KEY for the account that owns the UserPool.",
            )
        self.region = region
        ident = self.call("sts", "GetCallerIdentity", "2018-01-01", {})
        self.account_id = str(ident.get("AccountId") or "")
        if expect_account and self.account_id != expect_account:
            raise AuthError(
                f"refusing to provision: caller account {self.account_id} != expected {expect_account}"
            )

    def call(self, service: str, action: str, version: str, body: dict) -> dict:
        if service in _QUERY_PARAM_SERVICES:
            query = {"Action": action, "Version": version}
            for k, v in body.items():
                if isinstance(v, (list, tuple)):
                    for i, item in enumerate(v):
                        query[f"{k}.{i + 1}"] = str(item)
                else:
                    query[k] = str(v)
            payload = b""
        else:
            query = {"Action": action, "Version": version}
            payload = json.dumps(body).encode()
        headers = sign_headers(
            "POST", _HOST, query, payload,
            access_key=self.ak, secret_key=self.sk, service=service, region=self.region,
            session_token=self.token,
        )
        url = f"https://{_HOST}/?{urllib.parse.urlencode(query)}"
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        try:
            raw = urllib.request.urlopen(req, timeout=30).read()
        except urllib.error.HTTPError as exc:
            raw = exc.read()
        data = json.loads(raw)
        err = (data.get("ResponseMetadata") or {}).get("Error")
        if err:
            raise ApiError(action, str(err.get("Code")), str(err.get("Message")))
        return data.get("Result") or {}

    def call_get(self, service: str, action: str, version: str, params: dict) -> dict:
        """GET-style signed call (params in the query string) — e.g. the vpc service."""
        query = {"Action": action, "Version": version}
        for k, v in params.items():
            if isinstance(v, (list, tuple)):
                for i, item in enumerate(v):
                    query[f"{k}.{i + 1}"] = str(item)
            else:
                query[k] = str(v)
        headers = sign_headers(
            "GET", _HOST, query, b"",
            access_key=self.ak, secret_key=self.sk, service=service, region=self.region,
            session_token=self.token,
        )
        url = f"https://{_HOST}/?{urllib.parse.urlencode(query)}"
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            raw = urllib.request.urlopen(req, timeout=30).read()
        except urllib.error.HTTPError as exc:
            raw = exc.read()
        data = json.loads(raw)
        err = (data.get("ResponseMetadata") or {}).get("Error")
        if err:
            raise ApiError(action, str(err.get("Code")), str(err.get("Message")))
        return data.get("Result") or {}

    def call_ok(self, service, action, version, body, *, ok=("Exist", "Duplicate", "Conflict", "AlreadyExist")):
        """Like :meth:`call` but swallow 'already exists'-style errors (idempotent ensure)."""
        try:
            return self.call(service, action, version, body)
        except ApiError as exc:
            if any(tok.lower() in exc.code.lower() for tok in ok):
                return {}
            raise
