"""Chat agent module wrapping Google ADK."""

import asyncio
import logging
import os
from typing import AsyncGenerator, Callable, TypeVar, Awaitable

from google.adk import Agent, Runner
from google.adk.events import Event
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part, GenerateContentConfig

from .config import Config


logger = logging.getLogger(__name__)

T = TypeVar("T")


# Exceptions that should NOT be retried (fail fast)
NON_RETRYABLE_ERRORS = (
    ValueError,  # Invalid configuration, safety filter blocks
    KeyError,  # Missing configuration
    TypeError,  # Programming errors
    AttributeError,  # Programming errors
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

    Args:
        func: Async function to retry
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds

    Returns:
        Result from successful function call

    Raises:
        Exception: Last exception if all attempts fail
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
            logger.warning(
                f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                f"Retrying in {delay:.1f}s..."
            )

            await asyncio.sleep(min(delay, max_delay))
            delay *= 2


class ChatAgent:
    """Chat agent wrapping Google ADK Agent/Runner/InMemorySessionService."""

    def __init__(self, config: Config, session_id: str):
        """
        Initialize chat agent.

        Args:
            config: Configuration settings
            session_id: Session identifier (generated via uuid.uuid4())
        """
        self.config = config
        self.session_id = session_id
        self.session_service = InMemorySessionService()
        self.app_name = "chat_agent"
        self.user_id = "local_user"
        self._session_created = False

        # Set up logging
        self._setup_logging()

        logger.info(
            f"ChatAgent initialized with model={config.model}, "
            f"session_id={session_id}"
        )

    def _setup_logging(self) -> None:
        """Configure logging for the agent."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        # Suppress noisy telemetry warnings from ADK
        logging.getLogger("opentelemetry.context").setLevel(logging.CRITICAL)

    def _create_agent(self, model: str) -> Agent:
        """
        Create ADK Agent with specified model.

        Args:
            model: Model name (e.g., "gemini-3.5-flash-lite")

        Returns:
            Configured Agent instance
        """
        # Create generation config
        gen_config = GenerateContentConfig(
            temperature=self.config.temperature,
            max_output_tokens=self.config.max_output_tokens,
        )

        # Create agent
        agent = Agent(
            name="chat_agent",
            model=model,
            instruction=self.config.system_prompt,
            generate_content_config=gen_config,
        )

        return agent

    def _create_runner(self, agent: Agent) -> Runner:
        """
        Create ADK Runner with agent and session service.

        Args:
            agent: Configured Agent instance

        Returns:
            Configured Runner instance
        """
        runner = Runner(
            app_name=self.app_name,
            agent=agent,
            session_service=self.session_service,
        )

        return runner

    async def _ensure_session_created(self) -> None:
        """Create session if not already created."""
        if not self._session_created:
            # Create session in session service
            await self.session_service.create_session(
                app_name=self.app_name,
                user_id=self.user_id,
                session_id=self.session_id,
            )
            self._session_created = True
            logger.info(f"Session created: {self.session_id}")

    async def _extract_final_response(
        self, runner: Runner, message_text: str
    ) -> str:
        """
        Send message and extract final response from event stream.

        Args:
            runner: Configured Runner instance
            message_text: User message text

        Returns:
            Final response text from agent

        Raises:
            ValueError: If no final response received
        """
        # Ensure session is created
        await self._ensure_session_created()

        # Create structured message
        message = Content(role="user", parts=[Part(text=message_text)])

        # Consume event stream
        final_response = None

        async for event in runner.run_async(
            user_id=self.user_id,
            session_id=self.session_id,
            new_message=message,
        ):
            # Check if this is the final response
            if event.is_final_response():
                # Extract text from content parts
                if event.content and event.content.parts:
                    response_parts = []
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            response_parts.append(part.text)

                    if response_parts:
                        final_response = "".join(response_parts)
                        break

        if final_response is None:
            raise ValueError("No final response received from agent")

        return final_response

    async def _send_with_model(self, model: str, message: str) -> str:
        """
        Send message using specified model.

        Args:
            model: Model name
            message: User message text

        Returns:
            Agent response text
        """
        agent = self._create_agent(model)
        runner = self._create_runner(agent)
        return await self._extract_final_response(runner, message)

    async def send_message(self, message: str) -> str:
        """
        Send message to agent with retry and fallback logic.

        Attempts primary model first, falls back to FALLBACK_MODEL on retryable failure.
        Session state is preserved across both attempts.

        MVP Limitation: If primary request partially updates session before failing,
        fallback may add the same user message again (possible duplicate turns).

        Args:
            message: User message text

        Returns:
            Agent response text

        Raises:
            Exception: If both primary and fallback models fail
        """

        async def _send_with_retry_and_fallback() -> str:
            """Inner function implementing retry and fallback logic."""
            try:
                # Try primary model with retry
                return await retry_with_backoff(
                    lambda: self._send_with_model(self.config.model, message),
                    max_attempts=self.config.retry_max_attempts,
                )
            except NON_RETRYABLE_ERRORS:
                # Don't fallback on non-retryable errors
                raise
            except Exception as e:
                # Log fallback attempt
                logger.warning(
                    f"Primary model {self.config.model} failed: {e}. "
                    f"Switching to fallback model {self.config.fallback_model}"
                )

                # Try fallback model (same session service and IDs)
                return await retry_with_backoff(
                    lambda: self._send_with_model(
                        self.config.fallback_model, message
                    ),
                    max_attempts=self.config.retry_max_attempts,
                )

        try:
            response = await _send_with_retry_and_fallback()
            logger.info(f"Message sent successfully, response length: {len(response)}")
            return response
        except Exception as e:
            logger.error(f"Failed to get response from agent: {e}")
            raise
