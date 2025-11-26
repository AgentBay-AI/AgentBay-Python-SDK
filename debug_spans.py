import sys
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from agentbay import trace as agentbay_trace

# 1. Configure OTel to print to Console
provider = TracerProvider()
# ConsoleSpanExporter prints the internal OTel Span object to stdout
processor = SimpleSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

# 2. Define a dummy function
@agentbay_trace
def example_agent_task(user_query):
    print(f"Processing: {user_query}")
    return {"response": "I am a robot", "confidence": 0.99}

# 3. Run it
print("--- STARTING AGENT ---")
try:
    example_agent_task("Hello OpenTelemetry")
except Exception as e:
    print(e)
print("--- DONE ---")

