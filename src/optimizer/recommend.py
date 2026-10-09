from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from src.draft.roster import roster_need_score


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _risk_label(sd: float) -> str:
    if sd <= 6:
        return "Low"
    if sd <= 12:
        return "Medium"
    return "High"


def score_available_players(
    available: pd.DataFrame,
    my_picks: list[dict[str, Any]],
    current_overall_pick: int,
    next_pick: int | None,
    current_round: int,
    total_rounds: int,
) -> pd.DataFrame:
    if available.empty:
        return available.copy()

    scored = available.copy()

    # Current consensus quality: strongest players start near 100.
    scored["base_score"] = np.clip(101 - (scored["ecr"] * 0.45), 0, 100)

    # Roster fit.
    scored["roster_fit"] = scored["position"].map(
        lambda p: roster_need_score(p, my_picks)
    )

    # ADP value: being available after market cost is good; reaching is penalized.
    scored["adp_delta"] = current_overall_pick - scored["espn_adp"]
    scored["adp_value"] = np.clip(50 + scored["adp_delta"] * 2.0, 0, 100)

    # Estimated chance the player makes it to the user's following turn.
    if next_pick is None:
        scored["return_probability"] = 0.0
    else:
        scored["return_probability"] = scored["espn_adp"].map(
            lambda adp: _sigmoid((float(adp) - next_pick) / 8.0)
        )
    scored["urgency"] = (1 - scored["return_probability"]) * 100

    # Positional tier pressure: measure ECR gap to next three players at same position.
    scarcity = {}
    for pos, group in scored.sort_values("ecr").groupby("position"):
        values = group["ecr"].tolist()
        idxs = group.index.tolist()
        for i, idx in enumerate(idxs):
            later = values[i + 1 : i + 4]
            gap = (np.mean(later) - values[i]) if later else 0
            scarcity[idx] = float(np.clip(45 + gap * 7, 0, 100))
    scored["scarcity"] = pd.Series(scarcity)

    # Consensus spread is not an injury score; lower spread means safer consensus.
    scored["safety"] = np.clip(100 - scored["sd"] * 3.0, 0, 100)
    scored["consensus_risk"] = scored["sd"].map(_risk_label)

    scored["optimizer_score"] = (
        scored["base_score"] * 0.34
        + scored["roster_fit"] * 0.22
        + scored["urgency"] * 0.16
        + scored["adp_value"] * 0.12
        + scored["scarcity"] * 0.10
        + scored["safety"] * 0.06
    )

    # In 10-team 1QB, keep K/DST late and avoid unnecessary second QB/TE.
    early_special = (scored["position"].isin(["K", "DST"])) & (
        current_round < max(total_rounds - 1, 1)
    )
    scored.loc[early_special, "optimizer_score"] -= 32

    drafted_qbs = sum(p["position"] == "QB" for p in my_picks)
    drafted_tes = sum(p["position"] == "TE" for p in my_picks)
    if drafted_qbs >= 1:
        scored.loc[scored["position"] == "QB", "optimizer_score"] -= 12
    if drafted_tes >= 1:
        scored.loc[scored["position"] == "TE", "optimizer_score"] -= 8

    # Mild bye-week concentration penalty.
    byes = [p.get("bye", 0) for p in my_picks if p.get("bye", 0)]
    scored["bye_conflicts"] = scored["bye"].map(lambda b: byes.count(int(b)) if b else 0)
    scored["optimizer_score"] -= np.clip(scored["bye_conflicts"] * 2.5, 0, 8)

    scored["optimizer_score"] = np.clip(scored["optimizer_score"], 0, 100)
    return scored.sort_values(["optimizer_score", "ecr"], ascending=[False, True])


def recommendation_reason(player: pd.Series, current_pick: int, next_pick: int | None) -> list[str]:
    reasons: list[str] = []

    if player["roster_fit"] >= 90:
        reasons.append(f"Fills an important {player['position']} roster need.")
    elif player["roster_fit"] >= 80:
        reasons.append("Can strengthen a starting or FLEX spot.")

    delta = current_pick - float(player["espn_adp"])
    if delta >= 5:
        reasons.append(f"Strong market value: about {delta:.0f} picks past ESPN ADP.")
    elif delta <= -8:
        reasons.append(f"This is a reach of roughly {abs(delta):.0f} picks versus ESPN ADP.")

    if next_pick is not None:
        p = float(player["return_probability"])
        if p <= 0.25:
            reasons.append(f"Only about a {p:.0%} estimated chance to reach your next turn.")
        elif p >= 0.70:
            reasons.append(f"About a {p:.0%} estimated chance to still be there next turn.")

    if player["scarcity"] >= 70:
        reasons.append(f"A meaningful {player['position']} tier drop follows this player.")

    if int(player.get("bye_conflicts", 0)) >= 2:
        reasons.append(f"Caution: adds another Week {int(player['bye'])} bye conflict.")

    if not reasons:
        reasons.append("Strong blend of consensus rank, roster fit, and draft cost.")
    return reasons[:4]
