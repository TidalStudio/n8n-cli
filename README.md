<p align="center">
  <img src="N8N-CLI.png" alt="n8n-cli logo" width="200">
</p>

<h1 align="center">n8n-cli</h1>

<p align="center">
  A command-line interface for interacting with n8n workflow automation.
</p>

<p align="center">
  <a href="https://pypi.org/project/n8n-cli/"><img src="https://img.shields.io/pypi/v/n8n-cli.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/n8n-cli/"><img src="https://img.shields.io/pypi/pyversions/n8n-cli.svg" alt="Python versions"></a>
  <a href="https://github.com/TidalStudio/n8n-cli/blob/main/LICENSE"><img src="https://img.shields.io/pypi/l/n8n-cli.svg" alt="License"></a>
  <a href="https://github.com/TidalStudio/n8n-cli/actions"><img src="https://github.com/TidalStudio/n8n-cli/actions/workflows/tests.yml/badge.svg" alt="Tests"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/badge/code%20style-ruff-000000.svg" alt="Code style: ruff"></a>
</p>

---

## Installation

```bash
pip install n8n-cli
```

Or with [pipx](https://pipx.pypa.io/) (recommended):

```bash
pipx install n8n-cli
```

## Quick Start

```bash
# Configure your n8n instance
n8n-cli configure

# List all workflows
n8n-cli workflows

# Trigger a workflow
n8n-cli trigger <workflow-id>

# Check execution status
n8n-cli execution <execution-id>
```

## Features

- **Workflow Management** - List, create, update, delete, enable, and disable workflows
- **Execution Control** - Trigger workflows, monitor executions, and retrieve results
- **Flexible Output** - JSON (default) or formatted tables
- **Agent-Friendly** - Designed for AI agent integration with structured JSON output
- **Secure Configuration** - Credentials stored with proper file permissions

## Commands

| Command | Description |
|---------|-------------|
| `configure` | Set up n8n API credentials |
| `workflows` | List all workflows |
| `workflow` | Get workflow details |
| `create` | Create a new workflow |
| `update` | Update an existing workflow |
| `update-node` | Update a specific node parameter |
| `delete` | Delete a workflow |
| `enable` | Activate a workflow |
| `disable` | Deactivate a workflow |
| `executions` | List workflow executions |
| `execution` | Get execution details |
| `trigger` | Trigger a workflow |

## Documentation

For detailed documentation, see the [Wiki](https://github.com/TidalStudio/n8n-cli/wiki):

- [Configuration](https://github.com/TidalStudio/n8n-cli/wiki/Configuration) - Setup and environment variables
- [Command Reference](https://github.com/TidalStudio/n8n-cli/wiki/Command-Reference) - Full command documentation
- [Agent Integration](https://github.com/TidalStudio/n8n-cli/wiki/Agent-Integration) - Using with AI agents
- [Troubleshooting](https://github.com/TidalStudio/n8n-cli/wiki/Troubleshooting) - Common issues and solutions

## License

MIT
