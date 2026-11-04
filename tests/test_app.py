"""Tests for app module."""

import signal
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from io import StringIO

from chat_agent.app import ChatApplication
from chat_agent.agent import ChatAgent


@pytest.fixture
def mock_agent():
    """Mock ChatAgent for testing."""
    agent = MagicMock(spec=ChatAgent)
    agent.send_message = AsyncMock(return_value="Agent response")
    return agent


class TestChatApplication:
    """Tests for ChatApplication class."""

    def test_initialization(self, mock_agent):
        """Test ChatApplication initialization."""
        app = ChatApplication(mock_agent)

        assert app.agent == mock_agent
        assert app._running is False

    @pytest.mark.asyncio
    async def test_get_user_input(self, mock_agent):
        """Test getting user input."""
        app = ChatApplication(mock_agent)

        with patch("builtins.input", return_value="Hello"):
            user_input = await app._get_user_input()

        assert user_input == "Hello"

    @pytest.mark.asyncio
    async def test_get_user_input_strips_whitespace(self, mock_agent):
        """Test that user input is stripped of whitespace."""
        app = ChatApplication(mock_agent)

        with patch("builtins.input", return_value="  Hello  \n"):
            user_input = await app._get_user_input()

        assert user_input == "Hello"

    @pytest.mark.asyncio
    async def test_get_user_input_eof(self, mock_agent):
        """Test handling EOF (Ctrl+D)."""
        app = ChatApplication(mock_agent)

        with patch("builtins.input", side_effect=EOFError):
            user_input = await app._get_user_input()

        assert user_input is None

    @pytest.mark.asyncio
    async def test_handle_message_exit_command(self, mock_agent):
        """Test /exit command returns False."""
        app = ChatApplication(mock_agent)

        should_continue = await app._handle_message("/exit")

        assert should_continue is False
        mock_agent.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_message_exit_command_case_insensitive(self, mock_agent):
        """Test /exit command is case insensitive."""
        app = ChatApplication(mock_agent)

        should_continue = await app._handle_message("/EXIT")

        assert should_continue is False
        mock_agent.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_message_empty(self, mock_agent):
        """Test empty message returns True without calling agent."""
        app = ChatApplication(mock_agent)

        should_continue = await app._handle_message("")

        assert should_continue is True
        mock_agent.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_message_success(self, mock_agent):
        """Test successful message handling."""
        app = ChatApplication(mock_agent)

        should_continue = await app._handle_message("Hello")

        assert should_continue is True
        mock_agent.send_message.assert_called_once_with("Hello")

    @pytest.mark.asyncio
    async def test_handle_message_agent_error(self, mock_agent):
        """Test error handling when agent fails."""
        app = ChatApplication(mock_agent)
        mock_agent.send_message.side_effect = Exception("Agent error")

        # Should not raise, should return True to continue
        should_continue = await app._handle_message("Hello")

        assert should_continue is True

    @pytest.mark.asyncio
    async def test_run_single_message_then_exit(self, mock_agent):
        """Test running app with single message then exit."""
        app = ChatApplication(mock_agent)

        # Mock input sequence: one message, then /exit
        inputs = ["Hello", "/exit"]
        input_iter = iter(inputs)

        with patch("builtins.input", side_effect=lambda _: next(input_iter)):
            await app.run()

        # Verify message was sent
        mock_agent.send_message.assert_called_once_with("Hello")
        assert app._running is False

    @pytest.mark.asyncio
    async def test_run_multiple_messages(self, mock_agent):
        """Test running app with multiple messages."""
        app = ChatApplication(mock_agent)

        # Mock input sequence: multiple messages, then /exit
        inputs = ["First message", "Second message", "/exit"]
        input_iter = iter(inputs)

        with patch("builtins.input", side_effect=lambda _: next(input_iter)):
            await app.run()

        # Verify both messages were sent
        assert mock_agent.send_message.call_count == 2
        mock_agent.send_message.assert_any_call("First message")
        mock_agent.send_message.assert_any_call("Second message")

    @pytest.mark.asyncio
    async def test_run_eof_handling(self, mock_agent):
        """Test running app with EOF (Ctrl+D)."""
        app = ChatApplication(mock_agent)

        # Mock input: one message, then EOF
        with patch("builtins.input", side_effect=["Hello", EOFError]):
            await app.run()

        # Verify message was sent
        mock_agent.send_message.assert_called_once_with("Hello")
        assert app._running is False

    @pytest.mark.asyncio
    async def test_run_empty_messages_skipped(self, mock_agent):
        """Test that empty messages are skipped."""
        app = ChatApplication(mock_agent)

        # Mock input: empty strings and one real message, then exit
        inputs = ["", "  ", "Hello", "/exit"]
        input_iter = iter(inputs)

        with patch("builtins.input", side_effect=lambda _: next(input_iter)):
            await app.run()

        # Only the real message should be sent
        mock_agent.send_message.assert_called_once_with("Hello")

    @pytest.mark.asyncio
    async def test_run_continues_after_agent_error(self, mock_agent):
        """Test that app continues after agent error."""
        app = ChatApplication(mock_agent)

        # First message fails, second succeeds
        mock_agent.send_message.side_effect = [
            Exception("Error"),
            "Success response",
        ]

        inputs = ["First", "Second", "/exit"]
        input_iter = iter(inputs)

        with patch("builtins.input", side_effect=lambda _: next(input_iter)):
            await app.run()

        # Both messages should have been attempted
        assert mock_agent.send_message.call_count == 2

    def test_stop(self, mock_agent):
        """Test stopping the application."""
        app = ChatApplication(mock_agent)
        app._running = True

        app.stop()

        assert app._running is False

    @pytest.mark.asyncio
    async def test_signal_handler_setup(self, mock_agent):
        """Test that signal handlers are set up."""
        with patch("signal.signal") as mock_signal:
            app = ChatApplication(mock_agent)

            # Verify SIGINT handler was registered
            mock_signal.assert_called_once()
            call_args = mock_signal.call_args
            assert call_args[0][0] == signal.SIGINT
