"""Deterministic provider simulator with explicit admission and completion."""
from __future__ import annotations
from dataclasses import dataclass
from .errors import ProviderUnavailable
from .models import ProviderRecord

@dataclass(slots=True)
class _StoredRequest:
    idempotency_key: str
    request_id: str
    payload: str
    status: str = "pending"

class DeterministicProvider:
    """Provider simulator deduplicating requests by stable idempotency key.

    Admission and completion are separate. Tests control completion explicitly,
    avoiding timing-dependent behaviour.
    """
    def __init__(self) -> None:
        self._requests: dict[str, _StoredRequest] = {}
        self._effect_keys: set[str] = set()
        self.available = True
        self.admission_count = 0

    def admit(self, idempotency_key: str, payload: str) -> ProviderRecord:
        self._require_available()
        existing = self._requests.get(idempotency_key)
        if existing is not None:
            if existing.payload != payload:
                raise ValueError("An idempotency key cannot be reused with a different payload")
            return self._as_record(existing)
        request = _StoredRequest(idempotency_key, f"provider-{len(self._requests)+1:04d}", payload)
        self._requests[idempotency_key] = request
        self.admission_count += 1
        return self._as_record(request)

    def lookup(self, idempotency_key: str) -> ProviderRecord | None:
        self._require_available()
        request = self._requests.get(idempotency_key)
        return None if request is None else self._as_record(request)

    def complete(self, idempotency_key: str) -> ProviderRecord:
        self._require_available()
        request = self._requests.get(idempotency_key)
        if request is None:
            raise KeyError(f"No admitted request for key {idempotency_key!r}")
        if request.status != "completed":
            request.status = "completed"
            self._effect_keys.add(idempotency_key)
        return self._as_record(request)

    @property
    def effect_count(self) -> int:
        """Number of distinct completed external effects."""
        return len(self._effect_keys)

    def _require_available(self) -> None:
        if not self.available:
            raise ProviderUnavailable("Provider status is temporarily unavailable")

    @staticmethod
    def _as_record(request: _StoredRequest) -> ProviderRecord:
        return ProviderRecord(request.idempotency_key, request.request_id, request.status, request.payload)
