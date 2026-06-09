# AgentKit Sandbox CLI

The sandbox CLI provides helper commands for creating and reusing AgentKit tool
sandbox sessions.

## Commands

### Create

Create a sandbox session through `CreateSession` and persist the result locally.

```bash
agentkit sandbox create \
  --user-session-id 123456789 \
  --ttl 28800 \
  --tool-id t-example
```

Options:

- `--user-session-id`: optional. Defaults to a generated UUID.
- `--ttl`: optional. Defaults to `AGENTKIT_SANDBOX_TTL`, then `28800`.
- `--tool-id`: optional. Defaults to `AGENTKIT_SANDBOX_TOOL_ID`. If neither is
  set, the command fails.

Output:

```json
{
  "user_session_id": "123456789",
  "tool_id": "t-example",
  "session_id": "s-example",
  "endpoint": "https://example.com/?Authorization=..."
}
```

### Get

Read a created sandbox session from the local session store.

```bash
agentkit sandbox get --user-session-id 123456789
```

Options:

- `--user-session-id`: required. User session ID to look up.

### Exec

Execute a command in a sandbox shell.

```bash
agentkit sandbox exec \
  --user-session-id 123456789 \
  --command 'echo $TEST_VAR' \
  --shell-id shell-example
```

Options:

- `--user-session-id`: required. Used to look up the stored endpoint.
- `--command`: required. Command to execute in the sandbox.
- `--exec-dir`: optional execution directory.
- `--shell-id`: optional shell terminal ID for re-entering an existing shell.

The command posts to `<endpoint>/v1/shell/exec` with:

```json
{
  "id": "shell-example",
  "exec_dir": "",
  "command": "echo $TEST_VAR"
}
```

The response is returned as JSON. If the service returns `data.session_id`, the
CLI renames it to `data.shell_id`.

## Local Store

`agentkit sandbox create` writes session results to:

```text
.agentkit/sandbox/sessions.json
```

The file is a JSON object keyed by `user_session_id`:

```json
{
  "123456789": {
    "user_session_id": "123456789",
    "tool_id": "t-example",
    "session_id": "s-example",
    "endpoint": "https://example.com/?Authorization=..."
  }
}
```

Repeated creates with the same `user_session_id` overwrite the previous entry.

## Module Layout

- `cli.py`: registers the sandbox Typer app and subcommands.
- `sandbox_create.py`: create command implementation.
- `sandbox_get.py`: get command implementation.
- `sandbox_exec.py`: exec command implementation.
- `utils.py`: shared store, URL, JSON, and error helpers.
