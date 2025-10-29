"""Xpander SDK instrumentation for bay_frameworks."""

import json
import time
from typing import Any, Optional, Dict

from opentelemetry.metrics import Meter
from opentelemetry.trace import SpanKind as OTelSpanKind
from opentelemetry import trace

from MYSDK.bay_frameworks.instrumentation.common import (
	CommonInstrumentor,
	InstrumentorConfig,
	StandardMetrics,
)
from MYSDK.bay_frameworks.instrumentation.common.span_management import SpanAttributeManager
from MYSDK.bay_frameworks.instrumentation.common.wrappers import (
	_finish_span_success,
	_finish_span_error,
	_update_span,
)
from MYSDK.bay_frameworks.helpers.serialization import safe_serialize, model_to_dict
from MYSDK.bay_frameworks.instrumentation.agentic_frameworks.xpander.context import XpanderContext
from MYSDK.bay_frameworks.semconv import SpanAttributes, SpanKind, ToolAttributes, AgentBaySpanKindValues
from MYSDK.bay_frameworks.semconv.message import MessageAttributes
from MYSDK.bay_frameworks.logging import logger


_instruments = ("xpander-sdk >= 1.0.0",)


def safe_set_attribute(span, key: str, value: Any) -> None:
	try:
		_update_span(span, {key: value})
	except Exception as e:
		logger.debug(f"Failed to set attribute {key}: {e}")


class XpanderInstrumentor(CommonInstrumentor):
	"""Instrumentor for Xpander SDK interactions."""

	def __init__(self, config: Optional[InstrumentorConfig] = None):
		if config is None:
			config = InstrumentorConfig(
				library_name="bay_frameworks.instrumentation.xpander",
				library_version="1.0.0",
				dependencies=_instruments,
				metrics_enabled=True,
			)
		super().__init__(config)
		self._context = XpanderContext()
		self._attribute_manager = SpanAttributeManager("bay_frameworks-xpander", "production")

	def _get_session_id_from_agent(self, agent) -> str:
		if hasattr(agent, "memory_thread_id"):
			return f"session_{agent.memory_thread_id}"
		if hasattr(agent, "execution") and hasattr(agent.execution, "memory_thread_id"):
			return f"session_{agent.execution.memory_thread_id}"
		agent_name = getattr(agent, "name", "unknown")
		agent_id = getattr(agent, "id", "unknown")
		return f"agent_{agent_name}_{agent_id}"

	def _extract_session_id(self, execution, agent=None) -> str:
		if isinstance(execution, dict):
			if "memory_thread_id" in execution:
				return f"session_{execution['memory_thread_id']}"
			elif "thread_id" in execution:
				return f"session_{execution['thread_id']}"
			elif "session_id" in execution:
				return f"session_{execution['session_id']}"
		if agent:
			return self._get_session_id_from_agent(agent)
		return f"session_{int(time.time())}"

	def _extract_tool_name(self, tool_call) -> str:
		if hasattr(tool_call, "function_name"):
			return tool_call.function_name
		if hasattr(tool_call, "function") and hasattr(tool_call.function, "name"):
			return tool_call.function.name
		if hasattr(tool_call, "name"):
			return tool_call.name
		if isinstance(tool_call, dict):
			if "function" in tool_call:
				return tool_call["function"].get("name", "unknown")
			if "function_name" in tool_call:
				return tool_call["function_name"]
			if "name" in tool_call:
				return tool_call["name"]
		return "unknown"

	def _extract_tool_params(self, tool_call) -> dict:
		if hasattr(tool_call, "function") and hasattr(tool_call.function, "arguments"):
			try:
				args = tool_call.function.arguments
				if isinstance(args, str):
					return json.loads(args)
				elif isinstance(args, dict):
					return args
			except Exception:
				pass
		elif hasattr(tool_call, "arguments"):
			try:
				args = tool_call.arguments
				if isinstance(args, str):
					return json.loads(args)
				elif isinstance(args, dict):
					return args
			except Exception:
				pass
		elif isinstance(tool_call, dict):
			if "function" in tool_call:
				args = tool_call["function"].get("arguments", "{}")
				try:
					return json.loads(args) if isinstance(args, str) else args
				except Exception:
					pass
			elif "arguments" in tool_call:
				args = tool_call["arguments"]
				try:
					return json.loads(args) if isinstance(args, str) else args
				except Exception:
					pass
		return {}

	def _extract_llm_data_from_messages(self, messages) -> dict:
		data = {}
		if isinstance(messages, dict):
			if "model" in messages:
				data["model"] = messages["model"]
			if "usage" in messages:
				data["usage"] = messages["usage"]
			if "choices" in messages and messages["choices"]:
				choice = messages["choices"][0]
				if "message" in choice:
					message = choice["message"]
					if "model" in message:
						data["model"] = message["model"]
		elif isinstance(messages, list):
			for msg in messages:
				if isinstance(msg, dict) and msg.get("role") == "assistant":
					if "model" in msg:
						data["model"] = msg["model"]
					if "usage" in msg:
						data["usage"] = msg["usage"]
					break
		elif hasattr(messages, "__dict__"):
			msg_dict = messages.__dict__
			if "model" in msg_dict:
				data["model"] = msg_dict["model"]
			if "usage" in msg_dict:
				data["usage"] = msg_dict["usage"]
		return data

	def _extract_and_set_openai_message_attributes(self, span, messages, result, agent=None):
		try:
			agent_messages = []
			if agent and hasattr(agent, "messages"):
				agent_messages = getattr(agent, "messages", [])
			elif agent and hasattr(agent, "conversation_history"):
				agent_messages = getattr(agent, "conversation_history", [])
			elif agent and hasattr(agent, "history"):
				agent_messages = getattr(agent, "history", [])
			if isinstance(messages, list):
				agent_messages.extend(messages)
			elif isinstance(messages, dict) and "messages" in messages:
				agent_messages.extend(messages.get("messages", []))
			prompt_index = 0
			for msg in agent_messages[-10:]:
				if isinstance(msg, dict):
					role = msg.get("role", "user")
					content = msg.get("content", "")
					if content and isinstance(content, str) and content.strip():
						safe_set_attribute(span, MessageAttributes.PROMPT_ROLE.format(i=prompt_index), role)
						safe_set_attribute(span, MessageAttributes.PROMPT_CONTENT.format(i=prompt_index), content[:2000])
						prompt_index += 1
					elif content and isinstance(content, list):
						content_str = str(content)[:2000]
						safe_set_attribute(span, MessageAttributes.PROMPT_ROLE.format(i=prompt_index), role)
						safe_set_attribute(span, MessageAttributes.PROMPT_CONTENT.format(i=prompt_index), content_str)
						prompt_index += 1
				elif hasattr(msg, "content"):
					content = getattr(msg, "content", "")
					role = getattr(msg, "role", "user")
					if content and isinstance(content, str) and content.strip():
						safe_set_attribute(span, MessageAttributes.PROMPT_ROLE.format(i=prompt_index), role)
						safe_set_attribute(span, MessageAttributes.PROMPT_CONTENT.format(i=prompt_index), str(content)[:2000])
						prompt_index += 1
			completion_index = 0
			response_data = result if result else messages
			if isinstance(response_data, dict):
				choices = response_data.get("choices", [])
				for choice in choices:
					message = choice.get("message", {})
					role = message.get("role", "assistant")
					content = message.get("content", "")
					if content:
						safe_set_attribute(span, MessageAttributes.COMPLETION_ROLE.format(i=completion_index), role)
						safe_set_attribute(span, MessageAttributes.COMPLETION_CONTENT.format(i=completion_index), content[:2000])
					tool_calls = message.get("tool_calls", [])
					for j, tool_call in enumerate(tool_calls):
						tool_id = tool_call.get("id", "")
						tool_name = tool_call.get("function", {}).get("name", "")
						tool_args = tool_call.get("function", {}).get("arguments", "")
						if tool_id:
							safe_set_attribute(span, MessageAttributes.COMPLETION_TOOL_CALL_ID.format(i=completion_index, j=j), tool_id)
						if tool_name:
							safe_set_attribute(span, MessageAttributes.COMPLETION_TOOL_CALL_NAME.format(i=completion_index, j=j), tool_name)
						if tool_args:
							safe_set_attribute(span, MessageAttributes.COMPLETION_TOOL_CALL_ARGUMENTS.format(i=completion_index, j=j), str(tool_args)[:500])
						safe_set_attribute(span, MessageAttributes.COMPLETION_TOOL_CALL_TYPE.format(i=completion_index, j=j), "function")
					completion_index += 1
			elif hasattr(response_data, "choices"):
				choices = getattr(response_data, "choices", [])
				for choice in choices:
					message = getattr(choice, "message", None)
					if message:
						role = getattr(message, "role", "assistant")
						content = getattr(message, "content", "")
						if content:
							safe_set_attribute(span, MessageAttributes.COMPLETION_ROLE.format(i=completion_index), role)
							safe_set_attribute(span, MessageAttributes.COMPLETION_CONTENT.format(i=completion_index), str(content)[:2000])
						tool_calls = getattr(message, "tool_calls", [])
						for j, tool_call in enumerate(tool_calls):
							tool_id = getattr(tool_call, "id", "")
							function = getattr(tool_call, "function", None)
							if function:
								tool_name = getattr(function, "name", "")
								tool_args = getattr(function, "arguments", "")
								if tool_id:
									safe_set_attribute(span, MessageAttributes.COMPLETION_TOOL_CALL_ID.format(i=completion_index, j=j), tool_id)
								if tool_name:
									safe_set_attribute(span, MessageAttributes.COMPLETION_TOOL_CALL_NAME.format(i=completion_index, j=j), tool_name)
								if tool_args:
									safe_set_attribute(span, MessageAttributes.COMPLETION_TOOL_CALL_ARGUMENTS.format(i=completion_index, j=j), str(tool_args)[:500])
								safe_set_attribute(span, MessageAttributes.COMPLETION_TOOL_CALL_TYPE.format(i=completion_index, j=j), "function")
						completion_index += 1
		except Exception as e:
			logger.debug(f"Error extracting OpenAI message attributes: {e}")

	def _instrument(self, **kwargs):
		try:
			from xpander_sdk import Agent
		except ImportError:
			logger.debug("Xpander SDK not available")
			return
		try:
			# Tracer already set in CommonInstrumentor; attribute manager ready
			Agent.add_task = self._wrap_init_task(Agent.add_task)
			Agent.init_task = self._wrap_init_task(Agent.init_task)
			Agent.run_tools = self._wrap_run_tools(Agent.run_tools)
			Agent.add_messages = self._wrap_add_messages(Agent.add_messages)
			Agent.is_finished = self._wrap_is_finished(Agent.is_finished)
			Agent.extract_tool_calls = self._wrap_extract_tool_calls(Agent.extract_tool_calls)
			Agent.report_execution_metrics = self._wrap_report_execution_metrics(Agent.report_execution_metrics)
			Agent.retrieve_execution_result = self._wrap_retrieve_execution_result(Agent.retrieve_execution_result)
		except Exception as e:
			logger.error(f"Failed to instrument Xpander SDK: {e}")

	def _uninstrument(self, **kwargs):
		pass

	def _create_metrics(self, meter: Meter) -> StandardMetrics:
		return StandardMetrics(
			requests_active=meter.create_up_down_counter(
				name="xpander_requests_active",
				description="Number of active Xpander requests",
			),
			requests_duration=meter.create_histogram(
				name="xpander_requests_duration",
				description="Duration of Xpander requests",
				unit="s",
			),
			requests_total=meter.create_counter(
				name="xpander_requests_total",
				description="Total number of Xpander requests",
			),
			requests_error=meter.create_counter(
				name="xpander_requests_error",
				description="Number of Xpander request errors",
			),
		)

	# wrappers
	def _wrap_init_task(self, original_method):
		instrumentor = self

		def wrapper(self, execution=None, input=None, **kwargs):
			if execution is None and input is not None:
				if isinstance(input, str):
					execution = {"input": {"text": input}}
				else:
					execution = {"input": input}
			elif execution is None:
				execution = {}
			session_id = instrumentor._extract_session_id(execution)
			agent_name = getattr(self, "name", "unknown")
			agent_id = getattr(self, "id", "unknown")
			if instrumentor._context.get_session(session_id):
				return original_method(self, input=input, **kwargs) if input is not None else original_method(self, execution)
			task_input = None
			if isinstance(execution, dict) and "input" in execution:
				input_data = execution["input"]
				if isinstance(input_data, dict) and "text" in input_data:
					task_input = input_data["text"]
				elif isinstance(input_data, str):
					task_input = input_data
			conversation_span_attributes = {
				SpanAttributes.BAYFW_ENTITY_NAME: f"Session - {agent_name}",
				"xpander.span.type": "session",
				"xpander.session.name": f"Session - {agent_name}",
				"xpander.agent.name": agent_name,
				"xpander.agent.id": agent_id,
				"xpander.session.id": session_id,
			}
			from opentelemetry.trace import SpanKind as OTelSpanKind2
			session_span = self._tracer.start_span(f"session.{agent_name}", kind=OTelSpanKind2.INTERNAL, attributes=conversation_span_attributes)  # type: ignore[attr-defined]
			if task_input:
				safe_set_attribute(session_span, SpanAttributes.BAYFW_ENTITY_INPUT, str(task_input)[:1000])
				safe_set_attribute(session_span, "xpander.session.initial_input", str(task_input)[:500])
			workflow_span_attributes = {
				"xpander.span.type": "workflow",
				"xpander.workflow.phase": "planning",
				"xpander.agent.name": agent_name,
				"xpander.agent.id": agent_id,
				"xpander.session.id": session_id,
				"agent.name": agent_name,
				"agent.id": agent_id,
			}
			workflow_span = self._tracer.start_span(f"workflow.{agent_name}", kind=OTelSpanKind2.INTERNAL, attributes=workflow_span_attributes)  # type: ignore[attr-defined]
			agent_info = {
				"agent_name": agent_name,
				"agent_id": agent_id,
				"task_input": task_input,
				"thread_id": execution.get("memory_thread_id") if isinstance(execution, dict) else None,
			}
			instrumentor._context.start_session(session_id, agent_info, workflow_span, None)
			instrumentor._context.start_conversation(session_id, session_span)
			try:
				result = original_method(self, input=input, **kwargs) if input is not None else original_method(self, execution)
				return result
			except Exception as e:
				_finish_span_error(workflow_span, e)
				raise

		return wrapper

	def _wrap_run_tools(self, original_method):
		instrumentor = self

		def wrapper(self, tool_calls, payload_extension=None):
			session_id = instrumentor._get_session_id_from_agent(self)
			current_session = instrumentor._context.get_session(session_id) or {}
			step_num = current_session.get("step_count", 0) + 1
			instrumentor._context.update_session(session_id, {
				"step_count": step_num,
				"phase": "executing",
				"tools_executed": current_session.get("tools_executed", []) + [instrumentor._extract_tool_name(tc) for tc in tool_calls],
			})
			current_span = trace.get_current_span()
			execution_span_context = trace.set_span_in_context(current_span) if current_span else None
            with instrumentor._tracer.start_as_current_span(
				"xpander.execution",
				kind=OTelSpanKind.INTERNAL,
				context=execution_span_context,
				attributes={
                    SpanAttributes.BAYFW_SPAN_KIND: AgentBaySpanKindValues.TASK.value,
					"xpander.span.type": "execution",
					"xpander.workflow.phase": "executing",
					"xpander.step.number": step_num,
					"xpander.step.tool_count": len(tool_calls),
					"xpander.session.id": session_id,
				},
			) as execution_span:
				results = []
				for i, tool_call in enumerate(tool_calls):
					tool_name = instrumentor._extract_tool_name(tool_call)
					tool_params = instrumentor._extract_tool_params(tool_call)
					tool_span_context = trace.set_span_in_context(execution_span)
                    with instrumentor._tracer.start_as_current_span(
						f"tool.{tool_name}",
						kind=OTelSpanKind.CLIENT,
						context=tool_span_context,
						attributes={
                            SpanAttributes.BAYFW_SPAN_KIND: AgentBaySpanKindValues.TOOL.value,
							ToolAttributes.TOOL_NAME: tool_name,
							ToolAttributes.TOOL_PARAMETERS: str(tool_params)[:500],
							"xpander.span.type": "tool",
							"xpander.workflow.phase": "executing",
							"xpander.tool.step": step_num,
							"xpander.tool.index": i,
						},
					) as tool_span:
						single_result = original_method(self, [tool_call], payload_extension)
						results.extend(single_result)
						if single_result:
							result_content = ""
							for res in single_result:
								if isinstance(res, (str, int, float, bool)):
									result_content += str(res)[:1000] + "\n"
								elif hasattr(res, "__dict__"):
									result_dict = model_to_dict(res)
									result_content += safe_serialize(result_dict)[:1000] + "\n"
								else:
									result_content += safe_serialize(res)[:1000] + "\n"
							if result_content.strip():
								safe_set_attribute(tool_span, ToolAttributes.TOOL_RESULT, result_content.strip()[:2000])
				return results

		return wrapper

	def _wrap_add_messages(self, original_method):
		instrumentor = self

		def wrapper(self, messages):
			session_id = instrumentor._get_session_id_from_agent(self)
			current_session = instrumentor._context.get_session(session_id) or {}
			current_phase = instrumentor._context.get_workflow_phase(session_id)
			workflow_span = instrumentor._context.get_workflow_span(session_id)
			llm_span_context = trace.set_span_in_context(workflow_span) if workflow_span else None
			result = original_method(self, messages)
            with instrumentor._tracer.start_as_current_span(
				f"llm.{current_phase}",
				kind=OTelSpanKind.CLIENT,
				context=llm_span_context,
				attributes={
                    SpanAttributes.BAYFW_SPAN_KIND: AgentBaySpanKindValues.LLM.value,
					"xpander.span.type": "llm",
					"xpander.workflow.phase": current_phase,
					"xpander.session.id": session_id,
				},
			) as llm_span:
				instrumentor._extract_and_set_openai_message_attributes(llm_span, messages, result, self)
				llm_data = instrumentor._extract_llm_data_from_messages(result if result else messages)
				if llm_data:
					if "model" in llm_data:
						safe_set_attribute(llm_span, SpanAttributes.LLM_REQUEST_MODEL, llm_data["model"])
						safe_set_attribute(llm_span, SpanAttributes.LLM_RESPONSE_MODEL, llm_data["model"])
					if "usage" in llm_data:
						usage = llm_data["usage"]
						if "prompt_tokens" in usage:
							safe_set_attribute(llm_span, SpanAttributes.LLM_USAGE_PROMPT_TOKENS, usage["prompt_tokens"])
						if "completion_tokens" in usage:
							safe_set_attribute(llm_span, SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, usage["completion_tokens"])
						if "total_tokens" in usage:
							safe_set_attribute(llm_span, SpanAttributes.LLM_USAGE_TOTAL_TOKENS, usage["total_tokens"])
							instrumentor._context.update_session(session_id, {"total_tokens": current_session.get("total_tokens", 0) + usage["total_tokens"]})
			return result

		return wrapper

	def _wrap_is_finished(self, original_method):
		instrumentor = self

		def wrapper(self):
			result = original_method(self)
			if result:
				session_id = instrumentor._get_session_id_from_agent(self)
				instrumentor._context.update_session(session_id, {"phase": "finished", "end_time": time.time()})
			return result

		return wrapper

	def _wrap_extract_tool_calls(self, original_method):
		def wrapper(self, messages):
			return original_method(self, messages)
		return wrapper

	def _wrap_report_execution_metrics(self, original_method):
		def wrapper(self, llm_tokens=None, ai_model=None):
			return original_method(self, llm_tokens, ai_model)
		return wrapper

	def _wrap_retrieve_execution_result(self, original_method):
		instrumentor = self

		def wrapper(self):
			session_id = instrumentor._get_session_id_from_agent(self)
			current_session = instrumentor._context.get_session(session_id) or {}
			workflow_span = instrumentor._context.get_workflow_span(session_id)
			session_span = instrumentor._context.get_conversation_span(session_id)
			try:
				result = original_method(self)
				if workflow_span and current_session:
					safe_set_attribute(workflow_span, "xpander.workflow.total_steps", current_session.get("step_count", 0))
					safe_set_attribute(workflow_span, "xpander.workflow.total_tokens", current_session.get("total_tokens", 0))
					safe_set_attribute(workflow_span, "xpander.workflow.tools_used", len(current_session.get("tools_executed", [])))
					start_time = current_session.get("start_time", time.time())
					execution_time = time.time() - start_time
					safe_set_attribute(workflow_span, "xpander.workflow.execution_time", execution_time)
					safe_set_attribute(workflow_span, "xpander.workflow.phase", "completed")
				if result:
					result_content = ""
					if hasattr(result, "result"):
						result_content = str(result.result)[:1000]
					if session_span and result_content:
						safe_set_attribute(session_span, SpanAttributes.BAYFW_ENTITY_OUTPUT, result_content)
						safe_set_attribute(session_span, "xpander.session.final_result", result_content)
						if hasattr(result, "memory_thread_id"):
							safe_set_attribute(session_span, "xpander.session.thread_id", result.memory_thread_id)
					if workflow_span:
						if result_content:
							safe_set_attribute(workflow_span, "xpander.result.content", result_content)
						if hasattr(result, "memory_thread_id"):
							safe_set_attribute(workflow_span, "xpander.result.thread_id", result.memory_thread_id)
				if workflow_span:
					_finish_span_success(workflow_span)
					workflow_span.end()
				if session_span:
					_finish_span_success(session_span)
					session_span.end()
				return result
			except Exception as e:
				if workflow_span:
					_finish_span_error(workflow_span, e)
					workflow_span.end()
				if session_span:
					_finish_span_error(session_span, e)
					session_span.end()
				raise
			finally:
				instrumentor._context.end_session(session_id)

		return wrapper

