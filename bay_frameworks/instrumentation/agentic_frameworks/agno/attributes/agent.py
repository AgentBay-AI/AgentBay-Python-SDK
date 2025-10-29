from typing import Optional, Tuple, Dict, Any
from MYSDK.bay_frameworks.instrumentation.common.attributes import AttributeMap
from MYSDK.bay_frameworks.semconv import SpanAttributes, AgentAttributes, ToolAttributes
from MYSDK.bay_frameworks.semconv.span_kinds import AgentBaySpanKindValues as AgentBaySpanKind
import json


def get_agent_run_attributes(
	args: Optional[Tuple] = None,
	kwargs: Optional[Dict] = None,
	return_value: Optional[Any] = None,
) -> AttributeMap:
	attributes: AttributeMap = {}
	agent_name = None
    attributes[SpanAttributes.BAYFW_SPAN_KIND] = AgentBaySpanKind.AGENT.value
	attributes[SpanAttributes.LLM_SYSTEM] = "agno"
	attributes[SpanAttributes.BAYFW_ENTITY_NAME] = "agent"
	if args and len(args) >= 1:
		agent = args[0]
		if hasattr(agent, "agent_id") and agent.agent_id:
			attributes[AgentAttributes.AGENT_ID] = str(agent.agent_id)
		if hasattr(agent, "name") and agent.name:
			agent_name = str(agent.name)
			attributes[AgentAttributes.AGENT_NAME] = agent_name
		if hasattr(agent, "role") and agent.role:
			attributes[AgentAttributes.AGENT_ROLE] = str(agent.role)
		if hasattr(agent, "_team") and agent._team:
			team = agent._team
			if hasattr(team, "name") and team.name:
				attributes["agent.parent_team"] = str(team.name)
				attributes["agent.parent_team_display"] = f"Under {team.name}"
			if hasattr(team, "team_id") and team.team_id:
				attributes["agent.parent_team_id"] = str(team.team_id)
		if hasattr(agent, "model") and agent.model:
			model = agent.model
			if hasattr(model, "id"):
				model_id = str(model.id)
				attributes[SpanAttributes.LLM_REQUEST_MODEL] = model_id
				attributes[SpanAttributes.LLM_RESPONSE_MODEL] = model_id
			if hasattr(model, "provider"):
				attributes["agent.model_provider"] = str(model.provider)
		if hasattr(agent, "description") and agent.description:
			attributes["agent.description"] = str(agent.description)
		if hasattr(agent, "goal") and agent.goal:
			attributes["agent.goal"] = str(agent.goal)
		if hasattr(agent, "instructions") and agent.instructions:
			if isinstance(agent.instructions, list):
				attributes["agent.instruction"] = " | ".join(str(i) for i in agent.instructions)
			else:
				attributes["agent.instruction"] = str(agent.instructions)
		if hasattr(agent, "expected_output") and agent.expected_output:
			attributes["agent.expected_output"] = str(agent.expected_output)
		if hasattr(agent, "markdown"):
			attributes["agent.markdown"] = str(agent.markdown)
		if hasattr(agent, "reasoning"):
			attributes[AgentAttributes.AGENT_REASONING] = str(agent.reasoning)
		if hasattr(agent, "stream"):
			attributes["agent.stream"] = str(agent.stream)
		if hasattr(agent, "show_tool_calls"):
			attributes["agent.show_tool_calls"] = str(agent.show_tool_calls)
		if hasattr(agent, "tool_call_limit") and agent.tool_call_limit:
			attributes["agent.tool_call_limit"] = str(agent.tool_call_limit)
		if hasattr(agent, "tools") and agent.tools:
			attributes["agent.tools_count"] = str(len(agent.tools))
			tool_names = []
			if len(agent.tools) == 1:
				tool = agent.tools[0]
				tool_name = None
				if hasattr(tool, "name"):
					tool_name = str(tool.name)
					attributes[ToolAttributes.TOOL_NAME] = tool_name
				elif hasattr(tool, "__name__"):
					tool_name = str(tool.__name__)
					attributes[ToolAttributes.TOOL_NAME] = tool_name
				elif callable(tool):
					tool_name = getattr(tool, "__name__", "unknown_tool")
					attributes[ToolAttributes.TOOL_NAME] = tool_name
				if tool_name:
					tool_names.append(tool_name)
				if hasattr(tool, "description") and tool.description:
					attributes[ToolAttributes.TOOL_DESCRIPTION] = str(tool.description)
				elif hasattr(tool, "__doc__") and tool.__doc__:
					attributes[ToolAttributes.TOOL_DESCRIPTION] = str(tool.__doc__).strip()
			else:
				for i, tool in enumerate(agent.tools):
					tool_name = None
					if hasattr(tool, "name"):
						tool_name = str(tool.name)
						attributes[f"tool.{i}.name"] = tool_name
					elif hasattr(tool, "__name__"):
						tool_name = str(tool.__name__)
						attributes[f"tool.{i}.name"] = tool_name
					elif callable(tool):
						tool_name = getattr(tool, "__name__", "unknown_tool")
						attributes[f"tool.{i}.name"] = tool_name
					if tool_name:
						tool_names.append(tool_name)
					if hasattr(tool, "description") and tool.description:
						attributes[f"tool.{i}.description"] = str(tool.description)
					elif hasattr(tool, "__doc__") and tool.__doc__:
						attributes[f"tool.{i}.description"] = str(tool.__doc__).strip()
			if tool_names:
				attributes[AgentAttributes.AGENT_TOOLS] = json.dumps(tool_names)
		if hasattr(agent, "knowledge") and agent.knowledge:
			attributes["agent.knowledge_type"] = type(agent.knowledge).__name__
		if hasattr(agent, "storage") and agent.storage:
			attributes["agent.storage_type"] = type(agent.storage).__name__
		if hasattr(agent, "session_id") and agent.session_id:
			attributes["agent.session_id"] = str(agent.session_id)
		if hasattr(agent, "user_id") and agent.user_id:
			attributes["agent.user_id"] = str(agent.user_id)
		if hasattr(agent, "output_key") and agent.output_key:
			attributes["agent.output_key"] = str(agent.output_key)
	if args and len(args) >= 2:
		message = args[1]
		if message:
			message_str = str(message)
			attributes["agent.input"] = message_str
			attributes[SpanAttributes.BAYFW_ENTITY_INPUT] = message_str
	if kwargs:
		if kwargs.get("stream") is not None:
			attributes[SpanAttributes.LLM_REQUEST_STREAMING] = str(kwargs["stream"])
		if kwargs.get("session_id"):
			attributes["agent.run_session_id"] = str(kwargs["session_id"])
		if kwargs.get("user_id"):
			attributes["agent.run_user_id"] = str(kwargs["user_id"])
	if return_value:
		if hasattr(return_value, "run_id") and return_value.run_id:
			attributes["agent.run_id"] = str(return_value.run_id)
		if hasattr(return_value, "content") and return_value.content:
			attributes["agent.output"] = str(return_value.content)
		if hasattr(return_value, "event") and return_value.event:
			attributes["agent.event"] = str(return_value.event)
		if hasattr(return_value, "tools") and return_value.tools:
			attributes["agent.tool_executions_count"] = str(len(return_value.tools))
			for i, tool_exec in enumerate(return_value.tools):
				if hasattr(tool_exec, "tool_name") and tool_exec.tool_name:
					attributes[f"tool.{i}.name"] = str(tool_exec.tool_name)
				if hasattr(tool_exec, "tool_args") and tool_exec.tool_args:
					try:
						attributes[f"tool.{i}.parameters"] = json.dumps(tool_exec.tool_args)
					except:
						attributes[f"tool.{i}.parameters"] = str(tool_exec.tool_args)
				if hasattr(tool_exec, "result") and tool_exec.result:
					attributes[f"tool.{i}.result"] = str(tool_exec.result)
				if hasattr(tool_exec, "tool_call_error") and tool_exec.tool_call_error:
					attributes[f"tool.{i}.error"] = str(tool_exec.tool_call_error)
				attributes[f"tool.{i}.status"] = "success"
	if agent_name:
		parent_team = attributes.get("agent.parent_team")
		attributes["agent.display_name"] = f"{agent_name} (Agent under {parent_team})" if parent_team else f"{agent_name}"
	return attributes


