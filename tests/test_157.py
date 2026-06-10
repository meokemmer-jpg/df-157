import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
# [CRUX-MK]
import importlib

aggregate_history = importlib.import_module("157").aggregate_history
classify_verdicts = importlib.import_module("157").classify_verdicts


def test_aggregate_history_core_metrics():
    records = [
        {
            "id": "case-1",
            "verdicts": {
                "gpt": "HARDENED",
                "claude": "HARDENED",
                "gemini": "HARDENED",
            },
            "patch_adopted": True,
        },
        {
            "id": "case-2",
            "verdicts": {
                "gpt": "CONDITIONAL",
                "claude": "CONDITIONAL",
                "gemini": "REJECTED",
            },
            "patch_adopted": False,
        },
        {
            "id": "case-3",
            "verdicts": {
                "gpt": "REJECTED",
                "claude": "HARDENED",
                "gemini": "REJECTED",
            },
            "patch_adopted": True,
        },
    ]

    summary = aggregate_history(records)

    assert summary["total_cases"] == 3
    assert summary["verdict_tier_distribution"] == {
        "HARDENED": 1,
        "CONDITIONAL": 1,
        "REJECTED": 1,
    }
    assert summary["convergence"]["counts"] == {"2OF3": 2, "3OF3": 1}
    assert summary["convergence"]["rates"] == {"2OF3": 2 / 3, "3OF3": 1 / 3}
    assert summary["llm_outlier_rate"] == 2 / 3
    assert summary["patch_adoption_rate"] == 2 / 3

    assert summary["cases"][1]["convergence"] == "2OF3"
    assert summary["cases"][1]["outlier_models"] == ["gemini"]
    assert summary["cases"][2]["majority_tier"] == "REJECTED"


def test_classify_verdicts_detects_unanimous_and_outlier():
    unanimous = classify_verdicts(
        {"gpt": "HARDENED", "claude": "HARDENED", "gemini": "HARDENED"}
    )
    outlier = classify_verdicts(
        {"gpt": "CONDITIONAL", "claude": "REJECTED", "gemini": "CONDITIONAL"}
    )

    assert unanimous == {
        "majority_tier": "HARDENED",
        "convergence": "3OF3",
        "outlier_models": [],
    }
    assert outlier == {
        "majority_tier": "CONDITIONAL",
        "convergence": "2OF3",
        "outlier_models": ["claude"],
    }
