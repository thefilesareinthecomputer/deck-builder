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


VOICE_RULES = ("One colleague talking to another", "is a full sentence", "Cut only whole points",
               "Slides get reordered", "presenter's script", "Cut, don't caveat",
               "Compelling comes from the order of the slides", "Plain words.", '"X, not Y"', "Register.",
               "Truth.", "Symbols.", "Emphasis.", "A line the user wrote stays as written", "old and new")


def test_the_agents_that_write_or_judge_slide_text_read_one_voice():
    """`docs voice` holds the writing rules. The decomposer, storyteller, builder, validator and the skill read
    it rather than keep copies that drift apart; the storyteller, builder and validator read `docs story`
    when there's a storyboard; the agents that can ask for the storyteller say how."""
    voice = (SRC / "reference" / "voice.md").read_text()
    assert all(rule in voice for rule in VOICE_RULES)
    assert "docs voice" in (AGENTS_DIR.parent / "skills" / "deck-builder" / "SKILL.md").read_text()
    for name in ("deck-decomposer-agent.md", "deck-storyteller-agent.md", "deck-builder-agent.md",
                 "deck-validator-agent.md"):
        text = (AGENTS_DIR / name).read_text()
        assert "docs voice" in text and "## Tone and style" not in text, name
    for name in ("deck-storyteller-agent.md", "deck-builder-agent.md", "deck-validator-agent.md"):
        text = (AGENTS_DIR / name).read_text()
        assert "storyboard" in text and ("`story`" in text or "docs story" in text), name
    for name in ("deck-builder-agent.md", "deck-decomposer-agent.md", "deck-brand-agent.md"):
        assert "`Storyteller: " in (AGENTS_DIR / name).read_text(), name


def test_a_deck_gets_one_send_back_and_the_loop_checks_and_renders_in_one_call():
    """AGENTS.md's stop rule: an agent's own check-and-fix loop stops after two rounds, and a deck or kit gets one
    send-back. No agent or skill asks for a second, and the builder goes straight to `check` with render, which
    returns the same issues a plain `check` does, so a build costs fewer turns."""
    assert "one send-back" in (SRC.parents[1] / "AGENTS.md").read_text()
    for path in [*AGENTS_DIR.glob("*.md"), *(AGENTS_DIR.parent / "skills").glob("*/SKILL.md")]:
        text = path.read_text().lower()
        assert "two send-backs" not in text and "up to two rounds" not in text, path.name
    assert "`check` with the deck's path and `render: true`" in (AGENTS_DIR / "deck-builder-agent.md").read_text()


def test_yaml_is_only_safe_loaded():
    offenders = [str(p.relative_to(SRC)) for p in modules()
                 if "yaml.load(" in p.read_text() or "yaml.unsafe_load" in p.read_text()]
    assert offenders == []
