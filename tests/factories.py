import itertools
from dataclasses import dataclass, asdict
from typing import Dict

_counter = itertools.count(1)


@dataclass
class Agent:
    id: int
    name: str
    metadata: Dict = None


@dataclass
class Session:
    id: int
    agent_id: int
    state: Dict = None


@dataclass
class Message:
    id: int
    session_id: int
    role: str
    content: str


def agent_factory(**kwargs):
    i = next(_counter)
    defaults = {"id": i, "name": f"test-agent-{i}", "metadata": {}}
    defaults.update(kwargs)
    return Agent(**defaults)


def session_factory(**kwargs):
    i = next(_counter)
    defaults = {"id": i, "agent_id": kwargs.get("agent_id", 1), "state": {}}
    defaults.update(kwargs)
    return Session(**defaults)


def message_factory(**kwargs):
    i = next(_counter)
    defaults = {"id": i, "session_id": kwargs.get("session_id", 1), "role": "user", "content": "hello"}
    defaults.update(kwargs)
    return Message(**defaults)
