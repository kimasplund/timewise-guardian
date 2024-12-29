"""WebSocket API for Timewise Guardian."""
from typing import Any, Callable, Dict, List
from datetime import datetime

import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.components.websocket_api import (
    async_register_command,
    websocket_command,
    require_admin,
    ActiveConnection,
    ERR_NOT_FOUND,
    ERR_INVALID_FORMAT,
)
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, ERROR_AUTH, ERROR_CANNOT_CONNECT, ERROR_INVALID_HOST
from .database import Database, PermissionDenied

class DatabaseError(HomeAssistantError):
    """Database operation error."""

async def async_setup_websocket_api(hass: HomeAssistant) -> None:
    """Set up WebSocket API."""
    
    @websocket_command({
        vol.Required('type'): 'twg/register_computer',
        vol.Required('computer_info'): {
            vol.Required('id'): str,
            vol.Required('name'): str,
            vol.Required('os'): str,
            vol.Optional('version'): str,
        },
    })
    async def websocket_register_computer(
        hass: HomeAssistant,
        connection: ActiveConnection,
        msg: Dict[str, Any]
    ) -> None:
        """Register a computer with Timewise Guardian."""
        try:
            entry_id = connection.context.get("entry_id")
            if not entry_id or entry_id not in hass.data[DOMAIN]:
                raise ValueError("Invalid entry_id")

            register_computer = hass.data[DOMAIN][entry_id]["register_computer"]
            await register_computer(msg["computer_info"])
            
            connection.send_result(msg["id"], {
                "success": True,
                "computer_id": msg["computer_info"]["id"]
            })
        except Exception as err:
            connection.send_error(msg["id"], "registration_failed", str(err))

    @websocket_command({
        vol.Required('type'): 'twg/get_roles',
    })
    @require_admin
    async def websocket_get_roles(
        hass: HomeAssistant,
        connection: ActiveConnection,
        msg: Dict[str, Any]
    ) -> None:
        """Get all roles."""
        try:
            db = Database()
            roles = db.get_roles()
            connection.send_result(msg['id'], {'roles': roles})
        except Exception as err:
            connection.send_error(msg['id'], 'database_error', str(err))

    @websocket_command({
        vol.Required('type'): 'twg/create_role',
        vol.Required('name'): str,
        vol.Required('description'): str,
        vol.Optional('permissions'): [str],
    })
    @require_admin
    async def websocket_create_role(
        hass: HomeAssistant,
        connection: ActiveConnection,
        msg: Dict[str, Any]
    ) -> None:
        """Create a new role."""
        try:
            db = Database()
            role_id = db.create_role(
                name=msg['name'],
                description=msg['description'],
                permissions=msg.get('permissions', [])
            )
            connection.send_result(msg['id'], {'success': True, 'role_id': role_id})
        except PermissionDenied as err:
            connection.send_error(msg['id'], 'permission_denied', str(err))
        except Exception as err:
            connection.send_error(msg['id'], 'create_failed', str(err))

    @websocket_command({
        vol.Required('type'): 'twg/update_role',
        vol.Required('role_id'): int,
        vol.Optional('name'): str,
        vol.Optional('description'): str,
        vol.Optional('permissions'): [str],
    })
    @require_admin
    async def websocket_update_role(
        hass: HomeAssistant,
        connection: ActiveConnection,
        msg: Dict[str, Any]
    ) -> None:
        """Update a role."""
        try:
            db = Database()
            db.update_role(
                role_id=msg['role_id'],
                name=msg.get('name'),
                description=msg.get('description'),
                permissions=msg.get('permissions')
            )
            connection.send_result(msg['id'], {'success': True})
        except PermissionDenied as err:
            connection.send_error(msg['id'], 'permission_denied', str(err))
        except Exception as err:
            connection.send_error(msg['id'], 'update_failed', str(err))

    @websocket_command({
        vol.Required('type'): 'twg/delete_role',
        vol.Required('role_id'): int,
    })
    @require_admin
    async def websocket_delete_role(
        hass: HomeAssistant,
        connection: ActiveConnection,
        msg: Dict[str, Any]
    ) -> None:
        """Delete a role."""
        try:
            db = Database()
            db.delete_role(msg['role_id'])
            connection.send_result(msg['id'], {'success': True})
        except PermissionDenied as err:
            connection.send_error(msg['id'], 'permission_denied', str(err))
        except Exception as err:
            connection.send_error(msg['id'], 'delete_failed', str(err))

    @websocket_command({
        vol.Required('type'): 'twg/get_user_permissions',
        vol.Required('user_id'): int,
    })
    async def websocket_get_user_permissions(
        hass: HomeAssistant,
        connection: ActiveConnection,
        msg: Dict[str, Any]
    ) -> None:
        """Get permissions for a user."""
        try:
            db = Database()
            permissions = db.get_user_permissions(msg['user_id'])
            connection.send_result(msg['id'], {'permissions': permissions})
        except Exception as err:
            connection.send_error(msg['id'], 'fetch_failed', str(err))

    @websocket_command({
        vol.Required('type'): 'twg/grant_permission',
        vol.Required('user_id'): int,
        vol.Required('permission'): str,
        vol.Optional('expires_at'): str,
        vol.Optional('reason'): str,
    })
    @require_admin
    async def websocket_grant_permission(
        hass: HomeAssistant,
        connection: ActiveConnection,
        msg: Dict[str, Any]
    ) -> None:
        """Grant a permission to a user."""
        try:
            db = Database()
            expires_at = None
            if msg.get('expires_at'):
                try:
                    expires_at = datetime.fromisoformat(msg['expires_at'])
                except ValueError as err:
                    connection.send_error(msg['id'], ERR_INVALID_FORMAT, f"Invalid date format: {err}")
                    return
            
            db.grant_permission(
                user_id=msg['user_id'],
                permission_name=msg['permission'],
                granted_by=connection.user.id,
                expires_at=expires_at,
                reason=msg.get('reason')
            )
            connection.send_result(msg['id'], {'success': True})
        except PermissionDenied as err:
            connection.send_error(msg['id'], 'permission_denied', str(err))
        except Exception as err:
            connection.send_error(msg['id'], 'grant_failed', str(err))

    # Register all commands
    for cmd in [
        websocket_register_computer,
        websocket_get_roles,
        websocket_create_role,
        websocket_update_role,
        websocket_delete_role,
        websocket_get_user_permissions,
        websocket_grant_permission,
    ]:
        async_register_command(hass, cmd) 