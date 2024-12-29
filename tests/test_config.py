"""Tests for the configuration module."""
import os
from pathlib import Path
import pytest
import yaml
from timewise_guardian_client.common.config import Config

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
    with open(config_path, "w") as f:
        yaml.dump(test_config, f)
    return config_path

def test_config_load(temp_config_file):
    """Test loading configuration from file."""
    config = Config(temp_config_file)
    assert config.ha_url == "http://test.local:8123"
    assert config.ha_token == "test_token"
    assert config.sync_interval == 30
    assert config.memory_settings["max_client_memory_mb"] == 150

def test_config_default():
    """Test default configuration."""
    config = Config(Path("nonexistent.yaml"))
    assert config.ha_url == "http://homeassistant.local:8123"
    assert config.ha_token == ""
    assert config.sync_interval == 60
    assert config.memory_settings["max_client_memory_mb"] == 100

def test_ha_settings_update():
    """Test updating Home Assistant settings."""
    config = Config(Path("nonexistent.yaml"))
    test_settings = {
        "categories": {
            "games": {
                "processes": ["game.exe"],
                "window_titles": ["Game"]
            }
        },
        "time_limits": {
            "games": 120
        }
    }
    config.update_ha_settings(test_settings)
    assert config.get_category_processes("games") == ["game.exe"]
    assert config.get_category_window_titles("games") == ["Game"]
    assert config.get_time_limit("games") == 120

def test_config_save(temp_config_file):
    """Test saving configuration."""
    config = Config(temp_config_file)
    config.set("client", {"sync_interval": 45})
    
    # Load config again to verify save
    new_config = Config(temp_config_file)
    assert new_config.sync_interval == 45

@pytest.mark.asyncio
async def test_config_async_compatible():
    """Test configuration can be used in async context."""
    config = Config(Path("nonexistent.yaml"))
    await asyncio.sleep(0)  # Verify no conflicts with async
    assert config.ha_url == "http://homeassistant.local:8123" 