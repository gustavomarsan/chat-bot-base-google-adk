"""Chat application module with async I/O loop."""

import asyncio
import signal
import sys
from typing import Optional

from .agent import ChatAgent


class ChatApplication:
    """Interactive terminal-based chat application."""

    def __init__(self, agent: ChatAgent):
        """
        Initialize chat application.

        Args:
            agent: Configured ChatAgent instance
        """
        self.agent = agent
        self._running = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Configure graceful shutdown on Ctrl+C (SIGINT)."""

        def signal_handler(sig, frame):
            """Handle SIGINT signal."""
            print("\n\nGoodbye.")
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)

    async def _get_user_input(self) -> Optional[str]:
        """
        Get user input asynchronously.

        Returns:
            User input string, or None if EOF
        """
        loop = asyncio.get_event_loop()

        try:
            # Run input() in thread pool to avoid blocking
            user_input = await loop.run_in_executor(None, input, "You: ")
            return user_input.strip()
        except EOFError:
            # Handle Ctrl+D or end of input
            return None

    async def _handle_message(self, user_message: str) -> bool:
        """
        Handle user message and display agent response.

        Args:
            user_message: User's message text

        Returns:
            False if application should exit, True otherwise
        """
        # Check for exit command
        if user_message.lower() == "/exit":
            print("\nGoodbye.")
            return False

        # Handle empty messages
        if not user_message:
            return True

        try:
            # Send message to agent
            response = await self.agent.send_message(user_message)

            # Display response
            print(f"Agent: {response}\n")

        except Exception as e:
            # Display error but keep session alive
            print(f"Error: Unable to get response from agent")
            print("The conversation will continue. Try sending your message again.\n")

        return True

    async def run(self) -> None:
        """
        Run the chat application loop.

        Continuously prompts for user input and displays agent responses
        until /exit is entered, Ctrl+C is pressed, or EOF is reached.
        """
        self._running = True

        # Display welcome message
        print("Chat Agent")
        print("Type /exit to quit, or press Ctrl+C\n")

        try:
            while self._running:
                # Get user input
                user_input = await self._get_user_input()

                # Handle EOF (Ctrl+D)
                if user_input is None:
                    print("\nGoodbye.")
                    break

                # Handle message and check if should continue
                should_continue = await self._handle_message(user_input)
                if not should_continue:
                    break

        except KeyboardInterrupt:
            # Should be caught by signal handler, but handle it just in case
            print("\n\nGoodbye.")

        finally:
            self._running = False

    def stop(self) -> None:
        """Stop the application loop."""
        self._running = False
