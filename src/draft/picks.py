def calculate_pick(
    round_number: int,
    draft_position: int,
    teams: int = 10,
) -> int:
    if round_number % 2 == 1:
        return (round_number - 1) * teams + draft_position

    return round_number * teams - draft_position + 1


def generate_user_picks(
    draft_position: int,
    rounds: int,
    teams: int = 10,
) -> list[int]:
    return [
        calculate_pick(
            round_number=round_number,
            draft_position=draft_position,
            teams=teams,
        )
        for round_number in range(1, rounds + 1)
    ]

def selections_until_next_pick(
    current_pick: int,
    next_pick: int,
) -> int:
    return max(next_pick - current_pick - 1, 0)

if __name__ == "__main__":
    picks = generate_user_picks(
        draft_position=7,
        rounds=4,
        teams=10,
    )

    print(picks)

    for current_pick, next_pick in zip(picks, picks[1:]):
        gap = selections_until_next_pick(
            current_pick=current_pick,
            next_pick=next_pick,
        )

        print(
            f"Pick {current_pick} -> Pick {next_pick}: "
            f"{gap} selections between"
        )