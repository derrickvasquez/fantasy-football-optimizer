from __future__ import annotations


def calculate_pick(round_number: int, draft_position: int, teams: int = 10) -> int:
    if round_number % 2 == 1:
        return (round_number - 1) * teams + draft_position
    return round_number * teams - draft_position + 1


def generate_user_picks(draft_position: int, rounds: int, teams: int = 10) -> list[int]:
    return [
        calculate_pick(round_number, draft_position, teams)
        for round_number in range(1, rounds + 1)
    ]


def selections_until_next_pick(current_pick: int, next_pick: int) -> int:
    return max(next_pick - current_pick - 1, 0)


def round_number(overall_pick: int, teams: int = 10) -> int:
    return ((overall_pick - 1) // teams) + 1


def pick_in_round(overall_pick: int, teams: int = 10) -> int:
    return ((overall_pick - 1) % teams) + 1


def owner_draft_slot(overall_pick: int, teams: int = 10) -> int:
    rnd = round_number(overall_pick, teams)
    slot = pick_in_round(overall_pick, teams)
    if rnd % 2 == 1:
        return slot
    return teams - slot + 1


def next_user_pick(user_picks: list[int], current_overall_pick: int) -> int | None:
    for pick in user_picks:
        if pick >= current_overall_pick:
            return pick
    return None
