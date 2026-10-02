# rpa-agent

Agentic AI project: an LLM tool-use loop for automating tasks.

## Layout
- `src/rpa_agent/agents/` - agent loops
- `src/rpa_agent/tools/` - tools the agent can call (registry + implementations)
- `src/rpa_agent/llm/` - model client wrapper
- `src/rpa_agent/memory/` - conversation/long-term memory
- `src/rpa_agent/orchestration/` - multi-agent workflows
- `src/rpa_agent/config/` - settings
- `prompts/`, `configs/` - prompts and YAML config
- `tests/` - unit and integration tests

## Setup
    python -m venv .venv && .venv\Scripts\activate
    pip install -e .[dev]
    copy .env.example .env   (then add ANTHROPIC_API_KEY)
    rpa-agent "summarize data/inputs/notes.txt into data/outputs/summary.txt"
    pytest
