"""Render tier: needs LibreOffice and poppler. Run with `uv run pytest -m render`; CI runs it too."""
import json
import shutil
from pathlib import Path

import pytest
import yaml
from PIL import Image

from deck_builder.cli import main
from deck_builder.qa import tools

pytestmark = [
    pytest.mark.render,
    pytest.mark.skipif(tools.soffice() is None or bool(tools.poppler_missing()),
                       reason="needs LibreOffice and poppler"),
]


def run(*argv, capsys):
    code = main([*argv, "--json"])
    return code, json.loads(capsys.readouterr().out)


@pytest.fixture(scope="module")
def project(tmp_path_factory):
    root = tmp_path_factory.mktemp("render")
    assert main(["init", "--dir", str(root)]) == 0
    return root


def cfg(project):
    return str(project / "deck-builder.toml")


def test_example_renders_clean_with_libreoffice(project, capsys):
    deck = project / "workspace" / "decks" / "quarterly-review" / "deck.md"
    code, out = run("--config", cfg(project), "check", str(deck), "--render", capsys=capsys)
    errors = [i for i in out["issues"] if i["severity"] == "error"]
    assert code == 0, errors
    assert out["backend"] == "libreoffice"
    assert out["flagged_slides"] == []
    render_dir = Path(out["render_dir"])
    pngs = sorted(render_dir.glob("slide-*.png"))
    assert len(pngs) == 12
    with Image.open(pngs[0]) as im:
        assert im.size == (1280, 720)
    sheets = out["contact_sheets"]
    assert len(sheets) == 1
    with Image.open(sheets[0]) as im:
        assert im.width * im.height < 2_000_000  # stays cheap for an agent to look at


def test_overflow_is_measured_and_flagged(project, capsys):
    kit = project / "workspace" / "brands" / "neutral"
    tokens = yaml.safe_load((kit / "tokens.yaml").read_text())
    tokens["layouts"]["content"]["fields"]["body"].update(max_chars=5000, max_bullets=40, max_bullet_chars=500,
                                                          max_lines=500)  # past every budget, so it overflows
    (kit / "tokens.yaml").write_text(yaml.safe_dump(tokens, sort_keys=False))
    long = "".join(f"- Paper volume note number {i}, which runs on long enough to wrap the line twice over\n"
                   for i in range(16))
    deck = project / "workspace" / "decks" / "long.md"
    deck.write_text(f"---\nbrand: neutral\n---\n\n## Fine slide\nlayout: content\n\n- short\n\n"
                    f"## Too much text\nlayout: content\n\n{long}")
    code, out = run("--config", cfg(project), "check", str(deck), "--render", capsys=capsys)
    assert code == 1
    flagged = {f["slide"]: f["codes"] for f in out["flagged_slides"]}
    assert list(flagged) == [2]  # sixteen long bullets also warn as convention: too many bullets and words
    assert set(flagged[2]) == {"OVERFLOW_MEASURED", "BULLETS_MANY", "WORDS_MANY"}
    issue = next(i for i in out["issues"] if i["code"] == "OVERFLOW_MEASURED")
    assert issue["field"] == "body" and issue["actual"] > 20


def test_table_cells_sharing_the_footers_words_dont_misreport_footer_overflow(project, capsys):
    """Wrapped table cells sit below the table's nominal frame (row height times row count), which
    used to make their words match the nearest other shape by token - often the footer - and get
    reported as that shape's overflow."""
    deck = project / "workspace" / "decks" / "table-footer.md"
    deck.write_text(
        "---\nbrand: neutral\nfooter: Confidential draft\n---\n\n"
        "## Footer word test\nlayout: table\n\n"
        "| Item | Note |\n|---|---|\n"
        "| Lease | Confidential draft notes about the warehouse lease renewal running long enough "
        "that this single cell wraps across several lines inside its column so we can check nothing "
        "lower down gets blamed on the footer placeholder by mistake |\n"
        "| Audit | Routine |\n")
    code, out = run("--config", cfg(project), "check", str(deck), "--render", capsys=capsys)
    assert code == 0, out["issues"]
    assert out["flagged_slides"] == []
    assert not any("Footer" in i["message"] for i in out["issues"])


def test_a_table_that_overruns_its_area_is_reported(project, capsys):
    kit = project / "workspace" / "brands" / "neutral"
    tokens = yaml.safe_load((kit / "tokens.yaml").read_text())
    tokens["layouts"]["table"]["fields"]["table"].update(max_rows=20)
    (kit / "tokens.yaml").write_text(yaml.safe_dump(tokens, sort_keys=False))
    cell = "Lorem ipsum dolor sit amet consectetur"
    row = " | ".join([cell] * 6)
    rows = "\n".join(f"| {row} |" for _ in range(9))
    deck = project / "workspace" / "decks" / "table-overrun.md"
    deck.write_text(
        "---\nbrand: neutral\n---\n\n## Overrun test\nlayout: table\n\n"
        "| A | B | C | D | E | F |\n|---|---|---|---|---|---|\n" + rows + "\n")
    code, out = run("--config", cfg(project), "check", str(deck), "--render", capsys=capsys)
    assert code == 1
    flagged = {f["slide"]: f["codes"] for f in out["flagged_slides"]}
    assert set(flagged) == {1} and "OVERFLOW_MEASURED" in flagged[1]  # TABLE_TALL, from check, flags it too
    issue = next(i for i in out["issues"] if i["code"] == "OVERFLOW_MEASURED")
    assert "Table" in issue["message"]


def test_render_selected_slides_only(project, capsys):
    deck = project / "workspace" / "decks" / "quarterly-review" / "deck.md"
    run("--config", cfg(project), "build", str(deck), capsys=capsys)
    pptx = project / "workspace" / "out" / "quarterly-review.pptx"
    code, out = run("--config", cfg(project), "render", str(pptx), "--slides", "2,5", capsys=capsys)
    assert code == 0, out["issues"]
    assert sorted(p.name for p in Path(out["render_dir"]).glob("slide-*.png")) == ["slide-02.png", "slide-05.png"]


def test_powerpoint_backend_results_are_marked_unverified(project, capsys, monkeypatch):
    """LibreOffice stands in for PowerPoint; the result must still say the backend is unverified."""
    from deck_builder.qa import backends

    monkeypatch.setattr(backends, "choose", lambda requested: "powerpoint")
    monkeypatch.setattr(backends, "powerpoint", backends.libreoffice)
    deck = project / "workspace" / "decks" / "quarterly-review" / "deck.md"
    run("--config", cfg(project), "build", str(deck), capsys=capsys)
    pptx = project / "workspace" / "out" / "quarterly-review.pptx"
    code, out = run("--config", cfg(project), "render", str(pptx), "--slides", "1", capsys=capsys)
    assert out["backend"] == "powerpoint"
    assert "RENDER_UNVERIFIED" in [i["code"] for i in out["issues"]]


def test_render_skips_a_hidden_slide_without_crashing(project, capsys, tmp_path):
    from pptx import Presentation

    deck = project / "workspace" / "decks" / "quarterly-review" / "deck.md"
    pptx = tmp_path / "quarterly-review.pptx"
    run("--config", cfg(project), "build", str(deck), "-o", str(pptx), capsys=capsys)
    prs = Presentation(str(pptx))
    prs.slides[5]._element.set("show", "0")  # hide the 6th of 12 slides
    prs.save(str(pptx))
    code, out = run("--config", cfg(project), "render", str(pptx), capsys=capsys)
    assert code == 0, out["issues"]
    assert out["hidden_slides"] == [6]
    render_dir = Path(out["render_dir"])
    names = sorted(p.name for p in render_dir.glob("slide-*.png"))
    assert names == [f"slide-{n:02d}.png" for n in range(1, 13) if n != 6]
    assert out["flagged_slides"] == []


def test_workbook_resaved_by_libreoffice_builds_identically(project, capsys, tmp_path):
    import subprocess

    src = project / "workspace" / "decks" / "quarterly-review" / "deck.md"
    xlsx = tmp_path / "deck.xlsx"
    assert main(["--config", cfg(project), "convert", str(src), str(xlsx)]) == 0
    resaved_dir = tmp_path / "resaved"
    resaved_dir.mkdir()
    profile = (tmp_path / "lo").as_uri()
    lo = subprocess.run([tools.soffice(), f"-env:UserInstallation={profile}", "--headless", "--convert-to", "xlsx",
                         "--outdir", str(resaved_dir), str(xlsx)], check=True, capture_output=True, text=True,
                        timeout=300)
    resaved = resaved_dir / "deck.xlsx"
    # soffice exits 0 without writing anything when it can't load the file, e.g. Calc isn't installed
    assert resaved.exists(), f"LibreOffice wrote no workbook (is Calc installed?): {lo.stdout} {lo.stderr}"
    shutil.copytree(src.parent / "assets", resaved_dir / "assets")  # a symlink out of the folder is refused
    capsys.readouterr()
    outs = []
    for p in (src, resaved):
        code, out = run("--config", cfg(project), "build", str(p), "-o", str(tmp_path / f"{p.parent.name}.pptx"),
                        capsys=capsys)
        assert code == 0, out
        outs.append(Path(out["output"]).read_bytes())
    assert outs[0] == outs[1]
