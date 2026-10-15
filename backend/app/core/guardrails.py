"""
Guardrails and Prompt Injection Defense.
Treats all social posts and retrieved KB passages as untrusted data.
Neutralizes adversarial instructions, system prompt extraction, and roleplay jailbreaks.
"""
import json
import re
from typing import Any

# Adversarial prompt injection signatures
INJECTION_SIGNATURES = [
    r"(?i)ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"(?i)system\s+prompt",
    r"(?i)you\s+are\s+now\s+(in\s+)?developer\s+mode",
    r"(?i)output\s+the\s+(secret|api)\s+key",
    r"(?i)bypass\s+all\s+(rules|guidelines|guardrails)",
    r"(?i)dan\s+mode",
    r"(?i)jailbreak",
    r"(?i)do\s+anything\s+now",
    r"(?i)act\s+as\s+an\s+unfiltered",
    r"(?i)disregard\s+the\s+above",
]

class PromptInjectionDefense:
    """
    Sanitizes external content and wraps it in protective delimiter boundaries.
    """
    @staticmethod
    def inspect(text: str) -> tuple[bool, list[str]]:
        """
        Checks if text contains known prompt injection triggers.
        Returns: (is_suspicious: bool, detected_patterns: List[str])
        """
        detected = []
        for pat in INJECTION_SIGNATURES:
            if re.search(pat, text):
                detected.append(pat)
        return len(detected) > 0, detected

    @staticmethod
    def wrap_untrusted(text: str, context_label: str = "social_post") -> str:
        """
        Wraps content inside protective XML boundaries and instructs LLMs
        to treat internal content strictly as data to analyze, never instructions.
        """
        # Neutralize control characters
        cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
        
        # Disarm active triggers
        for pat in INJECTION_SIGNATURES:
            cleaned = re.sub(pat, "[FILTERED_ADVERSARIAL_INSTRUCTION]", cleaned)

        return (
            f"<{context_label}_untrusted_data>\n"
            f"{cleaned}\n"
            f"</{context_label}_untrusted_data>"
        )

def parse_json_markdown(raw: str) -> Any:
    """
    Safely parses JSON responses from LLMs, stripping markdown code fences if present.
    Robustly handles single-quoted dict strings via ast.literal_eval fallback.
    """
    clean = raw.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
    clean = clean.strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        # Try extracting JSON object substring
        m = re.search(r"(\{.*\})", clean, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        # Fallback to ast.literal_eval for single-quoted dicts
        import ast
        try:
            val = ast.literal_eval(clean)
            if isinstance(val, (dict, list)):
                return val
        except Exception:
            pass
        raise

