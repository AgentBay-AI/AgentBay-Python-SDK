from typing import Optional
from .config import Config
from .transport import Transport

class AgentBay:
    """
    The main AgentBay client.
    This is a singleton that manages configuration and data transmission.
    """
    _instance: Optional['AgentBay'] = None

    def __init__(self, config: Config):
        self.config = config
        self.transport = Transport(config) # Initialize the transport layer
        self.transport.start() # Start the transport thread as soon as the AgentBay client is initialized

    @classmethod
    def initialize(cls, api_key: Optional[str] = None, api_url: Optional[str] = None) -> 'AgentBay':
        """
        Initializes the global AgentBay client.
        """
        config = Config(api_key=api_key, api_url=api_url)
        config.validate()
        
        cls._instance = cls(config)
        return cls._instance

    @classmethod
    def get_instance(cls) -> 'AgentBay':
        """
        Returns the global AgentBay client instance.
        Raises an error if not initialized.
        """
        if cls._instance is None:
            raise RuntimeError(
                "AgentBay is not initialized. "
                "Please call `agentbay.init(api_key='...')` first."
            )
        return cls._instance

    def shutdown(self):
        """
        Stops the background transport thread and flushes remaining data.
        """
        if self.transport:
            self.transport.stop()
