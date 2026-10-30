"""Service layer enforcing a serialized local admission and handover boundary."""
from __future__ import annotations
import threading
from .errors import ProviderUnavailable, ResponseLost
from .provider import DeterministicProvider
from .store import OperationStore

class ContinuityService:
    """Coordinate ownership, provider admission, and reconciliation.

    The per-operation lock protects one process only. Multi-process deployments
    require a shared linearizable gate or fencing enforced by a trusted gateway.
    """
    def __init__(self, store: OperationStore, provider: DeterministicProvider) -> None:
        self.store = store
        self.provider = provider
        self._locks: dict[str, threading.RLock] = {}
        self._locks_guard = threading.Lock()

    def _lock_for(self, operation_id: str) -> threading.RLock:
        with self._locks_guard:
            return self._locks.setdefault(operation_id, threading.RLock())

    def submit(self, operation_id: str, generation: int, *, lose_response: bool = False) -> dict[str,str]:
        with self._lock_for(operation_id):
            attempt = self.store.prepare_attempt(operation_id,generation)
            record = self.provider.admit(attempt["provider_key"],f"operation:{operation_id}")
            if lose_response:
                raise ResponseLost("Provider admitted the request; acknowledgement was lost")
            self.store.mark_committed(operation_id,generation,attempt["attempt_id"],record.request_id)
            return {"attempt_id":attempt["attempt_id"],"provider_request_id":record.request_id,
                    "provider_status":record.status}

    def handover(self, operation_id: str, generation: int) -> dict[str,object]:
        with self._lock_for(operation_id):
            return self.store.transfer(operation_id,generation)

    def reconcile(self, operation_id: str, generation: int) -> dict[str,object]:
        with self._lock_for(operation_id):
            self.store.assert_generation(operation_id,generation)
            try:
                record = self.provider.lookup(operation_id)
            except ProviderUnavailable:
                record = _UnknownProviderRecord()
            return self.store.reconcile(operation_id,generation,record)

class _UnknownProviderRecord:
    status = "unknown"
    request_id = None
