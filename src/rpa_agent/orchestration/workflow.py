from rpa_agent.agents.base import Agent


def run_pipeline(agents: list[Agent], task: str) -> str:
    """Run agents sequentially, passing each output as the next task."""
    result = task
    for agent in agents:
        result = agent.run(result)
    return result
