"""旧脚本兼容入口，新代码请从 backend.core.config 导入配置。"""

from backend.core.config import Settings, get_settings

Config = Settings

__all__ = ["Config", "Settings", "get_settings"]
