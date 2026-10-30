"""SQLite operation registry with generation checks and a chained event log."""
from __future__ import annotations
import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .errors import InvalidTransition, OperationNotFound, StaleGeneration
from .models import OperationState, ProviderRecord

def _canonical(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

class OperationStore:
    """Durable registry. Production deployments must validate their own DB guarantees."""
    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        if self.database != ":memory:":
            Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=10, isolation_level="DEFERRED")
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute("PRAGMA journal_mode = WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS operations (
                    operation_id TEXT PRIMARY KEY, generation INTEGER NOT NULL,
                    state TEXT NOT NULL, payload TEXT NOT NULL, provider_key TEXT NOT NULL,
                    provider_request_id TEXT, version INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS attempts (
                    attempt_id TEXT PRIMARY KEY, operation_id TEXT NOT NULL REFERENCES operations(operation_id),
                    generation INTEGER NOT NULL, provider_key TEXT NOT NULL,
                    provider_request_id TEXT, status TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS attempts_operation_idx ON attempts(operation_id, generation);
                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, operation_id TEXT NOT NULL,
                    generation INTEGER NOT NULL, event_type TEXT NOT NULL, details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL, previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL
                );
            """)

    def _append_event(self, db: sqlite3.Connection, operation_id: str, generation: int,
                      event_type: str, details: dict[str, Any]) -> None:
        previous = db.execute("SELECT event_hash FROM events ORDER BY sequence DESC LIMIT 1").fetchone()
        previous_hash = "0" * 64 if previous is None else str(previous["event_hash"])
        created_at = datetime.now(timezone.utc).isoformat()
        body = {"operation_id": operation_id, "generation": generation, "event_type": event_type,
                "details": details, "created_at": created_at, "previous_hash": previous_hash}
        digest = hashlib.sha256(_canonical(body).encode()).hexdigest()
        db.execute("""INSERT INTO events(operation_id,generation,event_type,details_json,created_at,
                   previous_hash,event_hash) VALUES(?,?,?,?,?,?,?)""",
                   (operation_id,generation,event_type,_canonical(details),created_at,previous_hash,digest))

    def create_operation(self, operation_id: str, payload: str) -> dict[str, Any]:
        if not operation_id.strip():
            raise ValueError("operation_id must not be empty")
        with self._connect() as db:
            db.execute("INSERT INTO operations(operation_id,generation,state,payload,provider_key) VALUES(?,0,?,?,?)",
                       (operation_id,OperationState.PROPOSED.value,payload,operation_id))
            self._append_event(db,operation_id,0,"OPERATION_PROPOSED",{"payload":payload})
        return self.get_operation(operation_id)

    def approve(self, operation_id: str) -> dict[str, Any]:
        with self._connect() as db:
            row = self._require(db,operation_id)
            if row["state"] != OperationState.PROPOSED.value:
                raise InvalidTransition(f"Cannot approve operation in {row['state']} state")
            db.execute("UPDATE operations SET state=?,version=version+1 WHERE operation_id=?",
                       (OperationState.APPROVED.value,operation_id))
            self._append_event(db,operation_id,0,"OPERATION_APPROVED",{})
        return self.get_operation(operation_id)

    def activate(self, operation_id: str) -> dict[str, Any]:
        with self._connect() as db:
            row = self._require(db,operation_id)
            if row["state"] != OperationState.APPROVED.value:
                raise InvalidTransition(f"Cannot activate operation in {row['state']} state")
            db.execute("UPDATE operations SET generation=1,state=?,version=version+1 WHERE operation_id=? AND generation=0",
                       (OperationState.FENCED.value,operation_id))
            self._append_event(db,operation_id,1,"GENERATION_ACTIVATED",{})
        return self.get_operation(operation_id)

    def assert_generation(self, operation_id: str, generation: int) -> dict[str, Any]:
        with self._connect() as db:
            row = self._require(db,operation_id)
            self._check_generation(row,generation)
            return dict(row)

    def prepare_attempt(self, operation_id: str, generation: int) -> dict[str, Any]:
        with self._connect() as db:
            row = self._require(db,operation_id)
            self._check_generation(row,generation)
            if row["state"] not in {OperationState.FENCED.value,OperationState.RECONCILED.value}:
                raise InvalidTransition(f"Cannot prepare an attempt in {row['state']} state")
            attempt_id = str(uuid.uuid4())
            db.execute("INSERT INTO attempts(attempt_id,operation_id,generation,provider_key,status) VALUES(?,?,?,?,?)",
                       (attempt_id,operation_id,generation,row["provider_key"],"prepared"))
            db.execute("UPDATE operations SET state=?,version=version+1 WHERE operation_id=?",
                       (OperationState.PREPARED.value,operation_id))
            self._append_event(db,operation_id,generation,"ATTEMPT_PREPARED",
                               {"attempt_id":attempt_id,"provider_key":row["provider_key"]})
        return {"attempt_id":attempt_id,"provider_key":row["provider_key"],"generation":generation}

    def mark_committed(self, operation_id: str, generation: int, attempt_id: str,
                       request_id: str) -> dict[str, Any]:
        with self._connect() as db:
            row = self._require(db,operation_id)
            self._check_generation(row,generation)
            attempt = db.execute("SELECT * FROM attempts WHERE attempt_id=? AND operation_id=?",
                                 (attempt_id,operation_id)).fetchone()
            if attempt is None:
                raise OperationNotFound(f"Attempt {attempt_id!r} does not exist")
            db.execute("UPDATE attempts SET provider_request_id=?,status='admitted' WHERE attempt_id=?",
                       (request_id,attempt_id))
            db.execute("UPDATE operations SET state=?,provider_request_id=?,version=version+1 WHERE operation_id=?",
                       (OperationState.COMMITTED.value,request_id,operation_id))
            self._append_event(db,operation_id,generation,"PROVIDER_ADMITTED",
                               {"attempt_id":attempt_id,"provider_request_id":request_id})
        return self.get_operation(operation_id)

    def transfer(self, operation_id: str, generation: int) -> dict[str, Any]:
        with self._connect() as db:
            row = self._require(db,operation_id)
            self._check_generation(row,generation)
            if row["state"] in {OperationState.VERIFIED.value,OperationState.FAILED.value}:
                raise InvalidTransition(f"Cannot transfer a terminal operation in {row['state']}")
            next_generation = generation + 1
            db.execute("UPDATE operations SET generation=?,version=version+1 WHERE operation_id=? AND generation=?",
                       (next_generation,operation_id,generation))
            self._append_event(db,operation_id,next_generation,"OWNERSHIP_TRANSFERRED",
                               {"previous_generation":generation})
        return self.get_operation(operation_id)

    def reconcile(self, operation_id: str, generation: int,
                  record: ProviderRecord | None) -> dict[str, Any]:
        with self._connect() as db:
            row = self._require(db,operation_id)
            self._check_generation(row,generation)
            if record is None:
                state,status,request_id = OperationState.RECONCILED,"not_found",None
            elif record.status == "completed":
                state,status,request_id = OperationState.VERIFIED,"completed",record.request_id
            elif record.status == "pending":
                state,status,request_id = OperationState.COMMITTED,"admitted",record.request_id
            elif record.status == "failed":
                state,status,request_id = OperationState.FAILED,"failed",record.request_id
            else:
                state,status,request_id = OperationState.INCONCLUSIVE,"unknown",getattr(record,"request_id",None)
            db.execute("""UPDATE operations SET state=?,provider_request_id=COALESCE(?,provider_request_id),
                       version=version+1 WHERE operation_id=?""",(state.value,request_id,operation_id))
            db.execute("""UPDATE attempts SET status=?,provider_request_id=COALESCE(?,provider_request_id)
                       WHERE operation_id=? AND provider_key=?""",
                       (status,request_id,operation_id,row["provider_key"]))
            self._append_event(db,operation_id,generation,"RECONCILIATION_COMPLETED",
                               {"provider_status":status,"provider_request_id":request_id,
                                "resulting_state":state.value})
        return self.get_operation(operation_id)

    def get_operation(self, operation_id: str) -> dict[str, Any]:
        with self._connect() as db:
            return dict(self._require(db,operation_id))

    def get_attempts(self, operation_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            self._require(db,operation_id)
            return [dict(row) for row in db.execute(
                "SELECT * FROM attempts WHERE operation_id=? ORDER BY rowid",(operation_id,)).fetchall()]

    def events(self, operation_id: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as db:
            query = "SELECT * FROM events ORDER BY sequence" if operation_id is None else                     "SELECT * FROM events WHERE operation_id=? ORDER BY sequence"
            rows = db.execute(query) .fetchall() if operation_id is None else                    db.execute(query,(operation_id,)).fetchall()
            return [dict(row) for row in rows]

    def verify_event_chain(self) -> bool:
        """Detect modifications relative to the retained SHA-256 event chain."""
        previous = "0" * 64
        with self._connect() as db:
            rows = db.execute("SELECT * FROM events ORDER BY sequence").fetchall()
            for row in rows:
                if row["previous_hash"] != previous:
                    return False
                body = {"operation_id":row["operation_id"],"generation":row["generation"],
                        "event_type":row["event_type"],"details":json.loads(row["details_json"]),
                        "created_at":row["created_at"],"previous_hash":row["previous_hash"]}
                digest = hashlib.sha256(_canonical(body).encode()).hexdigest()
                if digest != row["event_hash"]:
                    return False
                previous = digest
        return True

    @staticmethod
    def _require(db: sqlite3.Connection, operation_id: str) -> sqlite3.Row:
        row = db.execute("SELECT * FROM operations WHERE operation_id=?",(operation_id,)).fetchone()
        if row is None:
            raise OperationNotFound(f"Operation {operation_id!r} does not exist")
        return row

    @staticmethod
    def _check_generation(row: sqlite3.Row, generation: int) -> None:
        if row["generation"] != generation:
            raise StaleGeneration(f"Generation {generation} is stale; current generation is {row['generation']}")
