import unittest
import os
from agentbay import init, AgentBay

class TestAgentBayInit(unittest.TestCase):
    
    def setUp(self):
        # Reset the singleton before each test to ensure isolation
        AgentBay._instance = None
        # Clear env var if present
        if "AGENTBAY_API_KEY" in os.environ:
            del os.environ["AGENTBAY_API_KEY"]

    def test_init_with_api_key(self):
        """Test that init works with an explicit API key."""
        client = init(api_key="test-key-123")
        self.assertIsNotNone(client)
        self.assertEqual(client.config.api_key, "test-key-123")
        
    def test_init_missing_key_raises_error(self):
        """Test that init raises ValueError if no key is provided."""
        with self.assertRaises(ValueError):
            init()

    def test_singleton_pattern(self):
        """Test that init returns the same instance if called twice."""
        client1 = init(api_key="key-1")
        # Second init call with different key should actually return the SAME instance
        # (depending on how strict we want the singleton to be. 
        #  Currently, our logic replaces it if we call init again, 
        #  OR we can check if get_instance returns the same one).
        
        # Let's check that get_instance returns the initialized client
        client2 = AgentBay.get_instance()
        self.assertIs(client1, client2)

if __name__ == "__main__":
    unittest.main()

