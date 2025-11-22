import unittest
from unittest.mock import MagicMock
from agentbay import trace, init, AgentBay

class TestDecorators(unittest.TestCase):
    
    def setUp(self):
        # Initialize the client with a fake key so transport exists
        self.client = init(api_key="test-key", api_url="http://test-url")
        # Mock the transport.send method so we can see if it was called
        self.client.transport.send = MagicMock()

    def tearDown(self):
        self.client.shutdown()

    def test_trace_success(self):
        """Test that a successful function call is tracked."""
        
        @trace
        def add(a, b):
            return a + b
        
        # 1. Call the function
        result = add(2, 3)
        
        # 2. Verify result is correct
        self.assertEqual(result, 5)
        
        # 3. Verify transport.send was called
        self.assertTrue(self.client.transport.send.called)
        
        # 4. Verify data sent
        call_args = self.client.transport.send.call_args[0][0]
        self.assertEqual(call_args["name"], "add")
        self.assertEqual(call_args["status"], "success")
        self.assertIn("5", call_args["output"])

    def test_trace_error(self):
        """Test that an error in the function is tracked."""
        
        @trace
        def divider(x):
            return 10 / x
        
        # 1. Call function expecting an error
        with self.assertRaises(ZeroDivisionError):
            divider(0)
            
        # 2. Verify transport.send was still called
        self.assertTrue(self.client.transport.send.called)
        
        # 3. Verify it logged the error
        call_args = self.client.transport.send.call_args[0][0]
        self.assertEqual(call_args["status"], "error")
        self.assertIn("division by zero", call_args["output"])

if __name__ == "__main__":
    unittest.main()

