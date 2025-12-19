# n8n-cli

A command-line interface for interacting with n8n workflow automation.

## Features

- **Workflow Management** - List, create, update, delete, enable, and disable workflows
- **Execution Control** - Trigger workflows, monitor executions, and retrieve results
- **Flexible Output** - JSON (default) or formatted tables
- **Agent-Friendly** - Designed for AI agent integration with structured JSON output
- **Secure Configuration** - Credentials stored with proper file permissions

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [Command Reference](#command-reference)
- [Global Options](#global-options)
- [Agent Integration](#agent-integration)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

## Installation

### Using pip

```bash
pip install n8n-cli
```

### Using pipx (recommended for CLI tools)

```bash
pipx install n8n-cli
```

### Development Installation

```bash
# Clone the repository
git clone https://github.com/your-org/n8n-cli.git
cd n8n-cli

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

## Configuration

Before using the CLI, configure your n8n instance credentials.

### Interactive Setup

```bash
n8n-cli configure
```

This prompts for:
- **n8n API URL** - Your n8n instance URL (e.g., `http://localhost:5678`)
- **API Key** - Your n8n API key

Configuration is saved to `~/.config/n8n-cli/.env` with secure permissions.

### Non-Interactive Setup (CI/CD)

```bash
n8n-cli configure --url http://localhost:5678 --api-key your-api-key
```

### Environment Variable Override

Environment variables take precedence over saved configuration:

```bash
export N8N_API_URL=http://localhost:5678
export N8N_API_KEY=your-api-key
n8n-cli workflows
```

## Quick Start

```bash
# 1. Configure credentials
n8n-cli configure

# 2. List all workflows
n8n-cli workflows

# 3. Trigger a workflow
n8n-cli trigger 123

# 4. Check execution status
n8n-cli execution 456
```

## Command Reference

### configure

Configure n8n-cli with your n8n instance credentials.

```bash
n8n-cli configure [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `--url URL` | n8n instance URL (e.g., http://localhost:5678) |
| `--api-key KEY` | n8n API key for authentication |

**Examples:**
```bash
# Interactive setup
n8n-cli configure

# Non-interactive (CI/CD)
n8n-cli configure --url http://localhost:5678 --api-key your-key
```

---

### workflows

List all workflows in the n8n instance.

```bash
n8n-cli workflows [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `--active` | Filter to only active workflows |
| `--inactive` | Filter to only inactive workflows |
| `--tag TAG` | Filter by tag name (can be repeated) |

**Examples:**
```bash
# List all workflows
n8n-cli workflows

# List only active workflows
n8n-cli workflows --active

# Filter by tag
n8n-cli workflows --tag production

# Filter by multiple tags
n8n-cli workflows --tag production --tag critical

# Table format
n8n-cli workflows --format table
```

**Output (JSON):**
```json
[
  {
    "id": "123",
    "name": "My Workflow",
    "active": true,
    "updatedAt": "2024-01-15T10:30:00.000Z"
  }
]
```

---

### workflow

Get detailed information about a specific workflow.

```bash
n8n-cli workflow WORKFLOW_ID
```

**Examples:**
```bash
n8n-cli workflow 123
```

**Output includes:** id, name, active status, nodes, connections, timestamps.

---

### create

Create a new workflow from a JSON definition.

```bash
n8n-cli create [OPTIONS]
```

**Options:**
| Option | Short | Description |
|--------|-------|-------------|
| `--file PATH` | `-f` | Path to workflow JSON file |
| `--stdin` | | Read workflow JSON from stdin |
| `--name NAME` | `-n` | Override the workflow name |
| `--activate` | `-a` | Activate immediately after creation |

**Examples:**
```bash
# Create from file
n8n-cli create --file workflow.json

# Create and activate
n8n-cli create --file workflow.json --activate

# Create with custom name
n8n-cli create --file workflow.json --name "Production Workflow"

# Create from stdin
cat workflow.json | n8n-cli create --stdin

# Create from stdin with name
echo '{"nodes": [], "connections": {}}' | n8n-cli create --stdin --name "Empty Workflow"
```

---

### update

Update an existing workflow.

```bash
n8n-cli update WORKFLOW_ID [OPTIONS]
```

**Options:**
| Option | Short | Description |
|--------|-------|-------------|
| `--file PATH` | `-f` | Path to workflow JSON file |
| `--stdin` | | Read workflow JSON from stdin |
| `--name NAME` | `-n` | Update the workflow name |
| `--activate` | | Activate the workflow |
| `--deactivate` | | Deactivate the workflow |

**Examples:**
```bash
# Replace entire workflow definition
n8n-cli update 123 --file workflow.json

# Just rename a workflow
n8n-cli update 123 --name "New Name"

# Activate a workflow
n8n-cli update 123 --activate

# Combined: update definition, rename, and activate
n8n-cli update 123 --file workflow.json --name "My Workflow" --activate
```

---

### delete

Delete a workflow by ID.

```bash
n8n-cli delete WORKFLOW_ID [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `--confirm` | Confirm deletion (required unless using --force) |
| `--force` | Force deletion without confirmation |

**Examples:**
```bash
# Delete with confirmation
n8n-cli delete 123 --confirm

# Force delete (for scripting)
n8n-cli delete 123 --force

# Force required for active workflows
n8n-cli delete 123 --force  # if workflow is active
```

---

### enable

Enable (activate) a workflow by ID.

```bash
n8n-cli enable WORKFLOW_ID
```

**Examples:**
```bash
n8n-cli enable 123
```

Activates the workflow so it can be triggered via webhooks or schedules. This operation is idempotent.

---

### disable

Disable (deactivate) a workflow by ID.

```bash
n8n-cli disable WORKFLOW_ID
```

**Examples:**
```bash
n8n-cli disable 123
```

Deactivates the workflow. This operation is idempotent.

---

### executions

List workflow executions.

```bash
n8n-cli executions [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `--workflow ID` | Filter by workflow ID |
| `--status STATUS` | Filter by status: success, error, running, waiting, canceled |
| `--limit N` | Number of results (default: 20, max: 250) |

**Examples:**
```bash
# List recent executions
n8n-cli executions

# Filter by workflow
n8n-cli executions --workflow 123

# Filter by status
n8n-cli executions --status error

# Combine filters
n8n-cli executions --workflow 123 --status success --limit 50
```

---

### execution

Get detailed information about a specific execution.

```bash
n8n-cli execution EXECUTION_ID
```

**Examples:**
```bash
n8n-cli execution 456
```

**Output includes:** id, workflowId, status, timestamps, and execution data with node outputs.

---

### trigger

Trigger workflow execution.

```bash
n8n-cli trigger WORKFLOW_ID [OPTIONS]
```

**Options:**
| Option | Short | Description |
|--------|-------|-------------|
| `--data JSON` | `-d` | JSON input data to pass to the workflow |
| `--file PATH` | `-f` | Path to JSON file containing input data |
| `--wait` | `-w` | Wait for execution to complete |
| `--timeout SECS` | `-t` | Timeout in seconds when using --wait (default: 300) |

**Examples:**
```bash
# Simple trigger (returns immediately)
n8n-cli trigger 123

# Trigger with inline data
n8n-cli trigger 123 --data '{"email": "user@example.com"}'

# Trigger with data from file
n8n-cli trigger 123 --file input.json

# Wait for completion
n8n-cli trigger 123 --wait

# Wait with custom timeout
n8n-cli trigger 123 --wait --timeout 60

# Full example: data + wait
n8n-cli trigger 123 --data '{"key": "value"}' --wait --timeout 120
```

**Immediate output:**
```json
{
  "executionId": "456"
}
```

**Output with --wait:**
```json
{
  "id": "456",
  "workflowId": "123",
  "status": "success",
  "startedAt": "2024-01-15T10:30:00.000Z",
  "stoppedAt": "2024-01-15T10:30:05.000Z",
  "data": { ... }
}
```

## Global Options

These options are available for all commands:

| Option | Description |
|--------|-------------|
| `--format [json\|table]` | Output format (default: json) |
| `--no-color` | Disable colored output |
| `--debug` | Show full stack traces on errors |
| `--version` | Show version and exit |
| `--help` | Show help message |

**Examples:**
```bash
# JSON output (default)
n8n-cli workflows

# Table output
n8n-cli workflows --format table

# Disable colors (useful for logging)
n8n-cli workflows --no-color

# Debug mode for troubleshooting
n8n-cli workflows --debug
```

## Agent Integration

The n8n-cli is designed for AI agent integration with consistent JSON output.

### Why JSON Output?

JSON output (the default) is ideal for agents because:
- Structured data that's easy to parse
- Consistent field names across commands
- No formatting artifacts to strip

### Example: List and Filter Workflows

```bash
# Agent prompt: "List all active workflows"
n8n-cli workflows --active
```

**Agent parses response:**
```json
[
  {"id": "1", "name": "Email Notifications", "active": true, "updatedAt": "2024-01-15T10:00:00Z"},
  {"id": "2", "name": "Data Sync", "active": true, "updatedAt": "2024-01-14T15:30:00Z"}
]
```

### Example: Create Workflow from Agent-Generated JSON

```bash
# Agent generates workflow definition
WORKFLOW_JSON='{
  "name": "Agent-Created Workflow",
  "nodes": [
    {
      "parameters": {},
      "name": "Start",
      "type": "n8n-nodes-base.manualTrigger",
      "typeVersion": 1,
      "position": [250, 300]
    }
  ],
  "connections": {}
}'

# Create the workflow
echo "$WORKFLOW_JSON" | n8n-cli create --stdin --activate
```

**Response:**
```json
{
  "id": "123",
  "name": "Agent-Created Workflow",
  "active": true,
  "createdAt": "2024-01-15T12:00:00Z",
  "updatedAt": "2024-01-15T12:00:00Z"
}
```

### Example: Trigger Workflow and Parse Response

```bash
# Trigger with data and wait for result
n8n-cli trigger 123 --data '{"customer_id": "C001", "action": "notify"}' --wait --timeout 60
```

**Response:**
```json
{
  "id": "456",
  "workflowId": "123",
  "status": "success",
  "startedAt": "2024-01-15T12:05:00Z",
  "stoppedAt": "2024-01-15T12:05:03Z",
  "data": {
    "resultData": {
      "runData": {
        "Send Email": [{"data": {"main": [[{"json": {"success": true}}]]}}]
      }
    }
  }
}
```

### Example: Monitor Execution Status

```bash
# Get execution ID from trigger
EXEC_ID=$(n8n-cli trigger 123 | jq -r '.executionId')

# Poll for completion
while true; do
  STATUS=$(n8n-cli execution "$EXEC_ID" | jq -r '.status')
  echo "Status: $STATUS"

  if [[ "$STATUS" == "success" || "$STATUS" == "error" ]]; then
    break
  fi

  sleep 2
done

# Get final result
n8n-cli execution "$EXEC_ID"
```

### Example: Multi-Step Workflow Automation

```bash
#!/bin/bash
# Agent automation script

# Step 1: Find target workflow by tag
WORKFLOW_ID=$(n8n-cli workflows --tag automation | jq -r '.[0].id')

if [ -z "$WORKFLOW_ID" ]; then
  echo "No automation workflow found"
  exit 1
fi

# Step 2: Check if workflow is active
IS_ACTIVE=$(n8n-cli workflow "$WORKFLOW_ID" | jq -r '.active')

if [ "$IS_ACTIVE" != "true" ]; then
  echo "Activating workflow..."
  n8n-cli enable "$WORKFLOW_ID"
fi

# Step 3: Trigger with data and wait
RESULT=$(n8n-cli trigger "$WORKFLOW_ID" \
  --data '{"source": "agent", "timestamp": "'$(date -Iseconds)'"}' \
  --wait \
  --timeout 120)

# Step 4: Check result status
STATUS=$(echo "$RESULT" | jq -r '.status')
echo "Execution completed with status: $STATUS"

if [ "$STATUS" == "error" ]; then
  echo "Error details:"
  echo "$RESULT" | jq '.data'
  exit 1
fi

echo "Success!"
```

### Exit Codes for Agents

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error (API error, validation, etc.) |
| 2 | Configuration error (missing credentials) |

Agents can check exit codes to determine success/failure:

```bash
n8n-cli workflows
if [ $? -eq 0 ]; then
  echo "Success"
elif [ $? -eq 2 ]; then
  echo "Need to run: n8n-cli configure"
else
  echo "API or validation error"
fi
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `N8N_API_URL` | n8n instance URL | (from config file) |
| `N8N_API_KEY` | API authentication key | (from config file) |
| `N8N_CLI_FORMAT` | Default output format | `json` |
| `N8N_CLI_DEBUG` | Enable debug mode (show stack traces) | `false` |

**Example:**
```bash
# Override API URL for this command
N8N_API_URL=http://staging:5678 n8n-cli workflows

# Set default table output
export N8N_CLI_FORMAT=table
n8n-cli workflows  # Uses table format

# Enable debug mode
N8N_CLI_DEBUG=true n8n-cli workflows
```

## Troubleshooting

### Connection Refused

**Error:** `Connection error: Cannot connect to n8n instance`

**Causes:**
- n8n is not running
- Wrong URL in configuration
- Firewall blocking connection

**Solutions:**
1. Verify n8n is running: `curl http://localhost:5678/healthz`
2. Check configured URL: `cat ~/.config/n8n-cli/.env`
3. Reconfigure: `n8n-cli configure`

---

### 401 Unauthorized

**Error:** `Authentication failed: Invalid or expired API key`

**Causes:**
- Invalid API key
- API key expired or revoked

**Solutions:**
1. Generate a new API key in n8n Settings > API
2. Reconfigure: `n8n-cli configure`

---

### 404 Not Found

**Error:** `Not found: Workflow not found: 123`

**Causes:**
- Workflow/execution ID doesn't exist
- Workflow was deleted

**Solutions:**
1. List available workflows: `n8n-cli workflows`
2. Verify the ID is correct

---

### Timeout Error

**Error:** `Timeout: Execution did not complete within 300s`

**Causes:**
- Workflow takes longer than timeout
- n8n instance is slow or overloaded

**Solutions:**
1. Increase timeout: `n8n-cli trigger 123 --wait --timeout 600`
2. Use async mode without `--wait` and poll manually

---

### Configuration Not Found

**Error:** `Configuration required. Run 'n8n-cli configure' first.`

**Causes:**
- First time using the CLI
- Config file was deleted

**Solutions:**
1. Run initial setup: `n8n-cli configure`
2. Or set environment variables:
   ```bash
   export N8N_API_URL=http://localhost:5678
   export N8N_API_KEY=your-api-key
   ```

---

### Invalid JSON

**Error:** `Invalid JSON - Expecting property name at line 1, column 2`

**Causes:**
- Malformed JSON in `--data` flag
- Invalid JSON file

**Solutions:**
1. Validate JSON: `echo '{"key": "value"}' | jq .`
2. Check for common issues: missing quotes, trailing commas

## Development

### Running Tests

```bash
pytest
```

### Linting and Type Checking

```bash
# Run linter
ruff check .

# Run type checker
mypy src/
```

### Project Structure

```
n8n-cli/
├── src/n8n_cli/
│   ├── main.py           # CLI entry point
│   ├── client.py         # Async HTTP client
│   ├── config.py         # Configuration management
│   ├── output.py         # Output formatting
│   ├── exceptions.py     # Custom exceptions
│   └── commands/         # Individual commands
├── tests/                # Test suite
└── pyproject.toml        # Project configuration
```

## License

MIT
