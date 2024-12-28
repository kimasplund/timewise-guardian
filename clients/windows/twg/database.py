"""Database handler for Timewise Guardian."""
import os
import sqlite3
from typing import Dict, List, Optional, Union
from datetime import datetime, time
import json

class PermissionDenied(Exception):
    """Exception raised when a user lacks required permissions."""
    pass

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

    def check_permission(self, user_id: int, permission_name: str) -> bool:
        """Check if a user has a specific permission."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check role-based permissions
            cursor.execute("""
                SELECT COUNT(*) FROM users u
                JOIN roles r ON u.role_id = r.id
                JOIN role_permissions rp ON r.id = rp.role_id
                JOIN permissions p ON rp.permission_id = p.id
                WHERE u.id = ? AND p.name = ?
            """, (user_id, permission_name))
            if cursor.fetchone()[0] > 0:
                return True
            
            # Check group-based permissions
            cursor.execute("""
                SELECT COUNT(*) FROM user_group_members ugm
                JOIN group_permissions gp ON ugm.group_id = gp.group_id
                JOIN permissions p ON gp.permission_id = p.id
                WHERE ugm.user_id = ? AND p.name = ?
            """, (user_id, permission_name))
            if cursor.fetchone()[0] > 0:
                return True
            
            # Check override permissions
            cursor.execute("""
                SELECT COUNT(*) FROM override_permissions op
                JOIN permissions p ON op.permission_id = p.id
                WHERE op.user_id = ? AND p.name = ?
                AND (op.expires_at IS NULL OR op.expires_at > CURRENT_TIMESTAMP)
            """, (user_id, permission_name))
            return cursor.fetchone()[0] > 0

    def require_permission(self, user_id: int, permission_name: str) -> None:
        """Require a specific permission or raise PermissionDenied."""
        if not self.check_permission(user_id, permission_name):
            raise PermissionDenied(f"User {user_id} lacks permission: {permission_name}")

    def get_user_permissions(self, user_id: int) -> List[dict]:
        """Get all permissions for a user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = self._dict_factory
            cursor = conn.cursor()
            
            # Get role-based permissions
            cursor.execute("""
                SELECT DISTINCT p.name, p.description, 'role' as source, r.name as source_name
                FROM users u
                JOIN roles r ON u.role_id = r.id
                JOIN role_permissions rp ON r.id = rp.role_id
                JOIN permissions p ON rp.permission_id = p.id
                WHERE u.id = ?
            """, (user_id,))
            role_perms = cursor.fetchall()
            
            # Get group-based permissions
            cursor.execute("""
                SELECT DISTINCT p.name, p.description, 'group' as source, g.name as source_name
                FROM user_group_members ugm
                JOIN user_groups g ON ugm.group_id = g.id
                JOIN group_permissions gp ON ugm.group_id = gp.group_id
                JOIN permissions p ON gp.permission_id = p.id
                WHERE ugm.user_id = ?
            """, (user_id,))
            group_perms = cursor.fetchall()
            
            # Get override permissions
            cursor.execute("""
                SELECT DISTINCT p.name, p.description, 'override' as source,
                       u.ha_username as granted_by, op.expires_at, op.reason
                FROM override_permissions op
                JOIN permissions p ON op.permission_id = p.id
                JOIN users u ON op.granted_by = u.id
                WHERE op.user_id = ?
                AND (op.expires_at IS NULL OR op.expires_at > CURRENT_TIMESTAMP)
            """, (user_id,))
            override_perms = cursor.fetchall()
            
            return role_perms + group_perms + override_perms

    def grant_permission(self, user_id: int, permission_name: str, granted_by: int,
                        expires_at: Optional[datetime] = None, reason: Optional[str] = None) -> None:
        """Grant a temporary permission override to a user."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get permission ID
            cursor.execute("SELECT id FROM permissions WHERE name = ?", (permission_name,))
            permission_id = cursor.fetchone()
            if not permission_id:
                raise ValueError(f"Invalid permission: {permission_name}")
            
            cursor.execute("""
                INSERT INTO override_permissions
                (user_id, permission_id, granted_by, expires_at, reason)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, permission_id[0], granted_by, expires_at, reason))

    def revoke_permission(self, user_id: int, permission_name: str) -> None:
        """Revoke a temporary permission override from a user."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM override_permissions
                WHERE user_id = ? AND permission_id = (
                    SELECT id FROM permissions WHERE name = ?
                )
            """, (user_id, permission_name))

    def create_user_group(self, name: str, description: str, created_by: int,
                         permissions: Optional[List[str]] = None) -> int:
        """Create a new user group."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO user_groups (name, description, created_by)
                VALUES (?, ?, ?)
            """, (name, description, created_by))
            group_id = cursor.lastrowid
            
            if permissions:
                # Add permissions to group
                cursor.executemany("""
                    INSERT INTO group_permissions (group_id, permission_id)
                    SELECT ?, id FROM permissions WHERE name = ?
                """, [(group_id, perm) for perm in permissions])
            
            return group_id

    def add_user_to_group(self, user_id: int, group_id: int) -> None:
        """Add a user to a group."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_group_members (group_id, user_id)
                VALUES (?, ?)
            """, (group_id, user_id))

    def remove_user_from_group(self, user_id: int, group_id: int) -> None:
        """Remove a user from a group."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM user_group_members
                WHERE group_id = ? AND user_id = ?
            """, (group_id, user_id))

    def get_user_groups(self, user_id: int) -> List[dict]:
        """Get all groups a user belongs to."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = self._dict_factory
            cursor = conn.cursor()
            cursor.execute("""
                SELECT g.*, u.ha_username as created_by_name
                FROM user_groups g
                JOIN user_group_members ugm ON g.id = ugm.group_id
                JOIN users u ON g.created_by = u.id
                WHERE ugm.user_id = ?
            """, (user_id,))
            return cursor.fetchall()

    def set_user_role(self, user_id: int, role_name: str) -> None:
        """Set a user's role."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET role_id = (
                    SELECT id FROM roles WHERE name = ?
                )
                WHERE id = ?
            """, (role_name, user_id))

    def set_parent_child_relationship(self, parent_id: int, child_id: int) -> None:
        """Set a parent-child relationship between users."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET parent_id = ?
                WHERE id = ?
            """, (parent_id, child_id))

    def get_children(self, parent_id: int) -> List[dict]:
        """Get all children for a parent user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = self._dict_factory
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.*, r.name as role_name
                FROM users u
                LEFT JOIN roles r ON u.role_id = r.id
                WHERE u.parent_id = ?
            """, (parent_id,))
            return cursor.fetchall() 

    def get_roles(self) -> List[dict]:
        """Get all roles."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = self._dict_factory
            cursor = conn.cursor()
            cursor.execute("""
                SELECT r.*, COUNT(rp.permission_id) as permission_count
                FROM roles r
                LEFT JOIN role_permissions rp ON r.id = rp.role_id
                GROUP BY r.id
            """)
            return cursor.fetchall()

    def create_role(self, name: str, description: str, permissions: Optional[List[str]] = None) -> int:
        """Create a new role."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO roles (name, description)
                VALUES (?, ?)
            """, (name, description))
            role_id = cursor.lastrowid
            
            if permissions:
                # Add permissions to role
                cursor.executemany("""
                    INSERT INTO role_permissions (role_id, permission_id)
                    SELECT ?, id FROM permissions WHERE name = ?
                """, [(role_id, perm) for perm in permissions])
            
            return role_id

    def update_role(self, role_id: int, name: Optional[str] = None,
                   description: Optional[str] = None,
                   permissions: Optional[List[str]] = None) -> None:
        """Update a role."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Update role details if provided
            if name or description:
                updates = []
                params = []
                if name:
                    updates.append("name = ?")
                    params.append(name)
                if description:
                    updates.append("description = ?")
                    params.append(description)
                
                cursor.execute(f"""
                    UPDATE roles
                    SET {', '.join(updates)}
                    WHERE id = ?
                """, params + [role_id])
            
            # Update permissions if provided
            if permissions is not None:
                # Remove existing permissions
                cursor.execute("""
                    DELETE FROM role_permissions
                    WHERE role_id = ?
                """, (role_id,))
                
                # Add new permissions
                cursor.executemany("""
                    INSERT INTO role_permissions (role_id, permission_id)
                    SELECT ?, id FROM permissions WHERE name = ?
                """, [(role_id, perm) for perm in permissions])

    def delete_role(self, role_id: int) -> None:
        """Delete a role."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if role is in use
            cursor.execute("""
                SELECT COUNT(*) FROM users
                WHERE role_id = ?
            """, (role_id,))
            if cursor.fetchone()[0] > 0:
                raise ValueError("Cannot delete role that is assigned to users")
            
            cursor.execute("""
                DELETE FROM roles
                WHERE id = ?
            """, (role_id,))

    def get_role_permissions(self, role_id: int) -> List[dict]:
        """Get permissions for a role."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = self._dict_factory
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.name, p.description
                FROM role_permissions rp
                JOIN permissions p ON rp.permission_id = p.id
                WHERE rp.role_id = ?
            """, (role_id,))
            return cursor.fetchall()

    def get_available_permissions(self) -> List[dict]:
        """Get all available permissions."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = self._dict_factory
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM permissions")
            return cursor.fetchall() 

    def log_permission_change(self, user_id: int, action_type: str, target_type: str,
                            target_id: int, permission_name: str, performed_by: int,
                            reason: Optional[str] = None) -> None:
        """Log a permission change to the audit log."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO permission_audit_log
                (user_id, action_type, target_type, target_id, permission_name, performed_by, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, action_type, target_type, target_id, permission_name, performed_by, reason))

    def log_role_change(self, role_id: int, action_type: str, performed_by: int,
                       details: Optional[Dict] = None, reason: Optional[str] = None) -> None:
        """Log a role change to the audit log."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            details_json = json.dumps(details) if details else None
            cursor.execute("""
                INSERT INTO role_audit_log
                (role_id, action_type, performed_by, details, reason)
                VALUES (?, ?, ?, ?, ?)
            """, (role_id, action_type, performed_by, details_json, reason))

    def log_group_change(self, group_id: int, action_type: str, performed_by: int,
                        details: Optional[Dict] = None, reason: Optional[str] = None) -> None:
        """Log a group change to the audit log."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            details_json = json.dumps(details) if details else None
            cursor.execute("""
                INSERT INTO group_audit_log
                (group_id, action_type, performed_by, details, reason)
                VALUES (?, ?, ?, ?, ?)
            """, (group_id, action_type, performed_by, details_json, reason))

    def get_permission_audit_logs(self, user_id: Optional[int] = None,
                                target_type: Optional[str] = None,
                                target_id: Optional[int] = None,
                                limit: int = 100) -> List[dict]:
        """Get permission audit logs with optional filters."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = self._dict_factory
            cursor = conn.cursor()
            
            query = """
                SELECT pal.*, 
                       u1.ha_username as user_name,
                       u2.ha_username as performed_by_name
                FROM permission_audit_log pal
                JOIN users u1 ON pal.user_id = u1.id
                JOIN users u2 ON pal.performed_by = u2.id
                WHERE 1=1
            """
            params = []
            
            if user_id is not None:
                query += " AND pal.user_id = ?"
                params.append(user_id)
            if target_type:
                query += " AND pal.target_type = ?"
                params.append(target_type)
            if target_id is not None:
                query += " AND pal.target_id = ?"
                params.append(target_id)
            
            query += " ORDER BY pal.created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            return cursor.fetchall()

    def get_role_audit_logs(self, role_id: Optional[int] = None,
                           limit: int = 100) -> List[dict]:
        """Get role audit logs with optional filters."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = self._dict_factory
            cursor = conn.cursor()
            
            query = """
                SELECT ral.*,
                       r.name as role_name,
                       u.ha_username as performed_by_name
                FROM role_audit_log ral
                JOIN roles r ON ral.role_id = r.id
                JOIN users u ON ral.performed_by = u.id
                WHERE 1=1
            """
            params = []
            
            if role_id is not None:
                query += " AND ral.role_id = ?"
                params.append(role_id)
            
            query += " ORDER BY ral.created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            return cursor.fetchall()

    def get_group_audit_logs(self, group_id: Optional[int] = None,
                            limit: int = 100) -> List[dict]:
        """Get group audit logs with optional filters."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = self._dict_factory
            cursor = conn.cursor()
            
            query = """
                SELECT gal.*,
                       g.name as group_name,
                       u.ha_username as performed_by_name
                FROM group_audit_log gal
                JOIN user_groups g ON gal.group_id = g.id
                JOIN users u ON gal.performed_by = u.id
                WHERE 1=1
            """
            params = []
            
            if group_id is not None:
                query += " AND gal.group_id = ?"
                params.append(group_id)
            
            query += " ORDER BY gal.created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            return cursor.fetchall() 