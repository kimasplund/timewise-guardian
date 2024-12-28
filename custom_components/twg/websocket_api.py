"""WebSocket API for Timewise Guardian."""
from typing import Any, Callable, Dict, List
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.components import websocket_api
from homeassistant.components.websocket_api import async_register_command
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.const import ERR_NOT_FOUND
from datetime import datetime
from .const import DOMAIN
from .database import Database, PermissionDenied

async def async_setup_websocket_api(hass: HomeAssistant) -> None:
    """Set up WebSocket API."""
    
    @websocket_api.require_admin
    @websocket_api.websocket_command({
        vol.Required('type'): 'twg/get_roles',
    })
    async def websocket_get_roles(
        hass: HomeAssistant,
        connection: ActiveConnection,
        msg: Dict[str, Any]
    ) -> None:
        """Get all roles."""
        db = Database()
        roles = db.get_roles()
        connection.send_result(msg['id'], {'roles': roles})

    @websocket_api.require_admin
    @websocket_api.websocket_command({
        vol.Required('type'): 'twg/create_role',
        vol.Required('name'): str,
        vol.Required('description'): str,
        vol.Optional('permissions'): [str],
    })
    async def websocket_create_role(
        hass: HomeAssistant,
        connection: ActiveConnection,
        msg: Dict[str, Any]
    ) -> None:
        """Create a new role."""
        db = Database()
        try:
            role_id = db.create_role(
                name=msg['name'],
                description=msg['description'],
                permissions=msg.get('permissions', [])
            )
            connection.send_result(msg['id'], {'success': True, 'role_id': role_id})
        except Exception as err:
            connection.send_error(msg['id'], 'create_failed', str(err))

    @websocket_api.require_admin
    @websocket_api.websocket_command({
        vol.Required('type'): 'twg/update_role',
        vol.Required('role_id'): int,
        vol.Optional('name'): str,
        vol.Optional('description'): str,
        vol.Optional('permissions'): [str],
    })
    async def websocket_update_role(
        hass: HomeAssistant,
        connection: ActiveConnection,
        msg: Dict[str, Any]
    ) -> None:
        """Update a role."""
        db = Database()
        try:
            db.update_role(
                role_id=msg['role_id'],
                name=msg.get('name'),
                description=msg.get('description'),
                permissions=msg.get('permissions')
            )
            connection.send_result(msg['id'], {'success': True})
        except Exception as err:
            connection.send_error(msg['id'], 'update_failed', str(err))

    @websocket_api.require_admin
    @websocket_api.websocket_command({
        vol.Required('type'): 'twg/delete_role',
        vol.Required('role_id'): int,
    })
    async def websocket_delete_role(
        hass: HomeAssistant,
        connection: ActiveConnection,
        msg: Dict[str, Any]
    ) -> None:
        """Delete a role."""
        db = Database()
        try:
            db.delete_role(msg['role_id'])
            connection.send_result(msg['id'], {'success': True})
        except Exception as err:
            connection.send_error(msg['id'], 'delete_failed', str(err))

    @websocket_api.websocket_command({
        vol.Required('type'): 'twg/get_user_permissions',
        vol.Required('user_id'): int,
    })
    async def websocket_get_user_permissions(
        hass: HomeAssistant,
        connection: ActiveConnection,
        msg: Dict[str, Any]
    ) -> None:
        """Get permissions for a user."""
        db = Database()
        try:
            permissions = db.get_user_permissions(msg['user_id'])
            connection.send_result(msg['id'], {'permissions': permissions})
        except Exception as err:
            connection.send_error(msg['id'], 'fetch_failed', str(err))

    @websocket_api.require_admin
    @websocket_api.websocket_command({
        vol.Required('type'): 'twg/grant_permission',
        vol.Required('user_id'): int,
        vol.Required('permission'): str,
        vol.Optional('expires_at'): str,
        vol.Optional('reason'): str,
    })
    async def websocket_grant_permission(
        hass: HomeAssistant,
        connection: ActiveConnection,
        msg: Dict[str, Any]
    ) -> None:
        """Grant a permission to a user."""
        db = Database()
        try:
            expires_at = None
            if msg.get('expires_at'):
                expires_at = datetime.fromisoformat(msg['expires_at'])
            
            db.grant_permission(
                user_id=msg['user_id'],
                permission_name=msg['permission'],
                granted_by=connection.user.id,
                expires_at=expires_at,
                reason=msg.get('reason')
            )
            connection.send_result(msg['id'], {'success': True})
        except Exception as err:
            connection.send_error(msg['id'], 'grant_failed', str(err))

    @websocket_api.require_admin
    @websocket_api.websocket_command({
        vol.Required('type'): 'twg/revoke_permission',
        vol.Required('user_id'): int,
        vol.Required('permission'): str,
    })
    async def websocket_revoke_permission(
        hass: HomeAssistant,
        connection: ActiveConnection,
        msg: Dict[str, Any]
    ) -> None:
        """Revoke a permission from a user."""
        db = Database()
        try:
            db.revoke_permission(
                user_id=msg['user_id'],
                permission_name=msg['permission']
            )
            connection.send_result(msg['id'], {'success': True})
        except Exception as err:
            connection.send_error(msg['id'], 'revoke_failed', str(err))

    @websocket_api.require_admin
    @websocket_api.websocket_command({
        vol.Required('type'): 'twg/create_group',
        vol.Required('name'): str,
        vol.Required('description'): str,
        vol.Optional('permissions'): [str],
    })
    async def websocket_create_group(
        hass: HomeAssistant,
        connection: ActiveConnection,
        msg: Dict[str, Any]
    ) -> None:
        """Create a new group."""
        db = Database()
        try:
            group_id = db.create_user_group(
                name=msg['name'],
                description=msg['description'],
                created_by=connection.user.id,
                permissions=msg.get('permissions', [])
            )
            connection.send_result(msg['id'], {'success': True, 'group_id': group_id})
        except Exception as err:
            connection.send_error(msg['id'], 'create_failed', str(err))

    @websocket_api.websocket_command({
        vol.Required('type'): 'twg/get_user_groups',
        vol.Required('user_id'): int,
    })
    async def websocket_get_user_groups(
        hass: HomeAssistant,
        connection: ActiveConnection,
        msg: Dict[str, Any]
    ) -> None:
        """Get groups for a user."""
        db = Database()
        try:
            groups = db.get_user_groups(msg['user_id'])
            connection.send_result(msg['id'], {'groups': groups})
        except Exception as err:
            connection.send_error(msg['id'], 'fetch_failed', str(err))

    @websocket_api.require_admin
    @websocket_api.websocket_command({
        vol.Required('type'): 'twg/add_user_to_group',
        vol.Required('user_id'): int,
        vol.Required('group_id'): int,
    })
    async def websocket_add_user_to_group(
        hass: HomeAssistant,
        connection: ActiveConnection,
        msg: Dict[str, Any]
    ) -> None:
        """Add a user to a group."""
        db = Database()
        try:
            db.add_user_to_group(
                user_id=msg['user_id'],
                group_id=msg['group_id']
            )
            connection.send_result(msg['id'], {'success': True})
        except Exception as err:
            connection.send_error(msg['id'], 'add_failed', str(err))

    @websocket_api.require_admin
    @websocket_api.websocket_command({
        vol.Required('type'): 'twg/remove_user_from_group',
        vol.Required('user_id'): int,
        vol.Required('group_id'): int,
    })
    async def websocket_remove_user_from_group(
        hass: HomeAssistant,
        connection: ActiveConnection,
        msg: Dict[str, Any]
    ) -> None:
        """Remove a user from a group."""
        db = Database()
        try:
            db.remove_user_from_group(
                user_id=msg['user_id'],
                group_id=msg['group_id']
            )
            connection.send_result(msg['id'], {'success': True})
        except Exception as err:
            connection.send_error(msg['id'], 'remove_failed', str(err))

    @websocket_api.websocket_command({
        vol.Required('type'): 'twg/get_permission_audit_logs',
        vol.Optional('user_id'): int,
        vol.Optional('target_type'): str,
        vol.Optional('target_id'): int,
        vol.Optional('limit'): int,
    })
    async def websocket_get_permission_audit_logs(
        hass: HomeAssistant,
        connection: ActiveConnection,
        msg: Dict[str, Any]
    ) -> None:
        """Get permission audit logs."""
        db = Database()
        try:
            logs = db.get_permission_audit_logs(
                user_id=msg.get('user_id'),
                target_type=msg.get('target_type'),
                target_id=msg.get('target_id'),
                limit=msg.get('limit', 100)
            )
            connection.send_result(msg['id'], {'logs': logs})
        except Exception as err:
            connection.send_error(msg['id'], 'fetch_failed', str(err))

    @websocket_api.websocket_command({
        vol.Required('type'): 'twg/get_role_audit_logs',
        vol.Optional('role_id'): int,
        vol.Optional('limit'): int,
    })
    async def websocket_get_role_audit_logs(
        hass: HomeAssistant,
        connection: ActiveConnection,
        msg: Dict[str, Any]
    ) -> None:
        """Get role audit logs."""
        db = Database()
        try:
            logs = db.get_role_audit_logs(
                role_id=msg.get('role_id'),
                limit=msg.get('limit', 100)
            )
            connection.send_result(msg['id'], {'logs': logs})
        except Exception as err:
            connection.send_error(msg['id'], 'fetch_failed', str(err))

    @websocket_api.websocket_command({
        vol.Required('type'): 'twg/get_group_audit_logs',
        vol.Optional('group_id'): int,
        vol.Optional('limit'): int,
    })
    async def websocket_get_group_audit_logs(
        hass: HomeAssistant,
        connection: ActiveConnection,
        msg: Dict[str, Any]
    ) -> None:
        """Get group audit logs."""
        db = Database()
        try:
            logs = db.get_group_audit_logs(
                group_id=msg.get('group_id'),
                limit=msg.get('limit', 100)
            )
            connection.send_result(msg['id'], {'logs': logs})
        except Exception as err:
            connection.send_error(msg['id'], 'fetch_failed', str(err))

    # Register all commands
    async_register_command(hass, websocket_get_roles)
    async_register_command(hass, websocket_create_role)
    async_register_command(hass, websocket_update_role)
    async_register_command(hass, websocket_delete_role)
    async_register_command(hass, websocket_get_user_permissions)
    async_register_command(hass, websocket_grant_permission)
    async_register_command(hass, websocket_revoke_permission)
    async_register_command(hass, websocket_create_group)
    async_register_command(hass, websocket_get_user_groups)
    async_register_command(hass, websocket_add_user_to_group)
    async_register_command(hass, websocket_remove_user_from_group)
    async_register_command(hass, websocket_get_permission_audit_logs)
    async_register_command(hass, websocket_get_role_audit_logs)
    async_register_command(hass, websocket_get_group_audit_logs) 