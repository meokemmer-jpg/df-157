# DF-157 PVG-Wargame-History-Aggregator [CRUX-MK]

**Status:** SKELETON-CONDITIONAL (Welle-51 W51-B Skeleton-Wave-2)
**Domain:** META (Cross-LLM-Verdict-Historie, I_min)
**Welle:** 25

## Mission

Cross-LLM-Verdict-Trend-Aggregation aus branch-hub/cross-llm/. Tracking:
- Verdict-Tier-Distribution (HARDENED/CONDITIONAL/REJECTED)
- Konvergenz-Rate (2OF3, 3OF3)
- LLM-Outlier-Rate
- Patch-Adoption-Rate

**NIEMALS Cross-LLM-Verdicts modifizieren.**

## Usage

```bash
cd ~/Projects/dark-factories/df-157
python df-157-engine.py        # Mock-Mode default
pytest tests/                   # Existing tests
```

## Output

- Reports: `reports/df-157-{date}.json`
- STOP-Flag: `/tmp/df-157.stop`

[CRUX-MK]
