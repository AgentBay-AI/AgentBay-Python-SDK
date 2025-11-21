import uuid
import time
from typing import Optional, Dict, Any, Union

class Span:
    """
    Represents a single unit of work (e.g., an LLM call, a tool execution).
    """
    def __init__(
        self, 
        session_id: str, 
        name: str, 
        input_data: Optional[Union[str, Dict[str, Any]]] = None
    ):
        self.span_id = str(uuid.uuid4())
        self.session_id = session_id
        self.name = name
        self.input = input_data
        self.output: Optional[Union[str, Dict[str, Any]]] = None
        
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.status = "active"  # active, success, error

    def end(self, output: Optional[Union[str, Dict[str, Any]]] = None, status: str = "success"):
        """
        Completes the span.
        """
        self.end_time = time.time()
        self.output = output
        self.status = status

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the span to a dictionary.
        """
        return {
            "id": self.span_id,
            "session_id": self.session_id,
            "name": self.name,
            "input": self.input,
            "output": self.output,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status
        }
