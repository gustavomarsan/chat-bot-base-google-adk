# Local Chat Agent — Technical Plan

**Status:** Initial local implementation
**Purpose:** Define the smallest useful version of a conversational agent that runs on a developer machine.

## 1. Goal

Build a simple terminal chat application. A user sends messages and receives replies from one general-purpose agent. The agent maintains context during the current process and answers naturally without being specialized for a particular domain.

The application runs locally from the terminal and sends chat requests to the configured Gemini API. It does not expose a public service or persist user data.

## 2. Scope

### 2.1 In scope

- Python 3.11+ dependencies managed with `uv`
- Local execution from the terminal
- One general chat agent
- Interactive stdin/stdout conversation
- Conversation history kept in memory while the process is running
- Configurable model and API key loaded from `.env`
- Basic error handling and a clean exit command
- Minimal tests for the conversation loop and configuration
- Agent framework: Google Agent Development Kit (ADK) - **Session objects** maintain conversation context automatically
- Primary LLM: Configured via `MODEL` environment variable (default: `gemini-3.5-flash-lite`)
- Fallback LLM: Configured via `FALLBACK_MODEL` environment variable (default: `gemini-3.6-flash-lite`) - used if primary model fails or is unavailable
- Google ADK manages conversation history internally via InMemorySessionService and Session objects; application does not need to track message history
- ADK uses async/await patterns for session management and agent execution

### 2.2 Out of scope

- Web or graphical UI
- Multiple agents, coordinator agents, specialist agents, or agent handoffs
- Agent tools and function calling
- User accounts, authentication, notifications, or analytics

---

## 3. User experience

The application starts in interactive chat mode:

```text
$ uv run python -m chat_agent
Chat agent started. Type /exit to quit.

You: Hello
Agent: Hi! How can I help?

You: /exit
Goodbye.
```

**Output Formatting:** Agent responses are rendered as Markdown for improved readability (bold text, numbered lists, and code blocks) using the `rich` library.

---
## 4. Requirements

## 4.1 Functional requirements

| ID | Requirement |
|---|---|
| FR-01 | The user can chat with one general-purpose agent in the terminal. |
| FR-02 | The agent receives the current conversation history for context. |
| FR-03 | Conversation history exists only in process memory and is discarded on exit. |
| FR-04 | `/exit` and Ctrl+C close the application cleanly without an error traceback. |
| FR-05 | Temporary model failures produce a short user-facing error and keep the chat running when possible. |
| FR-06 | Invalid or missing configuration is reported clearly at startup. |


## 4.2 Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-01 | **SOLID:** components have one responsibility each, depend on small abstractions where appropriate, and can be replaced or tested independently. SOLID must be applied without adding unnecessary framework complexity. |
| NFR-02 | **Session management:** Session is identified by user_id/session_id passed to Runner.run(). InMemorySessionService maintains conversation context automatically. Verify whether explicit session creation is required or if Runner handles it implicitly. |
| NFR-03 | **Configurability:** model name, API keys, limits and timeouts are set in `.env`, validated at startup. |
| NFR-04 | **Resilience:** model throttling and temporary errors are retried; the chat never crashes on a failed request. |
| NFR-05 | **Security:** API keys and secrets are never logged or displayed; configuration is validated before use. |
| NFR-06 | **Testability:** all business logic is unit-testable without network access (mock Runner/InMemorySessionService for tests). |

---


## 5. Minimal architecture

```text
Terminal input/output
        |
   ChatApplication
        |
     ChatAgent
        |
   ADK Runner + Session
        |
      ADK Agent
        |
    Gemini API
```

### Components

| Component | Responsibility |
|---|---|
| `ChatApplication` | Runs the input/output loop, handles exit, and coordinates one turn. |
| `ChatAgent` | Wraps ADK Runner and InMemorySessionService, creates Content messages, consumes event stream and returns only final textual response to ChatApplication, provides retry logic. Uses consistent user_id/session_id. |
| `Settings` | Loads and validates the model name, API key, and configuration from environment variables. |

### Key Architectural Decisions

**ADK Session-Based Design:** Google ADK uses a Runner to execute agents with explicit session management via InMemorySessionService. Sessions are identified by user and session identifiers; conversation history is maintained automatically.

- API key configures Gemini API client (exact mechanism varies)
- ADK Agent created once with model and instruction (stateless definition)
- InMemorySessionService manages session storage (no API key needed - local storage only)
- Runner created with application identifier and session service
- Runner.run() takes user/session identifiers and structured message (not plain strings)
- Messages use structured format (likely Content-like with role and parts)
- Runner executes agent asynchronously, producing events
- Session persists for entire terminal session (same identifiers), tracks conversation state
- Events stream from Runner.run() - ChatAgent must identify final response event and extract text from content
- Do not print intermediate or partial events - only final agent response
- No need to manually pass history - SessionService maintains context via identifiers
- **Note:** Exact parameter names and structures must be verified against google-adk 1.18 API

Keep these components small. Apply SOLID through clear responsibilities and small interfaces where they improve testability. Do not introduce unnecessary factories, dependency-injection frameworks, ports, adapters, or a multi-layer architecture.

**Technical Debt:**
- `ChatAgent` directly instantiates ADK components (Agent, Runner, InMemorySessionService) internally, which violates Dependency Inversion Principle (SOLID). For the single-provider prototype, this trade-off favors simplicity. When adding multiple LLM providers, refactor to inject a factory for better testability and provider swapping.
- Application uses asyncio for ADK integration, which adds complexity to the terminal I/O loop. This is necessary for ADK's async API.

## 6. Conversation flow

1. Load and validate settings.
2. Configure GEMINI_API_KEY for Gemini API client.
3. Create ADK Agent with configuration (model, instruction, temperature, max_output_tokens).
4. Create InMemorySessionService (no API key needed).
5. Create Runner with Agent, app_name, and InMemorySessionService.
6. Print a short startup message.
7. Read a user message.
8. If the message is `/exit`, stop.
9. Create types.Content message with role="user" and text part.
10. ChatAgent executes via Runner.run() with user_id, session_id, and Content message (async event stream).
11. ChatAgent filters event stream to identify final response event and extract text from content parts.
12. ChatAgent returns final text response to ChatApplication.
13. ChatApplication prints response.
14. Repeat until `/exit`, Ctrl+C, or end-of-input.

**Key simplification:** SessionService maintains conversation context via user_id/session_id. ChatAgent handles event filtering and extracts final response. Use same user_id/session_id for entire conversation.

If a model request fails, show a concise error and continue waiting for input when the process is still usable.

## 7. Configuration

Use a `.env` file for local development. Configuration uses Google ADK standard environment variables.

Suggested variables:

```env
MODEL=gemini-3.5-flash-lite
FALLBACK_MODEL=gemini-3.6-flash-lite
GEMINI_API_KEY=<your-google-api-key>
RETRY_MAX_ATTEMPTS=3
TEMPERATURE=0.7
MAX_OUTPUT_TOKENS=2048
```

### Environment Variables

| Variable | Purpose | Used By |
|---|---|---|
| `MODEL` | Primary Gemini model to use | ADK Agent creation |
| `FALLBACK_MODEL` | Fallback model if primary fails | Error handling / retry logic |
| `GEMINI_API_KEY` | Authentication for Gemini API | Model/API client configuration |
| `RETRY_MAX_ATTEMPTS` | Maximum retry attempts for failed requests | Application retry strategy |
| `TEMPERATURE` | Model creativity (0.0-1.0) | ADK Agent configuration |
| `MAX_OUTPUT_TOKENS` | Maximum response length | ADK Agent configuration |

**Note:** Google ADK manages the conversation context window size automatically based on the model's capabilities.

**Fallback behavior:** On a retryable primary model failure, recreate the Agent with FALLBACK_MODEL and continue using the same InMemorySessionService and session identifiers. If the fallback also fails, show an error and retain the session for the next user turn.

**Note on fallback limitation (accepted for MVP):** If the primary request reaches ADK and partially updates the session before failing, the fallback may add the same user message again, resulting in possible duplicate turns. Reusing the same session preserves history, but it does not guarantee that the failed turn was rolled back.

Do not commit `.env` or secrets. Never print the API key or include it in logs.

## 8. Prompt

Use one short system prompt that defines the agent as a helpful general-purpose conversational assistant. It should not mention apartments, rentals, web search, listing sites, or any other specialized workflow.

**File location:** `prompts/system_prompt.md`

The prompt should encourage:

- Clear and natural responses
- Asking a clarifying question when the request is ambiguous
- Honest acknowledgement of uncertainty
- Respectful, concise conversation

The application, not the prompt, owns the exit command.

### Prompt File Format

- Plain markdown file
- Must be readable at startup
- Validation: file must exist and be non-empty
- Error on missing or empty prompt file halts startup with clear message

## 9. Project structure

Keep the initial structure small:

```text
.
├── pyproject.toml
├── .env.example
├── .gitignore
├── README.md
├── plan.md
├── prompts/
│   └── system_prompt.md
├── src/
│   └── chat_agent/
│       ├── __main__.py
│       ├── app.py
│       ├── agent.py
│       └── config.py
└── tests/
    ├── test_app.py
    ├── test_agent.py
    └── test_config.py
```

### Component Descriptions

- `app.py` - ChatApplication that runs the input/output loop
- `agent.py` - Wraps ADK Agent/Runner/InMemorySessionService with async execution, event handling, and retry logic
- `config.py` - Settings loader and validator
- `prompts/system_prompt.md` - System prompt loaded at agent initialization
- `README.md` - Project documentation with installation, usage, and development instructions
- `.gitignore` - Git ignore rules for virtual environments, cache files, and secrets

The implementation may use a single module initially if that is enough, but it should preserve the responsibilities described above.

---

## 9.1 Supporting Files

**pyproject.toml**: Use `google-adk>=1.18,<2.0`, `python-dotenv>=1.0.0`, and `rich>=13.0.0` for Markdown output. Dev dependencies: `pytest>=7.0.0`, `pytest-asyncio>=0.21.0` for async tests.

**.env.example**: Copy from Section 7.

**.gitignore**: Standard Python ignores (`.env`, `__pycache__`, `.venv`, `.pytest_cache`). Commit `uv.lock` for reproducible builds.

**prompts/system_prompt.md**: General-purpose assistant prompt encouraging clear responses, clarifying questions, and honest uncertainty acknowledgment.

**README.md**: Installation (uv), configuration (.env setup), usage (`uv run python -m chat_agent`), testing (`uv run pytest`).

## 10. Verification

The first version is complete when:

- `uv run python -m chat_agent` starts a local interactive chat.
- Multiple messages preserve context during the same process.
- ADK Session maintains conversation context across multiple async Runner executions without manual history passing.
- `/exit`, Ctrl+C, and end-of-input terminate cleanly.
- Missing configuration produces a useful startup error.
- `uv run pytest` passes the tests for configuration and the chat loop.

### Context Preservation Example

```text
You: My name is Alice
Agent: Nice to meet you, Alice! How can I help you today?

You: What's my name?
Agent: Your name is Alice.
```

This demonstrates the Session correctly maintains context across multiple agent executions.

---

## 11. Google ADK Usage

**Installation:** `uv add "google-adk>=1.18,<2.0" python-dotenv`

⚠️ **WARNING: All code examples below are CONCEPTUAL. Parameter names, import paths, and structures must be verified against google-adk 1.18 API documentation before implementation. Do not assume these exact names exist.**

**Conceptual Pattern (verify exact API against google-adk 1.18 documentation):**
```python
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk import types  # Or equivalent module for message types
import os
import asyncio

# API key should already be set in environment from .env file (loaded by python-dotenv)
# No additional configuration needed - google-adk reads GEMINI_API_KEY automatically

# Create agent with model configuration
# Parameter names are conceptual - verify exact API against google-adk 1.18
# Generation settings (temperature, max_output_tokens, etc.) must be configured
# using the exact configuration object supported by the pinned google-adk version
agent = Agent(
    model=os.getenv("MODEL"),
    instruction=system_prompt,  # May be named differently (system_instruction, prompt, etc.)
    # Add generation settings here according to google-adk 1.18 API
    # Example: config=GenerationConfig(temperature=0.7, max_output_tokens=2048)
)

# Create in-memory session service
session_service = InMemorySessionService()

# Create runner (parameter names are conceptual - verify actual API)
runner = Runner(
    agent=agent,
    app_name="chat-agent",  # Or equivalent application identifier
    session_service=session_service,
)

# Execute agent with identifiers and structured message
# Parameter names (user_id, session_id, new_message) are conceptual
# Message structure (Content, Part) is conceptual
# Verify exact names and structure against google-adk 1.18 API
#
# NOTE: For this MVP stage:
# - app_name: hardcoded application identifier (e.g., "chat-agent")
# - user_id: hardcoded user identifier (e.g., "local-user")
# - session_id: generated once at startup using str(uuid.uuid4())
#   - Ensures unique session per terminal session (security)
#   - Same session_id reused for all messages in that terminal session (context continuity)
#   - New app startup = new UUID = fresh session
import uuid

session_id = str(uuid.uuid4())  # Generate once at application startup

final_response = None
async for event in runner.run(
    user_id="local-user",  # Hardcoded for MVP - identifies the user in session service
    session_id=session_id,  # Generated at startup - unique per terminal session
    new_message=types.Content(  # Or equivalent message structure
        role="user",
        parts=[types.Part(text="Hello")],
    ),
):
    # Event filtering logic depends on ADK version
    if is_final_response_event(event):  # Implementation-specific
        final_response = extract_text_from_event(event)
        break

print(final_response)
```

**Key Concepts (verify exact API against google-adk 1.18 documentation):**
- API key configures Gemini client (mechanism may vary)
- Agent is stateless definition with model configuration
- InMemorySessionService stores session state locally
- Runner created with application identifier and session service
- **Session creation:** Verify whether explicit `await session_service.create_session()` is required, or if Runner.run() implicitly creates sessions when called with new user_id/session_id identifiers
- Runner.run() takes user/session identifiers and structured message (not plain strings)
- Messages likely use structured format (Content-like with role and parts)
- Runner execution is async and produces event stream (not a simple response object)
- **Event Handling:** ChatAgent must identify final response event and extract text from content
- Do not print intermediate events - only final agent response
- **Identifiers (MVP):** 
  - `app_name`: hardcoded constant (e.g., "chat-agent")
  - `user_id`: hardcoded constant (e.g., "local-user")
  - `session_id`: generated once at application startup using `str(uuid.uuid4())` for security, then reused for all messages in that terminal session for context continuity. Each new app startup generates a new UUID = fresh session.
- **Critical:** Parameter names shown (instruction, app_name, user_id, session_id, new_message, Content, Part) are conceptual
- Actual parameter names, import paths, and structures must be verified against google-adk 1.18 API documentation
- For testing: mock Runner or InMemorySessionService; inject via dependency injection

---

## 12. Implementation Details

### 12.1 Retry Strategy

Use async exponential backoff for transient failures only. Do not retry authentication, configuration, safety filter, or programming errors.

```python
import asyncio
from typing import Callable, TypeVar, Awaitable

T = TypeVar('T')

# Exceptions that should NOT be retried (fail fast)
NON_RETRYABLE_ERRORS = (
    # Authentication/configuration errors
    ValueError,      # Invalid configuration, safety filter blocks
    KeyError,        # Missing configuration
    TypeError,       # Programming errors
    AttributeError,  # Programming errors
    # Add API-specific auth errors when identified (e.g., AuthenticationError)
)

async def retry_with_backoff(
    func: Callable[[], Awaitable[T]],
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
) -> T:
    """
    Retry async function with exponential backoff.
    
    Only retries transient failures (network, rate limits, temporary unavailability).
    Fails fast on authentication, configuration, safety, or programming errors.
    """
    delay = initial_delay

    for attempt in range(max_attempts):
        try:
            return await func()
        except NON_RETRYABLE_ERRORS:
            # Don't retry these - fail immediately
            raise
        except Exception as e:
            if attempt == max_attempts - 1:
                # Last attempt failed
                raise
            
            # Log retry attempt
            import logging
            logging.warning(
                f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                f"Retrying in {delay:.1f}s..."
            )
            
            await asyncio.sleep(min(delay, max_delay))
            delay *= 2
```

**Retryable Errors (transient):**
- Network timeouts and connection errors
- Rate limiting (HTTP 429)
- Temporary service unavailability (HTTP 503)
- Temporary API errors

**Non-Retryable Errors (fail fast):**
- Authentication failures (invalid API key)
- Configuration errors (invalid model name, missing settings)
- Safety filter blocks (content policy violations)
- Programming errors (TypeError, AttributeError, KeyError)
- Invalid input format

**Usage:**

The retry wrapper works with functions that return an awaitable value. Since `runner.run()` returns an async generator (consumed with `async for`), the retry must wrap the entire operation that consumes the event stream and extracts the final response:

```python
async def send_message_with_retry(
    runner: Runner,
    user_id: str,
    session_id: str,
    message: types.Content
) -> str:
    """Send message and extract final response, with retry logic."""
    
    async def _send_and_extract() -> str:
        """Inner function that consumes event stream and returns final response."""
        final_response = None
        
        async for event in runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=message
        ):
            if is_final_response_event(event):
                final_response = extract_text_from_event(event)
                break
        
        if final_response is None:
            raise ValueError("No final response received from agent")
        
        return final_response
    
    # Retry the entire send-and-extract operation
    return await retry_with_backoff(_send_and_extract, max_attempts=3)
```

**Key Point:** The retry wraps the complete "send message + consume event stream + extract final response" operation, not just the `runner.run()` call.

**Model Fallback Pattern:**

When the primary model fails with a retryable error, switch to fallback model while preserving session:

```python
async def send_message_with_fallback(
    message_text: str, 
    session_service: InMemorySessionService,
    user_id: str,
    session_id: str,
    system_prompt: str
) -> str:
    """
    Attempt with primary model, fall back to FALLBACK_MODEL on retryable failure.
    Session state is preserved across both attempts.
    """
    
    async def _send_with_model(model_name: str) -> str:
        """Create runner with specified model and consume event stream."""
        # Create agent with specific model
        # Generation settings must use exact configuration object from google-adk 1.18
        agent = Agent(
            model=model_name,
            instruction=system_prompt,
            # Add generation settings according to google-adk 1.18 API
        )
        
        # Create runner with same session service
        runner = Runner(
            agent=agent,
            app_name="chat-agent",
            session_service=session_service,
        )
        
        # Consume event stream
        final_response = None
        async for event in runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=types.Content(role="user", parts=[types.Part(text=message_text)]),
        ):
            if is_final_response_event(event):
                final_response = extract_text_from_event(event)
                break
        
        if final_response is None:
            raise ValueError(f"No final response from {model_name}")
        
        return final_response
    
    try:
        # Try primary model first
        return await _send_with_model(os.getenv("MODEL"))
    except Exception as e:
        # Only fallback on retryable errors
        if isinstance(e, NON_RETRYABLE_ERRORS):
            raise
        
        logging.warning(f"Primary model failed: {e}. Switching to fallback model.")
        
        # Try fallback model with same session service and IDs
        return await _send_with_model(os.getenv("FALLBACK_MODEL"))
```

**Key Points:**
- Same `InMemorySessionService` instance used for both primary and fallback
- Same `user_id` and `session_id` maintained across fallback
- Each attempt creates new Agent + Runner, but reuses session service
- Conversation context preserved - fallback agent has access to full history
- If fallback also fails, error propagates to caller, session remains valid for next turn
- **MVP Limitation (accepted):** Possible duplicate turns if primary request partially updates session before failing. Reusing the same session preserves history but does not guarantee failed turn rollback.

### 12.2 Error Messages

**Configuration Errors (startup):**
```
Configuration error: GEMINI_API_KEY not set
Please set GEMINI_API_KEY in your .env file
```

**Prompt File Errors (startup):**
```
Prompt file error: prompts/system_prompt.md not found
Please create the prompt file before starting the agent
```

**Runtime Errors (during chat):**
```
Error: Unable to get response from agent
The conversation will continue. Try sending your message again.
```

### 12.3 Logging

**Levels:**
- `INFO`: Session start/end, configuration loaded
- `WARNING`: Retry attempts, degraded functionality
- `ERROR`: Request failures, configuration errors
- Never log: API keys, conversation content (privacy)

**Format:**
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

**Security:**
- Never log `GEMINI_API_KEY` or other secrets
- Sanitize any logged data that might contain PII
- Use placeholders: `"Model: {model_name}"` not `"API Key: {api_key}"`

### 12.4 Signal Handling (Ctrl+C)

For clean exit on Ctrl+C (SIGINT):

```python
import signal
import sys

def setup_signal_handlers():
    """Configure graceful shutdown on Ctrl+C."""
    def signal_handler(sig, frame):
        print("\n\nGoodbye.")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)

# Call at application startup
setup_signal_handlers()
```

This ensures FR-04 requirement: clean exit without error traceback.

---

## 13. Implementation Order

1. **config.py**: Settings dataclass, load/validate env vars, load system prompt file
2. **agent.py**: ChatAgent class wrapping ADK Agent/Runner/InMemorySessionService, creates structured messages, filters event stream to identify final response, extracts text from content structure, async send_message() returns final text with retry logic. ChatAgent accepts session_id (generated by caller) in constructor or send_message method.
3. **app.py**: ChatApplication with async I/O loop, /exit command, Ctrl+C handler. Generates session_id once at startup using str(uuid.uuid4()) and passes to ChatAgent for all messages.
4. **__main__.py**: Wire components, handle startup errors, run async application loop
5. **tests/**: Unit tests (mock Runner/InMemorySessionService), integration test (optional, requires API key)

**Critical First Step:** Before writing any code, verify exact API against google-adk 1.18 documentation:
- All parameter names (Agent, Runner, runner.run())
- Message structure and types
- Event structure and final response identification
- Import paths and module names

Parameter names shown throughout this plan (instruction, app_name, user_id, session_id, new_message, Content, Part) are conceptual and may differ from actual API.

---

## 14. Implementation Notes

**Common Pitfalls:**
- ❌ Don't change user/session identifiers per message → ✅ Use same identifiers for entire conversation
- ❌ Don't use hardcoded session_id like "terminal-session-001" → ✅ Generate once at startup using str(uuid.uuid4())
- ❌ Don't call Agent directly → ✅ Execute via Runner.run()
- ❌ Don't forget API key → ✅ Configure GEMINI_API_KEY environment variable for Gemini client
- ❌ Don't expect synchronous execution → ✅ Use async/await and event streaming
- ❌ Don't pass plain string messages → ✅ Use structured message format (verify exact structure)
- ❌ Don't print all events → ✅ Filter for final response event only
- ❌ Don't access event content blindly → ✅ Extract text from content structure properly
- ❌ Don't assume parameter names → ✅ Verify all parameter names against google-adk 1.18 API

**Event Handling:**
- Runner.run() produces multiple events (intermediate and final)
- Identify final agent response event before extracting content
- Extract text from event's content parts structure
- Event types and structure are version-specific - consult ADK 1.18 docs
- ChatAgent should encapsulate event filtering logic, returning clean text to ChatApplication

**Error Handling:**
- Wrap `async for event in runner.run()` in try/except
- Handle safety filter blocks: catch ValueError, fail fast (do not retry)
- Use async exponential backoff for retries (see Section 12.1)
- Retry wraps the entire operation: send message + consume event stream + extract final response
- Only retry transient errors (network, rate limits, temporary unavailability)
- Fail fast on authentication, configuration, safety, or programming errors
- Fallback: On a retryable primary model failure, recreate Agent with FALLBACK_MODEL and continue using the same InMemorySessionService and session identifiers
- If fallback also fails, show an error message and retain the session for the next user turn
- Never discard session state on model failures - conversation context must persist
- Accept possible duplicate turns in this MVP: if primary request partially updates session before failing, fallback may add same user message again

**Testing:**
- Unit tests: Mock Runner or InMemorySessionService, inject into ChatAgent
- Mock async event streams for Runner.run() testing - include intermediate and final events
- Integration tests: Use real ADK components with `@pytest.mark.skipif` for missing API key
- Test context preservation: execute twice with same user_id/session_id, verify second references first
- Use pytest-asyncio for async test support

**API Verification (Critical - Do First):**
- **All code examples in this plan are conceptual** - parameter names and structures shown are illustrative
- Before implementation, consult google-adk 1.18 API documentation to verify:
  - Exact parameter names for Agent (instruction vs system_instruction vs prompt, etc.)
  - **Generation settings configuration:** Must use the exact configuration object supported by the pinned google-adk version (e.g., GenerationConfig, config parameter, or direct parameters)
  - Exact parameter names for Runner (app_name vs application_name, etc.)
  - Exact parameter names for runner.run() (user_id, session_id, new_message, etc.)
  - **Session creation:** Whether explicit `await session_service.create_session(user_id, session_id)` is required before first runner.run() call, or if sessions are created implicitly by Runner
  - Message structure (types.Content, types.Part, or different names/module)
  - Event structure and types for identifying final responses
  - Import paths (google.adk.agents, google.adk.runners, google.adk.sessions, google.adk.types)
- Current ADK examples show inspecting final-response events before printing content
- Parameter names shown here (instruction, app_name, user_id, session_id, new_message) may not match actual API
