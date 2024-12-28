"""Database handler for Timewise Guardian."""
import os
import sqlite3
from typing import Dict, List, Optional, Union
from datetime import datetime, time
import json

class Database:
    """Database handler class."""

    def __init__(self, db_path: str = "config.db"):
        """Initialize database connection."""
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database with schema."""
        if not os.path.exists(self.db_path):
            with open("schema.sql", "r") as f:
                schema = f.read()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(schema)

    def _dict_factory(self, cursor: sqlite3.Cursor, row: tuple) -> dict:
        """Convert database row to dictionary."""
        fields = [column[0] for column in cursor.description]
        return {key: value for key, value in zip(fields, row)}

    def get_user(self, windows_username: str) -> Optional[dict]:
        """Get user by Windows username."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = self._dict_factory
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE windows_username = ?",
                (windows_username,)
            )
            return cursor.fetchone()

    def get_categories(self) -> List[dict]:
        """Get all categories with their patterns and restrictions."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = self._dict_factory
            cursor = conn.cursor()
            
            # Get categories
            cursor.execute("SELECT * FROM categories")
            categories = cursor.fetchall()
            
            for category in categories:
                # Get process patterns
                cursor.execute(
                    "SELECT pattern FROM process_patterns WHERE category_id = ?",
                    (category["id"],)
                )
                category["processes"] = [row["pattern"] for row in cursor.fetchall()]
                
                # Get window patterns
                cursor.execute(
                    "SELECT pattern FROM window_patterns WHERE category_id = ?",
                    (category["id"],)
                )
                category["window_titles"] = [row["pattern"] for row in cursor.fetchall()]
                
                # Get browser patterns
                cursor.execute(
                    "SELECT type, pattern, is_exclude FROM browser_patterns WHERE category_id = ?",
                    (category["id"],)
                )
                browser_patterns = cursor.fetchall()
                category["browser_patterns"] = {
                    "urls": [],
                    "titles": [],
                    "youtube_channels": [],
                    "exclude": []
                }
                for pattern in browser_patterns:
                    if pattern["is_exclude"]:
                        category["browser_patterns"]["exclude"].append(pattern["pattern"])
                    else:
                        category["browser_patterns"][pattern["type"]].append(pattern["pattern"])
                
                # Get time restrictions
                cursor.execute(
                    "SELECT day_type, start_time, end_time FROM time_restrictions WHERE category_id = ?",
                    (category["id"],)
                )
                restrictions = cursor.fetchall()
                category["time_restrictions"] = {
                    row["day_type"]: {
                        "start": row["start_time"],
                        "end": row["end_time"]
                    }
                    for row in restrictions
                }
            
            return categories

    def get_settings(self) -> dict:
        """Get all settings."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = self._dict_factory
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings")
            settings = {row["key"]: row["value"] for row in cursor.fetchall()}
            
            # Convert string lists to actual lists
            if "warning_intervals" in settings:
                settings["warning_intervals"] = [
                    int(x) for x in settings["warning_intervals"].split(",")
                ]
            
            # Convert string booleans to actual booleans
            if "sound_enabled" in settings:
                settings["sound_enabled"] = settings["sound_enabled"].lower() == "true"
            
            return settings

    def get_user_settings(self, user_id: int) -> dict:
        """Get settings for a specific user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = self._dict_factory
            cursor = conn.cursor()
            cursor.execute(
                "SELECT key, value FROM user_settings WHERE user_id = ?",
                (user_id,)
            )
            return {row["key"]: row["value"] for row in cursor.fetchall()}

    def update_setting(self, key: str, value: Union[str, int, bool, list]) -> None:
        """Update a setting value."""
        # Convert value to string for storage
        if isinstance(value, bool):
            value = str(value).lower()
        elif isinstance(value, list):
            value = ",".join(str(x) for x in value)
        else:
            value = str(value)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO settings (key, value)
                VALUES (?, ?)
                """,
                (key, value)
            )

    def update_user_setting(self, user_id: int, key: str, value: str) -> None:
        """Update a user-specific setting."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO user_settings (user_id, key, value)
                VALUES (?, ?, ?)
                """,
                (user_id, key, value)
            )

    def add_category(
        self,
        name: str,
        time_limit: Optional[int] = None,
        processes: Optional[List[str]] = None,
        window_titles: Optional[List[str]] = None,
        browser_patterns: Optional[Dict[str, List[str]]] = None,
        time_restrictions: Optional[Dict[str, Dict[str, str]]] = None
    ) -> int:
        """Add a new category with all its patterns and restrictions."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Add category
            cursor.execute(
                "INSERT INTO categories (name, time_limit) VALUES (?, ?)",
                (name, time_limit)
            )
            category_id = cursor.lastrowid
            
            # Add process patterns
            if processes:
                cursor.executemany(
                    "INSERT INTO process_patterns (category_id, pattern) VALUES (?, ?)",
                    [(category_id, pattern) for pattern in processes]
                )
            
            # Add window patterns
            if window_titles:
                cursor.executemany(
                    "INSERT INTO window_patterns (category_id, pattern) VALUES (?, ?)",
                    [(category_id, pattern) for pattern in window_titles]
                )
            
            # Add browser patterns
            if browser_patterns:
                patterns = []
                for pattern_type, pattern_list in browser_patterns.items():
                    if pattern_type == "exclude":
                        patterns.extend([(category_id, "url", p, True) for p in pattern_list])
                    else:
                        patterns.extend([(category_id, pattern_type, p, False) for p in pattern_list])
                
                cursor.executemany(
                    """
                    INSERT INTO browser_patterns (category_id, type, pattern, is_exclude)
                    VALUES (?, ?, ?, ?)
                    """,
                    patterns
                )
            
            # Add time restrictions
            if time_restrictions:
                restrictions = []
                for day_type, times in time_restrictions.items():
                    restrictions.append((
                        category_id,
                        day_type,
                        times["start"],
                        times["end"]
                    ))
                
                cursor.executemany(
                    """
                    INSERT INTO time_restrictions (category_id, day_type, start_time, end_time)
                    VALUES (?, ?, ?, ?)
                    """,
                    restrictions
                )
            
            return category_id

    def update_category(
        self,
        category_id: int,
        time_limit: Optional[int] = None,
        processes: Optional[List[str]] = None,
        window_titles: Optional[List[str]] = None,
        browser_patterns: Optional[Dict[str, List[str]]] = None,
        time_restrictions: Optional[Dict[str, Dict[str, str]]] = None
    ) -> None:
        """Update an existing category."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Update time limit
            if time_limit is not None:
                cursor.execute(
                    "UPDATE categories SET time_limit = ? WHERE id = ?",
                    (time_limit, category_id)
                )
            
            # Update process patterns
            if processes is not None:
                cursor.execute(
                    "DELETE FROM process_patterns WHERE category_id = ?",
                    (category_id,)
                )
                cursor.executemany(
                    "INSERT INTO process_patterns (category_id, pattern) VALUES (?, ?)",
                    [(category_id, pattern) for pattern in processes]
                )
            
            # Update window patterns
            if window_titles is not None:
                cursor.execute(
                    "DELETE FROM window_patterns WHERE category_id = ?",
                    (category_id,)
                )
                cursor.executemany(
                    "INSERT INTO window_patterns (category_id, pattern) VALUES (?, ?)",
                    [(category_id, pattern) for pattern in window_titles]
                )
            
            # Update browser patterns
            if browser_patterns is not None:
                cursor.execute(
                    "DELETE FROM browser_patterns WHERE category_id = ?",
                    (category_id,)
                )
                patterns = []
                for pattern_type, pattern_list in browser_patterns.items():
                    if pattern_type == "exclude":
                        patterns.extend([(category_id, "url", p, True) for p in pattern_list])
                    else:
                        patterns.extend([(category_id, pattern_type, p, False) for p in pattern_list])
                
                cursor.executemany(
                    """
                    INSERT INTO browser_patterns (category_id, type, pattern, is_exclude)
                    VALUES (?, ?, ?, ?)
                    """,
                    patterns
                )
            
            # Update time restrictions
            if time_restrictions is not None:
                cursor.execute(
                    "DELETE FROM time_restrictions WHERE category_id = ?",
                    (category_id,)
                )
                restrictions = []
                for day_type, times in time_restrictions.items():
                    restrictions.append((
                        category_id,
                        day_type,
                        times["start"],
                        times["end"]
                    ))
                
                cursor.executemany(
                    """
                    INSERT INTO time_restrictions (category_id, day_type, start_time, end_time)
                    VALUES (?, ?, ?, ?)
                    """,
                    restrictions
                )

    def delete_category(self, category_id: int) -> None:
        """Delete a category and all its related data."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))

    def import_yaml_config(self, yaml_path: str) -> None:
        """Import configuration from YAML file."""
        import yaml
        
        with open(yaml_path, "r") as f:
            config = yaml.safe_load(f)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Import user mapping
            for windows_username, ha_username in config.get("user_mapping", {}).items():
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO users (windows_username, ha_username)
                    VALUES (?, ?)
                    """,
                    (windows_username, ha_username)
                )
            
            # Import categories
            for name, category in config.get("categories", {}).items():
                time_limit = config.get("time_limits", {}).get(name)
                time_restrictions = config.get("time_restrictions", {}).get(name)
                
                self.add_category(
                    name=name,
                    time_limit=time_limit,
                    processes=category.get("processes"),
                    window_titles=category.get("window_titles"),
                    browser_patterns={
                        "urls": category.get("browser_patterns", {}).get("urls", []),
                        "titles": category.get("browser_patterns", {}).get("titles", []),
                        "youtube_channels": category.get("browser_patterns", {}).get("youtube_channels", []),
                        "exclude": category.get("browser_patterns", {}).get("exclude", [])
                    },
                    time_restrictions=time_restrictions
                )
            
            # Import settings
            notifications = config.get("notifications", {})
            for key, value in notifications.items():
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO settings (key, value)
                    VALUES (?, ?)
                    """,
                    (key, str(value))
                )
            
            # Import Home Assistant settings
            cursor.execute(
                """
                INSERT OR REPLACE INTO settings (key, value)
                VALUES (?, ?)
                """,
                ("ha_url", config.get("ha_url"))
            )
            if "ha_token" in config:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO settings (key, value)
                    VALUES (?, ?)
                    """,
                    ("ha_token", config.get("ha_token"))
                )

    def export_yaml_config(self, yaml_path: str) -> None:
        """Export configuration to YAML file."""
        import yaml
        
        config = {
            "user_mapping": {},
            "categories": {},
            "time_limits": {},
            "time_restrictions": {},
            "notifications": {}
        }
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = self._dict_factory
            cursor = conn.cursor()
            
            # Export user mapping
            cursor.execute("SELECT windows_username, ha_username FROM users")
            config["user_mapping"] = {
                row["windows_username"]: row["ha_username"]
                for row in cursor.fetchall()
            }
            
            # Export categories
            categories = self.get_categories()
            for category in categories:
                name = category["name"]
                config["categories"][name] = {
                    "processes": category["processes"],
                    "window_titles": category["window_titles"],
                    "browser_patterns": category["browser_patterns"]
                }
                if category["time_limit"]:
                    config["time_limits"][name] = category["time_limit"]
                if category["time_restrictions"]:
                    config["time_restrictions"][name] = category["time_restrictions"]
            
            # Export settings
            settings = self.get_settings()
            config["ha_url"] = settings.get("ha_url")
            config["notifications"] = {
                "warning_threshold": int(settings.get("warning_threshold", 10)),
                "warning_intervals": settings.get("warning_intervals", [30, 15, 10, 5, 1]),
                "popup_duration": int(settings.get("popup_duration", 10)),
                "sound_enabled": settings.get("sound_enabled", True)
            }
        
        with open(yaml_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False) 