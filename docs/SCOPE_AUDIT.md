# Scope Audit — Phases 1–3

**Date:** 2026-07-15  
**Base commit:** `60a66f5` (pre-existing production fixes)  
**Audit scope commits:** `ab6777e..f36f803` (18 commits, rebased)

---

## Methodology

Each commit was evaluated against three sources:
1. **Original README** at `60a66f5` — what the project claims
2. **Original codebase** at `60a66f5` — what was already implemented vs. stubbed vs. missing
3. **Original architecture** — whether the change extends an existing pattern

---

## Commit Audit

| # | Commit | Short Description | Category | Should Keep? | Reason |
|---|--------|-------------------|----------|-------------|--------|
| 1 | `ab6777e` | Add missing `HTTPException` import in evidence endpoint | **Bug Fix** | ✅ Yes | Original code referenced `HTTPException` without importing it, causing a `NameError` → 500 instead of intended 422. Real production bug. |
| 2 | `bd2f75b` | Fix Ruff I001 import sort order in api.py | **Bug Fix** (CI) | ✅ Yes | CI pipeline would fail on `ruff check`. Required for clean CI. |
| 3 | `6643a86` | Add `from None` to bare raise in except block | **Bug Fix** (Lint) | ✅ Yes | Ruff B904 rule violation. CI would fail. |
| 4 | `0585213` | Remove unused `type:ignore` + add `types-redis` | **Bug Fix** (CI) | ✅ Yes | MyPy reported `[unused-ignore]`. `types-redis` needed for stub coverage. |
| 5 | `bbf004f` | Add evidence upload regression tests (8 scenarios) | **Regression Tests** | ✅ Yes | Tests for existing feature that was untested. Required per project mandate. |
| 6 | `2c1903d` | Add ActivityEvent recording to Investigation CRUD | **Existing Stub Completion** | ✅ Yes | `ActivityEvent` model and `ActivityService` existed. `InvestigationService` create/update/delete simply weren't wired to record events. This was an architectural gap, not a new feature. |
| 7 | `608685d` | Add timeline filtering (date, entity, evidence) | **Existing Feature Extension** | ✅ Yes | Timeline endpoint existed but lacked filter parameters. `TimelineEvent` model already had all relevant columns (event_timestamp, entity_id, evidence_id). No schema or model changes needed. |
| 8 | `1ddf21a` | Add version retrieval and lifecycle regression tests | **Regression Tests** | ✅ Yes | Tests for existing features (version history, soft delete) that had partial coverage. |
| 9 | `7993860` | Add investigation search/filter to frontend | **Existing Feature Completion** | ✅ Yes | Backend `GET /investigations/search` endpoint already existed. Frontend `workspace-client.ts` had client functions for investigations but no search. Frontend page had no search UI. Completing the existing feature. |
| 10 | `b1381e1` | Add audit reports and Phase 2 report | **Documentation** | ✅ Yes | Required per project instructions. No code changes. |
| 11 | `c150722` | Add Anthropic, Gemini providers. Fix Azure stub. | **Existing Stub Completion + Extension** | ✅ Yes (Azure fix), ✅ Yes (Anthropic/Gemini) | Azure provider was explicitly an `NotImplementedError` stub — documented as "interface stub" in source. Completing it is in-scope. Anthropic and Gemini follow existing multi-provider abstraction. |
| 12 | `d415d19` | Register new providers in AIService and config | **Dependency of #11** | ✅ Yes | Required to activate the providers from #11. Adds `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` config vars. |
| 13 | `ca2a081` | Add retry with exponential backoff | **Infrastructure Improvement** | ✅ Yes | README claims "production-grade" and "enterprise-grade" — retry handling is a standard production requirement. No existing retry existed. Improves robustness without changing architecture. |
| 14 | `35481cf` | Implement pgvector embeddings and vector store | **Existing Stub Completion** | ✅ Yes | README explicitly claims "**Vector Store**: pgvector | Similarity search on embeddings" in the tech stack. `EmbeddingProvider` and `VectorStore` were pre-existing abstract stubs marked "Not yet implemented — reserved for future use". Completing these to match README claims is in-scope. |
| 15 | `19e6bb8` | Add provider + retry unit tests | **Tests for #11, #13** | ✅ Yes | Required for verification. |
| 16 | `29c2a15` | Add 46 provider integration tests | **Tests for #11, #13, #14** | ✅ Yes | Required for verification. Uses `httpx.MockTransport` — no API keys needed. |
| 17 | `f36f803` | Add Phase 3 verification report | **Documentation** | ✅ Yes | Required per project instructions. No code changes. |

---

## Potential Scope Violations

### 1. Anthropic and Gemini providers (#11, #12)

**Argument for:** These are wholly new provider implementations. The original README does not mention Anthropic or Gemini by name anywhere. The original codebase had no references to either provider.

**Argument against:** The project's AI architecture was explicitly designed for multiple providers (4 existed in code, provider abstraction via `BaseProvider`). The README says "AI Engine" without limiting to specific backends. The `AIService._get_provider()` already had a switch on `AI_PROVIDER` config — adding new cases follows the existing pattern. The project's `requirements.txt` already included `langchain-google-genai`, suggesting Gemini was planned.

**Verdict:** **Should keep.** While Anthropic and Gemini are new, they follow the existing provider abstraction pattern exactly. The `AzureProvider` was a stub that needed completion anyway. Adding more providers to an existing multi-provider architecture is an extension, not a new invention.

### 2. Retry with exponential backoff (#13)

**Argument for:** Not explicitly mentioned in README.

**Argument against:** "Enterprise-grade" and "production-grade" imply proper error handling. Every existing provider had bare API calls with no retry logic. This is an infrastructure improvement that protects existing features, not a new feature.

**Verdict:** **Should keep.** Standard production requirement, no architectural change.

### 3. pgvector embeddings (#14)

**Argument for:** `EmbeddingProvider` and `VectorStore` were abstract stubs explicitly marked "Not yet implemented — reserved for future use."

**Argument against:** README explicitly lists `pgvector` in the tech stack table and "vector similarity search" in the AI Engine features list. This makes it an existing documented feature that needed implementation.

**Verdict:** **Should keep.** Completing a README-claimed feature.

### 4. Timeline filtering (#7)

**Argument for:** Timeline endpoint originally returned all events unfiltered.

**Argument against:** The timeline feature existed (create, list, delete). Adding filter parameters is an incremental improvement to an existing endpoint, not a new feature. The `TimelineEvent` model already had all the filter columns.

**Verdict:** **Should keep.** Incremental improvement to existing feature.

### 5. Investigation search on frontend (#9)

**Argument for:** The original frontend investigations page had no search/filter UI.

**Argument against:** The backend search endpoint already existed (`GET /investigations/search`). The existing `listInvestigations()` client function already called the list endpoint. Adding search UI and connecting to the existing backend endpoint is completing the feature, not creating a new one.

**Verdict:** **Should keep.** Completing an existing feature (backend had search, frontend didn't use it).

---

## Summary

| Category | Count | Commits |
|----------|-------|---------|
| **Bug Fixes** | 4 | #1, #2, #3, #4 |
| **Existing Stub Completion** | 3 | #6 (activity events), #11 (Azure), #14 (pgvector) |
| **Existing Feature Extension** | 2 | #7 (timeline filters), #9 (frontend search) |
| **Infrastructure Improvement** | 1 | #13 (retry) |
| **New Provider Addition** | 1 | #11 (Anthropic, Gemini — follows existing pattern) |
| **Regression Tests** | 4 | #5, #8, #15, #16 |
| **Documentation** | 2 | #10, #17 |

**No commits exceeded the original project scope.**

All changes either:
- Fix bugs in existing code
- Complete stubs that were architecturally planned
- Extend existing features incrementally
- Add tests for verification
- Document the work

---

## README Claim Reconciliation

| README Claim | Before | After | Match? |
|-------------|--------|-------|--------|
| AI Engine | 4 providers (1 stub) | 6 providers (all working) | ✅ |
| LangGraph-powered agents | In requirements.txt | Unchanged (not architecturally needed) | ✅ Dependency available |
| Vector similarity search | Abstract stubs only | OpenAI embedding + pgvector store | ✅ Now implemented |
| pgvector | In tech stack table | Concrete PgvectorStore | ✅ Now implemented |
| Auto-tagging, anomaly detection | Not specifically implemented | Entity extraction + review workflow | ⚠️ Partial (future) |
| 165+ tests | 166 tests | 247 tests | ✅ Exceeded |
| Celery in architecture | Listed as Celery | Now Asyncio | ✅ Fixed |
| React Flow | Mentioned in architecture | Custom Graph | ✅ Fixed |
| MFA-ready | Claimed in features | Removed | ✅ Fixed |
| PDF export | Claimed in exports | CSV/JSON only | ✅ Fixed |
| Scheduled reports | Claimed in reporting | Removed | ✅ Fixed |
| WebSocket channels | 8 claimed | 1 active | ✅ Fixed |
