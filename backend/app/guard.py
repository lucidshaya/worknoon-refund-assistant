"""Prompt-injection / policy-bypass detection.

This is a defense-in-depth layer, not the only one. Layers, in order:

1. This module runs a fast, deterministic heuristic scan over the raw
   customer message *before* it ever reaches the LLM. A hit here is
   logged and forces the final decision to ESCALATE (see policy.py) no
   matter what the LLM says later.
2. The LLM itself is prompted with the customer message wrapped as
   clearly-labelled untrusted data (see ai.py), and is instructed to
   never treat it as instructions and to never let it override policy.
3. The policy engine (policy.py) is deterministic Python and is always
   the final authority on the decision. The LLM is only ever consulted
   for classification/explanation/reply drafting -- it cannot approve or
   deny anything by itself, so even a successful jailbreak of the LLM
   cannot bypass the refund policy.

Heuristics here deliberately favor recall over precision: a false
positive just means a human looks at an otherwise-fine request, whereas
a false negative could mean a manipulated approval slips through.
"""
import re
from dataclasses import dataclass

INJECTION_PATTERNS = [
    r"ignore (all|any|the) (previous|prior|above)? ?instructions",
    r"disregard (the|all|your) (policy|rules|instructions)",
    r"you are now",
    r"act as (a|an) ",
    r"system prompt",
    r"new instructions?:",
    r"override (the )?(policy|refund policy|rules)",
    r"approve (this|my) refund (regardless|no matter|automatically)",
    r"forget (your|the) (rules|policy|instructions)",
    r"pretend (you are|to be)",
    r"as an ai (language model|assistant)? you (must|should)",
    r"this is (a test|urgent|an emergency),? (please )?bypass",
    r"do not (escalate|deny|flag) this",
    r"jailbreak",
    r"\bDAN\b",
    r"<\s*system\s*>",
    r"\[\s*system\s*\]",
    r"end of (user|customer) message",
    r"the (real|actual) policy is",
    r"i am (a|the) (developer|admin|administrator|engineer) (testing|debugging)",
    r"grant (me|full) access",
    r"unlimited refund",
    r"refund .* without (review|question|verification)",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


@dataclass
class GuardResult:
    flagged: bool
    matched_patterns: list[str]

    @property
    def detail(self) -> str:
        if not self.flagged:
            return ""
        return "Suspicious phrasing detected: " + "; ".join(self.matched_patterns)


def scan_message(message: str) -> GuardResult:
    hits = []
    for pattern in _COMPILED:
        if pattern.search(message):
            hits.append(pattern.pattern)
    return GuardResult(flagged=len(hits) > 0, matched_patterns=hits)
