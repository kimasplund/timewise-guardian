"""Tests for the configuration module."""
import os
import tempfile
from pathlib import Path
import pytest
import yaml

from timewise_guardian_client.common.config import Config

@pytest.fixture
def temp_config_file():
    """Create a temporary configuration file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump({
            "ha_url": "http://test.local:8123",
            "ha_token": "test_token",
            "user_mapping": {
                "testuser": "ha_user"
            },
            "categories": {
                "test": {
                    "processes": ["test.exe"],
                    "window_titles": ["Test Window"],
                    "browser_patterns": {
                        "urls": ["test.com"],
                        "titles": ["Test Site"]
                    }
                }
            },
            "time_limits": {
                "test": 60
            },
            "time_restrictions": {
                "test": {
                    "weekday": {
                        "start": "09:00",
                        "end": "17:00"
                    }
                }
            }
        }, f)
        return Path(f.name)

def test_config_load(temp_config_file):
    """Test loading configuration from file."""
    config = Config(temp_config_file)
    assert config.ha_url == "http://test.local:8123"
    assert config.ha_token == "test_token"
    assert config.get_user_mapping("testuser") == "ha_user"

def test_config_defaults():
    """Test default configuration values."""
    with tempfile.NamedTemporaryFile(suffix='.yaml') as f:
        config = Config(Path(f.name))
        assert config.ha_url == "http://homeassistant.local:8123"
        assert config.ha_token == ""
        assert config.get_user_mapping("testuser") is None

def test_category_settings(temp_config_file):
    """Test category-specific settings."""
    config = Config(temp_config_file)
    assert config.get_category_processes("test") == ["test.exe"]
    assert config.get_category_window_titles("test") == ["Test Window"]
    assert config.get_category_browser_patterns("test") == {
        "urls": ["test.com"],
        "titles": ["Test Site"]
    }
    assert config.get_time_limit("test") == 60

def test_time_restrictions(temp_config_file):
    """Test time restriction settings."""
    config = Config(temp_config_file)
    restrictions = config.get_time_restrictions("test")
    assert restrictions["weekday"]["start"] == "09:00"
    assert restrictions["weekday"]["end"] == "17:00"

def test_save_config(temp_config_file):
    """Test saving configuration changes."""
    config = Config(temp_config_file)
    config.set("ha_url", "http://new.local:8123")
    
    # Load config again to verify changes were saved
    new_config = Config(temp_config_file)
    assert new_config.ha_url == "http://new.local:8123"

def test_invalid_config():
    """Test handling of invalid configuration file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml') as f:
        f.write("invalid: yaml: content")
        f.flush()
        
        with pytest.raises(Exception):
            Config(Path(f.name))

def teardown_module():
    """Clean up temporary files after tests."""
    # Clean up any remaining temporary files
    temp_dir = tempfile.gettempdir()
    for file in os.listdir(temp_dir):
        if file.endswith('.yaml'):
            try:
                os.remove(os.path.join(temp_dir, file))
            except OSError:
                pass 