from typing import Any, Dict, List
import functools
from agentbay.client import AgentBay
from agentbay.span import Span
from agentbay.sessions import Session

def instrument_chat(openai_module: Any):
    """
    Instruments the OpenAI Chat Completions API.
    """
    # We want to patch: openai.resources.chat.completions.Completions.create
    # Note: This path might vary slightly depending on OpenAI SDK version (v1.0+).
    # We assume the user passes the 'openai' library or we find the class.
    
    try:
        from openai.resources.chat.completions import Completions
    except ImportError:
        # User might be on an older version or different structure
        return

    # Save the original method so we don't lose it
    original_create = Completions.create

    @functools.wraps(original_create)
    def wrapped_create(self, *args, **kwargs):
        # 1. Check initialization
        try:
            client = AgentBay.get_instance()
        except RuntimeError:
            return original_create(self, *args, **kwargs)

        # 2. Prepare Span Data
        model = kwargs.get("model", "unknown")
        messages = kwargs.get("messages", [])
        
        # Start Span
        span = Span(
            session_id="openai-session", # TODO: Better session handling
            name=f"openai.chat.completions.create ({model})",
            input_data={"messages": messages, "model": model}
        )

        try:
            # 3. Call Original OpenAI Method
            response = original_create(self, *args, **kwargs)
            
            # 4. Extract Response Data
            # OpenAI v1 returns Pydantic models, so we can access attributes directly
            output_content = ""
            if response.choices:
                output_content = response.choices[0].message.content
            
            usage = {}
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }

            # 5. End Span Success
            span.end(
                output={"content": output_content, "usage": usage},
                status="success"
            )
            return response

        except Exception as e:
            # 6. End Span Error
            span.end(output=str(e), status="error")
            raise e
        
        finally:
            # 7. Send Data
            client.transport.send(span.to_dict())

    # Apply the patch
    Completions.create = wrapped_create
