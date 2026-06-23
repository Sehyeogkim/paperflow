"""paperflow CLI.

  paperflow inspect <project_dir>          # parse inputs only (no LLM) — offline check
  paperflow run <project_dir> [--sections method,result] [--out DIR]
  paperflow compare <project_dir> [--out DIR]   # output vs answer key
"""
from __future__ import annotations

from pathlib import Path

import typer
from rich import print as rprint
from rich.panel import Panel

from . import config

app = typer.Typer(add_completion=False, help="Manuscript Compiler (thin slice).")


@app.command()
def inspect(project_dir: str):
    """Parse the 3 inputs + scan data/reference. No LLM calls."""
    from .ingest.parse_inputs import ingest
    ps = ingest(project_dir)
    rprint(Panel.fit("[bold]Parsed ProjectState[/bold] (no LLM)"))
    rprint(f"[bold]title[/bold]: {ps.journal_info.working_title}")
    rprint(f"[bold]field[/bold]: {ps.journal_info.author_field}")
    rprint(f"[bold]target[/bold]: {ps.journal_info.target_journals}")
    rprint(f"[bold]extra[/bold]: {ps.journal_info.extra}")
    rprint(f"[bold]core one_sentence[/bold]: {ps.core_message.one_sentence[:160]}")
    rprint(f"[bold]summary bullets[/bold]: {len(ps.core_message.summary_bullets)}")
    rprint(f"[bold]outline skeleton claims[/bold]: {len(ps.outline.skeleton)}")
    rprint(f"[bold]data assets[/bold]: {len(ps.data_assets)}  "
           f"({sum(1 for d in ps.data_assets if d.kind=='csv')} csv)")
    rprint(f"[bold]reference keys[/bold]: {len(ps.reference_keys)}")
    rprint(f"\n[dim]providers with keys:[/dim] {config.available_providers() or '[red]none[/red]'}")


@app.command()
def litsearch(project_dir: str):
    """Literature search (OpenAlex) only — find real papers + write a related-work survey."""
    from .ingest.parse_inputs import ingest
    from .litsearch import run as litrun
    ps = ingest(project_dir)
    rprint(Panel.fit("[bold]선행연구조사[/bold] · OpenAlex"))
    md, found = litrun.run(ps, progress=lambda m: rprint(f"  [blue]▶[/blue] {m}"))
    rprint(f"\n[green]found {len(found)} papers[/green]:")
    for r in found:
        rprint(f"  [cite:{r.key}] {r.year} — {r.title[:64]}  [dim]{r.topic[:40]}[/dim]")
    out_dir = Path(project_dir) / "_paperflow_out"
    out_dir.mkdir(parents=True, exist_ok=True)
    if md:
        (out_dir / "Literature.md").write_text(md)
        rprint(f"\nsurvey → {out_dir/'Literature.md'}")


@app.command()
def run(project_dir: str,
        sections: str = typer.Option(
            "method,result,introduction,conclusion",
            help="comma list: introduction,method,result,conclusion"),
        out: str = typer.Option("", help="output dir (default: <project>/_paperflow_out)"),
        litsearch: bool = typer.Option(True, help="run OpenAlex literature search first")):
    """Generate sections via claim-graph -> contract -> validator."""
    from .flows import method_result
    secs = [s.strip() for s in sections.split(",") if s.strip()]
    out_dir = Path(out) if out else Path(project_dir) / "_paperflow_out"

    if not config.available_providers():
        rprint("[red]No API keys found in engine/.env[/red] — add at least one "
               "(OPENAI/DEEPSEEK/GEMINI/ANTHROPIC). `paperflow inspect` works without keys.")
        raise typer.Exit(1)

    rprint(Panel.fit(f"[bold]paperflow run[/bold]  sections={secs}\nout={out_dir}"))
    manifest = method_result.run(project_dir, secs, out_dir, litsearch=litsearch,
                                 progress=lambda m: rprint(f"  [cyan]▶[/cyan] {m}"))
    rprint(f"\n[bold green]done[/bold green]  classification=[yellow]{manifest.classification}[/yellow]")
    rprint(f"tokens: input={manifest.total_input:,}  output={manifest.total_output:,}  "
           f"cached={manifest.total_cached:,} ([green]{manifest.cache_hit_rate:.0%}[/green] hit)")
    for step, d in manifest.by_step().items():
        rprint(f"  [dim]{step}[/dim]: in={d['input']:,} out={d['output']:,} "
               f"cached={d['cached']:,} calls={d['calls']}")
    rprint(f"\nartifacts → {out_dir}")


@app.command()
def figures(project_dir: str, out: str = typer.Option("", help="output dir with sections")):
    """Generate figure images (fal.ai nano-banana pro) from the (Fig N — caption) refs."""
    import json as _json

    from .figures.generate import generate
    from .ingest.parse_inputs import ingest
    out_dir = Path(out) if out else Path(project_dir) / "_paperflow_out"
    cm = ingest(project_dir).core_message.one_sentence
    rprint(Panel.fit("[bold]figure generation[/bold] · fal nano-banana pro"))
    made = generate(project_dir, out_dir, cm, progress=lambda m: rprint(f"  [magenta]▶[/magenta] {m}"))
    (out_dir / "figures_made.json").write_text(_json.dumps(made, ensure_ascii=False, indent=2))
    ok = [m for m in made if m.get("file")]
    rprint(f"\n[green]done[/green] — {len(ok)}/{len(made)} figures → {out_dir/'figures'}")
    for m in made:
        status = m.get("file") or f"[red]ERR {m.get('error')}[/red]"
        rprint(f"  Fig {m['fig']}: {status}")


@app.command()
def compare(project_dir: str, out: str = typer.Option("", help="output dir to compare")):
    """Compare generated Method/Result against the answer-key thesis sections."""
    from .eval.compare import compare_report
    out_dir = Path(out) if out else Path(project_dir) / "_paperflow_out"
    report_path = compare_report(project_dir, out_dir)
    rprint(f"[green]comparison report[/green] → {report_path}")


@app.command()
def serve(host: str = typer.Option("127.0.0.1"), port: int = typer.Option(8765)):
    """Launch the local web UI (FastAPI) — input + live workflow tree + Q&A."""
    from .server.app import serve as _serve
    rprint(Panel.fit(f"[bold]paperflow serve[/bold]\nhttp://{host}:{port}/"))
    _serve(host, port)


if __name__ == "__main__":
    app()
