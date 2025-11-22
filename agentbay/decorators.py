import functools
from typing import Any, Callable
from .client import AgentBay
from .span import Span
# We need a way to get the current session. 
# For now, we will create a new session for each trace if one doesn't exist,
# OR we will just pass a "default-session" ID.
from .sessions import Session

def trace(func: Callable) -> Callable:
    """
    Decorator to track the execution of a function as a Span.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 1. Get the global client
        try:
            client = AgentBay.get_instance()
        except RuntimeError:
            # If SDK is not initialized, just run the function normally
            return func(*args, **kwargs)

        # 2. Prepare inputs
        input_data = {
            "args": args,
            "kwargs": kwargs
        }

        # 3. Start a Span
        # TODO: In a real real-world scenario, we would get the active session ID from a ContextVar.
        # For now, we will generate a temporary session ID or use a placeholder.
        session_id = "global-session" 
        
        span = Span(
            session_id=session_id,
            name=func.__name__,
            input_data=str(input_data) # Convert to string to be safe
        )

        try:
            # 4. Run the user's function
            result = func(*args, **kwargs)
            
            # 5. On success, end the span
            span.end(output=str(result), status="success")
            return result

        except Exception as e:
            # 6. On error, record failure and re-raise
            span.end(output=str(e), status="error")
            raise e
        
        finally:
            # 7. Send the span to the transport
            client.transport.send(span.to_dict())

    return wrapper

