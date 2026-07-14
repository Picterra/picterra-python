import asyncio
import time

import pytest


@pytest.fixture(autouse=True)
def fast_sleep(monkeypatch):
    """Replace real sleeps with fast no-ops to keep tests quick and deterministic.

    This fixture is autouse so it applies to all tests. If a specific test
    requires real sleeping behavior, it can explicitly restore the original
    functions.
    """

    # Patch time.sleep to a no-op
    monkeypatch.setattr(time, "sleep", lambda s: None)

    # Patch asyncio.sleep to an async no-op
    async def _async_noop(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", _async_noop)

    yield
