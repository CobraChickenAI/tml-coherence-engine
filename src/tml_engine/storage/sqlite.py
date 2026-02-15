"""SQLite persistence for primitives, provenance, declarations, and interview sessions."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

_SCHEMA = """
-- Human identities (anchored to identity provider)
CREATE TABLE IF NOT EXISTS identities (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    title TEXT,
    department TEXT,
    workspace_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Extraction sessions
CREATE TABLE IF NOT EXISTS extractions (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_identifier TEXT NOT NULL,
    status TEXT DEFAULT 'in_progress',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- TML Primitives (polymorphic storage — all nine primitive types)
CREATE TABLE IF NOT EXISTS primitives (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    scope_id TEXT,
    identity_id TEXT REFERENCES identities(id),
    extraction_id TEXT REFERENCES extractions(id),
    data JSON NOT NULL,
    confirmation_status TEXT DEFAULT 'unconfirmed',
    confirmed_by TEXT,
    confirmed_at TIMESTAMP,
    original_data JSON,
    source TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Provenance (immutable, append-only)
CREATE TABLE IF NOT EXISTS provenance (
    id TEXT PRIMARY KEY,
    scope_id TEXT NOT NULL,
    primitive_id TEXT NOT NULL REFERENCES primitives(id),
    primitive_type TEXT NOT NULL,
    action TEXT NOT NULL,
    actor_identity_id TEXT NOT NULL REFERENCES identities(id),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details JSON,
    previous_state JSON
);

-- Declarations (versioned snapshots)
CREATE TABLE IF NOT EXISTS declarations (
    id TEXT PRIMARY KEY,
    version TEXT NOT NULL,
    scope_id TEXT NOT NULL,
    data JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completion_percentage REAL DEFAULT 0.0
);

-- Interview state (pause/resume)
CREATE TABLE IF NOT EXISTS interview_sessions (
    id TEXT PRIMARY KEY,
    identity_id TEXT REFERENCES identities(id),
    phase TEXT NOT NULL,
    conversation_history JSON,
    discovered_primitives JSON,
    status TEXT DEFAULT 'in_progress',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP
);
"""


class StorageEngine:
    """Async SQLite storage for the TML Coherence Engine."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Open connection and create schema."""
        self._db = await aiosqlite.connect(str(self.db_path))
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(_SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("StorageEngine not initialized — call initialize() first")
        return self._db

    # ----- Identities -----

    async def upsert_identity(
        self,
        *,
        identity_id: str,
        email: str,
        display_name: str,
        title: str | None = None,
        department: str | None = None,
        workspace_id: str | None = None,
    ) -> None:
        await self.db.execute(
            """INSERT INTO identities (id, email, display_name, title, department, workspace_id)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 email=excluded.email,
                 display_name=excluded.display_name,
                 title=excluded.title,
                 department=excluded.department,
                 workspace_id=excluded.workspace_id""",
            (identity_id, email, display_name, title, department, workspace_id),
        )
        await self.db.commit()

    async def get_identity(self, identity_id: str) -> dict | None:
        cursor = await self.db.execute("SELECT * FROM identities WHERE id = ?", (identity_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    # ----- Primitives -----

    async def store_primitive(
        self,
        *,
        primitive_id: str,
        primitive_type: str,
        scope_id: str | None,
        data: dict,
        source: str,
        identity_id: str | None = None,
        extraction_id: str | None = None,
    ) -> None:
        await self.db.execute(
            """INSERT INTO primitives (id, type, scope_id, identity_id, extraction_id, data, source)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 data=excluded.data,
                 updated_at=CURRENT_TIMESTAMP""",
            (
                primitive_id,
                primitive_type,
                scope_id,
                identity_id,
                extraction_id,
                json.dumps(data),
                source,
            ),
        )
        await self.db.commit()

    async def get_primitive(self, primitive_id: str) -> dict | None:
        cursor = await self.db.execute("SELECT * FROM primitives WHERE id = ?", (primitive_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def list_primitives(
        self,
        *,
        primitive_type: str | None = None,
        scope_id: str | None = None,
        confirmation_status: str | None = None,
    ) -> list[dict]:
        query = "SELECT * FROM primitives WHERE 1=1"
        params: list = []
        if primitive_type:
            query += " AND type = ?"
            params.append(primitive_type)
        if scope_id:
            query += " AND scope_id = ?"
            params.append(scope_id)
        if confirmation_status:
            query += " AND confirmation_status = ?"
            params.append(confirmation_status)
        query += " ORDER BY created_at"
        cursor = await self.db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def update_confirmation(
        self,
        primitive_id: str,
        *,
        status: str,
        confirmed_by: str,
        original_data: dict | None = None,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        await self.db.execute(
            """UPDATE primitives
               SET confirmation_status = ?,
                   confirmed_by = ?,
                   confirmed_at = ?,
                   original_data = ?,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (
                status,
                confirmed_by,
                now,
                json.dumps(original_data) if original_data else None,
                primitive_id,
            ),
        )
        await self.db.commit()

    # ----- Provenance -----

    async def append_provenance(
        self,
        *,
        provenance_id: str,
        scope_id: str,
        primitive_id: str,
        primitive_type: str,
        action: str,
        actor_identity_id: str,
        details: dict | None = None,
        previous_state: dict | None = None,
    ) -> None:
        await self.db.execute(
            """INSERT INTO provenance
               (id, scope_id, primitive_id, primitive_type, action, actor_identity_id, details, previous_state)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                provenance_id,
                scope_id,
                primitive_id,
                primitive_type,
                action,
                actor_identity_id,
                json.dumps(details) if details else None,
                json.dumps(previous_state) if previous_state else None,
            ),
        )
        await self.db.commit()

    async def get_provenance(
        self, primitive_id: str | None = None, scope_id: str | None = None
    ) -> list[dict]:
        query = "SELECT * FROM provenance WHERE 1=1"
        params: list = []
        if primitive_id:
            query += " AND primitive_id = ?"
            params.append(primitive_id)
        if scope_id:
            query += " AND scope_id = ?"
            params.append(scope_id)
        query += " ORDER BY timestamp"
        cursor = await self.db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    # ----- Extractions -----

    async def create_extraction(
        self, *, extraction_id: str, source_type: str, source_identifier: str
    ) -> None:
        await self.db.execute(
            "INSERT INTO extractions (id, source_type, source_identifier) VALUES (?, ?, ?)",
            (extraction_id, source_type, source_identifier),
        )
        await self.db.commit()

    async def complete_extraction(self, extraction_id: str) -> None:
        now = datetime.now(UTC).isoformat()
        await self.db.execute(
            "UPDATE extractions SET status = 'completed', completed_at = ? WHERE id = ?",
            (now, extraction_id),
        )
        await self.db.commit()

    # ----- Declarations -----

    async def store_declaration(
        self, *, declaration_id: str, version: str, scope_id: str, data: dict, completion: float
    ) -> None:
        await self.db.execute(
            """INSERT INTO declarations (id, version, scope_id, data, completion_percentage)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 data=excluded.data,
                 completion_percentage=excluded.completion_percentage""",
            (declaration_id, version, scope_id, json.dumps(data), completion),
        )
        await self.db.commit()

    async def get_declaration(self, declaration_id: str) -> dict | None:
        cursor = await self.db.execute("SELECT * FROM declarations WHERE id = ?", (declaration_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def list_declarations(self, scope_id: str | None = None) -> list[dict]:
        if scope_id:
            cursor = await self.db.execute(
                "SELECT * FROM declarations WHERE scope_id = ? ORDER BY created_at", (scope_id,)
            )
        else:
            cursor = await self.db.execute("SELECT * FROM declarations ORDER BY created_at")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    # ----- Interview Sessions -----

    async def create_interview_session(
        self, *, session_id: str, identity_id: str, phase: str
    ) -> None:
        await self.db.execute(
            """INSERT INTO interview_sessions (id, identity_id, phase, last_active_at)
               VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
            (session_id, identity_id, phase),
        )
        await self.db.commit()

    async def update_interview_session(
        self,
        session_id: str,
        *,
        phase: str | None = None,
        conversation_history: list | None = None,
        discovered_primitives: list | None = None,
        status: str | None = None,
    ) -> None:
        updates: list[str] = ["last_active_at = CURRENT_TIMESTAMP"]
        params: list = []
        if phase is not None:
            updates.append("phase = ?")
            params.append(phase)
        if conversation_history is not None:
            updates.append("conversation_history = ?")
            params.append(json.dumps(conversation_history))
        if discovered_primitives is not None:
            updates.append("discovered_primitives = ?")
            params.append(json.dumps(discovered_primitives))
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        params.append(session_id)
        await self.db.execute(
            f"UPDATE interview_sessions SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        await self.db.commit()

    async def get_interview_session(self, session_id: str) -> dict | None:
        cursor = await self.db.execute(
            "SELECT * FROM interview_sessions WHERE id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
