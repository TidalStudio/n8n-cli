# n8n-cli

A command-line interface for interacting with n8n.

## Installation

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

## Usage

```bash
# Show help
n8n-cli --help

# Show version
n8n-cli --version
```

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

## License

MIT
