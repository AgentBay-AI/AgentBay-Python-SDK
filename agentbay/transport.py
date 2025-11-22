import threading
import time
import queue
from typing import Dict, Any, List, Optional
from .config import Config

class Transport:
    """
    Handles asynchronous data transmission to the AgentBay backend.
    Uses a background thread to batch and send events.
    """
    def __init__(self, config: Config, batch_size: int = 10, flush_interval: float = 2.0):
        self.config = config
        self.queue: queue.Queue = queue.Queue()
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None

    def start(self):
        """
        Starts the background worker thread.
        """
        if self._worker_thread and self._worker_thread.is_alive():
            return

        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._worker_thread.start()

    def send(self, event: Dict[str, Any]):
        """
        Adds an event (Session or Span dict) to the queue.
        Non-blocking.
        """
        self.queue.put(event)

    def stop(self):
        """
        Stops the worker thread and flushes remaining events.
        """
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)

    def _flush_loop(self):
        """
        The main loop for the background thread.
        """
        while not self._stop_event.is_set():
            # TODO: In Step 2, we will implement the logic to 
            # read from self.queue and send via HTTP.
            time.sleep(0.1)
