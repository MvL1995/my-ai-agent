import time


class SearchCache:
    def __init__(
        self,
        ttl_seconds=300,
        clock=None
    ):
        self.ttl_seconds = ttl_seconds
        self.clock = clock or time.monotonic
        self.entries = {}

    def normalize_query(self, query):
        return query.strip().casefold()

    def get(self, query):
        key = self.normalize_query(query)
        entry = self.entries.get(key)

        if entry is None:
            return None

        created_at, message = entry

        if self.clock() - created_at >= self.ttl_seconds:
            self.entries.pop(key, None)
            return None

        return message

    def set(self, query, message):
        key = self.normalize_query(query)
        self.entries[key] = (
            self.clock(),
            message,
        )
