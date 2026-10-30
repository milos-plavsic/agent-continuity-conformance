from __future__ import annotations

import pytest

from continuity_conformance import ContinuityService, DeterministicProvider, OperationStore


@pytest.fixture
def system(tmp_path):
    store = OperationStore(tmp_path / "operations.sqlite3")
    provider = DeterministicProvider()
    service = ContinuityService(store,provider)
    return store,provider,service

@pytest.fixture
def active_system(system):
    store,provider,service = system
    store.create_operation("op-1","test-payload")
    store.approve("op-1")
    store.activate("op-1")
    return store,provider,service
