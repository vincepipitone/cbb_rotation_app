import numpy as np
import pandas as pd
import requests
from io import StringIO
from sklearn.linear_model import LinearRegression


PREDICTION_TRACKER_URL = "https://www.thepredictiontracker.com/ncaabb25.csv"
CREDIBILITY_COEFFICIENT = 0.15


TEAM_RENAME_DICT = {
    'A&M-Commerce': 'East Texas A&M',
    'Albany-NY': 'Albany',
    'Arkansas-Little Rock': 'Little Rock',
    'Boston': 'Boston University',
    'Cal Poly SLO': 'Cal Poly',
    'Cal Riverside': 'UC Riverside',
    'California Baptist': 'Cal Baptist',
    'Central Conn. St.': 'Central Connecticut',
    'Central Florida': 'UCF',
    'Citadel': 'The Citadel',
    'CS Bakersfield': 'Cal St. Bakersfield',
    'CS Sacramento': 'Sacramento St.',
    'CS Northridge': 'CSUN',
    'Detroit': 'Detroit Mercy',
    'Florida International': 'FIU',
    'Illinois-Chicago': 'Illinois Chicago',
    'IPFW': 'Purdue Fort Wayne',
    'Iu Indianapolis': 'IU Indy',
    'IU Indianapolis': 'IU Indy',
    'LIU Brooklyn': 'LIU',
    'Louisiana-Lafayette': 'Lafayette',
    'Louisiana-Monroe': 'Louisiana Monroe',
    'Loyola-Chicago': 'Loyola Chicago',
    'Loyola-Maryland': 'Loyola MD',
    'McNeese St.': 'McNeese',
    'MD Baltimore Co': 'UMBC',
    'Md. Eastern Shore': 'Maryland Eastern Shore',
    'Miami-Florida': 'Miami FL',
    'Miami-Ohio': 'Miami OH',
    'Middle Tenn St.': 'Middle Tennessee',
    'Miss Valley St.': 'Mississippi Valley St.',
    'Mo Kansas City': 'Kansas City',
    'Mount St. Marys': "Mount St. Mary's",
    'NC Asheville': 'UNC Asheville',
    'NC Central': 'North Carolina Central',
    'NC Charlotte': 'Charlotte',
    'NC Greensboro': 'UNC Greensboro',
    'NC Wilmington': 'UNC Wilmington',
    'Nicholls St.': 'Nicholls',
    'North Carolina St.': 'N.C. State',
    'Pennsylvania': 'Penn',
    'Prairie View': 'Prairie View A&M',
    'SE Louisiana': 'Southeastern Louisiana',
    'SE Missouri St.': 'Southeast Missouri',
    'SIU Edwardsville': 'SIUE',
    'South Carolina Upstat': 'USC Upstate',
    'St. Francis (PA)': 'Saint Francis',
    "St. Joseph's PA": "Saint Joseph's",
    "St. Mary's": "Saint Mary's",
    "St. Peter's": "Saint Peter's",
    'St. Thomas (Mn)': "St. Thomas",
    'SW Missouri St.': 'Missouri St.',
    'Tennessee-Martin': 'Tennessee Martin',
    'Texas A&M Corpus': 'Texas A&M Corpus Chris',
    'Texas Arlington': 'UT Arlington',
    'Texas San Antonio': 'UTSA',
    'Troy St.': 'Troy',
    'Umass Lowell': 'UMass Lowell',
    'VA Commonwealth': 'VCU',
    'Wisconsin-Green Bay': 'Green Bay',
    'Wisconsin-Milwaukee': 'Milwaukee',
    'Nevada': 'Nevada Wolf',
    'Texas A&M-Corpus Christi': 'Texas A&M Corpus Chris',
}


def load_prediction_tracker_data() -> pd.DataFrame:
    response = requests.get(PREDICTION_TRACKER_URL, timeout=30)
    response.raise_for_status()
    data = pd.read_csv(StringIO(response.content.decode("utf-8")))
    data.columns = data.columns.str.strip()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")

    for col in ["home", "road"]:
        data[col] = (
            data[col]
            .astype(str)
            .str.strip()
            .replace(TEAM_RENAME_DICT)
        )

    return data


def load_hca_data(hca_csv_path: str) -> pd.DataFrame:
    hca_data = pd.read_csv(hca_csv_path)
    hca_data.columns = hca_data.columns.str.strip()
    hca_data["Team"] = (
        hca_data["Team"]
        .astype(str)
        .str.strip()
        .replace(TEAM_RENAME_DICT)
    )
    hca_data["HCA"] = pd.to_numeric(hca_data["HCA"], errors="coerce")
    return hca_data


def build_cleaned_data(data: pd.DataFrame, hca_data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()

    line_cols = [
        "line",
        "lineavg", "linemoore", "lineopen", "linedok", "linepugh",
        "linedonc", "linetalis", "lineespn", "linepi", "linedd",
        "linemassey", "linedunk", "lineteamrnks"
    ]

    for col in ["hscore", "rscore", "neutral"] + [c for c in line_cols if c in data.columns]:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    data = data.dropna(subset=["date", "home", "road", "hscore", "rscore"]).copy()
    data = data[(data["hscore"] != 0) & (data["rscore"] != 0)].copy()

    if "line" not in data.columns:
        raise ValueError("PredictionTracker data does not contain a 'line' column.")

    data["spread_home"] = pd.to_numeric(data["line"], errors="coerce")

    # Keep this flip because your source is reversed relative to your preferred convention:
    # home favorite should be negative.
    data["spread_home"] = -data["spread_home"]

    data = data.dropna(subset=["spread_home"]).copy()
    data["neutral"] = data["neutral"].fillna(0)

    hca_lookup = hca_data[["Team", "HCA"]].drop_duplicates().copy()
    home_hca = hca_lookup.rename(columns={"Team": "home", "HCA": "home_hca"})
    road_hca = hca_lookup.rename(columns={"Team": "road", "HCA": "road_hca"})

    games = (
        data.merge(home_hca, on="home", how="left")
            .merge(road_hca, on="road", how="left")
    )

    games["home_hca"] = games["home_hca"].fillna(0)
    games["road_hca"] = games["road_hca"].fillna(0)

    games["actual_diff_home"] = games["hscore"] - games["rscore"]
    games["cover_margin_home"] = games["actual_diff_home"] + games["spread_home"]

    games["neutral_spread_home"] = np.where(
        games["neutral"] == 1,
        games["spread_home"],
        games["spread_home"] + games["home_hca"]
    )

    games["revised_spread_signal_home"] = (
        games["neutral_spread_home"] - CREDIBILITY_COEFFICIENT * games["cover_margin_home"]
    )

    home_side = games[["date", "home"]].rename(columns={"home": "team"}).copy()
    home_side["side"] = "home"

    road_side = games[["date", "road"]].rename(columns={"road": "team"}).copy()
    road_side["side"] = "road"

    team_games = pd.concat([home_side, road_side], ignore_index=True)
    team_games = team_games.sort_values(["team", "date"], ascending=[True, False]).reset_index(drop=True)
    team_games["games_ago_team"] = team_games.groupby("team").cumcount()

    home_games_ago = (
        team_games[team_games["side"] == "home"][["team", "date", "games_ago_team"]]
        .rename(columns={"team": "home", "games_ago_team": "home_games_ago"})
    )

    road_games_ago = (
        team_games[team_games["side"] == "road"][["team", "date", "games_ago_team"]]
        .rename(columns={"team": "road", "games_ago_team": "road_games_ago"})
    )

    games = games.merge(home_games_ago, on=["home", "date"], how="left")
    games = games.merge(road_games_ago, on=["road", "date"], how="left")

    games["home_weight"] = 1 / (games["home_games_ago"] + 0.5)
    games["road_weight"] = 1 / (games["road_games_ago"] + 0.5)

    home_df = pd.DataFrame({
        "date": games["date"],
        "team": games["home"],
        "opponent": games["road"],
        "home_road": "home",
        "neutral": games["neutral"],
        "spread": games["spread_home"],
        "neutral_spread": games["neutral_spread_home"],
        "actual_diff": games["actual_diff_home"],
        "cover_margin": games["cover_margin_home"],
        "games_ago": games["home_games_ago"],
        "team_weight": games["home_weight"],
    })

    road_df = pd.DataFrame({
        "date": games["date"],
        "team": games["road"],
        "opponent": games["home"],
        "home_road": "road",
        "neutral": games["neutral"],
        "spread": -games["spread_home"],
        "neutral_spread": -games["neutral_spread_home"],
        "actual_diff": -games["actual_diff_home"],
        "cover_margin": -games["cover_margin_home"],
        "games_ago": games["road_games_ago"],
        "team_weight": games["road_weight"],
    })

    cleaned_data = pd.concat([home_df, road_df], ignore_index=True)

    all_teams = sorted(set(cleaned_data["team"]).union(set(cleaned_data["opponent"])))
    team_to_idx = {team: idx for idx, team in enumerate(all_teams)}

    cleaned_data["team_idx"] = cleaned_data["team"].map(team_to_idx)
    cleaned_data["opponent_idx"] = cleaned_data["opponent"].map(team_to_idx)

    cleaned_data = cleaned_data.dropna(
        subset=["team", "opponent", "neutral_spread", "actual_diff", "games_ago", "team_idx", "opponent_idx"]
    ).copy()

    cleaned_data["team_weight"] = pd.to_numeric(cleaned_data["team_weight"], errors="coerce")
    missing_weight_mask = cleaned_data["team_weight"].isna() | (cleaned_data["team_weight"] <= 0)
    cleaned_data.loc[missing_weight_mask, "team_weight"] = 1 / (
        cleaned_data.loc[missing_weight_mask, "games_ago"] + 0.5
    )

    cleaned_data["date"] = pd.to_datetime(cleaned_data["date"], errors="coerce")
    cleaned_data = cleaned_data.sort_values(["team", "date"], ascending=[True, False]).reset_index(drop=True)

    return cleaned_data


def build_rankings_revised(cleaned_data: pd.DataFrame) -> pd.DataFrame:
    model_data = cleaned_data.copy()

    teams = sorted(set(model_data["team"]).union(set(model_data["opponent"])))
    team_index = {team: idx for idx, team in enumerate(teams)}

    model_data["team_idx"] = model_data["team"].map(team_index)
    model_data["opponent_idx"] = model_data["opponent"].map(team_index)

    num_teams = len(teams)
    X = np.zeros((len(model_data), num_teams), dtype=float)
    rows = np.arange(len(model_data))

    X[rows, model_data["team_idx"].to_numpy()] = 1.0
    X[rows, model_data["opponent_idx"].to_numpy()] = -1.0

    y = model_data["neutral_spread"].to_numpy(dtype=float)

    weights = model_data["team_weight"].to_numpy(dtype=float)
    weights = np.where(np.isfinite(weights) & (weights > 0), weights, 1e-8)
    weights = weights / weights.sum()

    base_model = LinearRegression(fit_intercept=False)
    base_model.fit(X, y, sample_weight=weights)

    model_data["cover_margin_model"] = model_data["actual_diff"] + model_data["neutral_spread"]
    model_data["revised_spread"] = (
        model_data["neutral_spread"]
        - CREDIBILITY_COEFFICIENT * model_data["cover_margin_model"]
    )

    revised_model = LinearRegression(fit_intercept=False)
    revised_model.fit(X, model_data["revised_spread"].to_numpy(dtype=float), sample_weight=weights)

    rankings_revised = pd.DataFrame({
        "team": teams,
        "power_rating": revised_model.coef_
    }).sort_values("power_rating", ascending=True).reset_index(drop=True)

    rankings_revised.insert(0, "rank", np.arange(1, len(rankings_revised) + 1))
    rankings_revised["power_rating"] = rankings_revised["power_rating"].round(2)

    return rankings_revised


def get_power_rankings(hca_csv_path: str = "data/ncaa_hca.csv") -> pd.DataFrame:
    data = load_prediction_tracker_data()
    hca_data = load_hca_data(hca_csv_path)
    cleaned_data = build_cleaned_data(data, hca_data)
    rankings_revised = build_rankings_revised(cleaned_data)
    return rankings_revised
