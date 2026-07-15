# Architecture Decision Report — Graph Data Source

**Date:** 2026-07-15  
**Review scope:** `GET /api/v1/investigations/{id}/graph` data source  
**Status:** **Implemented** — Two-tier with fallback (Option 3)

---

## Finding: Graph Data Source

`GET /api/v1/investigations/{id}/graph` previously read **entirely from PostgreSQL**.

Neo4j was **written to but never read from**.

---

## Evidence Summary (as discovered)

| Evidence File | Line(s) | Finding |
|---------------|---------|---------|
| `app/services/investigation_service.py` | 436–467 | `get_graph()` queries `Entity` and `Relationship` tables via SQLAlchemy. No `neo4j_manager` import. |
| `app/graph/graph_sync.py` | 57–173 | `GraphSyncService.sync_investigation()` writes all data to Neo4j but nothing reads it back. |
| `app/graph/neo4j.py` | 34–72 | `Neo4jConnectionManager.initialize()` guards on `settings.NEO4J_ENABLED` (default `False`). |
| `app/core/config.py` | 161 | `NEO4J_ENABLED: bool = False` — disabled by default for development. |
| `app/api/v1/endpoints/investigations.py` | 258–275 | Two endpoints: `GET /graph` and `POST /graph/sync`. Neither queries Neo4j. `POST /graph/sync` writes to Neo4j then calls the same PostgreSQL `get_graph()`. |
| `ARCHITECTURE.md` | 139 | Sequence diagram shows `FA->>N4J: Sync graph` — Neo4j is a **sync target after PostgreSQL write**, not a query source. |
| `ARCHITECTURE.md` | 178–192 | Knowledge Graph Synchronization flowchart: Neo4j sync is a conditional step (`Neo4j Available?`). The `GET /graph` step shows no dependency on Neo4j. |
| `docs/database-optimization.md` | 28–29 | PostgreSQL indexes exist on `entities` and `relationships` tables for "graph lookups" and "graph traversal." |
| `docs/database-optimization.md` | 202–238 | Separate Neo4j optimization section with Cypher query patterns for graph traversal. |
| `README.md` | 56 | Claims "Neo4j-backed graph visualization." |

---

## Architectural Classification

**Classification: B — Unfinished implementation of a planned two-tier architecture.**

The architecture document describes a clear two-database pattern:

1. **PostgreSQL** = Source of truth (write model)
2. **Neo4j** = Optimized graph read model (secondary/index)

The write path from PostgreSQL → Neo4j is fully implemented: every entity/relationship CRUD operation calls `graph_sync.sync_investigation()`. The Neo4j sync uses efficient batch writes (`UNWIND` queries).

The read path was never wired to Neo4j. `get_graph()` reads from PostgreSQL only, reconstructing the graph in memory from relational rows. The `POST /graph/sync` endpoint further confirms this gap — it syncs Neo4j then calls `get_graph()` which returns PostgreSQL data, not Neo4j data.

---

## Resolution

**Phase 4 implemented Option 3 — Two-tier with fallback:**

1. A Neo4j read path was added to `get_graph()`: when `NEO4J_ENABLED=True` and Neo4j is healthy, graph queries use Cypher
2. PostgreSQL fallback when Neo4j is unavailable or disabled
3. Frontend graph page works with both backends
4. All existing sync behavior preserved unchanged

### Architecture after Phase 4

```
Entity/Relationship CRUD
  → PostgreSQL (write)
  → GraphSyncService → Neo4j (write, if enabled)
GET /graph
  → if NEO4J_ENABLED and Neo4j healthy → query Neo4j (Cypher)
  → else → fallback to PostgreSQL (SQLAlchemy)
```

This matches the architecture document's "Knowledge Graph Synchronization" flowchart.

---

## Tradeoff Analysis — Why Option 3 Was Chosen

### Option 1: Keep PostgreSQL as graph query engine (status quo)
| Pro | Con |
|-----|-----|
| Works without Neo4j | Neo4j synchronization is wasted writes |
| Simpler deployment | Graph queries limited to SQL joins |
| No sync latency | README claim "Neo4j-backed" is false |
| No operational overhead | Entity resolution across graphs would need SQL CTEs |

### Option 2: Switch graph read to Neo4j
| Pro | Con |
|-----|-----|
| Fulfills README "Neo4j-backed" claim | Requires Neo4j running |
| Native graph traversal (paths, shortest-path) | Sync lag between PostgreSQL and Neo4j |
| Better for large entity graphs | Additional operational cost |
| Entity resolution queries become trivial Cypher queries | Sync failure could serve stale data |

### Option 3: Two-tier with fallback ✅ (IMPLEMENTED)
| Pro | Con |
|-----|-----|
| Works without Neo4j | Two query paths to maintain |
| Uses Neo4j when available | Sync drift can produce inconsistent results |
| CQRS separation | More complex deployment |
| No wasted sync writes | Requires coordination between PG and Neo4j transactions |

---

## What Changed (Phase 4)

1. ✅ `get_graph()` attempts Neo4j first when `NEO4J_ENABLED=True`
2. ✅ Falls back to PostgreSQL if Neo4j is unavailable or disabled
3. ✅ Tests added for both code paths
4. ✅ Neo4j health check before serving graph data

## What Did NOT Change

- `GraphSyncService` — already correct
- `Neo4jConnectionManager` — already correct
- `POST /graph/sync` — already correct
- Entity/Relationship CRUD sync — already correct
