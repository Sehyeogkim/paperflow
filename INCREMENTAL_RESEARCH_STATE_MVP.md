# PaperFlow — Incremental Research State MVP

## 1. Problem

The current Stage-1 advance path performs a fresh reconstruction after requirement answers:

```text
answers
→ full research reconstruction
→ full preliminary logic graph rebuild
→ full gap validation
```

This protects correctness, but repeats expensive LLM work even when an answer changes only one narrow fact such as mesh independence, cohort size, solver name, comparator, or the provenance of one numeric result.

The product hypothesis remains unchanged:

> A defensible manuscript requires an explicit research state and a claim–evidence graph before drafting.

The optimization target is therefore not to remove reconstruction, but to make the state persistent and incrementally updateable.

---

## 2. Target workflow

```text
INITIAL COLD PATH — expensive, once
inputs + uploaded assets
→ deterministic profiling
→ full Research State v1 reconstruction
→ full preliminary claim skeleton / graph
→ persist state, graph, fingerprints, dependencies

ANSWER HOT PATH — cheap, repeated
new requirement answer
→ parse into structured AnswerPatch
→ verify source-input fingerprint
→ apply patch to persistent Research State
→ identify affected state fields / evidence / claims
→ update only affected graph region where possible
→ validate only affected claims, then merge gap report

FINAL AUDIT — expensive, once
final state + all answers + current graph
→ strong-model consistency audit
→ full deterministic graph validation
→ downgrade / qualify unsupported claims
→ manuscript generation
```

---

## 3. Safety rule

Incremental update is the default only when the original source inputs have not changed.

Trigger a full reconstruction when any of the following is true:

- no persisted base state exists
- journal info, core message, outline, uploaded data, references, or data notes changed
- the primary objective, study design, primary outcome, or main contribution changed
- a new answer contradicts a previously accepted fact
- patch parsing confidence is low
- the user explicitly requests a full rebuild

The existing full-reconstruction path remains as the fallback and reference implementation.

---

## 4. Proposed persisted artifacts

```text
main/research_state_base.json          # cold reconstruction before author answers
main/research_state.json               # current canonical state
main/research_state_v2.json            # Stage-1 answer state, compatibility
main/research_state_final.json         # Stage-2/final state
main/research_state_meta.json           # source fingerprint + versions
main/answer_patches_requirement.json    # structured Stage-1 patches
main/answer_patches_logic.json          # structured Stage-2 patches
main/graph_dependencies.json            # state field → graph node/claim ids
main/preliminary_logic_graph.json
main/graph_gap_report.json
```

---

## 5. AnswerPatch contract

A requirement answer must first become a structured patch rather than an untyped string appended only to `key_observations`.

Example answer:

```text
Three meshes were compared and peak cap stress differed by less than 1.8%.
```

Example patch:

```json
{
  "answer_id": "REQ_mesh_independence",
  "operations": [
    {
      "op": "upsert_fact",
      "path": "validation.mesh_independence",
      "category": "validation",
      "value": {
        "performed": true,
        "mesh_count": 3,
        "metric": "peak cap stress",
        "maximum_difference_percent": 1.8
      },
      "source": "author_answer_requirement",
      "confidence": "high"
    }
  ],
  "affected_state_paths": [
    "validation.mesh_independence"
  ],
  "possible_graph_impacts": [
    "method",
    "numeric_evidence_provenance",
    "result_reliability"
  ],
  "requires_full_reconstruction": false
}
```

Unknown answers are represented explicitly and never converted into facts:

```json
{
  "op": "mark_unknown",
  "path": "validation.mesh_independence",
  "source": "author_answer_requirement"
}
```

---

## 6. Model routing

Use deterministic code or a small extraction model for:

- file hashing and change detection
- numeric/entity extraction from answers
- patch schema validation
- duplicate detection
- graph type/edge validation
- affected-node lookup

Reserve the strong reasoning model for:

- initial full research reconstruction
- ambiguous answer-to-state mapping
- claim–evidence relationship construction
- contradiction resolution
- final full consistency audit

The goal is not globally lower reasoning effort. It is concentrated reasoning effort at the few steps where semantic judgment changes manuscript defensibility.

---

## 7. Graph update strategy

### MVP-A

Keep the existing full preliminary graph rebuild, but eliminate repeated full Research State reconstruction. This immediately removes one expensive LLM pass while preserving graph behavior.

### MVP-B

Persist a stable claim skeleton and update graph grounding only:

- reuse claim nodes when the main contribution and possible claims are unchanged
- add or update evidence, method, data, warrant, qualifier, and provenance nodes
- validate only claims listed in `affected_claim_ids`
- run full graph validation before final manuscript generation

### MVP-C

Maintain explicit dependency indexes:

```json
{
  "validation.mesh_independence": {
    "claim_ids": ["C2"],
    "evidence_ids": ["E7"],
    "method_ids": ["M3"]
  }
}
```

---

## 8. Implementation order

1. Add `ResearchFact`, `PatchOperation`, and `AnswerPatch` schemas.
2. Add source-input fingerprinting that excludes answer and generated-state files.
3. Persist an answer-free `research_state_base.json` during cold reconstruction.
4. Implement deterministic patch application and provenance preservation.
5. Change `reconstruct_after_requirement_answers()` to:
   - reuse base state when fingerprint matches
   - apply all merged requirement patches
   - fall back to fresh reconstruction when unsafe
6. Add progress events that distinguish:
   - `incremental state update`
   - `full state reconstruction fallback`
7. Add tests for reuse, fallback, unknown answers, idempotency, and provenance.
8. Add claim-skeleton reuse and affected-claim validation as the next isolated change.

---

## 9. Acceptance tests for MVP-A

### Reuse

Given unchanged source inputs and a persisted base state, submitting a requirement answer must not call the full reconstruction LLM.

### Fallback

Changing `1_coremessage.md`, `3_outline.md`, a data file, reference file, or data note must force full reconstruction.

### Idempotency

Submitting the same answer twice must not duplicate facts or provenance entries.

### Unknown safety

`모름`, `나중에`, `unknown`, and equivalent answers must not create positive facts.

### Provenance

Every accepted patch must preserve:

```text
answer id
source = author_answer_requirement | author_answer_logic
state path
original answer text
```

### Compatibility

Existing consumers of `key_observations`, `unknowns`, `answer_provenance`, and `research_state.json` must continue to work during migration.

### Final safety

The final manuscript path must still run a complete graph validation and reject untraceable numeric evidence.

---

## 10. Product metric

Measure the hypothesis rather than only latency:

- cold reconstruction latency and token cost
- average answer hot-path latency and token cost
- percentage of answers handled incrementally
- percentage requiring full fallback
- graph-gap precision before and after incremental updates
- unsupported-claim rate in final validation
- manuscript quality difference versus direct drafting and versus full reconstruction after every answer

The desired product result is:

> Preserve the logical benefit of reconstruction while making each follow-up answer feel interactive rather than restarting the entire paper analysis.
