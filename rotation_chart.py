import requests
import xml.etree.ElementTree as ET
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import matplotlib.patches as mpatches
import re


def generate_rotation_chart(game_id):
    # -----------------------------------------------------------
    # Build URL from game_id (your required format)
    # -----------------------------------------------------------
    url = f"http://archive.statbroadcast.com/{game_id}.xml"

    # -----------------------------------------------------------
    # Duplicate fetch/parse logic so your original ordering works
    # (Option 1 — preserves exact execution order)
    # -----------------------------------------------------------
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch XML data. Status code: {response.status_code}")

    root = ET.fromstring(response.content)

    # -----------------------------------------------------------
    # Step 2: Extract and assign periods directly to plays
    # -----------------------------------------------------------
    data = []
    current_period = None

    for elem in root.iter():
        if elem.tag == 'period':
            current_period = elem.attrib.get('number')

        elif elem.tag == 'play':
            row = {
                "time": elem.attrib.get("time"),
                "period": current_period,
                "team": elem.attrib.get("team"),
                "vh": elem.attrib.get("vh"),
                "uni": elem.attrib.get("uni"),
                "checkname": elem.attrib.get("checkname"),
                "action": elem.attrib.get("action"),
                "type": elem.attrib.get("type"),
                "hscore": elem.attrib.get("hscore"),
                "vscore": elem.attrib.get("vscore"),
            }
            data.append(row)

    allGameData = pd.DataFrame(data)

    # -----------------------------------------------------------
    # clean_name function (first version)
    # -----------------------------------------------------------
    def clean_name(name):
        name = name.strip().upper()
        name = name.replace('"', '')
        name = re.sub(r'\s+', ' ', name)
        name = re.sub(r',\s+', ',', name)
        return name.strip()

    # -----------------------------------------------------------
    # Fetch AGAIN because your script does this twice (preserve logic)
    # -----------------------------------------------------------
    response = requests.get(url)
    response.raise_for_status()
    root = ET.fromstring(response.text)

    # -----------------------------------------------------------
    # Find starters
    # -----------------------------------------------------------
    starters = root.findall(".//player[@gs='1']")
    starter_players = []
    for player in starters:
        player_name = player.get('name', 'Unknown')
        cleaned_name = clean_name(player_name)
        starter_players.append(cleaned_name)

    # Apply your manual corrections exactly:
    starter_players = [
        "LINGUARD, JR.,CARLTON" if player == "LINGUARD,JR.,CARLTON" else
        "FLOYD, JR.,COREY" if player == "FLOYD,JR.,COREY" else
        "MCNEIL, JR.,PAUL" if player == "MCNEIL,JR.,PAUL" else player
        for player in starter_players
    ]

    print("Cleaned Starters:")
    for player_name in starter_players:
        print(player_name)

    # -----------------------------------------------------------
    # Sub data
    # -----------------------------------------------------------
    subData = allGameData[allGameData['action'] == 'SUB'].reset_index(drop=True)

    # Redefine clean_name (your script does this, we keep it)
    def clean_name(name):
        return re.sub(r'\s+', ' ', name.strip().upper())

    subData["checkname"] = subData["checkname"].apply(clean_name)

    print("Cleaned starter players:", starter_players)
    print("Cleaned checkname column:", subData["checkname"].unique())

    # -----------------------------------------------------------
    # Create SUB IN rows at 20:00 for starters
    # -----------------------------------------------------------
    new_rows = []
    for starter in starter_players:
        if starter not in subData["checkname"].unique():
            print(f"Warning: {starter} not found in subData['checkname']")
            continue

        starter_data = subData[subData["checkname"] == starter].iloc[0]
        new_rows.append({
            "time": "20:00",
            "period": "1",
            "team": starter_data["team"],
            "vh": starter_data["vh"],
            "uni": starter_data["uni"],
            "checkname": starter,
            "action": "SUB",
            "type": "IN",
            "hscore": None,
            "vscore": None,
        })

    if new_rows:
        subData = pd.concat([subData, pd.DataFrame(new_rows)], ignore_index=True)
        subData.drop_duplicates(inplace=True)

    subData.sort_values(by=["period", "time"], inplace=True)

    # -----------------------------------------------------------
    # Compute time_in_seconds, last_event logic (your code preserved)
    # -----------------------------------------------------------
    subData['time_in_seconds'] = subData['time'].str.split(':').apply(lambda x: int(x[0]) * 60 + int(x[1]))
    period_1_data = subData[subData['period'] == '1']

    last_event = period_1_data.loc[
        period_1_data.groupby('checkname')['time_in_seconds'].transform('min')
        == period_1_data['time_in_seconds']
    ]

    simultaneous_events = period_1_data.groupby(['checkname', 'time_in_seconds']).filter(
        lambda x: len(x) > 1 and {'IN', 'OUT'}.issubset(set(x['type']))
    )

    players_on_court_end_period_1 = pd.concat([
        last_event[last_event['type'] == 'IN'],
        simultaneous_events[simultaneous_events['type'] == 'IN']
    ]).drop_duplicates(subset=['checkname'])

    period_2_sub_out = subData[
        (subData['period'] == '2') &
        (subData['time'] == '20:00') &
        (subData['action'] == 'SUB') &
        (subData['type'] == 'OUT')
    ]

    players_to_add = players_on_court_end_period_1[
        ~players_on_court_end_period_1['checkname'].isin(period_2_sub_out['checkname'])
    ]

    new_rows = players_to_add.copy()
    new_rows['time'] = '20:00'
    new_rows['time_in_seconds'] = 1200
    new_rows['period'] = '2'
    new_rows['action'] = 'SUB'
    new_rows['type'] = 'IN'
    new_rows = new_rows[['time', 'period', 'team', 'vh', 'uni', 'checkname', 'action', 'type']]

    subData = pd.concat([subData, new_rows], ignore_index=True)
    subData = subData.sort_values(by=['period', 'time_in_seconds'], ascending=[True, False]).reset_index(drop=True)

    # -----------------------------------------------------------
    # Build mapping checkname -> team
    # -----------------------------------------------------------
    checkname_team_map = allGameData.dropna(subset=['checkname','team']).drop_duplicates(subset=['checkname'])[['checkname','team']]
    name_to_team = dict(zip(checkname_team_map['checkname'], checkname_team_map['team']))

    # Fetch AGAIN (preserve your logic)
    response = requests.get(url)
    root = ET.fromstring(response.content)

    # -----------------------------------------------------------
    # OT SUB IN logic (preserved exactly)
    # -----------------------------------------------------------
    for player in root.findall('.//player'):
        checkname = player.get('checkname')
        vh = player.get('vh')
        uni = player.get('uni')
        player_team = name_to_team.get(checkname, None)

        for stats in player.findall('statsbyprd'):
            prd_str = stats.get('prd')
            mins = stats.get('min')
            if prd_str is None or mins is None:
                continue

            prd = int(prd_str)
            has_sub_out_in_period = False

            if prd > 2:
                period_out = subData[
                    (subData['period'] == str(prd)) &
                    (subData['checkname'] == checkname) &
                    (subData['action'] == 'SUB') &
                    (subData['type'] == 'OUT')
                ]
                if not period_out.empty:
                    has_sub_out_in_period = True

            if prd > 2 and (mins == "5" or has_sub_out_in_period):
                existing = subData[
                    (subData['period'] == str(prd)) &
                    (subData['checkname'] == checkname) &
                    (subData['time'] == '5:00') &
                    (subData['action'] == 'SUB') &
                    (subData['type'] == 'IN')
                ]
                if existing.empty:
                    new_row = {
                        'time': '5:00',
                        'period': str(prd),
                        'team': player_team,
                        'vh': vh,
                        'uni': uni,
                        'checkname': checkname,
                        'action': 'SUB',
                        'type': 'IN'
                    }
                    subData = pd.concat([subData, pd.DataFrame([new_row])], ignore_index=True)

    subData = subData.sort_values(by=['period', 'time'], ascending=[True, False]).reset_index(drop=True)

    # -----------------------------------------------------------
    # Helper functions (your originals preserved)
    # -----------------------------------------------------------
    def time_to_seconds(time_str):
        minutes, seconds = map(int, time_str.split(":"))
        return minutes * 60 + seconds

    def seconds_to_time(seconds):
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02}"

    def plot_media_timeouts(ax, media_timeouts, period_end_time, base_offset=-25, offset_step=.1):
        for i, timeout in media_timeouts.iterrows():
            timeout_time = time_to_seconds(timeout['time'])
            timeout_str = timeout['time']
            timeout_time = period_end_time - timeout_time
            ax.axvline(x=timeout_time, color='black', linestyle=':', linewidth=2)
            label_y = base_offset + i * offset_step
            ax.text(timeout_time, label_y, timeout_str,
                    color='black', fontsize=8,
                    verticalalignment='center', horizontalalignment='right')

    def plot_half(ax, period, period_end_time):
        for player in ordered_players:
            player_data = rotation_data[
                (rotation_data["checkname"] == player) & (rotation_data["period"] == str(period))
            ].sort_values(by="time", ascending=False)

            on_time = None
            for _, row in player_data.iterrows():
                if row["type"] == "IN":
                    on_time = time_to_seconds(row["time"])
                elif row["type"] == "OUT" and on_time is not None:
                    off_time = time_to_seconds(row["time"])
                    player_y = player_positions[player]
                    ax.broken_barh(
                        [(period_end_time - on_time, on_time - off_time)],
                        (player_y - 0.2, 0.4),
                        facecolors=team_colors[row["team"]]
                    )
                    on_time = None

            if on_time is not None:
                player_y = player_positions[player]
                ax.broken_barh(
                    [(period_end_time - on_time, on_time)],
                    (player_y - 0.2, 0.4),
                    facecolors=team_colors[row["team"]]
                )

            # Fouls:
            player_foul_data = allGameData[
                (allGameData["checkname"] == player) &
                (allGameData["action"] == "FOUL") &
                (allGameData["period"] == str(period))
            ]
            for _, foul_row in player_foul_data.iterrows():
                foul_time = time_to_seconds(foul_row["time"])
                foul_y = player_positions[player]
                foul_time = period_end_time - foul_time
                ax.scatter(foul_time, foul_y, color="black", s=30, marker="x", zorder=5)

    def adjust_y_axis(ax, player_labels, player_y_positions):
        ax.set_yticks(player_y_positions)
        ax.set_yticklabels(player_labels, fontsize=10)
        N = len(player_labels)
        ax.set_ylim(-0.5, N - 0.5)
        ax.set_ylabel("Players")

    # -----------------------------------------------------------
    # Build rotation_data (unchanged)
    # -----------------------------------------------------------
    rotation_data = subData[
        (subData["action"] == "SUB") &
        (subData["type"].isin(["IN", "OUT"]))
    ].sort_values(by=["team", "checkname", "period", "time"])

    teams = rotation_data["team"].unique()

    # Identify starters (unchanged)
    team_players = {}
    for team in teams:
        team_data_period1 = rotation_data[
            (rotation_data["team"] == team) &
            (rotation_data["period"] == '1')
        ]
        starters = team_data_period1[
            (team_data_period1["time"] == "20:00") &
            (team_data_period1["type"] == "IN")
        ]["checkname"].unique().tolist()

        all_team_players = rotation_data[rotation_data["team"] == team]["checkname"].unique().tolist()
        bench = [p for p in all_team_players if p not in starters]
        team_players[team] = starters + bench

    ordered_players = (team_players[teams[0]] + team_players[teams[1]])[::-1]
    player_positions = {player: idx * 0.5 for idx, player in enumerate(ordered_players)}

    team_colors = {
        teams[0]: "yellow",
        teams[1]: "green",
    }

    media_timeouts = allGameData[
        (allGameData["checkname"] == "TEAM") &
        (allGameData["action"] == "TIMEOUT") &
        (allGameData["type"] == "MEDIA")
    ]

    # -----------------------------------------------------------
    # Build figure and axes (preserved)
    # -----------------------------------------------------------
    periods = sorted(rotation_data["period"].unique(), key=lambda x: int(x))
    periods = [int(p) for p in periods]
    num_periods = len(periods)

    if num_periods == 2:
        fig, axes = plt.subplots(1, num_periods, figsize=(22, 10), sharey=True)
    else:
        fig, axes = plt.subplots(1, num_periods, figsize=(22, 10), sharey=True)

    if num_periods == 1:
        axes = [axes]

    for i, period in enumerate(periods):
        current_period_end_time = 300 if period > 2 else 1200

        plot_half(axes[i], period, current_period_end_time)
        axes[i].set_title(f"Period {period}")
        axes[i].set_xlim(0, current_period_end_time)

        tick_interval = current_period_end_time // 4
        axes[i].set_xticks(range(0, current_period_end_time + 1, tick_interval))
        axes[i].set_xticklabels([
            seconds_to_time(t)
            for t in range(current_period_end_time, -1, -tick_interval)
        ])
        axes[i].set_xlabel("Game Time (MM:SS)")
        axes[i].grid(axis="x", linestyle="--", alpha=0.7)

    player_labels = ordered_players
    player_y_positions = [player_positions[p] for p in player_labels]

    for ax in axes:
        adjust_y_axis(ax, player_labels, player_y_positions)

    # -----------------------------------------------------------
    # Plot media timeouts
    # -----------------------------------------------------------
    for i, period in enumerate(periods):
        period_str = str(period)
        period_media_timeouts = media_timeouts[media_timeouts['period'] == period_str]

        if period == 1:
            plot_media_timeouts(
                axes[i], period_media_timeouts,
                1200, base_offset=0, offset_step=0.02
            )
        else:
            current_period_end_time = 300 if period > 2 else 1200
            plot_media_timeouts(
                axes[i], period_media_timeouts,
                current_period_end_time,
                base_offset=0, offset_step=0.01
            )

    # -----------------------------------------------------------
    # Set legend
    # -----------------------------------------------------------
    media_timeout_handle = mlines.Line2D([], [], color='black', linestyle=':', label='Media Timeout')
    foul_handle = mlines.Line2D([], [], color='black', marker='x', linestyle='None', label='Foul')

    if num_periods == 2:
        fig.legend(handles=[foul_handle, media_timeout_handle],
                   loc='lower center', bbox_to_anchor=(0.58, 0.22), ncol=2)
    elif num_periods == 3:
        fig.legend(handles=[foul_handle, media_timeout_handle],
                   loc='lower center', bbox_to_anchor=(0.55, 0.25), ncol=2)
    else:
        fig.legend(handles=[foul_handle, media_timeout_handle],
                   loc='lower center', bbox_to_anchor=(0.55, 0.3), ncol=2)

    # -----------------------------------------------------------
    # Final layout + return fig (instead of plt.show)
    # -----------------------------------------------------------
    plt.tight_layout(pad=3.0)
    return fig



