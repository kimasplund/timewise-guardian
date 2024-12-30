"""Tests for blocklist management."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.timewise_guardian_client.common.blocklists import BlocklistManager
import os

@pytest.fixture
def mock_hosts_content():
    """Create mock hosts file content."""
    return """
# Comment line
127.0.0.1 localhost
0.0.0.0 ads.example.com
0.0.0.0 malware.example.com
0.0.0.0 tracking.example.com
# Another comment
0.0.0.0 spam.example.com
"""

@pytest.fixture
def blocklist_manager(tmp_path):
    """Create blocklist manager instance."""
    config_dir = tmp_path / "twg"
    config_dir.mkdir()
    return BlocklistManager(str(config_dir))

async def test_blocklist_initialization(blocklist_manager):
    """Test blocklist manager initialization."""
    assert blocklist_manager.whitelist == set()
    assert blocklist_manager.blacklist == set()
    assert blocklist_manager.enabled_categories == set()
    assert blocklist_manager.domains == set()

async def test_parse_hosts_file(blocklist_manager, mock_hosts_content):
    """Test parsing hosts file content."""
    domains = blocklist_manager._parse_hosts_file(mock_hosts_content)
    assert "ads.example.com" in domains
    assert "malware.example.com" in domains
    assert "tracking.example.com" in domains
    assert "spam.example.com" in domains
    assert "localhost" not in domains

async def test_whitelist_management(blocklist_manager):
    """Test whitelist management."""
    blocklist_manager.add_to_whitelist("example.com")
    assert "example.com" in blocklist_manager.whitelist

    blocklist_manager.remove_from_whitelist("example.com")
    assert "example.com" not in blocklist_manager.whitelist

async def test_blacklist_management(blocklist_manager):
    """Test blacklist management."""
    blocklist_manager.add_to_blacklist("example.com")
    assert "example.com" in blocklist_manager.blacklist

    blocklist_manager.remove_from_blacklist("example.com")
    assert "example.com" not in blocklist_manager.blacklist

async def test_category_management(blocklist_manager):
    """Test category management."""
    blocklist_manager.update_enabled_categories(["social", "gaming"])
    assert "social" in blocklist_manager.enabled_categories
    assert "gaming" in blocklist_manager.enabled_categories

async def test_domain_blocking(blocklist_manager):
    """Test domain blocking."""
    # Setup test data
    blocklist_manager.add_to_blacklist("blocked.com")
    blocklist_manager.add_to_whitelist("allowed.com")
    
    # Create a mock blocklist file
    base_file = os.path.join(blocklist_manager.blocklists_dir, "base.txt")
    os.makedirs(os.path.dirname(base_file), exist_ok=True)
    with open(base_file, "w") as f:
        f.write("ads.example.com\n")
    
    blocklist_manager.enabled_categories.add("base")
    
    assert blocklist_manager.is_domain_blocked("blocked.com")
    assert not blocklist_manager.is_domain_blocked("allowed.com")
    assert blocklist_manager.is_domain_blocked("ads.example.com")
    assert not blocklist_manager.is_domain_blocked("example.com")

@pytest.mark.asyncio
async def test_update_blocklists(blocklist_manager, mock_hosts_content):
    """Test updating blocklists."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value=mock_hosts_content)

    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()

    with patch("aiohttp.ClientSession", return_value=mock_session):
        await blocklist_manager.update_blocklists()
        
        # Verify domains are saved to file
        base_file = os.path.join(blocklist_manager.blocklists_dir, "base.txt")
        assert os.path.exists(base_file)
        with open(base_file) as f:
            content = f.read()
            assert "ads.example.com" in content
            assert "malware.example.com" in content

async def test_available_categories(blocklist_manager):
    """Test getting available categories."""
    categories = blocklist_manager.get_available_categories()
    assert isinstance(categories, dict)
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in categories.items())

async def test_invalid_domain_handling(blocklist_manager):
    """Test handling of invalid domains."""
    invalid_domains = [
        None,
        "",
        "not_a_domain",
        ".com",
        "http://",
        "example.",
        "-example.com",
        "example-.com",
        "exam!ple.com"
    ]

    for domain in invalid_domains:
        assert not blocklist_manager._is_valid_domain(domain)
        if isinstance(domain, str):
            blocklist_manager.add_to_whitelist(domain)
            blocklist_manager.add_to_blacklist(domain) 