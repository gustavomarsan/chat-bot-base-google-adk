"""Main entry point for chat agent."""

import asyncio
import sys
import uuid

from .config import Config
from .agent import ChatAgent
from .app import ChatApplication


def main() -> int:
    """
    Main entry point.

    Loads configuration, initializes agent and application, and runs the chat loop.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Load configuration
        config = Config.load()

    except ValueError as e:
        # Configuration error - print message and exit
        print(str(e), file=sys.stderr)
        return 1

    except Exception as e:
        # Unexpected error loading configuration
        print(f"Error loading configuration: {e}", file=sys.stderr)
        return 1

    try:
        # Generate unique session ID for this terminal session
        session_id = str(uuid.uuid4())

        # Initialize agent
        agent = ChatAgent(config, session_id=session_id)

        # Initialize application
        app = ChatApplication(agent)

        # Run application
        asyncio.run(app.run())

        return 0

    except KeyboardInterrupt:
        # Handled by signal handler, but catch here just in case
        print("\n\nGoodbye.")
        return 0

    except Exception as e:
        # Unexpected error during execution
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
