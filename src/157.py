from __future__ import annotations

from collections import Counter
from typing import Dict, Iterable, List, Mapping, Optional

VERDICT_TIERS = ("HARDENED", "CONDITIONAL", "REJECTED")


def classify_verdicts(verdicts: Mapping[str, str]) -> Dict[str, Optional[object]]:
    """
    Classify a single 3-LLM verdict set without mutating the input.

    Returns:
        {
            "majority_tier": "HARDENED" | "CONDITIONAL" | "REJECTED" | None,
            "convergence": "3OF3" | "2OF3" | None,
            "outlier_models": [<model>, ...],
        }
    """
    items = list(verdicts.items())
    tiers = [tier for _, tier in items]
    counts = Counter(tiers)
    majority_tier, majority_count = counts.most_common(1)[0]

    if majority_count == 3:
        return {
            "majority_tier": majority_tier,
            "convergence": "3OF3",
            "outlier_models": [],
        }

    if majority_count == 2 and len(items) == 3:
        outliers = [model for model, tier in items if tier != majority_tier]
        return {
            "majority_tier": majority_tier,
            "convergence": "2OF3",
            "outlier_models": outliers,
        }

    return {
        "majority_tier": None,
        "convergence": None,
        "outlier_models": [],
    }


def aggregate_history(records: Iterable[Mapping[str, object]]) -> Dict[str, object]:
    """
    Aggregate cross-LLM verdict history.

    Each record is expected to look like:
        {
            "id": "case-1",
            "verdicts": {"gpt": "...", "claude": "...", "gemini": "..."},
            "patch_adopted": True/False,
        }
    """
    records = list(records)
    total_cases = len(records)
    tier_distribution = {tier: 0 for tier in VERDICT_TIERS}
    convergence_counts = {"2OF3": 0, "3OF3": 0}
    outlier_case_count = 0
    adopted_count = 0
    case_summaries: List[Dict[str, object]] = []

    for record in records:
        verdicts = dict(record["verdicts"])
        result = classify_verdicts(verdicts)

        majority_tier = result["majority_tier"]
        convergence = result["convergence"]
        outlier_models = list(result["outlier_models"])

        if majority_tier in tier_distribution:
            tier_distribution[majority_tier] += 1
        if convergence in convergence_counts:
            convergence_counts[convergence] += 1
        if outlier_models:
            outlier_case_count += 1
        if bool(record.get("patch_adopted", False)):
            adopted_count += 1

        case_summaries.append(
            {
                "id": record.get("id"),
                "majority_tier": majority_tier,
                "convergence": convergence,
                "outlier_models": outlier_models,
                "patch_adopted": bool(record.get("patch_adopted", False)),
            }
        )

    def rate(numerator: int) -> float:
        return 0.0 if total_cases == 0 else numerator / total_cases

    return {
        "total_cases": total_cases,
        "verdict_tier_distribution": tier_distribution,
        "convergence": {
            "counts": convergence_counts,
            "rates": {key: rate(value) for key, value in convergence_counts.items()},
        },
        "llm_outlier_rate": rate(outlier_case_count),
        "patch_adoption_rate": rate(adopted_count),
        "cases": case_summaries,
    }
# [CRUX-MK]
