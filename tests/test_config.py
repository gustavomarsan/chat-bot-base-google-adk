"""Tests for configuration module."""

import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from chat_agent.config import Config


@pytest.fixture(autouse=True)
def mock_dotenv(monkeypatch):
    """Mock dotenv loading to prevent .env file from being loaded."""
    import dotenv
    monkeypatch.setattr(dotenv, "load_dotenv", MagicMock())


@pytest.fixture
def mock_env():
    """Mock environment variables for testing."""
    return {
        "MODEL": "gemini-3.5-flash-lite",
        "FALLBACK_MODEL": "gemini-3.6-flash-lite",
        "GEMINI_API_KEY": "test-api-key",
        "RETRY_MAX_ATTEMPTS": "3",
        "TEMPERATURE": "0.7",
        "MAX_OUTPUT_TOKENS": "2048",
    }


@pytest.fixture
def mock_prompt_file(tmp_path):
    """Create a temporary prompt file for testing."""
    prompt_file = tmp_path / "test_prompt.md"
    prompt_file.write_text("You are a helpful assistant.")
    return str(prompt_file)


def test_load_config_success(mock_env, mock_prompt_file):
    """Test successful configuration loading."""
    with patch.dict(os.environ, mock_env, clear=True):
        config = Config.load(prompt_file=mock_prompt_file, load_env=False)

    assert config.model == "gemini-3.5-flash-lite"
    assert config.fallback_model == "gemini-3.6-flash-lite"
    assert config.gemini_api_key == "test-api-key"
    assert config.retry_max_attempts == 3
    assert config.temperature == 0.7
    assert config.max_output_tokens == 2048
    assert config.system_prompt == "You are a helpful assistant."


def test_load_config_with_defaults(mock_env, mock_prompt_file):
    """Test configuration loading with default values."""
    # Remove optional settings
    env = {k: v for k, v in mock_env.items() if k in ["MODEL", "FALLBACK_MODEL", "GEMINI_API_KEY"]}

    with patch.dict(os.environ, env, clear=True):
        config = Config.load(prompt_file=mock_prompt_file, load_env=False)

    assert config.retry_max_attempts == 3
    assert config.temperature == 0.7
    assert config.max_output_tokens == 2048


def test_load_config_missing_model(mock_env, mock_prompt_file):
    """Test error when MODEL is missing."""
    env = {k: v for k, v in mock_env.items() if k != "MODEL"}

    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ValueError, match="Configuration error: MODEL not set"):
            Config.load(prompt_file=mock_prompt_file, load_env=False)


def test_load_config_missing_fallback_model(mock_env, mock_prompt_file):
    """Test error when FALLBACK_MODEL is missing."""
    env = {k: v for k, v in mock_env.items() if k != "FALLBACK_MODEL"}

    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ValueError, match="Configuration error: FALLBACK_MODEL not set"):
            Config.load(prompt_file=mock_prompt_file, load_env=False)


def test_load_config_missing_api_key(mock_env, mock_prompt_file):
    """Test error when GEMINI_API_KEY is missing."""
    env = {k: v for k, v in mock_env.items() if k != "GEMINI_API_KEY"}

    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ValueError, match="Configuration error: GEMINI_API_KEY not set"):
            Config.load(prompt_file=mock_prompt_file, load_env=False)


def test_load_config_invalid_retry_attempts(mock_env, mock_prompt_file):
    """Test error when RETRY_MAX_ATTEMPTS is invalid."""
    mock_env["RETRY_MAX_ATTEMPTS"] = "0"

    with patch.dict(os.environ, mock_env, clear=True):
        with pytest.raises(ValueError, match="RETRY_MAX_ATTEMPTS must be at least 1"):
            Config.load(prompt_file=mock_prompt_file)


def test_load_config_invalid_temperature_low(mock_env, mock_prompt_file):
    """Test error when TEMPERATURE is below valid range."""
    mock_env["TEMPERATURE"] = "-0.1"

    with patch.dict(os.environ, mock_env, clear=True):
        with pytest.raises(ValueError, match="TEMPERATURE must be between 0.0 and 1.0"):
            Config.load(prompt_file=mock_prompt_file)


def test_load_config_invalid_temperature_high(mock_env, mock_prompt_file):
    """Test error when TEMPERATURE is above valid range."""
    mock_env["TEMPERATURE"] = "1.1"

    with patch.dict(os.environ, mock_env, clear=True):
        with pytest.raises(ValueError, match="TEMPERATURE must be between 0.0 and 1.0"):
            Config.load(prompt_file=mock_prompt_file)


def test_load_config_invalid_max_tokens(mock_env, mock_prompt_file):
    """Test error when MAX_OUTPUT_TOKENS is invalid."""
    mock_env["MAX_OUTPUT_TOKENS"] = "0"

    with patch.dict(os.environ, mock_env, clear=True):
        with pytest.raises(ValueError, match="MAX_OUTPUT_TOKENS must be at least 1"):
            Config.load(prompt_file=mock_prompt_file)


def test_load_prompt_file_not_found(mock_env):
    """Test error when prompt file does not exist."""
    with patch.dict(os.environ, mock_env, clear=True):
        with pytest.raises(ValueError, match="Prompt file error: nonexistent.md not found"):
            Config.load(prompt_file="nonexistent.md")


def test_load_prompt_file_empty(mock_env, tmp_path):
    """Test error when prompt file is empty."""
    empty_file = tmp_path / "empty.md"
    empty_file.write_text("")

    with patch.dict(os.environ, mock_env, clear=True):
        with pytest.raises(ValueError, match="Prompt file error: .* is empty"):
            Config.load(prompt_file=str(empty_file))


def test_load_prompt_file_whitespace_only(mock_env, tmp_path):
    """Test error when prompt file contains only whitespace."""
    whitespace_file = tmp_path / "whitespace.md"
    whitespace_file.write_text("   \n\t  \n  ")

    with patch.dict(os.environ, mock_env, clear=True):
        with pytest.raises(ValueError, match="Prompt file error: .* is empty"):
            Config.load(prompt_file=str(whitespace_file))
