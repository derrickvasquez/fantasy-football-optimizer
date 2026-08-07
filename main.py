import json
from pathlib import Path
from typing import Any


CONFIG_PATH = Path("config/espn_league_data.json")


def load_league_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"League configuration was not found: {CONFIG_PATH}"
        )

    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def main() -> None:
    league = load_league_config()

    print("Fantasy Football Optimizer initialized successfully.")
    print(f"League: {league['league_name']}")
    print(f"Draft type: {league['draft_type'].title()}")
    print(f"Draft positions supported: 1–{league['teams']}")
    print(f"Default rounds: {league['default_rounds']}")


if __name__ == "__main__":
    main()