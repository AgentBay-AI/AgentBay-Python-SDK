import unittest
import time
from agentbay.sessions import Session
from agentbay.span import Span

class TestDataModels(unittest.TestCase):
    
    def test_session_lifecycle(self):
        """Test creating and ending a session."""
        # 1. Start Session
        session = Session()
        self.assertIsNotNone(session.session_id)
        self.assertIsNotNone(session.start_time)
        self.assertIsNone(session.end_time)
        self.assertEqual(session.status, "active")
        
        # Sleep briefly to ensure time difference
        time.sleep(0.01)
        
        # 2. End Session
        session.end(status="completed")
        self.assertIsNotNone(session.end_time)
        self.assertGreater(session.end_time, session.start_time)
        self.assertEqual(session.status, "completed")
        
        # 3. Check Dict Serialization
        data = session.to_dict()
        self.assertEqual(data["id"], session.session_id)
        self.assertEqual(data["status"], "completed")

    def test_span_lifecycle(self):
        """Test creating and ending a span."""
        session = Session()
        
        # 1. Start Span
        span = Span(
            session_id=session.session_id,
            name="test_action",
            input_data={"query": "hello"}
        )
        
        self.assertEqual(span.session_id, session.session_id)
        self.assertEqual(span.name, "test_action")
        self.assertEqual(span.input, {"query": "hello"})
        self.assertIsNone(span.output)
        
        # 2. End Span
        output_data = "Hello world response"
        span.end(output=output_data)
        
        self.assertEqual(span.output, output_data)
        self.assertEqual(span.status, "success")
        self.assertIsNotNone(span.end_time)
        
        # 3. Check Dict Serialization
        data = span.to_dict()
        self.assertEqual(data["name"], "test_action")
        self.assertEqual(data["output"], output_data)

if __name__ == "__main__":
    unittest.main()

