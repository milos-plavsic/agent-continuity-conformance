"""Small immutable data types shared by the package."""
from dataclasses import dataclass
from enum import StrEnum

class OperationState(StrEnum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    FENCED = "FENCED"
    PREPARED = "PREPARED"
    COMMITTED = "COMMITTED"
    RECONCILED = "RECONCILED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    INCONCLUSIVE = "INCONCLUSIVE"

@dataclass(frozen=True, slots=True)
class ProviderRecord:
    idempotency_key: str
    request_id: str
    status: str
    payload: str
