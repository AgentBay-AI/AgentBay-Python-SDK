import sys
import time
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource

# 1. Setup OTel with realistic Resource metadata
resource = Resource.create({
    "service.name": "agentbay-python-sdk",
    "service.version": "0.1.0",
    "deployment.environment": "production"
})

provider = TracerProvider(resource=resource)
processor = SimpleSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

tracer = trace.get_tracer("agentbay.debug")

# 2. Simulate a Complex Agent Workflow
def simulate_openai_call(prompt):
    """Simulates a call to OpenAI with token usage."""
    with tracer.start_as_current_span("openai.chat.completions.create") as span:
        span.set_attribute("llm.system", "openai")
        span.set_attribute("llm.request.model", "gpt-4")
        span.set_attribute("llm.request.messages", f"[{{'role': 'user', 'content': '{prompt}'}}]")
        
        # Simulate network delay
        time.sleep(0.2)
        
        # Record Response
        response_content = "Here is a summary of your data..."
        span.set_attribute("llm.response.content", response_content)
        span.set_attribute("llm.usage.prompt_tokens", 50)
        span.set_attribute("llm.usage.completion_tokens", 20)
        span.set_attribute("llm.usage.total_tokens", 70)
        
        return response_content

def agent_workflow(user_query):
    """Top level agent function."""
    with tracer.start_as_current_span("agent.run") as span:
        span.set_attribute("agent.name", "FinancialAnalystAgent")
        span.set_attribute("input.query", user_query)
        
        print(f"Agent processing: {user_query}")
        
        # Step 1: Search
        with tracer.start_as_current_span("tool.search") as tool_span:
            tool_span.set_attribute("tool.name", "google_search")
            time.sleep(0.1)
            tool_span.set_attribute("tool.result", "Found 5 financial reports.")
        
        # Step 2: LLM
        result = simulate_openai_call(user_query)
        
        span.set_attribute("output.result", result)

# 3. Run the Simulation
print("--- SIMULATING REALISTIC AGENT TRACE ---")
agent_workflow("Analyze AAPL stock performance")
print("--- DONE ---")
print("\nCheck the output above. Your backend will receive:")
print("1. A parent span 'agent.run'")
print("2. A child span 'tool.search'")
print("3. A child span 'openai.chat.completions.create'")
print("All linked by the same trace_id.")
