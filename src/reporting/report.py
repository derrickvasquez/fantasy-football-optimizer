from __future__ import annotations

import math
from collections import Counter
from typing import Any

import numpy as np

from src.draft.roster import build_roster

CORE_VALUE_POSITIONS = {"QB", "RB", "WR", "TE"}
SPECIAL_POSITIONS = {"K", "DST"}


def letter_grade(score: float) -> str:
    """Convert a 0-100 score to a conventional letter grade."""
    if score >= 97:
        return "A+"
    if score >= 93:
        return "A"
    if score >= 90:
        return "A-"
    if score >= 87:
        return "B+"
    if score >= 83:
        return "B"
    if score >= 80:
        return "B-"
    if score >= 77:
        return "C+"
    if score >= 73:
        return "C"
    if score >= 70:
        return "C-"
    if score >= 60:
        return "D"
    return "F"


def _draft_value_score(my_picks: list[dict[str, Any]]) -> tuple[float, float]:
    """Grade market value without allowing K/DST ADP to dominate the result.

    A draft that follows market ADP should land around 80 (B-), not 50/F.
    Each offensive pick's value delta is capped at +/-20 picks, and earlier
    rounds receive a modestly larger weight.
    """
    weighted_deltas: list[float] = []
    weights: list[float] = []

    for pick in my_picks:
        if pick.get("position") not in CORE_VALUE_POSITIONS:
            continue

        adp = pick.get("espn_adp")
        if adp in (None, ""):
            continue

        try:
            adp_value = float(adp)
        except (TypeError, ValueError):
            continue

        if adp_value <= 0:
            continue

        delta = float(pick["overall_pick"]) - adp_value
        capped_delta = float(np.clip(delta, -20, 20))
        round_num = max(int(pick.get("round", 1)), 1)
        weight = 1.0 / math.pow(round_num, 0.30)

        weighted_deltas.append(capped_delta * weight)
        weights.append(weight)

    if not weights:
        return 80.0, 0.0

    weighted_average = sum(weighted_deltas) / sum(weights)

    # Be slightly harsher on reaching than on finding equivalent value.
    multiplier = 1.0 if weighted_average >= 0 else 1.20
    score = 80.0 + (weighted_average * multiplier)
    return float(np.clip(score, 45, 100)), float(weighted_average)


def _construction_score(
    my_picks: list[dict[str, Any]],
    total_rounds: int,
) -> float:
    slots, bench = build_roster(my_picks)

    # 70 points for filling every required starter slot.
    starter_completion = sum(player is not None for player in slots.values()) / len(slots)
    score = starter_completion * 70.0

    # 20 points for using the expected bench capacity in a completed draft.
    expected_bench = max(total_rounds - len(slots), 0)
    if expected_bench == 0:
        score += 20.0
    else:
        score += min(len(bench) / expected_bench, 1.0) * 20.0

    # 10 points for avoiding excessive one-start-position redundancy.
    score += 10.0
    counts = Counter(p.get("position") for p in my_picks)
    # In a 10-team 1QB league, a second QB/TE is allowed but usually costs
    # a small amount of bench upside compared with another RB/WR lottery ticket.
    score -= max(counts.get("QB", 0) - 1, 0) * 2.0
    score -= max(counts.get("TE", 0) - 1, 0) * 2.0
    score -= max(counts.get("K", 0) - 1, 0) * 8.0
    score -= max(counts.get("DST", 0) - 1, 0) * 8.0

    return float(np.clip(score, 0, 100))


def _depth_score(my_picks: list[dict[str, Any]], total_rounds: int) -> float:
    """Reward usable RB/WR depth and a reasonably balanced skill-position room."""
    rb_count = sum(p.get("position") == "RB" for p in my_picks)
    wr_count = sum(p.get("position") == "WR" for p in my_picks)
    rb_wr_total = rb_count + wr_count

    # In a 16-round 1QB league, ~9 RB/WR selections is a strong target.
    target_total = max(6, total_rounds - 7)
    total_component = min(rb_wr_total / target_total, 1.0) * 70.0

    # Avoid a roster that is deep at only one of RB/WR.
    rb_target = 4 if total_rounds >= 14 else 3
    wr_target = 4 if total_rounds >= 14 else 3
    rb_component = min(rb_count / rb_target, 1.0) * 15.0
    wr_component = min(wr_count / wr_target, 1.0) * 15.0

    return float(np.clip(total_component + rb_component + wr_component, 0, 100))


def _bye_balance_score(my_picks: list[dict[str, Any]]) -> float:
    """Measure concentrated bye-week risk among offensive starters only."""
    slots, _ = build_roster(my_picks)
    offensive_slots = ["QB", "RB1", "RB2", "WR1", "WR2", "TE", "FLEX"]
    byes = []

    for slot in offensive_slots:
        player = slots.get(slot)
        if not player:
            continue
        bye = player.get("bye")
        if bye:
            try:
                byes.append(int(bye))
            except (TypeError, ValueError):
                pass

    counts = Counter(byes)
    penalty = 0.0
    for count in counts.values():
        if count > 1:
            penalty += (count - 1) * 5.0
        if count >= 3:
            penalty += 5.0

    return float(np.clip(100.0 - penalty, 55, 100))


def _discipline_score(my_picks: list[dict[str, Any]], total_rounds: int) -> float:
    """Grade roster-cost discipline without double-counting K/DST against ADP."""
    score = 100.0

    # Reasonable windows in a 16-round 10-team league: DST around R13+, K around R14+.
    dst_target_round = max(total_rounds - 3, 1)
    kicker_target_round = max(total_rounds - 2, 1)

    position_rounds: dict[str, list[int]] = {}
    for pick in my_picks:
        position_rounds.setdefault(str(pick.get("position")), []).append(int(pick.get("round", 1)))

    for round_num in position_rounds.get("DST", [])[:1]:
        if round_num < dst_target_round:
            score -= min((dst_target_round - round_num) * 6.0, 24.0)

    for round_num in position_rounds.get("K", [])[:1]:
        if round_num < kicker_target_round:
            score -= min((kicker_target_round - round_num) * 6.0, 24.0)

    # Extra K/DST slots are usually dead roster value.
    score -= max(len(position_rounds.get("K", [])) - 1, 0) * 18.0
    score -= max(len(position_rounds.get("DST", [])) - 1, 0) * 18.0

    # Backup QB/TE is fine late; penalize only if the second one came notably early.
    for pos in ("QB", "TE"):
        rounds = sorted(position_rounds.get(pos, []))
        if len(rounds) >= 2:
            second_round = rounds[1]
            if second_round <= max(total_rounds - 6, 8):
                score -= 10.0
            elif second_round <= max(total_rounds - 4, 10):
                score -= 6.0
            else:
                score -= 2.0

    return float(np.clip(score, 0, 100))


def build_report(my_picks: list[dict[str, Any]], total_rounds: int) -> dict[str, Any]:
    if not my_picks:
        return {
            "score": 0.0,
            "grade": "F",
            "value_score": 0.0,
            "construction_score": 0.0,
            "depth_score": 0.0,
            "bye_score": 0.0,
            "discipline_score": 0.0,
            "best_value": None,
            "biggest_reach": None,
        }

    slots, bench = build_roster(my_picks)

    value_score, weighted_value_delta = _draft_value_score(my_picks)
    construction_score = _construction_score(my_picks, total_rounds)
    depth_score = _depth_score(my_picks, total_rounds)
    bye_score = _bye_balance_score(my_picks)
    discipline_score = _discipline_score(my_picks, total_rounds)

    score = (
        value_score * 0.35
        + construction_score * 0.25
        + depth_score * 0.20
        + bye_score * 0.10
        + discipline_score * 0.10
    )
    score = float(np.clip(score, 0, 100))

    enriched = []
    graded_picks = []
    for p in my_picks:
        item = dict(p)
        adp = float(p.get("espn_adp", p["overall_pick"]))
        item["value_delta"] = float(p["overall_pick"]) - adp
        item["graded_for_value"] = p.get("position") in CORE_VALUE_POSITIONS
        enriched.append(item)
        if item["graded_for_value"]:
            graded_picks.append(item)

    best_value = max(graded_picks, key=lambda p: p["value_delta"]) if graded_picks else None
    biggest_reach = min(graded_picks, key=lambda p: p["value_delta"]) if graded_picks else None

    return {
        "score": score,
        "grade": letter_grade(score),
        "value_score": value_score,
        "value_grade": letter_grade(value_score),
        "weighted_value_delta": weighted_value_delta,
        "construction_score": construction_score,
        "construction_grade": letter_grade(construction_score),
        "depth_score": depth_score,
        "depth_grade": letter_grade(depth_score),
        "bye_score": bye_score,
        "bye_grade": letter_grade(bye_score),
        "discipline_score": discipline_score,
        "discipline_grade": letter_grade(discipline_score),
        "best_value": best_value,
        "biggest_reach": biggest_reach,
        "slots": slots,
        "bench": bench,
        "methodology": (
            "Draft Value excludes K/DST, caps each offensive ADP delta at +/-20 picks, "
            "and gives earlier rounds modestly more weight. Overall grade = 35% Draft Value, "
            "25% Roster Construction, 20% RB/WR Depth, 10% Bye Balance, and 10% Draft Discipline."
        ),
    }
