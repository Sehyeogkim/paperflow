"""Shared fixtures: a minimal legacy-format project on disk, and the repo's demo project."""
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]      # repo root (…/paperflow)
DEMO = REPO / "projects" / "coronary_plaque_demo"


@pytest.fixture
def demo_dir() -> str:
    """The real coronary_plaque_demo project (legacy 0/1/3 md + data/)."""
    return str(DEMO)


@pytest.fixture
def mini_project(tmp_path: Path) -> str:
    """A tiny legacy-format project: 3 input md files + 2 data files + notes."""
    main = tmp_path / "main"
    main.mkdir(parents=True)
    (main / "0_journal_info.md").write_text(
        "## Working title\nWidget rupture risk\n\n## Author's field\nbiomechanics\n\n"
        "## Target journals\n1. Journal of Widgets\n\n## Extra info\n- authors: A B\n")
    (main / "1_coremessage.md").write_text(
        "## One sentence\nMaterial properties dominate rupture risk.\n\n"
        "## One paragraph\nWe built a dataset and ran sensitivity analysis. "
        "Material factors dominate over hemodynamic factors.\n\n"
        "## Novelty\n- Material > Hemo > Morpho\n- Amplitude stress is clinically better\n\n"
        "## Keywords\nrupture, sensitivity\n")
    (main / "3_outline.md").write_text(
        "[Intro]\n1. Rupture is a major cause of events.\n"
        "[Results]\n2. Material factors dominate the sensitivity ranking.\n")
    data = tmp_path / "data"
    (data / "sobol").mkdir(parents=True)
    (data / "sobol" / "sobol_grp_LAP.csv").write_text(
        "group,S1,ST\nmaterial,0.61,0.72\nhemo,0.21,0.28\nmorpho,0.10,0.14\n")
    (data / "input_parameter").mkdir(parents=True)
    (data / "input_parameter" / "input.csv").write_text(
        "E_vessel,E_fc,SBP,PP\n1.2,0.8,120,40\n1.5,0.9,130,45\n")
    (main / "data_notes.json").write_text(json.dumps({
        "data/sobol/sobol_grp_LAP.csv": "group-level Sobol sensitivity result",
        "data/input_parameter/input.csv": "1000-sample input design space",
    }, ensure_ascii=False))
    return str(tmp_path)
