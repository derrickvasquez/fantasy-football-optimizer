import json
from pathlib import Path
from typing import Any

import streamlit as st

from src.draft.picks import (
    generate_user_picks,
    selections_until_next_pick,
)


CONFIG_PATH = Path("config/espn_league.json")


def load_league_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"League configuration was not found: {CONFIG_PATH}"
        )

    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


league = load_league_config()


# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="Fantasy Football Draft Optimizer",
    page_icon="🏈",
    layout="wide",
)


# ---------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------

if "draft_started" not in st.session_state:
    st.session_state.draft_started = False

if "draft_position" not in st.session_state:
    st.session_state.draft_position = None

if "rounds" not in st.session_state:
    st.session_state.rounds = None


# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------

st.title("Fantasy Football Draft Optimizer")
st.caption(league["league_name"])


# ---------------------------------------------------------
# DRAFT SETUP
# ---------------------------------------------------------

control_1, control_2, control_3 = st.columns([1, 1, 2])

with control_1:
    draft_position = st.selectbox(
        "Draft position",
        options=list(range(1, league["teams"] + 1)),
        index=0,
    )

with control_2:
    rounds = st.selectbox(
        "Number of rounds",
        options=list(range(1, 17)),
        index=league["default_rounds"] - 1,
    )

with control_3:
    st.write("")
    st.write("")

    start_draft = st.button(
        "Start Draft",
        type="primary",
        use_container_width=True,
    )


# ---------------------------------------------------------
# START DRAFT
# ---------------------------------------------------------

if start_draft:
    st.session_state.draft_started = True
    st.session_state.draft_position = int(draft_position)
    st.session_state.rounds = int(rounds)


# ---------------------------------------------------------
# ACTIVE DRAFT
# ---------------------------------------------------------

if st.session_state.draft_started:
    st.success(
        f"Draft active — Position {st.session_state.draft_position}, "
        f"{st.session_state.rounds} rounds."
    )

    user_picks = generate_user_picks(
        draft_position=st.session_state.draft_position,
        rounds=st.session_state.rounds,
        teams=league["teams"],
    )

    # Current draft state
    current_pick = user_picks[0]

    if len(user_picks) > 1:
        next_pick = user_picks[1]

        gap = selections_until_next_pick(
            current_pick=current_pick,
            next_pick=next_pick,
        )
    else:
        next_pick = None
        gap = 0

    # -----------------------------------------------------
    # DRAFT STATUS
    # -----------------------------------------------------

    status_1, status_2, status_3 = st.columns(3)

    with status_1:
        st.metric(
            "Current Pick",
            current_pick,
        )

    with status_2:
        st.metric(
            "Next Pick",
            next_pick if next_pick is not None else "Final Round",
        )

    with status_3:
        st.metric(
            "Selections Until Next Pick",
            gap,
        )

    # -----------------------------------------------------
    # USER PICK SCHEDULE
    # -----------------------------------------------------

    st.subheader("Your Draft Picks")

    pick_columns = st.columns(4)

    for index, overall_pick in enumerate(user_picks):
        round_number = index + 1

        with pick_columns[index % 4]:
            st.metric(
                label=f"Round {round_number}",
                value=f"Pick {overall_pick}",
            )


# ---------------------------------------------------------
# MAIN DASHBOARD
# ---------------------------------------------------------

st.divider()

left_col, center_col, right_col = st.columns([1, 2, 1])

with left_col:
    st.subheader("Best Next Move")
    st.info("Recommendations will appear here.")

with center_col:
    st.subheader("Available Players")
    st.info("Player cards will appear here.")

with right_col:
    st.subheader("My Team")
    st.info("Your drafted players will appear here.")

    if st.session_state.draft_started:
        st.button(
            "Finish Draft",
            use_container_width=True,
        )