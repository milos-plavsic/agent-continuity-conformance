from __future__ import annotations
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from continuity_conformance import (
    ContinuityService, DeterministicProvider, InvalidTransition, OperationNotFound,
    OperationState, OperationStore, ResponseLost, StaleGeneration,
)

def activate(store: OperationStore, operation_id: str = "op-1") -> None:
    store.create_operation(operation_id,"test-payload")
    store.approve(operation_id)
    store.activate(operation_id)

def test_happy_path_reaches_verified(active_system):
    store,provider,service = active_system
    submitted = service.submit("op-1",1)
    assert submitted["provider_status"] == "pending"
    assert provider.lookup("op-1").payload == "test-payload"
    provider.complete("op-1")
    final = service.reconcile("op-1",1)
    assert final["state"] == OperationState.VERIFIED
    assert provider.effect_count == 1
    assert store.verify_event_chain()

def test_stale_generation_is_rejected_before_provider_admission(active_system):
    _,provider,service = active_system
    service.handover("op-1",1)
    with pytest.raises(StaleGeneration):
        service.submit("op-1",1)
    assert provider.admission_count == 0

def test_lost_response_is_reconciled_without_duplicate_effect(active_system):
    store,provider,service = active_system
    with pytest.raises(ResponseLost):
        service.submit("op-1",1,lose_response=True)
    assert store.get_operation("op-1")["state"] == OperationState.INCONCLUSIVE
    service.handover("op-1",1)
    provider.complete("op-1")
    final = service.reconcile("op-1",2)
    assert final["state"] == OperationState.VERIFIED
    assert provider.admission_count == 1
    assert provider.effect_count == 1

def test_delayed_provider_completion_after_handover(active_system):
    store,provider,service = active_system
    service.submit("op-1",1)
    service.handover("op-1",1)
    pending = service.reconcile("op-1",2)
    assert pending["state"] == OperationState.COMMITTED
    assert provider.effect_count == 0
    provider.complete("op-1")
    final = service.reconcile("op-1",2)
    assert final["state"] == OperationState.VERIFIED
    assert provider.effect_count == 1
    assert store.get_attempts("op-1")[0]["generation"] == 1

def test_provider_unavailability_preserves_inconclusive(active_system):
    _,provider,service = active_system
    service.submit("op-1",1)
    service.handover("op-1",1)
    provider.available = False
    final = service.reconcile("op-1",2)
    assert final["state"] == OperationState.INCONCLUSIVE
    with pytest.raises(InvalidTransition):
        service.submit("op-1",2)

def test_provider_idempotency_prevents_duplicate_admission(active_system):
    _,provider,_ = active_system
    first = provider.admit("op-1","same-payload")
    second = provider.admit("op-1","same-payload")
    assert first.request_id == second.request_id
    assert provider.admission_count == 1

def test_idempotency_key_cannot_be_reused_for_different_payload(active_system):
    _,provider,_ = active_system
    provider.admit("op-1","first-payload")
    with pytest.raises(ValueError,match="different payload"):
        provider.admit("op-1","different-payload")

def test_restart_recovers_durable_operation_and_attempt(tmp_path):
    database = tmp_path / "restart.sqlite3"
    store = OperationStore(database)
    provider = DeterministicProvider()
    service = ContinuityService(store,provider)
    activate(store)
    with pytest.raises(ResponseLost):
        service.submit("op-1",1,lose_response=True)
    restarted_store = OperationStore(database)
    restarted_service = ContinuityService(restarted_store,provider)
    restarted_service.handover("op-1",1)
    provider.complete("op-1")
    final = restarted_service.reconcile("op-1",2)
    assert final["state"] == OperationState.VERIFIED
    assert len(restarted_store.get_attempts("op-1")) == 1

def test_unknown_provider_outcome_is_not_marked_failed(active_system):
    _,provider,service = active_system
    with pytest.raises(ResponseLost):
        service.submit("op-1",1,lose_response=True)
    service.handover("op-1",1)
    provider.available = False
    final = service.reconcile("op-1",2)
    assert final["state"] == OperationState.INCONCLUSIVE
    assert final["state"] not in {OperationState.FAILED,OperationState.VERIFIED}

def test_generation_is_monotonic(active_system):
    _,_,service = active_system
    second = service.handover("op-1",1)
    third = service.handover("op-1",2)
    assert second["generation"] == 2
    assert third["generation"] == 3
    with pytest.raises(StaleGeneration):
        service.handover("op-1",1)

def test_invalid_lifecycle_transition_is_rejected(system):
    store,_,_ = system
    store.create_operation("op-2","payload")
    with pytest.raises(InvalidTransition):
        store.activate("op-2")

def test_terminal_operation_cannot_be_transferred(active_system):
    _,provider,service = active_system
    service.submit("op-1",1)
    provider.complete("op-1")
    service.reconcile("op-1",1)
    with pytest.raises(InvalidTransition):
        service.handover("op-1",1)

def test_event_chain_detects_modified_event(active_system):
    store,_,_ = active_system
    assert store.verify_event_chain()
    with sqlite3.connect(store.database) as db:
        db.execute("UPDATE events SET details_json=? WHERE sequence=1",('{"payload":"modified"}',))
    assert not store.verify_event_chain()

def test_event_chain_detects_deleted_middle_event(active_system):
    store,_,service = active_system
    service.handover("op-1",1)
    assert store.verify_event_chain()
    with sqlite3.connect(store.database) as db:
        db.execute("DELETE FROM events WHERE sequence=2")
    assert not store.verify_event_chain()

def test_two_operations_have_independent_idempotency_scopes(system):
    store,provider,service = system
    activate(store,"op-a")
    activate(store,"op-b")
    service.submit("op-a",1)
    service.submit("op-b",1)
    assert provider.admission_count == 2
    assert provider.lookup("op-a").request_id != provider.lookup("op-b").request_id

def test_reconciliation_with_no_provider_request_allows_safe_retry(active_system):
    store,provider,service = active_system
    service.handover("op-1",1)
    reconciled = service.reconcile("op-1",2)
    assert reconciled["state"] == OperationState.RECONCILED
    service.submit("op-1",2)
    assert provider.admission_count == 1
    assert len(store.get_attempts("op-1")) == 1

def test_reconciliation_is_rejected_for_stale_generation(active_system):
    _,_,service = active_system
    service.handover("op-1",1)
    with pytest.raises(StaleGeneration):
        service.reconcile("op-1",1)

def test_operation_creation_rejects_blank_identifier(system):
    store,_,_ = system
    with pytest.raises(ValueError):
        store.create_operation("  ","payload")

def test_missing_operation_is_reported(system):
    store,_,_ = system
    with pytest.raises(OperationNotFound):
        store.get_operation("missing")

def test_event_chain_spans_multiple_operations(system):
    store,_,_ = system
    activate(store,"first")
    activate(store,"second")
    assert store.verify_event_chain()

def test_provider_completion_is_idempotent(active_system):
    _,provider,_ = active_system
    provider.admit("op-1","payload")
    provider.complete("op-1")
    provider.complete("op-1")
    assert provider.effect_count == 1

def test_operation_generation_is_required_for_reconciliation(active_system):
    _,_,service = active_system
    with pytest.raises(StaleGeneration):
        service.reconcile("op-1",0)

def test_same_operation_id_cannot_be_created_twice(system):
    store,_,_ = system
    store.create_operation("duplicate","payload")
    with pytest.raises(sqlite3.IntegrityError):
        store.create_operation("duplicate","payload")

def test_second_service_instance_observes_fenced_generation(active_system):
    store,provider,service = active_system
    second_service = ContinuityService(store,provider)
    service.handover("op-1",1)
    with pytest.raises(StaleGeneration):
        second_service.submit("op-1",1)
    assert provider.admission_count == 0

def test_hash_chain_returns_false_for_malformed_event_json(active_system):
    store,_,_ = active_system
    with sqlite3.connect(store.database) as db:
        db.execute("UPDATE events SET details_json=? WHERE sequence=1",("{",))
    assert store.verify_event_chain() is False

def test_concurrent_handover_has_one_winner(active_system):
    store,_,service = active_system
    barrier = Barrier(2)
    def handover():
        barrier.wait()
        try:
            service.handover("op-1",1)
            return "transferred"
        except StaleGeneration:
            return "stale"
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: handover(), range(2)))
    assert sorted(outcomes) == ["stale","transferred"]
    assert store.get_operation("op-1")["generation"] == 2
