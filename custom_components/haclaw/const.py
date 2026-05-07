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
