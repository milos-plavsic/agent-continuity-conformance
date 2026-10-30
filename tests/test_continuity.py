from __future__ import annotations

import sqlite3
import tempfile
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from continuity_conformance import (
    ContinuityService,
    DeterministicProvider,
    InvalidTransition,
    OperationNotFound,
    OperationState,
    OperationStore,
    ResponseLost,
    StaleGeneration,
)


def _execute_sql(database: str, statement: str, parameters: tuple = ()) -> None:
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(statement,parameters)
        connection.commit()


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
    _execute_sql(store.database,"UPDATE events SET details_json=? WHERE sequence=1",('{"payload":"modified"}',))
    assert not store.verify_event_chain()

def test_event_chain_detects_deleted_middle_event(active_system):
    store,_,service = active_system
    service.handover("op-1",1)
    assert store.verify_event_chain()
    _execute_sql(store.database,"DELETE FROM events WHERE sequence=2")
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
    _execute_sql(store.database,"UPDATE events SET details_json=? WHERE sequence=1",("{",))
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


def test_transfer_rejected_before_initial_activation(system):
    store,_,_ = system
    store.create_operation("unstarted","payload")
    with pytest.raises(InvalidTransition):
        store.transfer("unstarted",0)
    store.approve("unstarted")
    with pytest.raises(InvalidTransition):
        store.transfer("unstarted",0)
    assert store.get_operation("unstarted")["generation"] == 0
    assert store.get_operation("unstarted")["state"] == OperationState.APPROVED


def test_commit_requires_prepared_current_generation_attempt(active_system):
    store,_,_ = active_system
    attempt = store.prepare_attempt("op-1",1)
    with pytest.raises(ValueError,match="non-empty"):
        store.mark_committed("op-1",1,attempt["attempt_id"]," ")
    assert store.get_operation("op-1")["state"] == OperationState.PREPARED


def test_commit_rejects_attempt_already_advanced(active_system):
    store,_,_ = active_system
    attempt = store.prepare_attempt("op-1",1)
    _execute_sql(store.database,"UPDATE attempts SET status='admitted' WHERE attempt_id=?",(attempt["attempt_id"],))
    with pytest.raises(InvalidTransition,match="prepared attempt"):
        store.mark_committed("op-1",1,attempt["attempt_id"],"provider-0001")


def test_inconclusive_requires_prepared_attempt(active_system):
    store,_,_ = active_system
    attempt = store.prepare_attempt("op-1",1)
    _execute_sql(store.database,"UPDATE attempts SET generation=0 WHERE attempt_id=?",(attempt["attempt_id"],))
    with pytest.raises(InvalidTransition,match="prepared attempt"):
        store.mark_inconclusive("op-1",1,attempt["attempt_id"],"ambiguous")


def test_reconciliation_rejects_cross_operation_evidence(active_system):
    from continuity_conformance.models import ProviderRecord

    store,_,service = active_system
    service.submit("op-1",1)
    forged = ProviderRecord("another-operation","provider-9999","completed","test-payload")
    with pytest.raises(ValueError,match="different operation identity"):
        store.reconcile("op-1",1,forged)
    assert store.get_operation("op-1")["state"] == OperationState.COMMITTED


def test_reconciliation_rejects_payload_substitution(active_system):
    from continuity_conformance.models import ProviderRecord

    store,_,service = active_system
    service.submit("op-1",1)
    forged = ProviderRecord("op-1","provider-0001","completed","different-payload")
    with pytest.raises(ValueError,match="payload"):
        store.reconcile("op-1",1,forged)


def test_reconciliation_rejects_missing_provider_request_identity(active_system):
    from continuity_conformance.models import ProviderRecord

    store,_,service = active_system
    service.submit("op-1",1)
    malformed = ProviderRecord("op-1"," ","completed","test-payload")
    with pytest.raises(ValueError,match="request identity"):
        store.reconcile("op-1",1,malformed)


def test_reconciliation_rejects_conflicting_request_identity(active_system):
    from continuity_conformance.models import ProviderRecord

    store,_,service = active_system
    service.submit("op-1",1)
    conflicting = ProviderRecord("op-1","provider-other","completed","test-payload")
    with pytest.raises(ValueError,match="conflicts"):
        store.reconcile("op-1",1,conflicting)


def test_unknown_provider_status_remains_inconclusive(active_system):
    from continuity_conformance.models import ProviderRecord

    store,_,service = active_system
    service.submit("op-1",1)
    unknown = ProviderRecord("op-1","provider-0001","mystery","test-payload")
    final = store.reconcile("op-1",1,unknown)
    assert final["state"] == OperationState.INCONCLUSIVE


def test_provider_admission_then_local_commit_crash_is_recoverable(active_system, monkeypatch):
    store,provider,service = active_system

    def crash_before_commit(*args, **kwargs):
        raise RuntimeError("simulated process failure after provider admission")

    monkeypatch.setattr(store,"mark_committed",crash_before_commit)
    with pytest.raises(RuntimeError,match="simulated process failure"):
        service.submit("op-1",1)
    assert store.get_operation("op-1")["state"] == OperationState.PREPARED
    assert provider.admission_count == 1

    successor = ContinuityService(store,provider)
    successor.handover("op-1",1)
    provider.complete("op-1")
    final = successor.reconcile("op-1",2)
    assert final["state"] == OperationState.VERIFIED
    assert provider.admission_count == 1
    assert provider.effect_count == 1


def _transfer_in_separate_process(database: str, barrier) -> str:
    from continuity_conformance import OperationStore, StaleGeneration

    store = OperationStore(database)
    barrier.wait(timeout=15)
    try:
        store.transfer("op-1",1)
        return "transferred"
    except StaleGeneration:
        return "stale"


def test_concurrent_handover_across_processes_has_one_winner(tmp_path):
    import multiprocessing
    from concurrent.futures import ProcessPoolExecutor

    database = str(tmp_path / "multi-process.sqlite3")
    store = OperationStore(database)
    activate(store)
    context = multiprocessing.get_context("spawn")
    with context.Manager() as manager:
        barrier = manager.Barrier(2)
        with ProcessPoolExecutor(max_workers=2,mp_context=context) as pool:
            futures = [pool.submit(_transfer_in_separate_process,database,barrier) for _ in range(2)]
            outcomes = [future.result(timeout=30) for future in futures]
    assert sorted(outcomes) == ["stale","transferred"]
    assert OperationStore(database).get_operation("op-1")["generation"] == 2


def test_transfer_from_prepared_state_requires_successor_reconciliation(active_system):
    store,provider,service = active_system
    attempt = store.prepare_attempt("op-1",1)
    transferred = service.handover("op-1",1)
    assert transferred["state"] == OperationState.PREPARED
    assert transferred["generation"] == 2
    provider.admit(attempt["provider_key"],attempt["payload"])
    reconciled = service.reconcile("op-1",2)
    assert reconciled["state"] == OperationState.COMMITTED
    assert len(store.get_attempts("op-1")) == 1


def test_attempt_from_another_operation_cannot_be_committed(system):
    store,_,_ = system
    activate(store,"op-a")
    activate(store,"op-b")
    attempt_a = store.prepare_attempt("op-a",1)
    attempt_b = store.prepare_attempt("op-b",1)
    with pytest.raises(OperationNotFound):
        store.mark_committed("op-a",1,attempt_b["attempt_id"],"provider-0001")
    assert store.get_operation("op-a")["state"] == OperationState.PREPARED
    assert store.get_operation("op-b")["state"] == OperationState.PREPARED
    assert attempt_a["provider_key"] != attempt_b["provider_key"]


def test_malformed_unhashable_provider_status_is_inconclusive(active_system):
    from continuity_conformance.models import ProviderRecord

    store,_,service = active_system
    service.submit("op-1",1)
    malformed = ProviderRecord("op-1","provider-0001",[],"test-payload")
    final = store.reconcile("op-1",1,malformed)
    assert final["state"] == OperationState.INCONCLUSIVE


def test_provider_failure_evidence_is_bound_and_terminal(active_system):
    from continuity_conformance.models import ProviderRecord

    store,_,service = active_system
    service.submit("op-1",1)
    failed = ProviderRecord("op-1","provider-0001","failed","test-payload")
    final = store.reconcile("op-1",1,failed)
    assert final["state"] == OperationState.FAILED
    with pytest.raises(InvalidTransition):
        store.transfer("op-1",1)


def _exercise_generated_lifecycle_sequence(commands, database: Path) -> None:
    from continuity_conformance.models import ProviderRecord

    store = OperationStore(database)
    store.create_operation("generated","generated-payload")
    store.approve("generated")
    store.activate("generated")
    generation = 1
    attempt_id = None
    previous_version = 1

    for command in commands:
        try:
            if command == "transfer":
                store.transfer("generated",generation)
                generation += 1
            elif command == "stale_transfer":
                store.transfer("generated",generation-1)
            elif command == "prepare":
                attempt = store.prepare_attempt("generated",generation)
                attempt_id = attempt["attempt_id"]
            elif command == "commit" and attempt_id is not None:
                store.mark_committed("generated",generation,attempt_id,"provider-generated")
            elif command == "inconclusive" and attempt_id is not None:
                store.mark_inconclusive("generated",generation,attempt_id,"generated ambiguity")
            elif command.startswith("reconcile_"):
                status = command.removeprefix("reconcile_")
                if status == "absent":
                    record = None
                else:
                    record = ProviderRecord(
                        "generated","provider-generated" if status != "unknown" else "",
                        "mystery" if status == "unknown" else status,
                        "generated-payload",
                    )
                store.reconcile("generated",generation,record)
        except (InvalidTransition,StaleGeneration,ValueError,OperationNotFound):
            pass

        current = store.get_operation("generated")
        assert current["generation"] == generation
        assert current["version"] >= previous_version
        previous_version = current["version"]
        assert store.verify_event_chain()


@settings(max_examples=40,deadline=None)
@given(st.lists(st.sampled_from([
    "transfer","stale_transfer","prepare","commit","inconclusive",
    "reconcile_absent","reconcile_pending","reconcile_completed",
    "reconcile_failed","reconcile_unknown",
]),min_size=1,max_size=35))
def test_generated_lifecycle_sequences_preserve_invariants(commands):
    with tempfile.TemporaryDirectory() as directory:
        _exercise_generated_lifecycle_sequence(commands,Path(directory) / "generated.sqlite3")


def test_stale_pending_evidence_cannot_regress_verified_operation(active_system):
    store,provider,service = active_system
    service.submit("op-1",1)
    pending_evidence = provider.lookup("op-1")
    assert pending_evidence is not None
    store.reconcile("op-1",1,pending_evidence)
    provider.complete("op-1")
    verified = service.reconcile("op-1",1)
    assert verified["state"] == OperationState.VERIFIED
    with pytest.raises(InvalidTransition):
        store.reconcile("op-1",1,pending_evidence)
    assert store.get_operation("op-1")["state"] == OperationState.VERIFIED


def test_repeated_provider_lookup_with_conflicting_request_identity_is_rejected(active_system, monkeypatch):
    from continuity_conformance.models import ProviderRecord

    store,provider,service = active_system
    service.submit("op-1",1)
    monkeypatch.setattr(
        provider,
        "lookup",
        lambda key: ProviderRecord(key,"provider-conflict","completed","test-payload"),
    )
    with pytest.raises(ValueError,match="conflicts"):
        service.reconcile("op-1",1)
    assert store.get_operation("op-1")["state"] == OperationState.COMMITTED
