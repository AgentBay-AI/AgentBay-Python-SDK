import time
import logging
from typing import Dict, Any
from contextlib import contextmanager

from opentelemetry.trace import SpanKind, get_current_span
from opentelemetry.metrics import Meter
from opentelemetry.instrumentation.utils import unwrap

from MYSDK.bay_frameworks.instrumentation.common import (
	CommonInstrumentor,
	InstrumentorConfig,
	StandardMetrics,
	create_wrapper_factory,
	create_span,
	SpanAttributeManager,
	safe_set_attribute,
	set_token_usage_attributes,
	TokenUsageExtractor,
)
from MYSDK.bay_frameworks.semconv import SpanAttributes, AgentBaySpanKindValues, ToolAttributes, MessageAttributes
from MYSDK.bay_frameworks.semconv.core import CoreAttributes


logger = logging.getLogger(__name__)

_instruments = ("crewai >= 0.70.0",)

_tool_executions_by_agent = {}


@contextmanager
def store_tool_execution():
	parent_span = get_current_span()
	parent_span_id = getattr(parent_span.get_span_context(), "span_id", None)
	if parent_span_id:
		if parent_span_id not in _tool_executions_by_agent:
			_tool_executions_by_agent[parent_span_id] = []
		tool_details = {}
		try:
			yield tool_details
			if tool_details:
				_tool_executions_by_agent[parent_span_id].append(tool_details)
		finally:
			pass
	else:
		yield {}


def attach_tool_executions_to_agent_span(span):
	span_id = getattr(span.get_span_context(), "span_id", None)
	if span_id and span_id in _tool_executions_by_agent:
		for idx, tool_execution in enumerate(_tool_executions_by_agent[span_id]):
			for key, value in tool_execution.items():
				if value is not None:
					span.set_attribute(f"crewai.agent.tool_execution.{idx}.{key}", str(value))
			del _tool_executions_by_agent[span_id]


class CrewaiInstrumentor(CommonInstrumentor):
	def __init__(self):
		config = InstrumentorConfig(
			library_name="crewai",
			library_version="0.0.0",
			wrapped_methods=[],
			metrics_enabled=True,
			dependencies=_instruments,
		)
		super().__init__(config)
		self._attribute_manager = None

	def _initialize(self, **kwargs):
		application_name = kwargs.get("application_name", "default_application")
		environment = kwargs.get("environment", "default_environment")
		self._attribute_manager = SpanAttributeManager(service_name=application_name, deployment_environment=environment)

	def _create_metrics(self, meter: Meter) -> Dict[str, Any]:
		return StandardMetrics.create_standard_metrics(meter)

	def _custom_wrap(self, **kwargs):
		from wrapt import wrap_function_wrapper
		attr_manager = self._attribute_manager
		wrap_function_wrapper(
			"crewai.crew",
			"Crew.kickoff",
			create_wrapper_factory(wrap_kickoff_impl, self._metrics, attr_manager)(self._tracer),
		)
		wrap_function_wrapper(
			"crewai.agent",
			"Agent.execute_task",
			create_wrapper_factory(wrap_agent_execute_task_impl, self._metrics, attr_manager)(self._tracer),
		)
		wrap_function_wrapper(
			"crewai.task",
			"Task.execute_sync",
			create_wrapper_factory(wrap_task_execute_impl, self._metrics, attr_manager)(self._tracer),
		)
		wrap_function_wrapper(
			"crewai.llm",
			"LLM.call",
			create_wrapper_factory(wrap_llm_call_impl, self._metrics, attr_manager)(self._tracer),
		)
		wrap_function_wrapper(
			"crewai.utilities.tool_utils",
			"execute_tool_and_check_finality",
			create_wrapper_factory(wrap_tool_execution_impl, self._metrics, attr_manager)(self._tracer),
		)
		wrap_function_wrapper(
			"crewai.tools.tool_usage",
			"ToolUsage.use",
			create_wrapper_factory(wrap_tool_usage_impl, self._metrics, attr_manager)(self._tracer),
		)

	def _custom_unwrap(self, **kwargs):
		unwrap("crewai.crew", "Crew.kickoff")
		unwrap("crewai.agent", "Agent.execute_task")
		unwrap("crewai.task", "Task.execute_sync")
		unwrap("crewai.llm", "LLM.call")
		unwrap("crewai.utilities.tool_utils", "execute_tool_and_check_finality")
		unwrap("crewai.tools.tool_usage", "ToolUsage.use")


def wrap_kickoff_impl(tracer, metrics, attr_manager, wrapped, instance, args, kwargs):
	attributes = {SpanAttributes.LLM_SYSTEM: "crewai"}
	span_name = "crewai.workflow"
	from MYSDK.bay_frameworks.semconv.core import CoreAttributes
	with create_span(tracer, span_name, kind=SpanKind.INTERNAL, attributes=attributes, attribute_manager=attr_manager) as span:
		result = wrapped(*args, **kwargs)
		return result


def wrap_agent_execute_task_impl(tracer, metrics, attr_manager, wrapped, instance, args, kwargs):
	agent_name = instance.role if hasattr(instance, "role") else "agent"
	with create_span(
		tracer,
		f"{agent_name}.agent",
		kind=SpanKind.CLIENT,
        attributes={SpanAttributes.BAYFW_SPAN_KIND: AgentBaySpanKindValues.AGENT.value},
		attribute_manager=attr_manager,
	) as span:
		result = wrapped(*args, **kwargs)
		attach_tool_executions_to_agent_span(span)
		return result


def wrap_task_execute_impl(tracer, metrics, attr_manager, wrapped, instance, args, kwargs):
	task_name = instance.description if hasattr(instance, "description") else "task"
	with create_span(
		tracer,
		f"{task_name}.task",
		kind=SpanKind.CLIENT,
        attributes={SpanAttributes.BAYFW_SPAN_KIND: AgentBaySpanKindValues.TASK.value},
		attribute_manager=attr_manager,
	) as span:
		result = wrapped(*args, **kwargs)
		return result


def wrap_llm_call_impl(tracer, metrics, attr_manager, wrapped, instance, args, kwargs):
	llm = instance.model if hasattr(instance, "model") else "llm"
	start_time = time.time()
	with create_span(tracer, f"{llm}.llm", kind=SpanKind.CLIENT, attribute_manager=attr_manager) as span:
		result = wrapped(*args, **kwargs)
		if metrics.get("duration_histogram"):
			duration = time.time() - start_time
			metrics["duration_histogram"].record(duration, attributes={SpanAttributes.LLM_SYSTEM: "crewai"})
		return result


def wrap_tool_execution_impl(tracer, metrics, attr_manager, wrapped, instance, args, kwargs):
	agent_action = args[0] if args else None
	tools = args[1] if len(args) > 1 else []
	if not agent_action:
		return wrapped(*args, **kwargs)
	tool_name = getattr(agent_action, "tool", "unknown_tool")
	tool_input = getattr(agent_action, "tool_input", "")
	with store_tool_execution() as tool_details:
		tool_details["name"] = tool_name
		tool_details["parameters"] = str(tool_input)
		start_time = time.time()
		with create_span(
			tracer,
			f"{tool_name}.tool",
			kind=SpanKind.CLIENT,
            attributes={
                SpanAttributes.BAYFW_SPAN_KIND: AgentBaySpanKindValues.TOOL.value,
                ToolAttributes.TOOL_NAME: tool_name,
                ToolAttributes.TOOL_PARAMETERS: str(tool_input),
            },
			attribute_manager=attr_manager,
		) as span:
			result = wrapped(*args, **kwargs)
			if metrics.get("duration_histogram"):
				duration = time.time() - start_time
				metrics["duration_histogram"].record(
					duration,
					attributes={SpanAttributes.LLM_SYSTEM: "crewai", ToolAttributes.TOOL_NAME: tool_name},
				)
			return result


def wrap_tool_usage_impl(tracer, metrics, attr_manager, wrapped, instance, args, kwargs):
	calling = args[0] if args else None
	if not calling:
		return wrapped(*args, **kwargs)
	tool_name = getattr(calling, "tool_name", "unknown_tool")
	with store_tool_execution() as tool_details:
		tool_details["name"] = tool_name
		with create_span(
			tracer,
			f"{tool_name}.tool_usage",
			kind=SpanKind.INTERNAL,
			attributes={SpanAttributes.BAYFW_SPAN_KIND: "tool.usage", ToolAttributes.TOOL_NAME: tool_name},
			attribute_manager=attr_manager,
		) as span:
			result = wrapped(*args, **kwargs)
			return result


