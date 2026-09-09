"""bastionprobe - the offensive twin of agentbastion.

Fire indirect prompt-injection payloads at an AI agent and report which land.
Every payload that gets through is a hole a runtime guard should close.
"""

from .analyze import GroupRate, group_rates
from .anthropic_target import make_anthropic_target
from .corpus import Payload, load_payloads
from .harden import build_hardening, write_hardening
from .runner import AttackResult, run_attack, run_suite
from .target import AgentResponse, Target

__version__ = "0.6.0"

__all__ = [
    "Payload",
    "load_payloads",
    "AttackResult",
    "run_attack",
    "run_suite",
    "AgentResponse",
    "Target",
    "make_anthropic_target",
    "build_hardening",
    "write_hardening",
    "group_rates",
    "GroupRate",
    "__version__",
]
