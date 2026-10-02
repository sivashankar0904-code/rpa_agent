import argparse

from rpa_agent.agents.base import Agent
from rpa_agent.config.settings import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(prog="rpa-agent")
    parser.add_argument("task", help="Task for the agent to perform")
    args = parser.parse_args()
    print(Agent(get_settings()).run(args.task))


if __name__ == "__main__":
    main()
