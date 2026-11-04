# Google ADK 1.39.1 API Verification

**Installed Version:** 1.39.1 (exceeds minimum requirement of 1.18)

## Verified Imports

```python
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.adk.events import Event
from google.genai.types import Content, Part, GenerateContentConfig
```

## Agent Creation

### Verified Parameters (Pydantic fields)

```python
Agent(
    name: str,                    # REQUIRED
    model: str,                   # REQUIRED - model name like "gemini-3.5-flash-lite"
    instruction: str,             # System instruction/prompt
    description: str = "",        # Optional
    tools: list = [],            # Optional
    generate_content_config: GenerateContentConfig | None = None,  # Generation settings
    # ... many other optional fields
)
```

### Generation Settings

Use `GenerateContentConfig` for temperature, max_output_tokens, etc.:

```python
from google.genai.types import GenerateContentConfig

config = GenerateContentConfig(
    temperature=0.7,
    max_output_tokens=2048
)

agent = Agent(
    name="chat-agent",
    model="gemini-3.5-flash-lite",
    instruction=system_prompt,
    generate_content_config=config
)
```

## Runner Creation

### Verified Signature

```python
Runner(
    *,
    app_name: str | None = None,                          # ✅ Confirmed
    agent: BaseAgent | None = None,                       # ✅ Confirmed
    session_service: BaseSessionService,                  # ✅ Confirmed - REQUIRED
    app: App | None = None,
    plugins: List[BasePlugin] | None = None,
    artifact_service: BaseArtifactService | None = None,
    memory_service: BaseMemoryService | None = None,
    credential_service: BaseCredentialService | None = None,
    plugin_close_timeout: float = 5.0,
    auto_create_session: bool = False
)
```

### Example

```python
runner = Runner(
    app_name="chat-agent",
    agent=agent,
    session_service=session_service
)
```

## InMemorySessionService

### Verified Methods

```python
# Constructor - no parameters
session_service = InMemorySessionService()

# Session management (all methods take keywords)
await session_service.create_session(
    app_name: str,
    user_id: str,
    session_id: str | None = None,  # Optional - will generate if not provided
    state: dict[str, Any] | None = None
) -> Session

await session_service.get_session(
    app_name: str,
    user_id: str,
    session_id: str,
    config: GetSessionConfig | None = None
) -> Session | None
```

**Important:** Session creation appears to be optional - `Runner` has `auto_create_session: bool = False` parameter. Need to test if explicit creation is needed.

## Running the Agent

### Verified Signature

```python
async def run_async(
    self,
    *,
    user_id: str,                           # ✅ Confirmed - REQUIRED
    session_id: str,                        # ✅ Confirmed - REQUIRED  
    new_message: types.Content | None = None,  # ✅ Confirmed
    invocation_id: str | None = None,
    state_delta: dict[str, Any] | None = None,
    run_config: RunConfig | None = None
) -> AsyncGenerator[Event, None]            # ✅ Returns async generator of Event
```

### Example

```python
import uuid

session_id = str(uuid.uuid4())

async for event in runner.run_async(
    user_id="local-user",
    session_id=session_id,
    new_message=Content(
        role="user",
        parts=[Part(text="Hello")]
    )
):
    if event.is_final_response():
        # Extract response
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(part.text)
```

## Message Structure

### Verified Structure

```python
from google.genai.types import Content, Part

# User message
message = Content(
    role="user",  # ✅ Confirmed
    parts=[       # ✅ Confirmed - list of Part objects
        Part(text="Hello")  # ✅ Confirmed
    ]
)
```

## Event Structure

### Verified Fields

```python
class Event:
    content: Content | None           # ✅ Contains the response content
    turn_complete: bool | None        # ✅ Indicates turn completion
    partial: bool | None              # ✅ Indicates partial response
    finish_reason: FinishReason | None
    error_code: str | None
    error_message: str | None
    author: str                       # "user" or "model"
    # ... many other fields
    
    def is_final_response(self) -> bool:  # ✅ Confirmed method
        """Returns whether the event is the final response of an agent."""
```

### Response Extraction

```python
async for event in runner.run_async(...):
    if event.is_final_response():
        if event.content and event.content.parts:
            response_text = ""
            for part in event.content.parts:
                if hasattr(part, 'text') and part.text:
                    response_text += part.text
            return response_text
```

## Session ID Management

**Verified pattern:**
- Generate once at application startup: `session_id = str(uuid.uuid4())`
- Reuse same session_id for all messages in that terminal session
- New app startup = new UUID = fresh session

## Key Differences from Plan

1. ✅ **Agent requires `name` parameter** (plan didn't mention this)
2. ✅ **Use `generate_content_config=GenerateContentConfig(...)` not direct params**
3. ✅ **Use `runner.run_async()` not `runner.run()`**
4. ✅ **Event has `is_final_response()` method** (exactly as planned)
5. ⚠️  **Session creation** - need to test if explicit `create_session()` is required or if Runner handles it with `auto_create_session`

## Testing Required

- [ ] Test if explicit `session_service.create_session()` is needed
- [ ] Verify fallback pattern works (recreating Agent with different model)
- [ ] Test event stream handling with actual ADK
- [ ] Verify error types for retry logic classification
