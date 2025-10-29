from typing import Any, List, Dict, Optional
from MYSDK.bay_frameworks.logging import logger
from MYSDK.bay_frameworks.semconv import (
    AgentAttributes,
    WorkflowAttributes,
    SpanAttributes,
    InstrumentationAttributes,
    ToolAttributes,
    AgentBaySpanKindValues,
    ToolStatus,
)
from MYSDK.bay_frameworks.helpers import safe_serialize

from MYSDK.bay_frameworks.instrumentation.common import AttributeMap, _extract_attributes_from_mapping
from MYSDK.bay_frameworks.instrumentation.common.attributes import get_common_attributes
from MYSDK.bay_frameworks.instrumentation.agentic_frameworks.openai_agents import LIBRARY_NAME, LIBRARY_VERSION
from MYSDK.bay_frameworks.instrumentation.agentic_frameworks.openai_agents.attributes.model import (
	get_model_attributes,
	get_model_config_attributes,
)
from MYSDK.bay_frameworks.instrumentation.agentic_frameworks.openai_agents.attributes.completion import get_generation_output_attributes


AGENT_SPAN_ATTRIBUTES: AttributeMap = {
	AgentAttributes.AGENT_NAME: "name",
	AgentAttributes.AGENT_TOOLS: "tools",
	AgentAttributes.HANDOFFS: "handoffs",
	WorkflowAttributes.WORKFLOW_INPUT: "input",
	WorkflowAttributes.WORKFLOW_OUTPUT: "output",
}


FUNCTION_SPAN_ATTRIBUTES: AttributeMap = {
	ToolAttributes.TOOL_NAME: "name",
	ToolAttributes.TOOL_PARAMETERS: "input",
	ToolAttributes.TOOL_RESULT: "output",
	AgentAttributes.FROM_AGENT: "from_agent",
}


HANDOFF_SPAN_ATTRIBUTES: AttributeMap = {
	AgentAttributes.FROM_AGENT: "from_agent",
	AgentAttributes.TO_AGENT: "to_agent",
}


GENERATION_SPAN_ATTRIBUTES: AttributeMap = {
	SpanAttributes.LLM_PROMPTS: "input",
}


RESPONSE_SPAN_ATTRIBUTES: AttributeMap = {
	SpanAttributes.LLM_RESPONSE_MODEL: "model",
}


TRANSCRIPTION_SPAN_ATTRIBUTES: AttributeMap = {
	WorkflowAttributes.WORKFLOW_OUTPUT: "output",
}


SPEECH_SPAN_ATTRIBUTES: AttributeMap = {
	WorkflowAttributes.WORKFLOW_INPUT: "input",
}


SPEECH_GROUP_SPAN_ATTRIBUTES: AttributeMap = {
	WorkflowAttributes.WORKFLOW_INPUT: "input",
}


def _get_llm_messages_attributes(messages: Optional[List[Dict]], attribute_base: str) -> AttributeMap:
	attributes: AttributeMap = {}
	if not messages:
		return attributes
	if not isinstance(messages, list):
		logger.warning(
			f"[_get_llm_messages_attributes] Expected a list of messages for base '{attribute_base}', got {type(messages)}. Value: {safe_serialize(messages)}. Returning empty."
		)
		return attributes
	for i, msg_dict in enumerate(messages):
		if isinstance(msg_dict, dict):
			role = msg_dict.get("role")
			content = msg_dict.get("content")
			name = msg_dict.get("name")
			tool_calls = msg_dict.get("tool_calls")
			tool_call_id = msg_dict.get("tool_call_id")
			if role:
				attributes[f"{attribute_base}.{i}.role"] = str(role)
			if content is not None:
				attributes[f"{attribute_base}.{i}.content"] = safe_serialize(content)
			if name:
				attributes[f"{attribute_base}.{i}.name"] = str(name)
			if tool_calls and isinstance(tool_calls, list):
				for tc_idx, tc_dict in enumerate(tool_calls):
					if isinstance(tc_dict, dict):
						tc_id = tc_dict.get("id")
						tc_type = tc_dict.get("type")
						tc_function_data = tc_dict.get("function")
						if tc_function_data and isinstance(tc_function_data, dict):
							tc_func_name = tc_function_data.get("name")
							tc_func_args = tc_function_data.get("arguments")
							base_tool_call_key_formatted = f"{attribute_base}.{i}.tool_calls.{tc_idx}"
							if tc_id:
								attributes[f"{base_tool_call_key_formatted}.id"] = str(tc_id)
							if tc_type:
								attributes[f"{base_tool_call_key_formatted}.type"] = str(tc_type)
							if tc_func_name:
								attributes[f"{base_tool_call_key_formatted}.function.name"] = str(tc_func_name)
							if tc_func_args is not None:
								attributes[f"{base_tool_call_key_formatted}.function.arguments"] = safe_serialize(tc_func_args)
			if tool_call_id:
				attributes[f"{attribute_base}.{i}.tool_call_id"] = str(tool_call_id)
		else:
			attributes[f"{attribute_base}.{i}.content"] = safe_serialize(msg_dict)
	return attributes


def get_common_instrumentation_attributes() -> AttributeMap:
	attributes = get_common_attributes()
	attributes.update({
		InstrumentationAttributes.LIBRARY_NAME: LIBRARY_NAME,
		InstrumentationAttributes.LIBRARY_VERSION: LIBRARY_VERSION,
	})
	return attributes


def get_agent_span_attributes(span_data: Any) -> AttributeMap:
	attributes = {}
	attributes.update(get_common_attributes())
    attributes[SpanAttributes.BAYFW_SPAN_KIND] = AgentBaySpanKindValues.AGENT.value
	if hasattr(span_data, "name") and span_data.name:
		attributes[AgentAttributes.AGENT_NAME] = str(span_data.name)
	if hasattr(span_data, "handoffs") and span_data.handoffs:
		attributes[AgentAttributes.HANDOFFS] = safe_serialize(span_data.handoffs)
	if hasattr(span_data, "tools") and span_data.tools:
		attributes[AgentAttributes.AGENT_TOOLS] = safe_serialize([str(getattr(t, "name", t)) for t in span_data.tools])
	return attributes


def get_function_span_attributes(span_data: Any) -> AttributeMap:
	attributes = _extract_attributes_from_mapping(span_data, FUNCTION_SPAN_ATTRIBUTES)
	attributes.update(get_common_attributes())
    attributes[SpanAttributes.BAYFW_SPAN_KIND] = AgentBaySpanKindValues.TOOL.value
	if hasattr(span_data, "error") and span_data.error:
		attributes[ToolAttributes.TOOL_STATUS] = ToolStatus.FAILED.value
	else:
		if hasattr(span_data, "output") and span_data.output is not None:
			attributes[ToolAttributes.TOOL_STATUS] = ToolStatus.SUCCEEDED.value
	return attributes


def get_handoff_span_attributes(span_data: Any) -> AttributeMap:
	attributes = _extract_attributes_from_mapping(span_data, HANDOFF_SPAN_ATTRIBUTES)
	attributes.update(get_common_attributes())
	return attributes


def _extract_text_from_content(content: Any) -> Optional[str]:
	if isinstance(content, str):
		return content
	if isinstance(content, dict):
		if "text" in content:
			return content["text"]
		if content.get("type") == "output_text":
			return content.get("text", "")
	if isinstance(content, list):
		text_parts = []
		for item in content:
			extracted = _extract_text_from_content(item)
			if extracted:
				text_parts.append(extracted)
		return " ".join(text_parts) if text_parts else None
	return None


def _build_prompt_messages_from_input(input_data: Any) -> List[Dict[str, Any]]:
	messages = []
	if isinstance(input_data, str):
		messages.append({"role": "user", "content": input_data})
	elif isinstance(input_data, list):
		for msg in input_data:
			if isinstance(msg, dict):
				role = msg.get("role")
				content = msg.get("content")
				if role and content is not None:
					extracted_text = _extract_text_from_content(content)
					if extracted_text:
						messages.append({"role": role, "content": extracted_text})
	return messages


def get_response_span_attributes(span_data: Any) -> AttributeMap:
	attributes = _extract_attributes_from_mapping(span_data, RESPONSE_SPAN_ATTRIBUTES)
	attributes.update(get_common_attributes())
	if span_data.response:
		from MYSDK.bay_frameworks.instrumentation.agentic_frameworks.openai_agents.attributes.response import get_response_response_attributes
		response_attrs = get_response_response_attributes(span_data.response)
		system_prompt = response_attrs.get(SpanAttributes.LLM_OPENAI_RESPONSE_INSTRUCTIONS)
		prompt_messages = []
		if system_prompt:
			prompt_messages.append({"role": "system", "content": system_prompt})
			response_attrs.pop(SpanAttributes.LLM_OPENAI_RESPONSE_INSTRUCTIONS, None)
		if hasattr(span_data, "input") and span_data.input:
			prompt_messages.extend(_build_prompt_messages_from_input(span_data.input))
		if prompt_messages:
			attributes.update(_get_llm_messages_attributes(prompt_messages, "gen_ai.prompt"))
		response_attrs = {k: v for k, v in response_attrs.items() if not k.startswith("gen_ai.prompt") and k != "gen_ai.request.tools"}
		attributes.update(response_attrs)
	else:
		if hasattr(span_data, "input") and span_data.input:
			prompt_messages = _build_prompt_messages_from_input(span_data.input)
			if prompt_messages:
				attributes.update(_get_llm_messages_attributes(prompt_messages, "gen_ai.prompt"))
    attributes[SpanAttributes.BAYFW_SPAN_KIND] = AgentBaySpanKindValues.LLM.value
	return attributes


def get_generation_span_attributes(span_data: Any) -> AttributeMap:
	attributes = _extract_attributes_from_mapping(span_data, GENERATION_SPAN_ATTRIBUTES)
	attributes.update(get_common_attributes())
	if SpanAttributes.LLM_PROMPTS in attributes:
		raw_prompt_input = attributes.pop(SpanAttributes.LLM_PROMPTS)
		formatted_prompt_for_llm = []
		if isinstance(raw_prompt_input, str):
			formatted_prompt_for_llm.append({"role": "user", "content": raw_prompt_input})
		elif isinstance(raw_prompt_input, list):
			temp_formatted_list = []
			all_strings_or_dicts = True
			for item in raw_prompt_input:
				if isinstance(item, str):
					temp_formatted_list.append({"role": "user", "content": item})
				elif isinstance(item, dict):
					temp_formatted_list.append(item)
				else:
					all_strings_or_dicts = False
					break
			if all_strings_or_dicts:
				formatted_prompt_for_llm = temp_formatted_list
			else:
				logger.warning(
					f"[get_generation_span_attributes] span_data.input was a list with mixed/unexpected content: {safe_serialize(raw_prompt_input)}"
				)
		if formatted_prompt_for_llm:
			attributes.update(_get_llm_messages_attributes(formatted_prompt_for_llm, "gen_ai.prompt"))
	if span_data.model:
		attributes.update(get_model_attributes(span_data.model))
	if span_data.output:
		attributes.update(get_generation_output_attributes(span_data.output))
	if span_data.model_config:
		attributes.update(get_model_config_attributes(span_data.model_config))
    attributes[SpanAttributes.BAYFW_SPAN_KIND] = AgentBaySpanKindValues.LLM.value
	return attributes


def get_transcription_span_attributes(span_data: Any) -> AttributeMap:
	attributes = _extract_attributes_from_mapping(span_data, TRANSCRIPTION_SPAN_ATTRIBUTES)
	attributes.update(get_common_attributes())
	return attributes


def get_speech_span_attributes(span_data: Any) -> AttributeMap:
	attributes = _extract_attributes_from_mapping(span_data, SPEECH_SPAN_ATTRIBUTES)
	attributes.update(get_common_attributes())
	return attributes


def get_speech_group_span_attributes(span_data: Any) -> AttributeMap:
	attributes = _extract_attributes_from_mapping(span_data, SPEECH_GROUP_SPAN_ATTRIBUTES)
	attributes.update(get_common_attributes())
	return attributes


def get_span_attributes(span_data: Any) -> AttributeMap:
	span_type = span_data.__class__.__name__
	if span_type == "AgentSpanData":
		attributes = get_agent_span_attributes(span_data)
	elif span_type == "FunctionSpanData":
		attributes = get_function_span_attributes(span_data)
	elif span_type == "GenerationSpanData":
		attributes = get_generation_span_attributes(span_data)
	elif span_type == "HandoffSpanData":
		attributes = get_handoff_span_attributes(span_data)
	elif span_type == "ResponseSpanData":
		attributes = get_response_span_attributes(span_data)
	elif span_type == "TranscriptionSpanData":
		attributes = get_transcription_span_attributes(span_data)
	elif span_type == "SpeechSpanData":
		attributes = get_speech_span_attributes(span_data)
	elif span_type == "SpeechGroupSpanData":
		attributes = get_speech_group_span_attributes(span_data)
	else:
		logger.debug(f"[bay_frameworks.instrumentation.openai_agents.attributes] Unknown span type: {span_type}")
		attributes = {}
	return attributes


