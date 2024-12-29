"""Test connection to Home Assistant."""
import sys
import yaml
import requests
from pathlib import Path

def test_connection():
    """Test connection to Home Assistant."""
    try:
        # Load config
        config_path = Path(__file__).parent / "config.yaml"
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Extract connection details
        ha_url = config["homeassistant"]["url"]
        ha_token = config["homeassistant"]["token"]

        # Test connection
        headers = {
            "Authorization": f"Bearer {ha_token}",
            "Content-Type": "application/json",
        }

        response = requests.get(f"{ha_url}/api/", headers=headers)
        response.raise_for_status()

        print("✓ Successfully connected to Home Assistant!")
        print(f"URL: {ha_url}")
        print(f"API Response: {response.json()}")
        return True

    except FileNotFoundError:
        print("✗ Error: config.yaml not found")
        return False
    except yaml.YAMLError as e:
        print(f"✗ Error parsing config.yaml: {e}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Error connecting to Home Assistant: {e}")
        return False

if __name__ == "__main__":
    sys.exit(0 if test_connection() else 1) 