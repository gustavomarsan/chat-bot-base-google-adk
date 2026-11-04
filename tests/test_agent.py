"""Tests for agent module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from google.genai.types import Content, Part

from chat_agent.agent import ChatAgent, retry_with_backoff, NON_RETRYABLE_ERRORS
from chat_agent.config import Config


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    config = MagicMock(spec=Config)
    config.model = "gemini-3.5-flash-lite"
    config.fallback_model = "gemini-3.6-flash-lite"
    config.system_prompt = "You are a helpful assistant."
    config.temperature = 0.7
    config.max_output_tokens = 2048
    config.retry_max_attempts = 3
    return config


@pytest.fixture
def mock_session_service():
    """Mock InMemorySessionService with async methods."""
    service = MagicMock()
    service.create_session = AsyncMock()
    return service


@pytest.fixture
def mock_event_final():
    """Mock final response event."""
    event = MagicMock()
    event.is_final_response.return_value = True
    event.content = MagicMock()
    part = MagicMock()
    part.text = "Hello! How can I help you?"
    event.content.parts = [part]
    return event


@pytest.fixture
def mock_event_intermediate():
    """Mock intermediate event."""
    event = MagicMock()
    event.is_final_response.return_value = False
    return event


class TestRetryWithBackoff:
    """Tests for retry_with_backoff function."""

    @pytest.mark.asyncio
    async def test_success_first_attempt(self):
        """Test successful execution on first attempt."""
        async def success_func():
            return "success"

        result = await retry_with_backoff(success_func, max_attempts=3)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_success_after_retries(self):
        """Test successful execution after retries."""
        attempts = []

        async def flaky_func():
            attempts.append(1)
            if len(attempts) < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        result = await retry_with_backoff(flaky_func, max_attempts=3)
        assert result == "success"
        assert len(attempts) == 3

    @pytest.mark.asyncio
    async def test_non_retryable_error_fails_immediately(self):
        """Test that non-retryable errors fail immediately."""
        attempts = []

        async def error_func():
            attempts.append(1)
            raise ValueError("Invalid configuration")

        with pytest.raises(ValueError, match="Invalid configuration"):
            await retry_with_backoff(error_func, max_attempts=3)

        assert len(attempts) == 1  # Should not retry

    @pytest.mark.asyncio
    async def test_all_attempts_fail(self):
        """Test that exception is raised after all attempts fail."""
        attempts = []

        async def always_fails():
            attempts.append(1)
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError, match="Always fails"):
            await retry_with_backoff(always_fails, max_attempts=3)

        assert len(attempts) == 3


class TestChatAgent:
    """Tests for ChatAgent class."""

    @pytest.mark.asyncio
    async def test_initialization(self, mock_config):
        """Test ChatAgent initialization."""
        with patch("chat_agent.agent.InMemorySessionService"):
            agent = ChatAgent(mock_config, session_id="test-session-123")

            assert agent.config == mock_config
            assert agent.session_id == "test-session-123"
            assert agent.app_name == "chat_agent"
            assert agent.user_id == "local_user"
            assert agent._session_created is False

    @pytest.mark.asyncio
    async def test_create_agent(self, mock_config):
        """Test Agent creation with correct parameters."""
        with patch("chat_agent.agent.InMemorySessionService"):
            chat_agent = ChatAgent(mock_config, session_id="test-session-123")

            with patch("chat_agent.agent.Agent") as mock_agent_class:
                agent = chat_agent._create_agent("gemini-3.5-flash-lite")

                # Verify Agent was called with correct parameters
                mock_agent_class.assert_called_once()
                call_kwargs = mock_agent_class.call_args[1]
                assert call_kwargs["name"] == "chat_agent"
                assert call_kwargs["model"] == "gemini-3.5-flash-lite"
                assert call_kwargs["instruction"] == "You are a helpful assistant."
                assert call_kwargs["generate_content_config"] is not None

    @pytest.mark.asyncio
    async def test_create_runner(self, mock_config):
        """Test Runner creation with correct parameters."""
        with patch("chat_agent.agent.InMemorySessionService"):
            chat_agent = ChatAgent(mock_config, session_id="test-session-123")

            mock_agent = MagicMock()
            with patch("chat_agent.agent.Runner") as mock_runner_class:
                runner = chat_agent._create_runner(mock_agent)

                # Verify Runner was called with correct parameters
                mock_runner_class.assert_called_once_with(
                    app_name="chat_agent",
                    agent=mock_agent,
                    session_service=chat_agent.session_service,
                )

    @pytest.mark.asyncio
    async def test_extract_final_response_success(
        self, mock_config, mock_session_service, mock_event_intermediate, mock_event_final
    ):
        """Test extracting final response from event stream."""
        with patch("chat_agent.agent.InMemorySessionService", return_value=mock_session_service):
            chat_agent = ChatAgent(mock_config, session_id="test-session-123")

            # Mock runner with event stream
            mock_runner = MagicMock()

            async def mock_event_stream(*args, **kwargs):
                yield mock_event_intermediate
                yield mock_event_final

            mock_runner.run_async = mock_event_stream

            # Extract response
            response = await chat_agent._extract_final_response(
                mock_runner, "Hello"
            )

            assert response == "Hello! How can I help you?"

    @pytest.mark.asyncio
    async def test_extract_final_response_no_response(
        self, mock_config, mock_session_service, mock_event_intermediate
    ):
        """Test error when no final response received."""
        with patch("chat_agent.agent.InMemorySessionService", return_value=mock_session_service):
            chat_agent = ChatAgent(mock_config, session_id="test-session-123")

            # Mock runner with only intermediate events
            mock_runner = MagicMock()

            async def mock_event_stream(*args, **kwargs):
                yield mock_event_intermediate

            mock_runner.run_async = mock_event_stream

            # Should raise ValueError
            with pytest.raises(ValueError, match="No final response received"):
                await chat_agent._extract_final_response(mock_runner, "Hello")

    @pytest.mark.asyncio
    async def test_send_message_success(self, mock_config, mock_event_final):
        """Test successful message sending."""
        with patch("chat_agent.agent.InMemorySessionService") as mock_session_service_class:
            # Mock session service with async create_session
            mock_session_service = MagicMock()
            mock_session_service.create_session = AsyncMock()
            mock_session_service_class.return_value = mock_session_service

            chat_agent = ChatAgent(mock_config, session_id="test-session-123")

            # Mock the event stream
            async def mock_event_stream(*args, **kwargs):
                yield mock_event_final

            with patch("chat_agent.agent.Runner") as mock_runner_class:
                mock_runner = MagicMock()
                mock_runner.run_async = mock_event_stream
                mock_runner_class.return_value = mock_runner

                with patch("chat_agent.agent.Agent"):
                    response = await chat_agent.send_message("Hello")

                assert response == "Hello! How can I help you?"
                # Verify session was created
                mock_session_service.create_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_with_fallback(self, mock_config, mock_event_final):
        """Test fallback to secondary model on primary failure."""
        with patch("chat_agent.agent.InMemorySessionService"):
            chat_agent = ChatAgent(mock_config, session_id="test-session-123")

            # Mock primary failure, fallback success
            attempts = []

            async def mock_send_with_model(model: str, message: str):
                attempts.append(model)
                if model == mock_config.model:
                    raise ConnectionError("Primary model failed")
                return "Fallback response"

            chat_agent._send_with_model = mock_send_with_model

            response = await chat_agent.send_message("Hello")

            assert response == "Fallback response"
            assert mock_config.model in attempts
            assert mock_config.fallback_model in attempts

    @pytest.mark.asyncio
    async def test_send_message_non_retryable_error_no_fallback(self, mock_config):
        """Test that non-retryable errors don't trigger fallback."""
        with patch("chat_agent.agent.InMemorySessionService"):
            chat_agent = ChatAgent(mock_config, session_id="test-session-123")

            attempts = []

            async def mock_send_with_model(model: str, message: str):
                attempts.append(model)
                raise ValueError("Safety filter blocked")

            chat_agent._send_with_model = mock_send_with_model

            with pytest.raises(ValueError, match="Safety filter blocked"):
                await chat_agent.send_message("Hello")

            # Should only try primary model, no fallback
            assert len(attempts) == 1
            assert attempts[0] == mock_config.model

    @pytest.mark.asyncio
    async def test_send_message_both_models_fail(self, mock_config):
        """Test error when both primary and fallback models fail."""
        with patch("chat_agent.agent.InMemorySessionService"):
            chat_agent = ChatAgent(mock_config, session_id="test-session-123")

            async def mock_send_with_model(model: str, message: str):
                raise ConnectionError(f"{model} failed")

            chat_agent._send_with_model = mock_send_with_model

            with pytest.raises(ConnectionError):
                await chat_agent.send_message("Hello")

    @pytest.mark.asyncio
    async def test_multiple_messages_same_session(
        self, mock_config, mock_session_service, mock_event_final
    ):
        """Test that multiple messages use the same session_id."""
        with patch("chat_agent.agent.InMemorySessionService", return_value=mock_session_service):
            chat_agent = ChatAgent(mock_config, session_id="test-session-123")

            session_ids_used = []

            async def mock_event_stream(*args, **kwargs):
                session_ids_used.append(kwargs.get("session_id"))
                yield mock_event_final

            with patch("chat_agent.agent.Runner") as mock_runner_class:
                mock_runner = MagicMock()
                mock_runner.run_async = mock_event_stream
                mock_runner_class.return_value = mock_runner

                with patch("chat_agent.agent.Agent"):
                    await chat_agent.send_message("First message")
                    await chat_agent.send_message("Second message")

            # Both messages should use the same session_id
            assert len(session_ids_used) == 2
            assert session_ids_used[0] == "test-session-123"
            assert session_ids_used[1] == "test-session-123"
            # Session should only be created once
            assert mock_session_service.create_session.call_count == 1
