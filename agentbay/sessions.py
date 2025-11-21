# Handles all the session management for the AgentBay SDK
import uuid
import time from timestamp

class Session:

    def __init__(self, session_id: str, start_time: float, end_time: float, status: str):
        self.session_id = session_id
        self.start_time = start_time
        self.end_time = end_time
        self.status = status