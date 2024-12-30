"""Constants for the Timewise Guardian integration."""

DOMAIN = "twg"
NAME = "Timewise Guardian"
VERSION = "1.0.0"

# Config flow
CONF_HOST = "host"
CONF_PORT = "port"
CONF_API_KEY = "api_key"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_USERS = "users"
CONF_BLOCKLIST_CATEGORIES = "blocklist_categories"
CONF_WHITELIST = "whitelist"
CONF_BLACKLIST = "blacklist"

# Defaults
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8123
DEFAULT_SCAN_INTERVAL = 30

# Services
SERVICE_UPDATE = "update"
SERVICE_REFRESH = "refresh"
SERVICE_SET_LIMIT = "set_limit"
SERVICE_ADD_CATEGORY = "add_category"
SERVICE_REMOVE_CATEGORY = "remove_category"

# Event types
EVENT_USER_ACTIVITY = "twg_user_activity"
EVENT_USER_DETECTED = "twg_user_detected"
EVENT_CATEGORIES_UPDATED = "twg_categories_updated"
EVENT_TIME_LIMIT_WARNING = "twg_time_limit_warning"
EVENT_TIME_LIMIT_REACHED = "twg_time_limit_reached"
EVENT_RESTRICTION_ACTIVE = "twg_restriction_active"

# Entity categories
ENTITY_CATEGORY_USER = "user"
ENTITY_CATEGORY_COMPUTER = "computer"
ENTITY_CATEGORY_SESSION = "session"

# State attributes
ATTR_USER = "user"
ATTR_COMPUTER = "computer"
ATTR_CATEGORY = "category"
ATTR_TIME_USED = "time_used"
ATTR_TIME_LIMIT = "time_limit"
ATTR_ACTIVE_WINDOW = "active_window"
ATTR_PROCESS = "process"
ATTR_START_TIME = "start_time"
ATTR_END_TIME = "end_time"
ATTR_DURATION = "duration"
ATTR_STATUS = "status"

# Error messages
ERROR_AUTH = "Invalid authentication"
ERROR_CANNOT_CONNECT = "Cannot connect to service"
ERROR_INVALID_HOST = "Invalid host"
ERROR_UNKNOWN = "Unknown error occurred" 