class SpanKind:
	INTERNAL = "internal"
	CLIENT = "client"
	SERVER = "server"
	PRODUCER = "producer"
	CONSUMER = "consumer"


class AgentBaySpanKindValues:
	AGENT = type("Enum", (), {"value": "agent"})()
	TASK = type("Enum", (), {"value": "task"})()
	LLM = type("Enum", (), {"value": "llm"})()
	TOOL = type("Enum", (), {"value": "tool"})()


