# Repository Guidelines

## Project Structure

- `src/chat_agent/` contains the installable Python package.
  - `agent.py` wraps Google ADK sessions, runners, event handling, retries, and fallback behavior.
  - `app.py` implements the terminal interaction loop.
  - `config.py` loads environment variables and the system prompt.
  - `__main__.py` is the `python -m chat_agent` entry point.
- `tests/` contains unit tests for configuration, agent behavior, and the application loop.
- `prompts/system_prompt.md` contains the general-purpose agent instruction.
- `ADK_API_VERIFICATION.md` records verified Google ADK API details.
- `plan.md` is the technical plan; update it when architecture or scope changes.

## Development Commands

```bash
uv sync --extra dev                 # Install project and test dependencies
uv run python -m chat_agent         # Run the local terminal chat
uv run pytest                       # Run the test suite
uv build                            # Build distribution artifacts
```

Copy `.env.example` to `.env` and set `GEMINI_API_KEY` before running the application. Never commit `.env` or credentials.

## Coding Style and Naming

Use Python 3.11+, four-space indentation, type hints, and concise docstrings for public classes and functions. Follow `snake_case` for modules, functions, and variables; `PascalCase` for classes; and `UPPER_SNAKE_CASE` for constants. Keep terminal I/O in `app.py` and ADK integration in `agent.py`. No formatter or linter is currently configured; preserve the existing style and run tests after changes.

## Testing Guidelines

Use `pytest` with `pytest-asyncio`. Name files `test_*.py` and tests `test_<behavior>`. Unit tests must not require network access or a real API key; mock ADK runners and session services. Add integration tests separately and skip them when credentials are unavailable. Run `uv run pytest` before submitting changes.

## Commits and Pull Requests

The repository currently has only an initial setup commit, so no established commit convention exists. Use short, imperative messages such as `Add session lifecycle tests`. Pull requests should explain the behavior change, identify configuration or API changes, describe tests run, and include terminal output or screenshots when the user experience changes.

## Security and Configuration

Do not log API keys, prompts containing sensitive data, or conversation content. Validate configuration at startup. Verify Google ADK API changes against `ADK_API_VERIFICATION.md` and the pinned dependency range before modifying integration code.
