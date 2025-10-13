


from datetime import datetime

class InteractionCounter:
    def __init__(self):
        self._count = 0
        self._start_time = None

    def increment(self):
        """Register a new interaction and update count."""
        if self._start_time is None:
            self._start_time = datetime.now()
        self._count += 1
        print(f"{self.frequency=}")

    @property
    def frequency(self):
        """
        Return average frequency since the first event:
        - per_minute
        - per_hour
        - per_day
        """
        if self._start_time is None or self._count == 0:
            return {"per_minute": 0, "per_hour": 0, "per_day": 0}

        elapsed = (datetime.now() - self._start_time).total_seconds()

        per_minute = self._count / (elapsed / 60) if elapsed >= 60 else self._count
        per_hour   = self._count / (elapsed / 3600) if elapsed >= 3600 else self._count
        per_day    = self._count / (elapsed / 86400) if elapsed >= 86400 else self._count

        return {
            "per_minute": per_minute,
            "per_hour": per_hour,
            "per_day": per_day,
        }
