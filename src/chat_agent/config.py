"""Configuration module for chat agent.

Loads and validates environment variables and system prompt.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass
class Config:
    """Configuration settings for the chat agent."""

    model: str
    fallback_model: str
    gemini_api_key: str
    system_prompt: str
    retry_max_attempts: int = 3
    temperature: float = 0.7
    max_output_tokens: int = 2048

    @classmethod
    def load(cls, prompt_file: str = "prompts/system_prompt.md", load_env: bool = True) -> "Config":
        """Load configuration from environment and prompt file.

        Args:
            prompt_file: Path to system prompt file (relative to project root)
            load_env: Whether to load .env file (set to False in tests)

        Returns:
            Config instance with validated settings

        Raises:
            ValueError: If required configuration is missing or invalid
        """
        # Load environment variables from .env file
        if load_env:
            load_dotenv()

        # Validate required environment variables
        model = os.getenv("MODEL")
        if not model:
            raise ValueError(
                "Configuration error: MODEL not set\n"
                "Please set MODEL in your .env file"
            )

        fallback_model = os.getenv("FALLBACK_MODEL")
        if not fallback_model:
            raise ValueError(
                "Configuration error: FALLBACK_MODEL not set\n"
                "Please set FALLBACK_MODEL in your .env file"
            )

        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError(
                "Configuration error: GEMINI_API_KEY not set\n"
                "Please set GEMINI_API_KEY in your .env file"
            )

        # Load optional settings with defaults
        retry_max_attempts = int(os.getenv("RETRY_MAX_ATTEMPTS", "3"))
        temperature = float(os.getenv("TEMPERATURE", "0.7"))
        max_output_tokens = int(os.getenv("MAX_OUTPUT_TOKENS", "2048"))

        # Validate ranges
        if retry_max_attempts < 1:
            raise ValueError("RETRY_MAX_ATTEMPTS must be at least 1")

        if not 0.0 <= temperature <= 1.0:
            raise ValueError("TEMPERATURE must be between 0.0 and 1.0")

        if max_output_tokens < 1:
            raise ValueError("MAX_OUTPUT_TOKENS must be at least 1")

        # Load system prompt
        system_prompt = cls._load_prompt(prompt_file)

        return cls(
            model=model,
            fallback_model=fallback_model,
            gemini_api_key=gemini_api_key,
            system_prompt=system_prompt,
            retry_max_attempts=retry_max_attempts,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

    @staticmethod
    def _load_prompt(prompt_file: str) -> str:
        """Load system prompt from file.

        Args:
            prompt_file: Path to prompt file

        Returns:
            Prompt content as string

        Raises:
            ValueError: If prompt file is missing or empty
        """
        prompt_path = Path(prompt_file)

        if not prompt_path.exists():
            raise ValueError(
                f"Prompt file error: {prompt_file} not found\n"
                "Please create the prompt file before starting the agent"
            )

        prompt_content = prompt_path.read_text(encoding="utf-8").strip()

        if not prompt_content:
            raise ValueError(
                f"Prompt file error: {prompt_file} is empty\n"
                "Please add content to the prompt file before starting the agent"
            )

        return prompt_content
