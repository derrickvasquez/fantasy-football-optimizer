from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
import streamlit as st

from src.data.players import load_player_pool
from src.draft.picks import (
    generate_user_picks,
    next_user_pick,
    owner_draft_slot,
    pick_in_round,
    round_number,
)
from src.draft.roster import build_roster
from src.optimizer.recommend import recommendation_reason, score_available_players
from src.reporting.report import build_report
from src.reporting.pdf_report import build_report_pdf

CONFIG_PATH = Path("config/espn_league.json")


def load_league_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


league = load_league_config()

st.set_page_config(
    page_title="Fantasy Football Draft Optimizer",
    page_icon="🏈",
    layout="wide",
)

# ---------- lightweight visual polish ----------
st.markdown(
    """
    <style>
    .block-container {padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1550px;}
    [data-testid="stMetric"] {background: rgba(120, 85, 255, 0.06); border: 1px solid rgba(150,120,255,.18); padding: 10px 14px; border-radius: 14px;}
    [data-testid="stVerticalBlockBorderWrapper"] {border-color: rgba(150,120,255,.16) !important; border-radius: 16px !important;}
    h1, h2, h3 {letter-spacing: -0.025em;}
    .muted {opacity:.72; font-size:.88rem;}
    .pick-banner {padding:.75rem 1rem; border-radius:14px; background:linear-gradient(90deg, rgba(124,58,237,.18), rgba(59,130,246,.08)); border:1px solid rgba(139,92,246,.30); margin-bottom:.75rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=1800, show_spinner=False)
def get_player_pool() -> pd.DataFrame:
    return load_player_pool()


def init_state() -> None:
    defaults = {
        "draft_started": False,
        "draft_position": None,
        "rounds": league["default_rounds"],
        "history": [],
        "finished": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_draft() -> None:
    st.session_state.draft_started = False
    st.session_state.draft_position = None
    st.session_state.rounds = league["default_rounds"]
    st.session_state.history = []
    st.session_state.finished = False


def add_pick(player: pd.Series, owner: str, overall_pick: int) -> None:
    st.session_state.history.append(
        {
            "player_id": player["player_id"],
            "name": player["name"],
            "position": player["position"],
            "team": player["team"],
            "bye": int(player["bye"]),
            "ecr": float(player["ecr"]),
            "espn_adp": float(player["espn_adp"]),
            "optimizer_score": float(player.get("optimizer_score", 0)),
            "owner": owner,
            "overall_pick": overall_pick,
            "round": round_number(overall_pick, league["teams"]),
            "pick_in_round": pick_in_round(overall_pick, league["teams"]),
            "headshot_url": player.get("headshot_url", ""),
        }
    )
    st.rerun()


init_state()

# ---------- header ----------
st.title("🏈 Fantasy Football Draft Optimizer")
st.caption("Draft Night v0.1 • ESPN 10-Team Full PPR")

setup_1, setup_2, setup_3, setup_4 = st.columns([1, 1, 1.6, 0.8])

with setup_1:
    selected_position = st.selectbox(
        "Draft position",
        list(range(1, league["teams"] + 1)),
        index=(st.session_state.draft_position - 1) if st.session_state.draft_position else 0,
        disabled=st.session_state.draft_started and bool(st.session_state.history),
    )

with setup_2:
    selected_rounds = st.selectbox(
        "Rounds",
        list(range(1, 17)),
        index=int(st.session_state.rounds) - 1,
        disabled=st.session_state.draft_started and bool(st.session_state.history),
    )

with setup_3:
    st.write("")
    st.write("")
    if st.button("Start / Restart Draft", type="primary", use_container_width=True):
        st.session_state.draft_started = True
        st.session_state.draft_position = int(selected_position)
        st.session_state.rounds = int(selected_rounds)
        st.session_state.history = []
        st.session_state.finished = False
        st.rerun()

with setup_4:
    st.write("")
    st.write("")
    if st.button("Reset", use_container_width=True):
        reset_draft()
        st.rerun()

# ---------- data ----------
try:
    with st.spinner("Loading current player rankings..."):
        player_pool = get_player_pool()
except Exception as exc:
    st.error("Player data could not be loaded. Check your internet connection, then refresh.")
    st.exception(exc)
    st.stop()

latest_scrape = str(player_pool["scrape_date"].dropna().max())
data_a, data_b = st.columns([4, 1])
with data_a:
    st.caption(
        f"Rankings source snapshot: {latest_scrape}. ESPN ADP is best-effort; "
        "if unavailable, the app safely falls back to PPR consensus rank."
    )
with data_b:
    if st.button("↻ Refresh Data", use_container_width=True):
        get_player_pool.clear()
        st.rerun()

if not st.session_state.draft_started:
    st.info("Choose your draft slot and rounds, then press **Start / Restart Draft**.")
    st.stop()

# ---------- draft state ----------
teams = league["teams"]
rounds = int(st.session_state.rounds)
max_overall_pick = teams * rounds
current_overall = len(st.session_state.history) + 1
user_picks = generate_user_picks(st.session_state.draft_position, rounds, teams)
current_round = round_number(min(current_overall, max_overall_pick), teams)
current_owner_slot = owner_draft_slot(min(current_overall, max_overall_pick), teams)
is_my_turn = current_owner_slot == st.session_state.draft_position and current_overall <= max_overall_pick
upcoming_user_pick = next_user_pick(user_picks, current_overall)
following_user_pick = None
if upcoming_user_pick is not None:
    try:
        i = user_picks.index(upcoming_user_pick)
        following_user_pick = user_picks[i + 1] if i + 1 < len(user_picks) else None
    except ValueError:
        pass

if current_overall <= max_overall_pick:
    banner = "🟣 **YOUR PICK**" if is_my_turn else f"Opponent draft slot **{current_owner_slot}** is on the clock"
    st.markdown(f'<div class="pick-banner">{banner}</div>', unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Current Overall", current_overall if current_overall <= max_overall_pick else "Done")
m2.metric("Round", current_round if current_overall <= max_overall_pick else rounds)
m3.metric("Your Next Pick", upcoming_user_pick if upcoming_user_pick else "—")
m4.metric(
    "Selections Before Your Pick",
    max((upcoming_user_pick or current_overall) - current_overall, 0) if current_overall <= max_overall_pick else 0,
)

control_a, control_b = st.columns([1, 4])
with control_a:
    if st.button("↶ Undo Last Pick", disabled=not st.session_state.history, use_container_width=True):
        st.session_state.history.pop()
        st.session_state.finished = False
        st.rerun()
with control_b:
    st.caption("✅ = your selection • ❌ = drafted by another manager")

# ---------- derive pools ----------
drafted_ids = {h["player_id"] for h in st.session_state.history}
available = player_pool[~player_pool["player_id"].isin(drafted_ids)].copy()
my_picks = [h for h in st.session_state.history if h["owner"] == "me"]

recommend_next_pick = following_user_pick if is_my_turn else upcoming_user_pick
scored = score_available_players(
    available,
    my_picks,
    current_overall,
    recommend_next_pick,
    current_round,
    rounds,
)
score_lookup = scored.set_index("player_id") if not scored.empty else pd.DataFrame()

# ---------- three-column dashboard ----------
st.divider()
left_col, center_col, right_col = st.columns([1.05, 2.35, 1.15], gap="large")

with left_col:
    st.subheader("Best Next Move")
    if is_my_turn and not scored.empty:
        top = scored.iloc[0]
        with st.container(border=True):
            if top["headshot_url"]:
                st.image(top["headshot_url"], width=120)
            st.markdown(f"### {top['name']}")
            st.write(f"**{top['position']} • {top['team']}**")
            r1, r2 = st.columns(2)
            r1.metric("Optimizer", f"{top['optimizer_score']:.1f}")
            r2.metric("PPR ECR", f"{top['ecr']:.1f}")
            r3, r4 = st.columns(2)
            r3.metric("ESPN ADP", f"{top['espn_adp']:.1f}")
            r4.metric("Bye", int(top["bye"]) if top["bye"] else "—")
            st.caption(f"Consensus volatility: {top['consensus_risk']} (SD {top['sd']:.1f})")
            for reason in recommendation_reason(top, current_overall, recommend_next_pick):
                st.write(f"• {reason}")

        if len(scored) > 1:
            safe = scored.sort_values(["safety", "optimizer_score"], ascending=[False, False]).iloc[0]
            value = scored.sort_values(["adp_value", "optimizer_score"], ascending=[False, False]).iloc[0]
            st.markdown("**Alternatives**")
            st.write(f"🛡️ Safe: **{safe['name']}** ({safe['position']})")
            st.write(f"💎 Value: **{value['name']}** ({value['position']})")
    elif current_overall > max_overall_pick:
        st.success("Draft board complete.")
    else:
        st.info("Mark opponent picks with ❌. Recommendations appear when your pick arrives.")
        if not scored.empty:
            st.caption("Current top consensus options")
            for _, p in scored.head(5).iterrows():
                st.write(f"**{p['name']}** — {p['position']} {p['team']} • ECR {p['ecr']:.1f}")

with center_col:
    st.subheader("Available Players")
    f1, f2, f3 = st.columns([2.2, 1, 1.3])
    with f1:
        search = st.text_input("Search", placeholder="Search player...", label_visibility="collapsed")
    with f2:
        position_filter = st.selectbox("Position", ["ALL", "QB", "RB", "WR", "TE", "DST", "K"], label_visibility="collapsed")
    with f3:
        sort_mode = st.selectbox("Sort", ["Optimizer", "ESPN ADP", "PPR ECR"], label_visibility="collapsed")

    filtered = scored.copy()
    if search:
        filtered = filtered[filtered["name"].str.contains(search, case=False, na=False)]
    if position_filter != "ALL":
        filtered = filtered[filtered["position"] == position_filter]

    if sort_mode == "ESPN ADP":
        filtered = filtered.sort_values("espn_adp")
    elif sort_mode == "PPR ECR":
        filtered = filtered.sort_values("ecr")
    else:
        filtered = filtered.sort_values("optimizer_score", ascending=False)

    st.caption(f"{len(filtered)} players available • showing first 24 cards")
    display = filtered.head(24)

    card_columns = st.columns(4)
    for idx, (_, player) in enumerate(display.iterrows()):
        with card_columns[idx % 4]:
            with st.container(border=True):
                if player["headshot_url"]:
                    st.image(player["headshot_url"], width=92)
                else:
                    st.markdown("### 🏈")
                st.markdown(f"**{player['name']}**")
                st.caption(f"{player['position']} • {player['team']} • Bye {int(player['bye']) if player['bye'] else '—'}")
                st.write(f"ECR **{player['ecr']:.1f}** • ADP **{player['espn_adp']:.1f}**")
                st.write(f"Optimizer **{player['optimizer_score']:.1f}**")
                b1, b2 = st.columns(2)
                with b1:
                    if st.button(
                        "✅",
                        key=f"mine_{player['player_id']}",
                        use_container_width=True,
                        disabled=(not is_my_turn or current_overall > max_overall_pick),
                        help="Draft this player to My Team",
                    ):
                        add_pick(player, "me", current_overall)
                with b2:
                    if st.button(
                        "❌",
                        key=f"other_{player['player_id']}",
                        use_container_width=True,
                        disabled=(is_my_turn or current_overall > max_overall_pick),
                        help="Mark this player drafted by another team",
                    ):
                        add_pick(player, "other", current_overall)

    with st.expander("View full available-player list"):
        full_table = filtered[["name", "position", "team", "bye", "ecr", "espn_adp", "optimizer_score"]].copy()
        full_table.columns = ["Player", "Pos", "Team", "Bye", "PPR ECR", "ESPN ADP", "Optimizer"]
        st.dataframe(full_table, use_container_width=True, hide_index=True, height=520)

with right_col:
    st.subheader("My Team")
    slots, bench = build_roster(my_picks)

    if my_picks:
        st.caption("Newest selection first")
        for pick in reversed(my_picks):
            with st.container(border=True):
                st.markdown(f"**R{pick['round']} • Overall {pick['overall_pick']}**")
                st.write(f"{pick['name']} — {pick['position']} {pick['team']}")
                st.caption(f"ESPN ADP {pick['espn_adp']:.1f} • Bye {pick['bye'] or '—'}")
    else:
        st.info("Your selections will appear here.")

    st.markdown("#### Roster")
    for slot, player in slots.items():
        value = f"{player['name']} ({player['position']})" if player else "—"
        st.write(f"**{slot}:** {value}")
    st.write(f"**Bench:** {len(bench)}/{league['bench_spots']}")
    for player in bench:
        st.caption(f"• {player['name']} — {player['position']}")

    if st.button("🏁 Finish Draft", type="primary", use_container_width=True, disabled=not my_picks):
        st.session_state.finished = True

# ---------- report card ----------
if st.session_state.finished:
    st.divider()
    st.header("Draft Report Card")
    report = build_report(my_picks, rounds)

    if len(my_picks) < rounds:
        st.warning(f"This is an early report: you have {len(my_picks)} of {rounds} expected selections.")

    g1, g2, g3 = st.columns(3)
    g1.metric("Overall Grade", report["grade"], f"{report['score']:.1f}/100")
    g2.metric("Draft Value", report.get("value_grade", "—"), f"{report.get('value_score', 0):.1f}/100")
    g3.metric("Roster Construction", report.get("construction_grade", "—"), f"{report.get('construction_score', 0):.1f}/100")

    g4, g5, g6 = st.columns(3)
    g4.metric("RB/WR Depth", report.get("depth_grade", "—"), f"{report.get('depth_score', 0):.1f}/100")
    g5.metric("Bye Balance", report.get("bye_grade", "—"), f"{report.get('bye_score', 0):.1f}/100")
    g6.metric("Draft Discipline", report.get("discipline_grade", "—"), f"{report.get('discipline_score', 0):.1f}/100")

    st.caption(report.get("methodology", ""))

    best = report.get("best_value")
    reach = report.get("biggest_reach")
    c1, c2 = st.columns(2)
    with c1:
        if best:
            st.success(
                f"Best value: {best['name']} at {best['overall_pick']} "
                f"({best['value_delta']:+.0f} picks vs ADP)."
            )
    with c2:
        if reach:
            st.warning(
                f"Biggest reach: {reach['name']} at {reach['overall_pick']} "
                f"({reach['value_delta']:+.0f} picks vs ADP)."
            )

    st.markdown("#### Pick-by-pick")
    rows = []
    for pick in my_picks:
        delta = pick["overall_pick"] - pick["espn_adp"]
        value_display = (
            round(delta, 1)
            if pick["position"] not in {"K", "DST"}
            else "Special teams"
        )
        rows.append(
            {
                "Round": pick["round"],
                "Overall": pick["overall_pick"],
                "Player": pick["name"],
                "Pos": pick["position"],
                "ESPN ADP": round(pick["espn_adp"], 1),
                "Value vs ADP": value_display,
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    pdf_bytes = build_report_pdf(
        my_picks=my_picks,
        report=report,
        league_name=league["league_name"],
    )

    st.download_button(
        "📄 Download Report Card PDF",
        data=pdf_bytes,
        file_name="fantasy-football-draft-report-card.pdf",
        mime="application/pdf",
        type="primary",
        use_container_width=True,
    )
