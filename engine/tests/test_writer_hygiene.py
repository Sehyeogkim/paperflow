from paperflow.compile.writer import _strip_internal_graph_ids
from paperflow.schemas.claim import ClaimGraph, GNode


def test_strips_exact_graph_ids_but_preserves_domain_abbreviations():
    graph = ClaimGraph(nodes=[
        GNode(id="M1", kind="method", text="method"),
        GNode(id="C1.1", kind="claim", text="claim"),
        GNode(id="DEC_GPR_HYPERPARAMS", kind="decision", text="choice"),
    ])
    draft = (
        "FSI and GPR were used (M1, C1.1). "
        "The ARD-RBF choice (DEC_GPR_HYPERPARAMS) supports VI1 and VI2."
    )

    cleaned = _strip_internal_graph_ids(draft, graph)

    assert "M1" not in cleaned
    assert "C1.1" not in cleaned
    assert "DEC_GPR_HYPERPARAMS" not in cleaned
    assert "FSI" in cleaned
    assert "GPR" in cleaned
    assert "VI1" in cleaned
    assert "VI2" in cleaned
    assert "()" not in cleaned
