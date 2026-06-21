from open_migration.connectors.auto import AutoConnector
from open_migration.connectors.chatgpt import ChatGPTConnector
from open_migration.connectors.claude import ClaudeConnector
from open_migration.connectors.gemini import GeminiConnector

CONNECTORS = {
    "auto": AutoConnector,
    "chatgpt": ChatGPTConnector,
    "claude": ClaudeConnector,
    "gemini": GeminiConnector,
}

__all__ = ["AutoConnector", "ChatGPTConnector", "ClaudeConnector", "GeminiConnector", "CONNECTORS"]
