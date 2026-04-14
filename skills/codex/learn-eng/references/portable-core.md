# Portable Core (Claude/Codex Future)

## Core Behavior
- Route input into `vocabulary`, `sentence`, or `paragraph` mode.
- Keep a stable structured output contract per mode.
- Support partial revision with `/revise <scope> <instruction>`.
- Keep tone concise, practical, learner-oriented.

## Keep Stable Across Platforms
- Routing rules.
- Field names and order inside each mode.
- Structure tags for sentence analysis.
- Paragraph logic sections.

## Adapter Strategy
- Codex adapter: `SKILL.md` + `agents/openai.yaml`.
- Claude adapter (future): reuse same contracts and route logic.

## Do Not Carry Forward
- Jailbreak/persona coercion.
- Policy-bypass wording.
- Prompt noise that does not improve learning outcomes.
