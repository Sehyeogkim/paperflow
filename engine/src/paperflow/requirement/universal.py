"""Universal schema — the only thing fixed across all research fields.

Per the literature-grounded design: we fix the TOP-LEVEL categories (the lens used to read
any paper) and a minimal set of base requirements that every empirical paper needs. Every
field-specific detail key (mesh independence, inclusion criteria, ablation study, ...) is
derived dynamically from related literature, never hard-coded here.
"""
from __future__ import annotations

# Fixed top-level categories used by per-paper extraction. Free-form item names live UNDER
# these; the categories themselves are the stable lens.
UNIVERSAL_CATEGORIES: tuple[str, ...] = (
    "objective",
    "study_design",
    "data_or_sample",
    "methods",
    "models_and_equations",
    "numerical_or_experimental_settings",
    "validation",
    "outcomes",
    "results",
    "statistical_analysis",
    "limitations",
    "figures_and_tables",
    "reported_items",
)

# Minimal base requirements every empirical paper needs (section 7.1). These seed the schema
# so a defensible Method/Result is always anchored even when literature is thin.
UNIVERSAL_BASE_REQUIREMENTS: tuple[dict, ...] = (
    {"key": "research_objective", "category": "objective",
     "reason": "Every paper must state what it sets out to show."},
    {"key": "study_subject_or_sample", "category": "data_or_sample",
     "reason": "The data/sample the results are computed over must be defined."},
    {"key": "primary_method", "category": "methods",
     "reason": "The main method producing the results must be described."},
    {"key": "primary_outcome", "category": "outcomes",
     "reason": "The quantity claimed must be defined."},
    {"key": "main_result", "category": "results",
     "reason": "The central result the claim rests on must be reported."},
    {"key": "limitation_boundary", "category": "limitations",
     "reason": "The scope/limitations that bound the claim must be stated."},
)


def empty_universal_schema() -> dict:
    """A blank universal schema object (top-level categories only)."""
    return {c: [] for c in UNIVERSAL_CATEGORIES}
