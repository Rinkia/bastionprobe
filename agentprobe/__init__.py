"""agentprobe - the offensive twin of agentbastion.

Fire indirect prompt-injection payloads at an AI agent and report which land.
Every payload that gets through is a hole a runtime guard should close.
"""

from .corpus import Payload, load_payloads
from .runner import AttackResult, run_attack, run_suite
from .target import AgentResponse, Target

__version__ = "0.1.0"

__all__ = [
    "Payload",
    "load_payloads",
    "AttackResult",
    "run_attack",
    "run_suite",
    "AgentResponse",
    "Target",
    "__version__",
]
