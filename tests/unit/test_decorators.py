import unittest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from agentbay import trace as agentbay_trace

class TestDecorators(unittest.TestCase):
    
    def setUp(self):
        # 1. Set up OTel for testing
        self.exporter = InMemorySpanExporter()
        self.provider = TracerProvider()
        processor = SimpleSpanProcessor(self.exporter)
        self.provider.add_span_processor(processor)
        
        # Force reset the global tracer provider for testing purposes
        # (This is a hack for unit tests because OTel is a singleton)
        trace._set_tracer_provider(self.provider, log=False)

    def test_trace_success(self):
        """Test that a successful function call is tracked via OTel."""
        
        @agentbay_trace
        def add(a, b):
            return a + b
        
        # 1. Call the function
        result = add(2, 3)
        self.assertEqual(result, 5)
        
        # 2. Verify Span was created
        spans = self.exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)
        
        span = spans[0]
        self.assertEqual(span.name, "add")
        self.assertEqual(span.status.status_code, trace.StatusCode.OK)
        self.assertEqual(span.attributes["input.args"], "(2, 3)")
        self.assertEqual(span.attributes["output"], "5")

    def test_trace_error(self):
        """Test that an error in the function is tracked via OTel."""
        
        @agentbay_trace
        def divider(x):
            return 10 / x
        
        # 1. Call function expecting an error
        with self.assertRaises(ZeroDivisionError):
            divider(0)
            
        # 2. Verify Span was created
        spans = self.exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)
        
        span = spans[0]
        self.assertEqual(span.name, "divider")
        self.assertEqual(span.status.status_code, trace.StatusCode.ERROR)
        
        # Check that we recorded an exception event
        # We just check that at least one event is an exception
        exception_events = [e for e in span.events if e.name == "exception"]
        self.assertGreaterEqual(len(exception_events), 1)

if __name__ == "__main__":
    unittest.main()
