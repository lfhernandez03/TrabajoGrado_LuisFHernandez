from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

FORBIDDEN_PHRASES = [
    "this film offers",
    "a unique experience",
    "based on your preferences",
    "mark as favorite",
    "mark it as favorite",
    "adding favorites",
    "improve future recommendations",
    "a cinematic experience",
    "this movie offers",
    "provides a unique",
    "is a must-watch",
    "you won't be disappointed",
    "something for everyone",
    "based on the context",
    "tailored to your",
]

# (min_words, max_words) per query type
WORD_LIMITS: dict[str, tuple[int, int]] = {
    "activity": (20, 100),
    "general": (40, 320),
    "mood_driven": (50, 350),
    "social": (50, 350),
    "cold_start": (50, 350),
}

JUDGE_THRESHOLD = 0.6


@dataclass
class EvalResult:
    passed: bool
    word_count: int
    issues: list[str] = field(default_factory=list)
    judge_score: float | None = None


def validate_text(text: str, title: str, query_type: str = "general") -> EvalResult:
    """Static validation: word count, title presence, forbidden phrases."""
    issues: list[str] = []
    stripped = text.strip()
    word_count = len(stripped.split())

    lo, hi = WORD_LIMITS.get(query_type, (40, 320))
    if word_count < lo:
        issues.append(f"too_short:{word_count}<{lo}")
    if word_count > hi:
        issues.append(f"too_long:{word_count}>{hi}")

    if title and title.lower() not in stripped.lower():
        issues.append("title_not_mentioned")

    text_lower = stripped.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in text_lower:
            issues.append(f"forbidden:{phrase}")
            break

    return EvalResult(passed=len(issues) == 0, word_count=word_count, issues=issues)


def build_judge_prompt(
    explanation: str, title: str, context_summary: str, query_type: str
) -> str:
    type_desc = {
        "activity": "a 2-3 sentence movie pitch for the hero section",
        "general": "a 3-5 sentence recommendation explanation",
        "mood_driven": "a mood-specific recommendation explanation",
        "social": "a socially-aware recommendation explanation",
        "cold_start": "a first-time user recommendation explanation",
    }.get(query_type, "a recommendation explanation")

    return (
        f"Evaluate the quality of {type_desc} for the movie '{title}'.\n\n"
        f"Context: {context_summary[:200]}\n\n"
        f"Explanation:\n\"{explanation}\"\n\n"
        "Score 0-10 based on:\n"
        "- Specificity: mentions the movie title and concrete details (plot, tone, atmosphere, performance)\n"
        "- Engagement: would make someone want to watch the movie right now\n"
        "- Correctness: appropriate length, no generic filler phrases\n\n"
        'Respond ONLY with JSON: {"score": <int 0-10>, "reason": "<one sentence>"}'
    )


def parse_judge_score(response_text: str) -> float:
    """Parse judge JSON response to a 0.0–1.0 score. Returns 1.0 on parse failure."""
    try:
        data = json.loads(response_text)
        raw = float(data.get("score", 10))
        return min(max(raw, 0.0), 10.0) / 10.0
    except Exception:
        m = re.search(r'"score"\s*:\s*(\d+)', response_text)
        if m:
            return min(int(m.group(1)), 10) / 10.0
        return 1.0


def build_retry_hint(issues: list[str]) -> str:
    """Append an issue-specific correction block to the original prompt."""
    hints: list[str] = []
    for issue in issues:
        if issue.startswith("too_short"):
            hints.append("Your response was too short — add specific details about the film's tone, plot, or atmosphere.")
        elif issue.startswith("too_long"):
            hints.append("Your response was too long — cut generic filler and keep only the most vivid, concrete details.")
        elif issue == "title_not_mentioned":
            hints.append("You MUST mention the movie title explicitly at least once in your response.")
        elif issue.startswith("forbidden:"):
            phrase = issue.split(":", 1)[1]
            hints.append(f"Do NOT use the phrase '{phrase}' or similar generic statements.")
        elif issue == "low_quality":
            hints.append(
                "Be more specific and evocative — name a concrete scene, the film's atmosphere, "
                "a standout performance, or a plot detail that sets this movie apart."
            )
    if not hints:
        return ""
    return "\n\nCRITICAL — rewrite to fix these issues:\n" + "\n".join(f"- {h}" for h in hints)
