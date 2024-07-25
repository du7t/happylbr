"""
This file is for default config only.
To put overrides - please use settings.py
"""

ADS = {}
ADS_FULL_CACHING = False

BALANCERS = {}

DNA = {
    'DNAURL': 'https://dns-api.mydomain',
}

RT = {}

NETBOX_API = ''

DNS = []
INVENTORY_MODE = 'RT'          # RT or NETBOX
DEFAULT_LOCATION = ''
SHARED_ENVS = []
CACHE_TTL = 0                  # 0 - disable cache

GIT_UPDATE = True              # Check script latest version in Git
LOG_LEVEL = 'INFO'             # Log level to console: DEBUG / INFO / WARN / ERROR / CRITICAL
LOG_FILE = True                # Enable logs to file
ENABLE_RETURN_LOG = True       # Enable logging of functions return
RETURN_LOG_MAX_LENGTH = 200    # Max length of return log before wrapping. 0 - unlimited
FRIENDLY_PRINT = False         # Enable friendly minimal prining. Usually combined with LOG_LEVEL = 'ERROR'
PROGRESS_BAR = False           # Enable progress bar
RETRY_COUNT = 2
CLEAR_CACHE_ON_START = True
CHECK_ENTRYPOINT_GROUP = False

SEND_STATS_TO_REDIS = True
REDIS_HOST = ""
REDIS_PORT = 6379
REDIS_TTL = 3600 * 24 * 7 * 4
