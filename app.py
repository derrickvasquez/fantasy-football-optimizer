import json
from pathlib import Path
from typing import Any

import streamlit as st


CONFIG_PATH = Path("config/espn_league_data.json")


def load_league_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"League configuration was not found: {CONFIG_PATH}"
        )

    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


league = load_league_config()

st.set_page_config(
    page_title="Fantasy Football Draft Optimizer",
    page_icon="🏈",
    layout="wide",
)

if "draft_started" not in st.session_state:
    st.session_state.draft_started = False

if "draft_position" not in st.session_state:
    st.session_state.draft_position = None

if "rounds" not in st.session_state:
    st.session_state.rounds = None

st.title("Fantasy Football Draft Optimizer")
st.caption(league["league_name"])

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

if start_draft:
    if league["teams"] > 12:
        st.error("This optimizer currently supports a maximum of 12 teams.")

    elif rounds > 16:
        st.error("This optimizer currently supports a maximum of 16 rounds.")

    else:
        st.session_state.draft_started = True
        st.session_state.draft_position = int(draft_position)
        st.session_state.rounds = int(rounds)
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