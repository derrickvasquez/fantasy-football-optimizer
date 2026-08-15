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