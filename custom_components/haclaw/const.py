"""Constants for HAclaw."""

from __future__ import annotations

DOMAIN = "haclaw"

CONF_PROVIDER_PRESET = "provider_preset"
CONF_API_KEY = "api_key"
CONF_BASE_URL = "base_url"
CONF_MODEL = "model"
CONF_TIMEOUT = "timeout"
CONF_TEMPERATURE = "temperature"
CONF_TOP_P = "top_p"
CONF_ENABLE_XIAOMI_ADVANCED_TOOLS = "enable_xiaomi_advanced_tools"
CONF_ENABLE_PROMPT_LOGGING = "enable_prompt_logging"

DEFAULT_TIMEOUT = 300
DEFAULT_TEMPERATURE = 0.2
DEFAULT_TOP_P = 0.9

PROVIDER_PRESETS = {
    "xiaomi_mimo": {
        "name": "Xiaomi MiMo",
        "base_url": "https://api.mimo-v2.com/v1",
        "model": "mimo-v2-flash",
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
    },
    "qwen": {
        "name": "Qwen / DashScope",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
    },
    "kimi": {
        "name": "Kimi / Moonshot",
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k",
    },
    "glm": {
        "name": "GLM / Zhipu",
        "base_url": "",
        "model": "glm-4",
    },
    "siliconflow": {
        "name": "SiliconFlow",
        "base_url": "https://api.siliconflow.cn/v1",
        "model": "",
    },
    "oneapi": {
        "name": "OneAPI / New API",
        "base_url": "",
        "model": "",
    },
    "custom": {
        "name": "Custom OpenAI-compatible",
        "base_url": "",
        "model": "",
    },
}

# New storage files (range B)
CONVERSATIONS_FILE = "conversations.json"
PRESENCE_FILE = "presence.json"
UI_STATE_FILE = "ui_state.json"

# New service names (range B)
SERVICE_GET_ENVIRONMENT_READINESS = "get_environment_readiness"
SERVICE_LIST_PRESENCE_CANDIDATES = "list_presence_candidates"
SERVICE_GET_PRESENCE_BINDING = "get_presence_binding"
SERVICE_BIND_PRESENCE_ENTITY = "bind_presence_entity"
SERVICE_SWITCH_MODEL = "switch_model"

# New WS commands
WS_TYPE_CHAT = "haclaw/chat"
WS_TYPE_CONVERSATIONS_LIST = "haclaw/conversations/list"
WS_TYPE_CONVERSATIONS_CLEAR = "haclaw/conversations/clear"

# Chat session limits
MAX_USER_MESSAGE_CHARS = 4000
MAX_HISTORY_CHARS = 8000
DEFAULT_CHAT_MAX_TOKENS = 1024
MAX_CONVERSATIONS = 50
MAX_MESSAGES_PER_CONVERSATION = 200
MAX_CONVERSATIONS_FILE_BYTES = 5 * 1024 * 1024

# Modes
MODE_PLAN = "plan"
MODE_AUTOMATION = "automation"
MODE_EXECUTE = "execute"
ALL_MODES = (MODE_PLAN, MODE_AUTOMATION, MODE_EXECUTE)
DEFAULT_MODE = MODE_AUTOMATION
