from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseNotifier(ABC):
    """
    Abstract Base Class for Alert Notification Channels.
    """

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def send_notification(self, alert: Dict[str, Any], matched_keywords: List[str], snippet: str) -> bool:
        """
        Sends notification to the target channel.

        Args:
            alert: Dict containing title, content, url, timestamp, etc.
            matched_keywords: List of keywords that triggered the alert.
            snippet: Highlighted text snippet.

        Returns:
            bool: True if send was successful, False otherwise.
        """
        pass
