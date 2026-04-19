"""Pure statistical computations."""

from __future__ import annotations

import hashlib
import math
import random
import statistics
from collections import defaultdict
from typing import Any

from ..constants import ANALYSIS_FAMILIES, RUBRIC_KEYS
from ..types import JoinedRow
from .types import (
    AgreementRow,
    ComparisonRow,
    CriterionEffectResult,
    EffectResult,
    LabelEffectResult,
)


def make_rng(seed: int, namespace: str) -> random.Random:
    # Namespace the RNG so result values do not depend on call order
    digest = hashlib.sha256(f"{seed}:{namespace}".encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else math.nan


def sample_stddev(values: list[float]) -> float:
    return statistics.stdev(values) if len(values) >= 2 else math.nan


def quantile(sorted_values: list[float], probability: float) -> float:
    if not sorted_values:
        return math.nan
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def bootstrap_mean_ci(values: list[float], iterations: int, rng: random.Random) -> dict[str, float]:
    if not values:
        return {"mean": math.nan, "ci_lower": math.nan, "ci_upper": math.nan}
    boot_means: list[float] = []
    for _ in range(iterations):
        sample = [values[rng.randrange(len(values))] for _ in range(len(values))]
        boot_means.append(mean(sample))
    boot_means.sort()
    return {"mean": mean(values), "ci_lower": quantile(boot_means, 0.025), "ci_upper": quantile(boot_means, 0.975)}


def standardized_effect(values: list[float]) -> float:
    sd = sample_stddev(values)
    return mean(values) / sd if values and not math.isnan(sd) and sd != 0 else math.nan


def sign_flip_pvalue(differences: list[float], permutations: int, rng: random.Random) -> dict[str, Any]:
    observed = abs(mean(differences)) if differences else math.nan
    if not differences:
        return {"n": 0, "observed_mean_difference": math.nan, "p_value": math.nan}
    extreme = 0
    for _ in range(permutations):
        simulated = [diff if rng.random() < 0.5 else -diff for diff in differences]
        if abs(mean(simulated)) >= observed - 1e-12:
            extreme += 1
    return {"n": len(differences), "observed_mean_difference": mean(differences), "p_value": (extreme + 1) / (permutations + 1)}


def descriptive_summary(rows: list[JoinedRow]) -> dict[str, Any]:
    by_judge_condition: dict[tuple[str, str], list[float]] = defaultdict(list)
    by_true_model: dict[str, list[float]] = defaultdict(list)
    by_displayed_model: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_judge_condition[(row.judge_name, row.condition)].append(row.overall_score)
        by_true_model[row.true_model].append(row.overall_score)
        by_displayed_model[row.displayed_model].append(row.overall_score)
    return {
        "row_count": len(rows),
        "judges": sorted({row.judge_name for row in rows}),
        "sets": sorted({row.set_name for row in rows}),
        "mean_overall_score_by_judge_and_condition": [
            {"judge_name": judge_name, "condition": condition, "n": len(values), "mean_overall_score": mean(values)}
            for (judge_name, condition), values in sorted(by_judge_condition.items())
        ],
        "mean_overall_score_by_true_model": [
            {"true_model": true_model, "n": len(values), "mean_overall_score": mean(values)}
            for true_model, values in sorted(by_true_model.items())
        ],
        "mean_overall_score_by_displayed_model": [
            {"displayed_model": displayed_model, "n": len(values), "mean_overall_score": mean(values)}
            for displayed_model, values in sorted(by_displayed_model.items())
        ],
    }


def build_effect_result(
    judge_name: str,
    differences: list[float],
    iterations: int,
    rng_ci: random.Random,
    rng_p: random.Random,
) -> dict[str, Any]:
    ci = bootstrap_mean_ci(differences, iterations, rng_ci)
    sig = sign_flip_pvalue(differences, iterations, rng_p)
    return EffectResult(
        judge_name=judge_name,
        n=len(differences),
        observed_mean_difference=ci["mean"],
        ci_lower=ci["ci_lower"],
        ci_upper=ci["ci_upper"],
        standardized_effect_dz=standardized_effect(differences),
        p_value=sig["p_value"],
    ).to_dict()


def build_criterion_effect_result(
    judge_name: str,
    criterion: str,
    differences: list[float],
    iterations: int,
    rng_ci: random.Random,
    rng_p: random.Random,
) -> dict[str, Any]:
    ci = bootstrap_mean_ci(differences, iterations, rng_ci)
    sig = sign_flip_pvalue(differences, iterations, rng_p)
    return CriterionEffectResult(
        judge_name=judge_name,
        criterion=criterion,
        n=len(differences),
        observed_mean_difference=ci["mean"],
        ci_lower=ci["ci_lower"],
        ci_upper=ci["ci_upper"],
        standardized_effect_dz=standardized_effect(differences),
        p_value=sig["p_value"],
    ).to_dict()


def build_label_effect_result(
    judge_name: str,
    displayed_model: str,
    values: list[float],
    iterations: int,
    rng_ci: random.Random,
    p_value: float,
) -> dict[str, Any]:
    ci = bootstrap_mean_ci(values, iterations, rng_ci)
    return LabelEffectResult(
        judge_name=judge_name,
        displayed_model=displayed_model,
        n=len(values),
        mean_centered_score_effect=ci["mean"],
        ci_lower=ci["ci_lower"],
        ci_upper=ci["ci_upper"],
        standardized_effect_d=standardized_effect(values),
        p_value=p_value,
    ).to_dict()


def control_vs_deranged(rows: list[JoinedRow], permutations: int, seed: int) -> list[dict[str, Any]]:
    rng_ci = make_rng(seed, ANALYSIS_FAMILIES["control_vs_deranged"] + ":ci")
    rng_p = make_rng(seed, ANALYSIS_FAMILIES["control_vs_deranged"] + ":p")
    by_block: dict[tuple[str, str], list[JoinedRow]] = defaultdict(list)
    for row in rows:
        by_block[(row.judge_name, row.source_file)].append(row)
    per_judge_diffs: dict[str, list[float]] = defaultdict(list)
    pooled_diffs: list[float] = []
    for (judge_name, _source_file), block_rows in sorted(by_block.items()):
        control_rows = [row for row in block_rows if row.condition == "original"]
        deranged_rows = [row for row in block_rows if row.condition == "deranged"]
        if len(control_rows) != 1 or not deranged_rows:
            continue
        diff = control_rows[0].overall_score - mean([row.overall_score for row in deranged_rows])
        per_judge_diffs[judge_name].append(diff)
        pooled_diffs.append(diff)
    results: list[dict[str, Any]] = []
    for judge_name, diffs in sorted(per_judge_diffs.items()):
        results.append(build_effect_result(judge_name, diffs, permutations, rng_ci, rng_p))
    results.append(build_effect_result("__pooled__", pooled_diffs, permutations, rng_ci, rng_p))
    return results


def criterion_control_vs_deranged(rows: list[JoinedRow], permutations: int, seed: int) -> list[dict[str, Any]]:
    by_block: dict[tuple[str, str], list[JoinedRow]] = defaultdict(list)
    for row in rows:
        by_block[(row.judge_name, row.source_file)].append(row)
    results: list[dict[str, Any]] = []
    for criterion in RUBRIC_KEYS:
        rng_ci = make_rng(seed, f"{ANALYSIS_FAMILIES['criterion_control_vs_deranged']}:{criterion}:ci")
        rng_p = make_rng(seed, f"{ANALYSIS_FAMILIES['criterion_control_vs_deranged']}:{criterion}:p")
        per_judge: dict[str, list[float]] = defaultdict(list)
        pooled: list[float] = []
        for (judge_name, _source_file), block_rows in sorted(by_block.items()):
            control_rows = [row for row in block_rows if row.condition == "original"]
            deranged_rows = [row for row in block_rows if row.condition == "deranged"]
            if len(control_rows) != 1 or not deranged_rows:
                continue
            diff = control_rows[0].scores[criterion] - mean([row.scores[criterion] for row in deranged_rows])
            per_judge[judge_name].append(diff)
            pooled.append(diff)
        for judge_name, diffs in sorted(per_judge.items()):
            results.append(build_criterion_effect_result(judge_name, criterion, diffs, permutations, rng_ci, rng_p))
        results.append(build_criterion_effect_result("__pooled__", criterion, pooled, permutations, rng_ci, rng_p))
    return results


def label_effects(rows: list[JoinedRow], permutations: int, seed: int) -> list[dict[str, Any]]:
    rng_perm = make_rng(seed, ANALYSIS_FAMILIES["displayed_model_effects"] + ":perm")
    rng_ci = make_rng(seed, ANALYSIS_FAMILIES["displayed_model_effects"] + ":ci")
    blocks: dict[tuple[str, str], list[JoinedRow]] = defaultdict(list)
    for row in rows:
        blocks[(row.judge_name, row.source_file)].append(row)
    observed_by_judge_model: dict[tuple[str, str], list[float]] = defaultdict(list)
    pooled_by_model: dict[str, list[float]] = defaultdict(list)
    block_payloads: list[tuple[tuple[str, str], list[str], list[float]]] = []
    for (judge_name, source_file), block_rows in sorted(blocks.items()):
        block_mean = mean([row.overall_score for row in block_rows])
        labels = [row.displayed_model for row in block_rows]
        centered = [row.overall_score - block_mean for row in block_rows]
        block_payloads.append(((judge_name, source_file), labels, centered))
        for row, value in zip(block_rows, centered):
            observed_by_judge_model[(judge_name, row.displayed_model)].append(value)
            pooled_by_model[row.displayed_model].append(value)
    observed_stats = {key: mean(values) for key, values in observed_by_judge_model.items()}
    observed_pooled = {key: mean(values) for key, values in pooled_by_model.items()}
    simulated_counts: dict[tuple[str, str], int] = defaultdict(int)
    pooled_counts: dict[str, int] = defaultdict(int)
    for _ in range(permutations):
        sim_values: dict[tuple[str, str], list[float]] = defaultdict(list)
        sim_pooled: dict[str, list[float]] = defaultdict(list)
        for (_judge_name, _source_file), labels, centered_scores in block_payloads:
            # Shuffle labels within a source-file block to preserve content effects
            shuffled = labels[:]
            rng_perm.shuffle(shuffled)
            for label, centered in zip(shuffled, centered_scores):
                sim_values[(_judge_name, label)].append(centered)
                sim_pooled[label].append(centered)
        for key, observed in observed_stats.items():
            if key in sim_values and abs(mean(sim_values[key])) >= abs(observed) - 1e-12:
                simulated_counts[key] += 1
        for key, observed in observed_pooled.items():
            if key in sim_pooled and abs(mean(sim_pooled[key])) >= abs(observed) - 1e-12:
                pooled_counts[key] += 1
    results: list[dict[str, Any]] = []
    for (judge_name, displayed_model), values in sorted(observed_by_judge_model.items()):
        results.append(
            build_label_effect_result(
                judge_name,
                displayed_model,
                values,
                permutations,
                rng_ci,
                (simulated_counts[(judge_name, displayed_model)] + 1) / (permutations + 1),
            )
        )
    for displayed_model, values in sorted(pooled_by_model.items()):
        results.append(
            build_label_effect_result(
                "__pooled__",
                displayed_model,
                values,
                permutations,
                rng_ci,
                (pooled_counts[displayed_model] + 1) / (permutations + 1),
            )
        )
    return results


def comparison_table(control_results: list[dict[str, Any]], label_results: list[dict[str, Any]], criterion_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pooled_control = next((row for row in control_results if row["judge_name"] == "__pooled__"), None)
    pooled_criteria = [row for row in criterion_results if row["judge_name"] == "__pooled__"]
    pooled_labels = [row for row in label_results if row["judge_name"] == "__pooled__"]
    strongest_label = max(pooled_labels, key=lambda row: abs(row["mean_centered_score_effect"]), default=None)
    table: list[dict[str, Any]] = []
    if pooled_control is not None:
        table.append(
            ComparisonRow(
                effect_type="content_control_vs_deranged_overall",
                target="__overall__",
                estimate=pooled_control["observed_mean_difference"],
                ci_lower=pooled_control["ci_lower"],
                ci_upper=pooled_control["ci_upper"],
                standardized_effect=pooled_control["standardized_effect_dz"],
                p_value=pooled_control["p_value"],
            ).to_dict()
        )
    for row in pooled_criteria:
        table.append(
            ComparisonRow(
                effect_type="content_control_vs_deranged_criterion",
                target=row["criterion"],
                estimate=row["observed_mean_difference"],
                ci_lower=row["ci_lower"],
                ci_upper=row["ci_upper"],
                standardized_effect=row["standardized_effect_dz"],
                p_value=row["p_value"],
            ).to_dict()
        )
    if strongest_label is not None:
        table.append(
            ComparisonRow(
                effect_type="strongest_displayed_label_effect",
                target=strongest_label["displayed_model"],
                estimate=strongest_label["mean_centered_score_effect"],
                ci_lower=strongest_label["ci_lower"],
                ci_upper=strongest_label["ci_upper"],
                standardized_effect=strongest_label["standardized_effect_d"],
                p_value=strongest_label["p_value"],
            ).to_dict()
        )
    return table


def pearson_correlation(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        return math.nan
    mean_x = mean(xs)
    mean_y = mean(ys)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    return num / (den_x * den_y) if den_x and den_y else math.nan


def rankdata(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        avg_rank = (i + j + 2) / 2.0
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg_rank
        i = j + 1
    return ranks


def spearman_correlation(xs: list[float], ys: list[float]) -> float:
    return pearson_correlation(rankdata(xs), rankdata(ys)) if len(xs) == len(ys) and len(xs) >= 2 else math.nan


def mean_pairwise(values: list[float]) -> float:
    cleaned = [value for value in values if not math.isnan(value)]
    return mean(cleaned) if cleaned else math.nan


def judge_agreement(rows: list[JoinedRow]) -> dict[str, Any]:
    by_judge_set: dict[tuple[str, str], dict[str, JoinedRow]] = defaultdict(dict)
    judges = sorted({row.judge_name for row in rows})
    set_names = sorted({row.set_name for row in rows})
    for row in rows:
        by_judge_set[(row.judge_name, row.set_name)][row.source_file] = row
    pairwise: list[dict[str, Any]] = []
    score_corrs: list[float] = []
    rank_corrs: list[float] = []
    top1_matches: list[float] = []
    for index, judge_a in enumerate(judges):
        for judge_b in judges[index + 1:]:
            shared_sets: list[str] = []
            set_score_corrs: list[float] = []
            set_rank_corrs: list[float] = []
            set_top1_matches: list[float] = []
            for set_name in set_names:
                rows_a = by_judge_set.get((judge_a, set_name))
                rows_b = by_judge_set.get((judge_b, set_name))
                if not rows_a or not rows_b:
                    continue
                shared_files = sorted(set(rows_a) & set(rows_b))
                if len(shared_files) < 2:
                    continue
                shared_sets.append(set_name)
                scores_a = [rows_a[source_file].overall_score for source_file in shared_files]
                scores_b = [rows_b[source_file].overall_score for source_file in shared_files]
                ranks_a = [float(rows_a[source_file].rank) for source_file in shared_files]
                ranks_b = [float(rows_b[source_file].rank) for source_file in shared_files]
                set_score_corrs.append(pearson_correlation(scores_a, scores_b))
                set_rank_corrs.append(spearman_correlation(ranks_a, ranks_b))
                top_a = min(shared_files, key=lambda source_file: rows_a[source_file].rank)
                top_b = min(shared_files, key=lambda source_file: rows_b[source_file].rank)
                set_top1_matches.append(1.0 if top_a == top_b else 0.0)
            pair_score = mean_pairwise(set_score_corrs)
            pair_rank = mean_pairwise(set_rank_corrs)
            pair_top1 = mean_pairwise(set_top1_matches)
            if not math.isnan(pair_score):
                score_corrs.append(pair_score)
            if not math.isnan(pair_rank):
                rank_corrs.append(pair_rank)
            if not math.isnan(pair_top1):
                top1_matches.append(pair_top1)
            pairwise.append(
                AgreementRow(
                    judge_a=judge_a,
                    judge_b=judge_b,
                    shared_set_count=len(shared_sets),
                    mean_score_pearson_r=pair_score,
                    mean_rank_spearman_rho=pair_rank,
                    top_rank_match_rate=pair_top1,
                ).to_dict()
            )
    return {"pairwise": pairwise, "pooled_summary": {"judge_count": len(judges), "pair_count": len(pairwise), "mean_pairwise_score_pearson_r": mean_pairwise(score_corrs), "mean_pairwise_rank_spearman_rho": mean_pairwise(rank_corrs), "mean_pairwise_top_rank_match_rate": mean_pairwise(top1_matches)}}
