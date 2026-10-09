from __future__ import annotations

from typing import Any

STARTER_ORDER = ["QB", "RB1", "RB2", "WR1", "WR2", "TE", "FLEX", "DST", "K"]
FLEX_POSITIONS = {"RB", "WR", "TE"}


def build_roster(my_picks: list[dict[str, Any]]) -> tuple[dict[str, dict | None], list[dict]]:
    slots: dict[str, dict | None] = {slot: None for slot in STARTER_ORDER}
    bench: list[dict] = []

    for pick in my_picks:
        pos = pick["position"]
        assigned = False

        if pos == "QB" and slots["QB"] is None:
            slots["QB"] = pick
            assigned = True
        elif pos == "RB":
            for slot in ["RB1", "RB2"]:
                if slots[slot] is None:
                    slots[slot] = pick
                    assigned = True
                    break
        elif pos == "WR":
            for slot in ["WR1", "WR2"]:
                if slots[slot] is None:
                    slots[slot] = pick
                    assigned = True
                    break
        elif pos == "TE" and slots["TE"] is None:
            slots["TE"] = pick
            assigned = True
        elif pos == "DST" and slots["DST"] is None:
            slots["DST"] = pick
            assigned = True
        elif pos == "K" and slots["K"] is None:
            slots["K"] = pick
            assigned = True

        if not assigned and pos in FLEX_POSITIONS and slots["FLEX"] is None:
            slots["FLEX"] = pick
            assigned = True

        if not assigned:
            bench.append(pick)

    return slots, bench


def open_starter_slots(my_picks: list[dict[str, Any]]) -> list[str]:
    slots, _ = build_roster(my_picks)
    return [slot for slot, player in slots.items() if player is None]


def roster_need_score(position: str, my_picks: list[dict[str, Any]]) -> float:
    slots, bench = build_roster(my_picks)

    if position == "QB":
        return 95.0 if slots["QB"] is None else 20.0
    if position == "RB":
        if slots["RB1"] is None or slots["RB2"] is None:
            return 100.0
        if slots["FLEX"] is None:
            return 82.0
        return 62.0 if sum(1 for p in bench if p["position"] == "RB") < 2 else 45.0
    if position == "WR":
        if slots["WR1"] is None or slots["WR2"] is None:
            return 100.0
        if slots["FLEX"] is None:
            return 85.0
        return 65.0 if sum(1 for p in bench if p["position"] == "WR") < 2 else 48.0
    if position == "TE":
        return 92.0 if slots["TE"] is None else 28.0
    if position == "DST":
        return 80.0 if slots["DST"] is None else 5.0
    if position == "K":
        return 80.0 if slots["K"] is None else 5.0
    return 50.0
