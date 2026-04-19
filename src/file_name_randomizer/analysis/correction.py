"""Multiple-comparison correction helpers."""

from __future__ import annotations

import math
from typing import Any


def apply_bh_fdr(rows: list[dict[str, Any]], alpha: float, p_key: str = "p_value") -> list[dict[str, Any]]:
    valid = [(index, row) for index, row in enumerate(rows) if isinstance(row.get(p_key), (int, float)) and not math.isnan(row[p_key])]
    total = len(valid)
    adjusted: dict[int, float] = {}
    if total:
        ranked = sorted(valid, key=lambda item: item[1][p_key])
        running_min = 1.0
        for reverse_rank, (index, row) in enumerate(reversed(ranked), start=1):
            rank = total - reverse_rank + 1
            running_min = min(running_min, row[p_key] * total / rank)
            adjusted[index] = min(1.0, running_min)

    enriched: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        new_row = dict(row)
        raw_p = new_row.get(p_key)
        adj_p = adjusted.get(index, math.nan)
        new_row["p_value_fdr"] = adj_p
        new_row["is_significant_raw"] = isinstance(raw_p, (int, float)) and not math.isnan(raw_p) and raw_p < alpha
        new_row["is_significant_fdr"] = isinstance(adj_p, (int, float)) and not math.isnan(adj_p) and adj_p < alpha
        enriched.append(new_row)
    return enriched
