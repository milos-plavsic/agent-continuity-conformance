"""Executable delayed-response recovery demonstration."""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from .errors import ResponseLost
from .provider import DeterministicProvider
from .service import ContinuityService
from .store import OperationStore


def run_demo(database: str | Path) -> dict[str,object]:
    store = OperationStore(database)
    provider = DeterministicProvider()
    service = ContinuityService(store,provider)
    store.create_operation("payment-2048","settle-invoice-2048")
    store.approve("payment-2048")
    store.activate("payment-2048")
    try:
        service.submit("payment-2048",1,lose_response=True)
    except ResponseLost:
        pass
    service.handover("payment-2048",1)
    provider.complete("payment-2048")
    final = service.reconcile("payment-2048",2)
    return {"operation_id":final["operation_id"],"generation":final["generation"],
            "state":final["state"],"provider_admissions":provider.admission_count,
            "provider_effects":provider.effect_count,"event_chain_valid":store.verify_event_chain(),
            "events":[{"sequence":e["sequence"],"generation":e["generation"],
                       "type":e["event_type"]} for e in store.events("payment-2048")]}

def main() -> None:
    parser = argparse.ArgumentParser(description="Demonstrate safe operation recovery.")
    parser.add_argument("--database",help="SQLite path; defaults to a temporary database")
    args = parser.parse_args()
    if args.database:
        result = run_demo(args.database)
    else:
        with tempfile.TemporaryDirectory() as directory:
            result = run_demo(Path(directory)/"continuity.sqlite3")
    print(json.dumps(result,indent=2))

if __name__ == "__main__":
    main()
