# Agent roles: who owns each CLI command and MCP tool

The one map of every `deck-builder` CLI command and MCP tool to the party that drives it. AGENTS.md,
the skills and the agent files point here instead of restating it. The delegation threshold and the
two-round stop rule live in AGENTS.md; this topic is only about which surface each party uses and who
calls which command.

## The four parties

- **Main agent.** Holds the conversation with the user. Has a shell, so it always runs the CLI
  directly (`deck-builder ...`); it never goes through its own MCP server. Owns every command and
  tool not delegated below, and approves anything a subagent proposes before the user sees it.
- **`deck-builder-agent`.** Writes and fixes one deck's content in its own context. No shell: reaches
  the engine only through the MCP tools it's given.
- **`deck-brand-agent`.** Generates or adopts a brand kit and tunes its budgets. No shell: MCP tools
  only.
- **`deck-decomposer-agent`.** Turns a body of source material into `outline.md` and a draft
  `deck.md`. Runs no commands at all, because what it reads is untrusted: Read, Write, Edit, Glob and
  Grep only, no MCP server.

## CLI commands

Every CLI command belongs to the main agent: the subagents have no shell, and the decomposer has
neither a shell nor an MCP server. Four commands exist only as CLI, never as MCP tools, because they
set up or link the local install rather than touch a deck or brand kit: `init`, `mcp`, `schema`,
`skills install`. Every other CLI command (`docs`, `explain`, `brand list/show/check/init/adopt/
add-asset`, `inspect`, `assets`, `check`, `build`, `convert`, `import`, `render`, `doctor`) also
exists as an MCP tool, named `brand_show` for `brand show` and so on; the table below gives that
tool's owner when the job is delegated to a subagent.

## MCP tools

| Tool | Owner | Notes |
|---|---|---|
| `check` | `deck-builder-agent` | Validates; with `render: true` it also builds, renders and measures in one call. Also called by `deck-brand-agent` (its test-deck render) and the main agent (the review gate, and the loop itself below the delegation threshold). |
| `build` | `deck-builder-agent` | Bulk runs only (`data`, one deck per row). The normal loop uses `check` with `render: true`, which builds internally. |
| `brand_show` | `deck-builder-agent` | Layouts, fields and budgets to write to, read first. Also called by `deck-brand-agent` (the report's summary) and the main agent. |
| `brand_check` | `deck-brand-agent` | Must pass before any deck uses the kit. |
| `brand_init` | `deck-brand-agent` | Generates a kit from a `brand.yaml`. |
| `brand_adopt` | `deck-brand-agent` | Wraps an existing `.potx` or `.pptx` as a kit. |
| `brand_add_asset` | `deck-brand-agent` | Copies a logo or icon PNG into a kit. |
| `inspect` | `deck-brand-agent` | A template's layouts and placeholders, for the adopt path. |
| `docs` | main agent | Reference topics (`deck-md`, `workbook`, `brand-yaml`, `tokens-yaml`, `workflow`, `design`, `agents`, `codes`). Also called by both subagents, each for the topics its own job needs. |
| `explain` | main agent | Cause and fix for one issue code. Also called by both subagents while fixing what `check` or `brand_check` reports. |
| `render` | main agent | Re-renders an already-built `.pptx` without rebuilding, e.g. the original side of a refresh. Not given to a subagent: `check --render` already covers both loops. |
| `convert` | main agent | `.md` / `.xlsx` / `.csv` conversion for team editing. |
| `import` | main agent | Turns an existing `.pptx` into `deck.md`, to refresh or re-brand it. |
| `brand_list` | main agent | Lists brands when choosing one with the user. |
| `assets` | main agent | Inventories a brand's or a deck's logos, icons and images. |
| `doctor` | main agent | Environment and dependency checks, for onboarding. |

## What each subagent reads and writes

- **`deck-builder-agent`** reads the source material and brand files it's given (read-only) and the
  reference topics; writes only the deck file and files in its `assets/` folder. `check` and `build`
  write the `.pptx`, its manifest and the render images, confined to the workspace.
- **`deck-brand-agent`** reads the brand guide, template, logos and icons it's given (read-only, from
  the workspace or a `brand_paths` folder) and the reference topics; writes `brand.yaml` and a test
  deck in a scratch folder, and the brand kit itself only through `brand_init`, `brand_adopt` and
  `brand_add_asset`, which write inside a `brand_paths` folder.
- **`deck-decomposer-agent`** reads the source folder it's given (read-only, untrusted) plus whatever
  the main agent puts in its prompt; writes only `outline.md` and `deck.md` (or `deck.draft.md` when
  `deck.md` already exists) in the deck folder it's given.

All three are confined by the MCP server itself, which refuses any path outside the workspace (brand
writes outside a `brand_paths` folder, brand reads outside the workspace or a `brand_paths` folder)
and the clone's own `src/`, `.claude/` and `.git/` regardless of where they sit.
