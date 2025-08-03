import threading
from datetime import datetime

MAX_LOGS = 1000


class LogStore:
    def __init__(self):
        self.logs = []
        self.lock = threading.Lock()
        self.error_count = 0

    def add(self, level: str, message: str):
        if level == "ERROR":
            self.error_count += 1
        if len(self.logs) >= MAX_LOGS:
            with self.lock:
                self.logs.pop(0)
        with self.lock:
            self.logs.append(
                {
                    "level": level,
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            )

    def get_all(self):
        with self.lock:
            return list(self.logs)

    def get_errors(self):
        with self.lock:
            return [log for log in self.logs if log["level"] == "ERROR"]

    def last_error(self):
        with self.lock:
            for log in reversed(self.logs):
                if log["level"] == "ERROR":
                    return log
            return None


log_store = LogStore()
