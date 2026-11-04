# Chat Agent

Terminal-based chat agent using Google Agent Development Kit (ADK).

## Features

- Interactive terminal-based chat interface
- Context-aware conversations using Google ADK sessions
- Automatic model fallback for resilience
- Configurable via environment variables
- Clean exit handling (Ctrl+C, `/exit`)

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- Google Gemini API key

## Installation

1. Clone the repository
2. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```
3. Edit `.env` and set your `GEMINI_API_KEY`
4. Install dependencies:
   ```bash
   uv sync
   ```

## Usage

Start the chat agent:
```bash
uv run python -m chat_agent
```

Exit the chat:
- Type `/exit` and press Enter
- Press Ctrl+C

## Configuration

Edit `.env` to configure:

| Variable | Description | Default |
|----------|-------------|---------|
| `MODEL` | Primary Gemini model | `gemini-3.5-flash-lite` |
| `FALLBACK_MODEL` | Fallback model if primary fails | `gemini-3.6-flash-lite` |
| `GEMINI_API_KEY` | Google Gemini API key | (required) |
| `RETRY_MAX_ATTEMPTS` | Max retry attempts for failed requests | `3` |
| `TEMPERATURE` | Model creativity (0.0-1.0) | `0.7` |
| `MAX_OUTPUT_TOKENS` | Maximum response length | `2048` |

## Development

### Running Tests

```bash
uv run pytest
```

### Project Structure

```
.
├── src/chat_agent/
│   ├── __init__.py
│   ├── config.py      # Configuration and validation
│   ├── agent.py       # ADK agent wrapper (TODO)
│   ├── app.py         # Chat application loop (TODO)
│   └── __main__.py    # Entry point (TODO)
├── tests/
│   └── test_config.py # Configuration tests
├── prompts/
│   └── system_prompt.md # System prompt
├── pyproject.toml     # Project dependencies
└── .env               # Environment variables (gitignored)
```

## Implementation Status

- [x] Configuration module (`config.py`)
- [x] Configuration tests (`test_config.py`)
- [x] Agent module (`agent.py`)
- [x] Agent tests (`test_agent.py`)
- [x] Application module (`app.py`)
- [x] Application tests (`test_app.py`)
- [x] Main entry point (`__main__.py`)
- [x] **All 42 tests passing**
- [x] **Verified working with real Google ADK**

## License

MIT
