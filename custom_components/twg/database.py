"""Database management for Timewise Guardian."""
from datetime import datetime
from typing import Dict, List, Optional
import logging
from pathlib import Path
import sqlite3
import json

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)

SCHEMA_VERSION = 1
DB_FILENAME = "twg.db"

# Default roles and permissions
DEFAULT_ROLES = {
    "admin": {
        "description": "Full system access",
        "permissions": [
            "manage_users",
            "manage_roles",
            "manage_permissions",
            "view_audit_log",
            "manage_categories",
            "manage_time_limits",
            "manage_restrictions",
            "view_statistics",
            "manage_notifications",
        ]
    },
    "parent": {
        "description": "Parent/Guardian access",
        "permissions": [
            "manage_users",
            "manage_categories",
            "manage_time_limits",
            "manage_restrictions",
            "view_statistics",
            "manage_notifications",
        ]
    },
    "user": {
        "description": "Standard user access",
        "permissions": [
            "view_own_statistics",
            "view_own_time_limits",
            "view_own_restrictions",
        ]
    },
}

DEFAULT_PERMISSIONS = {
    "manage_users": "Create, update, and delete user accounts",
    "manage_roles": "Create, update, and delete roles",
    "manage_permissions": "Grant and revoke permissions",
    "view_audit_log": "View system audit logs",
    "manage_categories": "Create and manage activity categories",
    "manage_time_limits": "Set and modify time limits",
    "manage_restrictions": "Set and modify time restrictions",
    "view_statistics": "View all user statistics",
    "manage_notifications": "Configure notification settings",
    "view_own_statistics": "View own usage statistics",
    "view_own_time_limits": "View own time limits",
    "view_own_restrictions": "View own time restrictions",
}

class PermissionDenied(HomeAssistantError):
    """Permission denied error."""

class Database:
    """Database management class."""

    def __init__(self, hass: Optional[HomeAssistant] = None) -> None:
        """Initialize database."""
        self.hass = hass
        self._conn = None
        self._cursor = None
        self._setup_database()
        self._initialize_defaults()

    def _setup_database(self) -> None:
        """Set up database and create tables if they don't exist."""
        db_path = Path(self.hass.config.path(DB_FILENAME)) if self.hass else Path(DB_FILENAME)
        
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._cursor = self._conn.cursor()

        # Create tables
        self._cursor.executescript("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            );

            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS role_permissions (
                role_id INTEGER,
                permission_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (role_id, permission_id),
                FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
                FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS user_roles (
                user_id TEXT,
                role_id INTEGER,
                granted_by TEXT,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, role_id),
                FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS user_permissions (
                user_id TEXT,
                permission_id INTEGER,
                granted_by TEXT,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                reason TEXT,
                PRIMARY KEY (user_id, permission_id),
                FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT,
                action TEXT,
                target_type TEXT,
                target_id TEXT,
                details TEXT
            );
        """)

        # Check schema version
        self._cursor.execute("SELECT version FROM schema_version LIMIT 1")
        result = self._cursor.fetchone()
        if not result:
            self._cursor.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
            self._conn.commit()

    def _initialize_defaults(self) -> None:
        """Initialize default roles and permissions."""
        try:
            # Initialize permissions
            for name, description in DEFAULT_PERMISSIONS.items():
                self._cursor.execute("""
                    INSERT OR IGNORE INTO permissions (name, description)
                    VALUES (?, ?)
                """, (name, description))

            # Initialize roles
            for role_name, role_data in DEFAULT_ROLES.items():
                self._cursor.execute("""
                    INSERT OR IGNORE INTO roles (name, description)
                    VALUES (?, ?)
                """, (role_name, role_data["description"]))

                # Get role ID
                self._cursor.execute("SELECT id FROM roles WHERE name = ?", (role_name,))
                role = self._cursor.fetchone()
                if not role:
                    continue

                # Add permissions to role
                for permission_name in role_data["permissions"]:
                    self._cursor.execute("""
                        INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
                        SELECT ?, id FROM permissions WHERE name = ?
                    """, (role["id"], permission_name))

            self._conn.commit()
        except sqlite3.Error as err:
            _LOGGER.error("Failed to initialize defaults: %s", err)

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()

    def get_roles(self) -> List[Dict]:
        """Get all roles."""
        self._cursor.execute("""
            SELECT r.*, GROUP_CONCAT(p.name) as permissions
            FROM roles r
            LEFT JOIN role_permissions rp ON r.id = rp.role_id
            LEFT JOIN permissions p ON rp.permission_id = p.id
            GROUP BY r.id
        """)
        return [dict(row) for row in self._cursor.fetchall()]

    def create_role(self, name: str, description: str, permissions: List[str] = None) -> int:
        """Create a new role."""
        try:
            self._cursor.execute(
                "INSERT INTO roles (name, description) VALUES (?, ?)",
                (name, description)
            )
            role_id = self._cursor.lastrowid

            if permissions:
                self._add_permissions_to_role(role_id, permissions)

            self._conn.commit()
            return role_id
        except sqlite3.IntegrityError as err:
            raise PermissionDenied(f"Role name already exists: {err}")

    def update_role(self, role_id: int, name: str = None, description: str = None,
                   permissions: List[str] = None) -> None:
        """Update a role."""
        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        
        if updates:
            params.append(role_id)
            self._cursor.execute(
                f"UPDATE roles SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                params
            )

        if permissions is not None:
            self._cursor.execute("DELETE FROM role_permissions WHERE role_id = ?", (role_id,))
            self._add_permissions_to_role(role_id, permissions)

        self._conn.commit()

    def delete_role(self, role_id: int) -> None:
        """Delete a role."""
        self._cursor.execute("DELETE FROM roles WHERE id = ?", (role_id,))
        self._conn.commit()

    def get_user_roles(self, user_id: str) -> List[Dict]:
        """Get roles assigned to a user."""
        self._cursor.execute("""
            SELECT r.*, ur.granted_by, ur.granted_at,
                   GROUP_CONCAT(p.name) as permissions
            FROM roles r
            JOIN user_roles ur ON r.id = ur.role_id
            LEFT JOIN role_permissions rp ON r.id = rp.role_id
            LEFT JOIN permissions p ON rp.permission_id = p.id
            WHERE ur.user_id = ?
            GROUP BY r.id
        """, (user_id,))
        return [dict(row) for row in self._cursor.fetchall()]

    def assign_role(self, user_id: str, role_name: str, granted_by: str) -> None:
        """Assign a role to a user."""
        try:
            self._cursor.execute("SELECT id FROM roles WHERE name = ?", (role_name,))
            role = self._cursor.fetchone()
            if not role:
                raise PermissionDenied(f"Role not found: {role_name}")

            self._cursor.execute("""
                INSERT OR REPLACE INTO user_roles (user_id, role_id, granted_by)
                VALUES (?, ?, ?)
            """, (user_id, role["id"], granted_by))
            self._conn.commit()

            self.log_audit(
                user_id=granted_by,
                action="assign_role",
                target_type="user",
                target_id=user_id,
                details={"role": role_name}
            )
        except sqlite3.Error as err:
            raise PermissionDenied(f"Failed to assign role: {err}")

    def remove_role(self, user_id: str, role_name: str, removed_by: str) -> None:
        """Remove a role from a user."""
        try:
            self._cursor.execute("SELECT id FROM roles WHERE name = ?", (role_name,))
            role = self._cursor.fetchone()
            if not role:
                raise PermissionDenied(f"Role not found: {role_name}")

            self._cursor.execute("""
                DELETE FROM user_roles
                WHERE user_id = ? AND role_id = ?
            """, (user_id, role["id"]))
            self._conn.commit()

            self.log_audit(
                user_id=removed_by,
                action="remove_role",
                target_type="user",
                target_id=user_id,
                details={"role": role_name}
            )
        except sqlite3.Error as err:
            raise PermissionDenied(f"Failed to remove role: {err}")

    def get_user_permissions(self, user_id: str) -> List[Dict]:
        """Get permissions for a user."""
        self._cursor.execute("""
            SELECT DISTINCT p.name, p.description,
                   up.granted_by, up.granted_at, up.expires_at, up.reason,
                   r.name as granted_by_role
            FROM permissions p
            LEFT JOIN user_permissions up ON p.id = up.permission_id AND up.user_id = ?
            LEFT JOIN user_roles ur ON ur.user_id = ?
            LEFT JOIN role_permissions rp ON rp.permission_id = p.id AND rp.role_id = ur.role_id
            LEFT JOIN roles r ON r.id = ur.role_id
            WHERE up.user_id IS NOT NULL OR ur.user_id IS NOT NULL
        """, (user_id, user_id))
        return [dict(row) for row in self._cursor.fetchall()]

    def grant_permission(self, user_id: str, permission_name: str, granted_by: str,
                        expires_at: Optional[datetime] = None, reason: Optional[str] = None) -> None:
        """Grant a permission to a user."""
        try:
            self._cursor.execute("SELECT id FROM permissions WHERE name = ?", (permission_name,))
            permission = self._cursor.fetchone()
            if not permission:
                raise PermissionDenied(f"Permission not found: {permission_name}")

            self._cursor.execute("""
                INSERT OR REPLACE INTO user_permissions
                (user_id, permission_id, granted_by, expires_at, reason)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, permission["id"], granted_by, expires_at, reason))
            self._conn.commit()

            self.log_audit(
                user_id=granted_by,
                action="grant_permission",
                target_type="user",
                target_id=user_id,
                details={
                    "permission": permission_name,
                    "expires_at": expires_at.isoformat() if expires_at else None,
                    "reason": reason
                }
            )
        except sqlite3.Error as err:
            raise PermissionDenied(f"Failed to grant permission: {err}")

    def revoke_permission(self, user_id: str, permission_name: str, revoked_by: str,
                         reason: Optional[str] = None) -> None:
        """Revoke a permission from a user."""
        try:
            self._cursor.execute("SELECT id FROM permissions WHERE name = ?", (permission_name,))
            permission = self._cursor.fetchone()
            if not permission:
                raise PermissionDenied(f"Permission not found: {permission_name}")

            self._cursor.execute("""
                DELETE FROM user_permissions
                WHERE user_id = ? AND permission_id = ?
            """, (user_id, permission["id"]))
            self._conn.commit()

            self.log_audit(
                user_id=revoked_by,
                action="revoke_permission",
                target_type="user",
                target_id=user_id,
                details={
                    "permission": permission_name,
                    "reason": reason
                }
            )
        except sqlite3.Error as err:
            raise PermissionDenied(f"Failed to revoke permission: {err}")

    def check_permission(self, user_id: str, permission_name: str) -> bool:
        """Check if a user has a specific permission."""
        self._cursor.execute("""
            SELECT 1
            FROM permissions p
            LEFT JOIN user_permissions up ON p.id = up.permission_id AND up.user_id = ?
            LEFT JOIN user_roles ur ON ur.user_id = ?
            LEFT JOIN role_permissions rp ON rp.permission_id = p.id AND rp.role_id = ur.role_id
            WHERE p.name = ?
                AND (up.user_id IS NOT NULL OR ur.user_id IS NOT NULL)
                AND (up.expires_at IS NULL OR up.expires_at > CURRENT_TIMESTAMP)
            LIMIT 1
        """, (user_id, user_id, permission_name))
        return bool(self._cursor.fetchone())

    def log_audit(self, user_id: str, action: str, target_type: str,
                 target_id: str, details: Optional[Dict] = None) -> None:
        """Log an audit entry."""
        try:
            self._cursor.execute("""
                INSERT INTO audit_log
                (user_id, action, target_type, target_id, details)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, action, target_type, target_id,
                 json.dumps(details) if details else None))
            self._conn.commit()
        except sqlite3.Error as err:
            _LOGGER.error("Failed to log audit entry: %s", err)

    def get_audit_log(self, user_id: Optional[str] = None,
                     action: Optional[str] = None,
                     target_type: Optional[str] = None,
                     target_id: Optional[str] = None,
                     limit: int = 100) -> List[Dict]:
        """Get audit log entries."""
        query = ["SELECT * FROM audit_log"]
        params = []
        conditions = []

        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)
        if action:
            conditions.append("action = ?")
            params.append(action)
        if target_type:
            conditions.append("target_type = ?")
            params.append(target_type)
        if target_id:
            conditions.append("target_id = ?")
            params.append(target_id)

        if conditions:
            query.append("WHERE " + " AND ".join(conditions))

        query.append("ORDER BY timestamp DESC LIMIT ?")
        params.append(limit)

        self._cursor.execute(" ".join(query), params)
        return [dict(row) for row in self._cursor.fetchall()]

    def _add_permissions_to_role(self, role_id: int, permission_names: List[str]) -> None:
        """Add permissions to a role."""
        placeholders = ",".join("?" * len(permission_names))
        self._cursor.execute(
            f"SELECT id, name FROM permissions WHERE name IN ({placeholders})",
            permission_names
        )
        permissions = self._cursor.fetchall()

        if len(permissions) != len(permission_names):
            found = {p["name"] for p in permissions}
            missing = set(permission_names) - found
            raise PermissionDenied(f"Permissions not found: {missing}")

        self._cursor.executemany(
            "INSERT INTO role_permissions (role_id, permission_id) VALUES (?, ?)",
            [(role_id, p["id"]) for p in permissions]
        ) 