from __future__ import annotations

import re
import unicodedata
from io import StringIO

import certifi
import numpy as np
import pandas as pd
import requests

RANKINGS_URL = (
    "https://raw.githubusercontent.com/dynastyprocess/data/"
    "master/files/db_fpecr_latest.csv"
)
PLAYER_IDS_URL = (
    "https://raw.githubusercontent.com/dynastyprocess/data/"
    "master/files/db_playerids.csv"
)
ESPN_ADP_URL = "https://www.fantasypros.com/nfl/adp/ppr-overall.php"
VALID_POSITIONS = {"QB", "RB", "WR", "TE", "DST", "K"}


def _fetch_text(url: str) -> str:
    response = requests.get(
        url,
        timeout=20,
        verify=certifi.where(),
        headers={"User-Agent": "fantasy-football-optimizer/0.1"},
    )
    response.raise_for_status()
    return response.text


def _normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    value = value.lower().replace("jr.", "").replace("sr.", "")
    return re.sub(r"[^a-z0-9]", "", value)


def _load_rankings() -> pd.DataFrame:
    df = pd.read_csv(StringIO(_fetch_text(RANKINGS_URL)), na_values=["NA", "NaN", ""])
    df = df[
        (df["fp_page"] == "/nfl/rankings/ppr-cheatsheets.php")
        & (df["page_type"] == "redraft-overall")
        & (df["ecr_type"] == "ro")
        & (df["pos"].isin(VALID_POSITIONS))
    ].copy()

    for col in ["id", "ecr", "sd", "bye"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["id", "player", "pos", "ecr"])
    df = df.sort_values("ecr").drop_duplicates(subset=["id"], keep="first")
    df["id"] = df["id"].astype(int)
    df["player_id"] = "fp_" + df["id"].astype(str)
    df["position_rank"] = (
        df.groupby("pos")["ecr"].rank(method="first").astype(int)
    )
    df["bye"] = df["bye"].fillna(0).astype(int)
    df["sd"] = df["sd"].fillna(df["sd"].median())
    return df


def _attach_player_ids(df: pd.DataFrame) -> pd.DataFrame:
    try:
        ids = pd.read_csv(
            StringIO(_fetch_text(PLAYER_IDS_URL)),
            usecols=["fantasypros_id", "espn_id", "age", "position", "team"],
            na_values=["NA", ""],
        )
        ids["fantasypros_id"] = pd.to_numeric(ids["fantasypros_id"], errors="coerce")
        ids["espn_id"] = pd.to_numeric(ids["espn_id"], errors="coerce")
        ids = ids.dropna(subset=["fantasypros_id"]).drop_duplicates("fantasypros_id")
        merged = df.merge(
            ids[["fantasypros_id", "espn_id", "age"]],
            left_on="id",
            right_on="fantasypros_id",
            how="left",
        )
    except Exception:
        merged = df.copy()
        merged["espn_id"] = np.nan
        merged["age"] = np.nan

    def headshot(row: pd.Series) -> str:
        if row["pos"] == "DST" or pd.isna(row.get("espn_id")):
            return ""
        return (
            "https://a.espncdn.com/i/headshots/nfl/players/full/"
            f"{int(row['espn_id'])}.png"
        )

    merged["headshot_url"] = merged.apply(headshot, axis=1)
    return merged


def _attach_espn_adp(df: pd.DataFrame) -> pd.DataFrame:
    """Best-effort ESPN PPR ADP enrichment. Falls back cleanly to ECR."""
    df = df.copy()
    df["espn_adp"] = np.nan

    try:
        tables = pd.read_html(StringIO(_fetch_text(ESPN_ADP_URL)))
        table = next(
            t for t in tables
            if any("ESPN" in str(c) for c in t.columns)
            and any("Player" in str(c) for c in t.columns)
        )

        if isinstance(table.columns, pd.MultiIndex):
            table.columns = [str(c[-1]) for c in table.columns]
        else:
            table.columns = [str(c) for c in table.columns]

        player_col = next(c for c in table.columns if "Player" in c)
        espn_col = next(c for c in table.columns if c.strip() == "ESPN")

        candidates = [
            (_normalize_name(name), idx)
            for idx, name in zip(df.index, df["player"])
        ]
        candidates.sort(key=lambda x: len(x[0]), reverse=True)

        matched: dict[int, float] = {}
        for _, row in table.iterrows():
            cell = _normalize_name(row.get(player_col, ""))
            if not cell:
                continue
            adp = pd.to_numeric(row.get(espn_col), errors="coerce")
            if pd.isna(adp):
                continue
            for normalized_name, idx in candidates:
                if normalized_name and normalized_name in cell:
                    matched[idx] = float(adp)
                    break

        if matched:
            for idx, value in matched.items():
                df.at[idx, "espn_adp"] = value
    except Exception:
        pass

    df["espn_adp"] = df["espn_adp"].fillna(df["ecr"])
    df["adp_source"] = np.where(
        np.isclose(df["espn_adp"], df["ecr"]),
        "ECR fallback",
        "ESPN PPR ADP",
    )
    return df


def load_player_pool() -> pd.DataFrame:
    df = _load_rankings()
    df = _attach_player_ids(df)
    df = _attach_espn_adp(df)

    keep = [
        "player_id",
        "player",
        "pos",
        "team",
        "position_rank",
        "bye",
        "ecr",
        "sd",
        "espn_adp",
        "adp_source",
        "headshot_url",
        "age",
        "scrape_date",
    ]
    df = df[keep].rename(columns={"player": "name", "pos": "position"})
    return df.reset_index(drop=True)
