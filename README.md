# AgentBay Python SDK

**Management & Observability SDK for AI Agents**

The **AgentBay Python SDK** provides a simple, lightweight way to track the performance, traces, sessions, and behavior of AI agents. It instruments your agent code, LLM calls, and tool executions—sending structured telemetry to the AgentBay backend for analysis and visualization.

This is the **foundation SDK** that enables deep observability for coded agents built with:
- Pure Python
- Multiple LLMs
- Multiple Frameworks

## 📦 Installation

```bash
pip install agentbay
```

## 🚀 Quick Start

### 1. Initialize the SDK
Start by initializing the SDK with your API key. This usually goes at the top of your main application file.

```python
import agentbay

# Initialize with your API Key
agentbay.init(api_key="your-api-key-here")
```

### 2. Track Functions
Use the `@trace` decorator to automatically track inputs, outputs, execution time, and errors for any function.

```python
from agentbay import trace

@trace
def chat_with_user(query):
    # Your agent logic here
    return "Response to: " + query

# When you call this, data is automatically sent to AgentBay
chat_with_user("Hello world")
```

## 🛠️ Core Concepts

- **Sessions**: A session represents a single conversation or thread.
- **Spans**: A span is a single unit of work (like a function call, an LLM request, or a database query).
- **Transport**: Data is sent asynchronously in the background, so your agent's performance is never impacted.

## 🤝 Contributing
We welcome contributions! Please check out the `frameworks/` and `llms/` directories for future integrations.
