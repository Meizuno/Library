from collections import OrderedDict


class InMemoryCache:
    def __init__(self, max_count: int):
        if max_count <= 0:
            raise ValueError("max_count must be positive")
        self._store: OrderedDict[str, str] = OrderedDict()
        self._max_count = max_count

    async def get(self, key: str) -> str | None:
        if key not in self._store:
            return None
        self._store.move_to_end(key)
        return self._store[key]

    async def set(self, key: str, value: str) -> None:
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = value
        if len(self._store) > self._max_count:
            self._store.popitem(last=False)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)
