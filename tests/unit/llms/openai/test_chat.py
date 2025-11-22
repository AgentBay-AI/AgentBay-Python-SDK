import unittest
from unittest.mock import MagicMock, patch
import sys

# We need to mock 'openai' BEFORE importing our instrumentation
# because our code tries to import it.
mock_openai = MagicMock()
sys.modules["openai"] = mock_openai
sys.modules["openai.resources"] = MagicMock()
sys.modules["openai.resources.chat"] = MagicMock()
sys.modules["openai.resources.chat.completions"] = MagicMock()

from agentbay import init
from agentbay.llms.openai import instrument
from agentbay.llms.openai.chat import instrument_chat

class TestOpenAIChat(unittest.TestCase):
    
    def setUp(self):
        # Initialize SDK
        self.client = init(api_key="test-key")
        self.client.transport.send = MagicMock()
        
        # Setup the mock class structure that our code expects
        # openai.resources.chat.completions.Completions.create
        self.mock_completions = MagicMock()
        self.mock_create = MagicMock()
        self.mock_completions.create = self.mock_create
        
        # We need to inject this mock into the place where our code looks for it
        # In chat.py, we do: from openai.resources.chat.completions import Completions
        # So we need to patch that import.
        
    def test_instrumentation_wraps_create(self):
        """Test that calling create() triggers our wrapper."""
        
        # 1. Mock the import in chat.py
        with patch("agentbay.llms.openai.chat.Completions", self.mock_completions):
            # 2. Run instrumentation
            # We pass a dummy module, but our code actually looks at the Class we just patched
            instrument_chat(mock_openai)
            
            # 3. Setup a fake response from OpenAI
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="AI Response"))]
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 5
            mock_response.usage.total_tokens = 15
            
            # The original create method (which is now wrapped) should return this
            # Note: We are mocking the 'original' create that our wrapper calls
            self.mock_create.return_value = mock_response
            
            # 4. Call the method (this is what the user would do)
            # Since we patched Completions.create, calling it should hit our wrapper
            self.mock_completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": "Hello"}]
            )
            
            # 5. Verify Transport received data
            self.assertTrue(self.client.transport.send.called)
            
            call_args = self.client.transport.send.call_args[0][0]
            self.assertIn("gpt-4", call_args["name"])
            self.assertEqual(call_args["status"], "success")
            
            # Verify metrics were captured
            output = call_args["output"]
            self.assertEqual(output["content"], "AI Response")
            self.assertEqual(output["usage"]["total_tokens"], 15)

if __name__ == "__main__":
    unittest.main()

