import pytest

from library.infrastructure import InMemoryCache


class TestInMemoryCache:
    async def test_get_missing_returns_none(self):
        cache = InMemoryCache(max_count=10)
        assert await cache.get("nope") is None

    async def test_set_then_get(self):
        cache = InMemoryCache(max_count=10)
        await cache.set("k", "v")
        assert await cache.get("k") == "v"

    async def test_overwrite_existing_key(self):
        cache = InMemoryCache(max_count=10)
        await cache.set("k", "v1")
        await cache.set("k", "v2")
        assert await cache.get("k") == "v2"

    async def test_delete_removes_key(self):
        cache = InMemoryCache(max_count=10)
        await cache.set("k", "v")
        await cache.delete("k")
        assert await cache.get("k") is None

    async def test_delete_missing_is_noop(self):
        cache = InMemoryCache(max_count=10)
        await cache.delete("nope")

    async def test_eviction_when_over_capacity(self):
        cache = InMemoryCache(max_count=2)
        await cache.set("a", "1")
        await cache.set("b", "2")
        await cache.set("c", "3")

        assert await cache.get("a") is None
        assert await cache.get("b") == "2"
        assert await cache.get("c") == "3"

    async def test_get_marks_as_recently_used(self):
        cache = InMemoryCache(max_count=2)
        await cache.set("a", "1")
        await cache.set("b", "2")

        await cache.get("a")
        await cache.set("c", "3")

        assert await cache.get("a") == "1"
        assert await cache.get("b") is None
        assert await cache.get("c") == "3"

    async def test_set_on_existing_key_refreshes_position(self):
        cache = InMemoryCache(max_count=2)
        await cache.set("a", "1")
        await cache.set("b", "2")

        await cache.set("a", "1-updated")
        await cache.set("c", "3")

        assert await cache.get("a") == "1-updated"
        assert await cache.get("b") is None
        assert await cache.get("c") == "3"

    @pytest.mark.parametrize("invalid", [0, -1, -100])
    def test_invalid_max_count_raises(self, invalid: int):
        with pytest.raises(ValueError):
            InMemoryCache(max_count=invalid)
