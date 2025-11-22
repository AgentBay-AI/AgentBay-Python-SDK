import unittest
from unittest.mock import MagicMock, patch
import sys
import types

# --- MOCK SETUP START ---
# We must setup the mocks BEFORE importing the module under test
# This simulates 'openai' being installed on the system

# 1. Create the mock OpenAI module structure
mock_openai = types.ModuleType("openai")
mock_resources = types.ModuleType("openai.resources")
mock_chat = types.ModuleType("openai.resources.chat")
mock_completions_module = types.ModuleType("openai.resources.chat.completions")

# 2. Create the Completions Class and create method
class MockCompletions:
    def create(self, *args, **kwargs):
        pass

mock_completions_module.Completions = MockCompletions

# 3. Connect them
mock_openai.resources = mock_resources
mock_resources.chat = mock_chat
mock_chat.completions = mock_completions_module

# 4. Register them in sys.modules so 'from openai...' works
sys.modules["openai"] = mock_openai
sys.modules["openai.resources"] = mock_resources
sys.modules["openai.resources.chat"] = mock_chat
sys.modules["openai.resources.chat.completions"] = mock_completions_module
# --- MOCK SETUP END ---

from agentbay import init
from agentbay.llms.openai import instrument
from agentbay.llms.openai.chat import instrument_chat

class TestOpenAIChat(unittest.TestCase):
    
    def setUp(self):
        self.client = init(api_key="test-key")
        self.client.transport.send = MagicMock()
        
        # Reset the mock create method before each test
        self.mock_create = MagicMock()
        # We need to replace the method on the CLASS in sys.modules
        sys.modules["openai.resources.chat.completions"].Completions.create = self.mock_create
        
    def test_instrumentation_wraps_create(self):
        """Test that calling create() triggers our wrapper."""
        
        # 1. Run instrumentation
        instrument_chat(mock_openai)
        
        # 2. Setup a fake response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="AI Response"))]
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        
        # The *original* create (which is now wrapped) returns this
        self.mock_create.return_value = mock_response
        
        # 3. Call the method (simulating user code)
        # We need to instantiate the class first, because 'create' expects 'self'
        completions_instance = sys.modules["openai.resources.chat.completions"].Completions()
        response = completions_instance.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        # 4. Verify the response bubbles up correctly
        self.assertEqual(response, mock_response)
        
        # 5. Verify Transport received data
        self.assertTrue(self.client.transport.send.called)
        
        call_args = self.client.transport.send.call_args[0][0]
        self.assertIn("gpt-4", call_args["name"])
        self.assertEqual(call_args["status"], "success")
        
        output = call_args["output"]
        self.assertEqual(output["content"], "AI Response")
        self.assertEqual(output["usage"]["total_tokens"], 15)

if __name__ == "__main__":
    unittest.main()
