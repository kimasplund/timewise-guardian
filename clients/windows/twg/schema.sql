-- User mapping table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    windows_username TEXT NOT NULL,
    ha_username TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(windows_username),
    role_id INTEGER REFERENCES roles(id)
);

-- Categories table
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    time_limit INTEGER,  -- in minutes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name)
);

-- Process patterns table
CREATE TABLE IF NOT EXISTS process_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    pattern TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);

-- Window title patterns table
CREATE TABLE IF NOT EXISTS window_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    pattern TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);

-- Browser patterns table
CREATE TABLE IF NOT EXISTS browser_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    type TEXT NOT NULL,  -- 'url', 'title', 'youtube_channel'
    pattern TEXT NOT NULL,
    is_exclude BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);

-- Time restrictions table
CREATE TABLE IF NOT EXISTS time_restrictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    day_type TEXT NOT NULL,  -- 'weekday' or 'weekend'
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);

-- Settings table
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(key)
);

-- User settings table
CREATE TABLE IF NOT EXISTS user_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, key)
);

-- Roles table
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name)
);

-- Permissions table
CREATE TABLE IF NOT EXISTS permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name)
);

-- Role permissions table
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
);

-- Insert default settings
INSERT OR IGNORE INTO settings (key, value) VALUES
    ('ha_url', 'http://homeassistant.local:8123'),
    ('warning_threshold', '10'),
    ('warning_intervals', '30,15,10,5,1'),
    ('popup_duration', '10'),
    ('sound_enabled', 'true');

-- Insert default roles
INSERT OR IGNORE INTO roles (name, description) VALUES
    ('admin', 'Full system access'),
    ('parent', 'Can manage child accounts and view statistics'),
    ('child', 'Limited access to own settings'),
    ('guest', 'View-only access');

-- Insert default permissions
INSERT OR IGNORE INTO permissions (name, description) VALUES
    ('manage_users', 'Create, update, and delete users'),
    ('manage_roles', 'Manage roles and permissions'),
    ('manage_categories', 'Create and modify activity categories'),
    ('manage_time_limits', 'Set and modify time limits'),
    ('manage_restrictions', 'Set and modify time restrictions'),
    ('view_statistics', 'View usage statistics'),
    ('modify_own_settings', 'Modify own user settings'),
    ('export_data', 'Export configuration and statistics'),
    ('manage_notifications', 'Configure notification settings'),
    ('bypass_restrictions', 'Bypass time restrictions');

-- Assign permissions to roles
INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE 
    (r.name = 'admin') OR
    (r.name = 'parent' AND p.name IN (
        'manage_users',
        'manage_categories',
        'manage_time_limits',
        'manage_restrictions',
        'view_statistics',
        'modify_own_settings',
        'export_data',
        'manage_notifications'
    )) OR
    (r.name = 'child' AND p.name IN (
        'view_statistics',
        'modify_own_settings'
    )) OR
    (r.name = 'guest' AND p.name IN (
        'view_statistics'
    ));

-- Create trigger for updated_at
CREATE TRIGGER IF NOT EXISTS update_timestamp_users
AFTER UPDATE ON users
BEGIN
    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_timestamp_categories
AFTER UPDATE ON categories
BEGIN
    UPDATE categories SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_timestamp_settings
AFTER UPDATE ON settings
BEGIN
    UPDATE settings SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_timestamp_user_settings
AFTER UPDATE ON user_settings
BEGIN
    UPDATE user_settings SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Create trigger for roles updated_at
CREATE TRIGGER IF NOT EXISTS update_timestamp_roles
AFTER UPDATE ON roles
BEGIN
    UPDATE roles SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Add parent_id to users table for parent-child relationships
ALTER TABLE users ADD COLUMN parent_id INTEGER REFERENCES users(id);

-- Add override_permissions table for temporary permission grants
CREATE TABLE IF NOT EXISTS override_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    granted_by INTEGER NOT NULL,
    expires_at TIMESTAMP,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES users(id) ON DELETE CASCADE
);

-- Add user groups table
CREATE TABLE IF NOT EXISTS user_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(name)
);

-- Add user group members table
CREATE TABLE IF NOT EXISTS user_group_members (
    group_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (group_id, user_id),
    FOREIGN KEY (group_id) REFERENCES user_groups(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Add group permissions table
CREATE TABLE IF NOT EXISTS group_permissions (
    group_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (group_id, permission_id),
    FOREIGN KEY (group_id) REFERENCES user_groups(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
);

-- Create trigger for user_groups updated_at
CREATE TRIGGER IF NOT EXISTS update_timestamp_user_groups
AFTER UPDATE ON user_groups
BEGIN
    UPDATE user_groups SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Add audit log table for permission changes
CREATE TABLE IF NOT EXISTS permission_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    action_type TEXT NOT NULL,  -- 'grant', 'revoke', 'role_update', 'group_update'
    target_type TEXT NOT NULL,  -- 'user', 'role', 'group'
    target_id INTEGER NOT NULL,
    permission_name TEXT NOT NULL,
    performed_by INTEGER NOT NULL,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (performed_by) REFERENCES users(id) ON DELETE CASCADE
);

-- Add audit log table for role changes
CREATE TABLE IF NOT EXISTS role_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id INTEGER NOT NULL,
    action_type TEXT NOT NULL,  -- 'create', 'update', 'delete'
    performed_by INTEGER NOT NULL,
    details TEXT,  -- JSON string with changed fields
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (performed_by) REFERENCES users(id) ON DELETE CASCADE
);

-- Add audit log table for group changes
CREATE TABLE IF NOT EXISTS group_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    action_type TEXT NOT NULL,  -- 'create', 'update', 'delete', 'add_user', 'remove_user'
    performed_by INTEGER NOT NULL,
    details TEXT,  -- JSON string with changed fields or affected user
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES user_groups(id) ON DELETE CASCADE,
    FOREIGN KEY (performed_by) REFERENCES users(id) ON DELETE CASCADE
); 