"""Blocklist management module."""
import os
import re
import asyncio
import logging
from typing import Dict, List, Set, Optional
import aiohttp
import yaml

logger = logging.getLogger(__name__)

STEVENBLACK_BASE_URL = "https://raw.githubusercontent.com/StevenBlack/hosts/master"
BLOCKLIST_CATEGORIES = {
    "base": "Ads and malware",
    "fakenews": "Fake news sites",
    "gambling": "Gambling sites",
    "porn": "Adult content",
    "social": "Social media",
    "youtube": "YouTube",
    "tiktok": "TikTok",
    "instagram": "Instagram",
    "facebook": "Facebook",
    "twitter": "Twitter",
    "reddit": "Reddit"
}

class BlocklistManager:
    """Manage domain blocklists."""
    
    def __init__(self, config_dir: str):
        """Initialize blocklist manager."""
        self.config_dir = config_dir
        self.blocklists_dir = os.path.join(config_dir, "blocklists")
        self.custom_dir = os.path.join(self.blocklists_dir, "custom")
        self._ensure_dirs()
        
        self.enabled_categories: Set[str] = set()
        self.whitelist: Set[str] = set()
        self.blacklist: Set[str] = set()
        self.blocked_domains: Set[str] = set()
        self.domains: Set[str] = set()
        
        # Load configuration
        self.load_config()
    
    def _ensure_dirs(self) -> None:
        """Ensure required directories exist."""
        os.makedirs(self.blocklists_dir, exist_ok=True)
        os.makedirs(self.custom_dir, exist_ok=True)
    
    def load_config(self) -> None:
        """Load blocklist configuration."""
        config_path = os.path.join(self.config_dir, "blocklists.yaml")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                self.enabled_categories = set(config.get("enabled_categories", []))
                self.whitelist = set(config.get("whitelist", []))
                self.blacklist = set(config.get("blacklist", []))
    
    def save_config(self) -> None:
        """Save blocklist configuration."""
        config = {
            "enabled_categories": sorted(list(self.enabled_categories)),
            "whitelist": sorted(list(self.whitelist)),
            "blacklist": sorted(list(self.blacklist))
        }
        config_path = os.path.join(self.config_dir, "blocklists.yaml")
        with open(config_path, "w") as f:
            yaml.dump(config, f)
    
    async def update_blocklists(self) -> None:
        """Update blocklists from sources."""
        async with aiohttp.ClientSession() as session:
            # Update base list
            await self._update_list(session, "base")
            
            # Update combination lists for enabled categories
            combinations = []
            for category in self.enabled_categories:
                if category in BLOCKLIST_CATEGORIES:
                    combinations.append(category)
            
            if combinations:
                combination_path = "-".join(sorted(combinations))
                await self._update_list(session, combination_path)
    
    async def _update_list(self, session: aiohttp.ClientSession, list_type: str) -> None:
        """Update a specific blocklist."""
        url = f"{STEVENBLACK_BASE_URL}"
        if list_type != "base":
            url += f"/alternates/{list_type}/hosts"
        else:
            url += "/hosts"
        
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    domains = self._parse_hosts_file(content)
                    self.domains.update(domains)
                    
                    # Save to file
                    output_path = os.path.join(self.blocklists_dir, f"{list_type}.txt")
                    with open(output_path, "w") as f:
                        for domain in sorted(domains):
                            f.write(f"{domain}\n")
                    
                    logger.info(f"Updated blocklist {list_type} with {len(domains)} domains")
                else:
                    logger.error(f"Failed to download blocklist {list_type}: {response.status}")
        except Exception as e:
            logger.error(f"Error updating blocklist {list_type}: {e}")
    
    def _parse_hosts_file(self, content: str) -> Set[str]:
        """Parse domains from hosts file content."""
        domains = set()
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                parts = line.split()
                if len(parts) >= 2:
                    domain = parts[1]
                    if self._is_valid_domain(domain):
                        domains.add(domain)
        return domains
    
    def _is_valid_domain(self, domain: str) -> bool:
        """Check if a domain is valid."""
        if not domain or not isinstance(domain, str):
            return False
        if domain in self.whitelist:
            return False
        if domain in self.blacklist:
            return True
        return bool(re.match(r"^[a-zA-Z0-9][-a-zA-Z0-9.]*\.[a-zA-Z]{2,}$", domain))
    
    def update_enabled_categories(self, categories: List[str]) -> None:
        """Update enabled blocklist categories."""
        self.enabled_categories = set(categories)
        self.save_config()
    
    def add_to_whitelist(self, domain: str) -> None:
        """Add domain to whitelist."""
        self.whitelist.add(domain)
        self.save_config()
    
    def remove_from_whitelist(self, domain: str) -> None:
        """Remove domain from whitelist."""
        self.whitelist.discard(domain)
        self.save_config()
    
    def add_to_blacklist(self, domain: str) -> None:
        """Add domain to blacklist."""
        self.blacklist.add(domain)
        self.save_config()
    
    def remove_from_blacklist(self, domain: str) -> None:
        """Remove domain from blacklist."""
        self.blacklist.discard(domain)
        self.save_config()
    
    def is_domain_blocked(self, domain: str) -> bool:
        """Check if a domain is blocked."""
        if domain in self.whitelist:
            return False
        if domain in self.blacklist:
            return True
        
        # Check against enabled blocklists
        for category in self.enabled_categories:
            blocklist_path = os.path.join(self.blocklists_dir, f"{category}.txt")
            if os.path.exists(blocklist_path):
                with open(blocklist_path, "r") as f:
                    if domain in {line.strip() for line in f}:
                        return True
        
        return False
    
    def get_available_categories(self) -> Dict[str, str]:
        """Get available blocklist categories with descriptions."""
        return BLOCKLIST_CATEGORIES.copy()
    
    async def schedule_updates(self, interval_hours: int = 24) -> None:
        """Schedule periodic blocklist updates."""
        while True:
            try:
                await self.update_blocklists()
            except Exception as e:
                logger.error(f"Error in scheduled blocklist update: {e}")
            await asyncio.sleep(interval_hours * 3600) 