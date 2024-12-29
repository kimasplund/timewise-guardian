"""Tests for the configuration module."""
import os
import asyncio
from pathlib import Path
import pytest
import yaml
from timewise_guardian_client.common.config import Config

pytestmark = pytest.mark.asyncio  # Mark all tests in this module as async

@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file."""
    config_path = tmp_path / "config.yaml"
    test_config = {
        "homeassistant": {
            "url": "http://test.local:8123",
            "token": "test_token"
        },
        "client": {
            "auto_register": True,
            "sync_interval": 30,
            "memory_management": {
                "max_client_memory_mb": 150,
                "cleanup_interval_minutes": 10,
                "memory_threshold": 85
            }
        }
    }
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(test_config, f)
    return config_path

@pytest.fixture
async def config(temp_config_file):
    """Fixture for config object."""
    return Config(temp_config_file)

async def test_config_load(config):
    """Test loading configuration from file."""
    assert config.ha_url == "http://test.local:8123"
    assert config.ha_token == "test_token"
    assert config.sync_interval == 30
    assert config.memory_settings["max_client_memory_mb"] == 150

async def test_config_default():
    """Test default configuration."""
    config = Config(Path("nonexistent.yaml"))
    assert config.ha_url == "http://homeassistant.local:8123"
    assert config.ha_token == ""
    assert config.sync_interval == 60
    assert config.memory_settings["max_client_memory_mb"] == 100

async def test_ha_settings_update():
    """Test updating Home Assistant settings."""
    config = Config(Path("nonexistent.yaml"))
    test_settings = {
        "categories": {
            "games": {
                "processes": ["game.exe"],
                "window_titles": ["Game"]
            }
        },
        "blocked_categories": ["youtube_gaming", "social_media"],
        "youtube_restrictions": {
            "blocked_categories": ["gaming", "entertainment"]
        },
        "blocked_patterns": [r"youtube\.com/watch\?v=.*&category=20"],
        "time_limits": {
            "games": 120
        }
    }
    config.update_ha_settings(test_settings)
    assert config.ha_settings == test_settings

async def test_config_save(temp_config_file):
    """Test saving configuration."""
    config = Config(temp_config_file)
    config.set("client", {"sync_interval": 45})
    
    # Load config again to verify save
    new_config = Config(temp_config_file)
    assert new_config.sync_interval == 45

async def test_config_async_compatible():
    """Test configuration can be used in async context."""
    config = Config(Path("nonexistent.yaml"))
    await asyncio.sleep(0)  # Verify no conflicts with async
    assert isinstance(config, Config) 