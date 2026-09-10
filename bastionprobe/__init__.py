"""bastionprobe - the offensive twin of agentbastion.

Fire indirect prompt-injection payloads at an AI agent and report which land.
Every payload that gets through is a hole a runtime guard should close.
"""

from .analyze import GroupRate, group_rates
from .anthropic_target import make_anthropic_target
from .corpus import Payload, load_payloads
from .harden import build_hardening, write_hardening
from .matrix import run_matrix, tactic_matrix
from .openai_target import make_openai_target
from .runner import AttackResult, run_attack, run_suite
from .target import AgentResponse, Target, rate_limited

__version__ = "0.9.0"

__all__ = [
    "Payload",
    "load_payloads",
    "AttackResult",
    "run_attack",
    "run_suite",
    "AgentResponse",
    "Target",
    "rate_limited",
    "make_anthropic_target",
    "make_openai_target",
    "build_hardening",
    "write_hardening",
    "group_rates",
    "GroupRate",
    "run_matrix",
    "tactic_matrix",
    "__version__",
]
