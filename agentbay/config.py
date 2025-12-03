import os
from typing import Optional

class Config:
    """
    Configuration settings for the AgentBay SDK.
    Handles API keys and endpoint URLs.
    """
    def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None):
        # 1. Try to get the API Key from the arguments first.
        # 2. If not provided, try to get it from the environment variables.
        self.api_key = api_key or os.environ.get("AGENTBAY_API_KEY")
        
        # Set the API URL (defaulting to the hosted version if not changed)
        self.api_url = api_url or os.environ.get("AGENTBAY_API_URL", "https://api.agentbay.co")

    def validate(self):
        """
        Checks if the configuration is valid (i.e., has an API key).
        Raises a ValueError if the key is missing.
        """
        if not self.api_key:
            raise ValueError(
                "AgentBay API Key is missing. "
                "Please provide it via `agentbay.init(api_key='...')` "
                "or set the `AGENTBAY_API_KEY` environment variable."
            )
