"""Static rules from the spec, enforced on the source tree."""
import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "deck_builder"
NETWORK = {"socket", "urllib", "http", "requests", "httpx", "ftplib", "smtplib", "aiohttp", "websockets"}
# Model calls belong to the agent layer's content work, never to layout, styling, check or render.
MODEL_SDKS = {"anthropic", "openai", "google", "vertexai", "mistralai", "cohere", "ollama", "litellm",
              "langchain", "langchain_core", "transformers", "llama_cpp", "boto3"}
STYLE_READERS = {"build/visuals.py"}  # the only module that turns tokens.yaml values into colors and sizes


def modules():
    return sorted(SRC.rglob("*.py"))


def test_engine_never_imports_a_network_library():
    found = []
    for path in modules():
        for node in ast.walk(ast.parse(path.read_text())):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            found += [f"{path.relative_to(SRC)}: {n}" for n in names if n.split(".")[0] in NETWORK | MODEL_SDKS]
    assert found == []


def test_engine_declares_no_model_sdk_dependency():
    """The engine stays deterministic and cheap to run: no model SDK in its runtime dependencies."""
    import tomllib

    project = tomllib.loads((SRC.parents[1] / "pyproject.toml").read_text())["project"]
    deps = [d.split("[")[0].split("<")[0].split(">")[0].split("=")[0].strip().lower()
            for d in project.get("dependencies", [])]
    assert [d for d in deps if d.replace("-", "_") in MODEL_SDKS] == []


def test_colors_and_sizes_only_come_from_tokens():
    # control: the scan sees the pattern where it is allowed, so a pass below means something
    assert "Pt(" in (SRC / "build" / "visuals.py").read_text()
    offenders = []
    for path in modules():
        rel = str(path.relative_to(SRC))
        if rel in STYLE_READERS:
            continue
        text = path.read_text()
        if "RGBColor" in text or "Pt(" in text:  # RGBColor.from_string too, not only the constructor
            offenders.append(rel)
    assert offenders == []


AGENTS_DIR = SRC.parents[1] / ".claude" / "agents"


def _frontmatter(path: Path) -> dict:
    import yaml

    return yaml.safe_load(path.read_text().split("---")[1])


def test_every_agent_is_installed_mapped_and_reads_the_design_rules():
    """The agent layer can't drift from the engine: each agent's MCP tools exist, `skills install` links
    it, `docs agents` maps it, and every agent that writes or judges slides reads `docs design`."""
    from deck_builder.mcp import TOOLS
    from deck_builder.skills import AGENTS

    files = sorted(p.name for p in AGENTS_DIR.glob("*.md"))
    assert files == sorted(AGENTS)
    role_map = (SRC / "reference" / "agents.md").read_text()
    for name in files:
        meta = _frontmatter(AGENTS_DIR / name)
        tools = [t.strip() for t in meta["tools"].split(",")]
        mcp = [t.removeprefix("mcp__deck-builder__") for t in tools if t.startswith("mcp__")]
        assert set(mcp) <= set(TOOLS), name
        assert f"`{meta['name']}`" in role_map, name
        assert "docs design" in (AGENTS_DIR / name).read_text() or "`design`" in (AGENTS_DIR / name).read_text(), name


def test_yaml_is_only_safe_loaded():
    offenders = [str(p.relative_to(SRC)) for p in modules()
                 if "yaml.load(" in p.read_text() or "yaml.unsafe_load" in p.read_text()]
    assert offenders == []
