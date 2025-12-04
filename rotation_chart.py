import requests
import xml.etree.ElementTree as ET
import pandas as pd

# Check if the response was successful
if response.status_code != 200:
    raise Exception(f"Failed to fetch XML data. Status code: {response.status_code}")

# Parse the XML content
root = ET.fromstring(response.content)

# Step 2: Extract and assign periods directly to plays
data = []
current_period = None  # Variable to keep track of the current period

for elem in root.iter():
    # Check if it's a <period> element, and if so, update current_period
    if elem.tag == 'period':
        current_period = elem.attrib.get('number')  # The period number (e.g., 1, 2, etc.)

    # Check if it's a <play> element, and add the current period to the data
    elif elem.tag == 'play':
        row = {
            "time": elem.attrib.get("time"),
            "period": current_period,  # Add the current period to the row
            "team": elem.attrib.get("team"),
            "vh": elem.attrib.get("vh"),  # Home or Visitor
            "uni": elem.attrib.get("uni"),  # Uniform number
            "checkname": elem.attrib.get("checkname"),  # Player's name
            "action": elem.attrib.get("action"),  # Action type (e.g., SUB, SHOT)
            "type": elem.attrib.get("type"),  # Action subtype (e.g., IN, OUT)
            "hscore": elem.attrib.get("hscore"),  # Home score
            "vscore": elem.attrib.get("vscore"),  # Visitor score
        }
        data.append(row)

# Step 3: Convert the list of dictionaries to a DataFrame
allGameData = pd.DataFrame(data)

import re
def clean_name(name):
    # 1. Trim leading/trailing whitespace, convert to uppercase
    name = name.strip().upper()

    # 2. Remove double quotes or any other unwanted characters
    name = name.replace('"', '')

    # 3. (Optional) Collapse multiple spaces into one
    name = re.sub(r'\s+', ' ', name)

    # 4. Remove space(s) after any comma
    #    e.g. "DOE,  JOHN" => "DOE,JOHN"
    name = re.sub(r',\s+', ',', name)

    # 5. Return the final cleaned name
    return name.strip()


# Fetch data from the URL
response = requests.get(url)
response.raise_for_status()

# Parse the XML response
root = ET.fromstring(response.text)

# Find all players with gs="1" (starters)
starters = root.findall(".//player[@gs='1']")

# Extract and clean player names
starter_players = []
for player in starters:
    # Extract player name or any other attribute needed
    player_name = player.get('name', 'Unknown')  # Use 'Unknown' as a fallback
    cleaned_name = clean_name(player_name)  # Clean the player name
    starter_players.append(cleaned_name)  # Append the cleaned name to the list

starter_players = [
    "LINGUARD, JR.,CARLTON" if player == "LINGUARD,JR.,CARLTON" else
    "FLOYD, JR.,COREY" if player == "FLOYD,JR.,COREY" else
    "MCNEIL, JR.,PAUL" if player == "MCNEIL,JR.,PAUL" else player
    for player in starter_players
]

# Debug: Print the cleaned starter players
print("Cleaned Starters:")
for player_name in starter_players:
    print(player_name)

subData = allGameData[allGameData['action'] == 'SUB']
subData = subData.reset_index(drop=True)

# Clean and standardize names in starter_players and checkname
def clean_name(name):
    # Remove leading/trailing spaces, convert to uppercase, replace multiple spaces with single space
    name = re.sub(r'\s+', ' ', name.strip().upper())
    return name

# Apply cleaning function to both starter_players and subData["checkname"]
subData["checkname"] = subData["checkname"].apply(clean_name)

# Debug: Print the cleaned lists to compare
print("Cleaned starter players:", starter_players)
print("Cleaned checkname column:", subData["checkname"].unique())

# Step 1: Create new rows for starters using the cleaned names
new_rows = []
for starter in starter_players:
    # Check if the player exists in subData
    if starter not in subData["checkname"].unique():
        print(f"Warning: {starter} not found in subData['checkname']")
        continue  # Skip this player if not found

    # Extract team, vh (home/visitor), and uni for the starter
    starter_data = subData[subData["checkname"] == starter].iloc[0]
    team = starter_data["team"]
    vh = starter_data["vh"]
    uni = starter_data["uni"]

    # Create a new row for the "SUB IN" action
    new_rows.append({
        "time": "20:00",  # Start of the first period
        "period": "1",  # First period
        "team": team,
        "vh": vh,
        "uni": uni,
        "checkname": starter,
        "action": "SUB",
        "type": "IN",
        "hscore": None,  # No scoring event
        "vscore": None,
    })

# Step 2: Append the new rows to the DataFrame
if new_rows:  # Ensure there are new rows to append
    subData = pd.concat([subData, pd.DataFrame(new_rows)], ignore_index=True)
    subData.reset_index(drop=True, inplace=True)
    subData.drop_duplicates(inplace=True)

# Step 3: Sort the DataFrame by period and time for chronological order
subData.sort_values(by=["period", "time"], inplace=True)

import pandas as pd

# Assuming subData is your DataFrame with the given columns
# Convert the time column to seconds remaining in the period
subData['time_in_seconds'] = subData['time'].str.split(':').apply(lambda x: int(x[0]) * 60 + int(x[1]))

# Filter the data for period = 1
period_1_data = subData[subData['period'] == '1']

# Find the event with the smallest time remaining for each player
last_event = period_1_data.loc[period_1_data.groupby('checkname')['time_in_seconds'].idxmin()]

import pandas as pd

# Assuming subData is your DataFrame
subData['time_in_seconds'] = subData['time'].str.split(':').apply(lambda x: int(x[0]) * 60 + int(x[1]))

# Step 1: Filter data for period = 1
period_1_data = subData[subData['period'] == '1']

# Step 2: Find the last event for each player in period = 1 based on the minimum time
last_event = period_1_data.loc[
    period_1_data.groupby('checkname')['time_in_seconds'].transform('min') == period_1_data['time_in_seconds']
]

# Step 3: Include players who sub IN and OUT at the same time
simultaneous_events = period_1_data.groupby(['checkname', 'time_in_seconds']).filter(
    lambda x: len(x) > 1 and {'IN', 'OUT'}.issubset(set(x['type']))
)

players_on_court_end_period_1 = pd.concat([
    last_event[last_event['type'] == 'IN'],
    simultaneous_events[simultaneous_events['type'] == 'IN']
]).drop_duplicates(subset=['checkname'])

# Step 4: Check for "SUB OUT" at 20:00 in period = 2
period_2_sub_out = subData[(subData['period'] == '2') & (subData['time'] == '20:00') & (subData['action'] == 'SUB') & (subData['type'] == 'OUT')]

# Step 5: Identify players on the court at the end of period 1 who do not have "SUB OUT" at 20:00 in period 2
players_to_add = players_on_court_end_period_1[~players_on_court_end_period_1['checkname'].isin(period_2_sub_out['checkname'])]

# Step 6: Create new rows for "SUB IN" at 20:00 in period = 2
new_rows = players_to_add.copy()
new_rows['time'] = '20:00'
new_rows['time_in_seconds'] = 1200  # 20:00 in seconds
new_rows['period'] = '2'
new_rows['action'] = 'SUB'
new_rows['type'] = 'IN'

# Drop unnecessary columns in the new rows
new_rows = new_rows[['time', 'period', 'team', 'vh', 'uni', 'checkname', 'action', 'type']]

# Step 7: Append the new rows to subData
subData = pd.concat([subData, new_rows], ignore_index=True)

# Optional: Sort the DataFrame if needed
subData = subData.sort_values(by=['period', 'time_in_seconds'], ascending=[True, False]).reset_index(drop=True)

# Create a mapping from checkname to team using allGameData
checkname_team_map = allGameData.dropna(subset=['checkname','team']).drop_duplicates(subset=['checkname'])[['checkname','team']]
name_to_team = dict(zip(checkname_team_map['checkname'], checkname_team_map['team']))

response = requests.get(url)
root = ET.fromstring(response.content)

for player in root.findall('.//player'):
    checkname = player.get('checkname')
    vh = player.get('vh')
    uni = player.get('uni')

    # Lookup the player's team from name_to_team
    player_team = name_to_team.get(checkname, None)

    for stats in player.findall('statsbyprd'):
        prd_str = stats.get('prd')
        mins = stats.get('min')

        if prd_str is None or mins is None:
            continue

        prd = int(prd_str)

        # Check conditions for adding SUB IN at 5:00 in overtime:
        # Condition A: Player played full 5 minutes (mins == "5")
        # Condition B: Player has a SUB OUT event in this OT period
        has_sub_out_in_period = False
        if prd > 2:
            # Check if player has SUB OUT in this period in subData
            period_out = subData[
                (subData['period'] == str(prd)) &
                (subData['checkname'] == checkname) &
                (subData['action'] == 'SUB') &
                (subData['type'] == 'OUT')
            ]
            if not period_out.empty:
                has_sub_out_in_period = True

        # If it's an overtime period and either condition is met
        if prd > 2 and (mins == "5" or has_sub_out_in_period):
            # Check if SUB IN at 5:00 already exists
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

import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.lines as mlines
import matplotlib.patches as mpatches

# Helper functions
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

        # Plot fouls
        player_foul_data = allGameData[
            (allGameData["checkname"] == player) &
            (allGameData["action"] == "FOUL") &
            (allGameData["period"] == str(period))
        ]
        for _, foul_row in player_foul_data.iterrows():
            foul_time = time_to_seconds(foul_row["time"])
            foul_y = player_positions[player]
            foul_time = period_end_time - foul_time
            ax.scatter(foul_time, foul_y, color="black", label="Foul", s=30, marker="x", zorder=5)

def adjust_y_axis(ax, player_labels, player_y_positions):
    ax.set_yticks(player_y_positions)
    ax.set_yticklabels(player_labels, fontsize=10)
    N = len(player_labels)
    ax.set_ylim(-0.5, N - 0.5)
    ax.set_ylabel("Players")

# Assume subData and allGameData are available DataFrames
rotation_data = subData[
    (subData["action"] == "SUB") &
    (subData["type"].isin(["IN", "OUT"]))
].sort_values(by=["team", "checkname", "period", "time"])

teams = rotation_data["team"].unique()

# Identify starters
team_players = {}
for team in teams:
    team_data_period1 = rotation_data[(rotation_data["team"] == team) & (rotation_data["period"] == '1')]
    starters = team_data_period1[
        (team_data_period1["time"] == "20:00") & (team_data_period1["type"] == "IN")
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

# Determine the distinct periods in the game
periods = sorted(rotation_data["period"].unique(), key=lambda x: int(x))
periods = [int(p) for p in periods]

num_periods = len(periods)
if num_periods == 2:
    fig, axes = plt.subplots(1, num_periods, figsize=(12, 10), sharey=True)
else:
    fig, axes = plt.subplots(1, num_periods, figsize=(20, 12), sharey=True)

if num_periods == 1:
    axes = [axes]

for i, period in enumerate(periods):
    # If period > 2, it's overtime (5 minutes = 300 seconds)
    # Otherwise, standard period = 20 minutes = 1200 seconds
    if period > 2:
        current_period_end_time = 300
    else:
        current_period_end_time = 1200

    plot_half(axes[i], period, period_end_time=current_period_end_time)
    axes[i].set_title(f"Period {period}")
    axes[i].set_xlim(0, current_period_end_time)
    # Set x-ticks dynamically based on period length
    tick_interval = current_period_end_time // 4
    axes[i].set_xticks(range(0, current_period_end_time + 1, tick_interval))
    axes[i].set_xticklabels([seconds_to_time(t) for t in range(current_period_end_time, -1, -tick_interval)])
    axes[i].set_xlabel("Game Time (MM:SS)")
    axes[i].grid(axis="x", linestyle="--", alpha=0.7)

player_labels = ordered_players
player_y_positions = [player_positions[p] for p in player_labels]

for ax in axes:
    adjust_y_axis(ax, player_labels, player_y_positions)

# Plot media timeouts for each period
for i, period in enumerate(periods):
    period_str = str(period)
    period_media_timeouts = media_timeouts[media_timeouts['period'] == period_str]

    if period == 1:
        plot_media_timeouts(axes[i], period_media_timeouts,
                            1200 if period <= 2 else 300,
                            base_offset=0, offset_step=0.02)
    else:
        # Use the same logic for period_end_time here as well
        current_period_end_time = 300 if period > 2 else 1200
        plot_media_timeouts(axes[i], period_media_timeouts,
                            current_period_end_time,
                            base_offset=0, offset_step=0.01)

N = len(player_labels)
top_bar_edge = (N-1)*0.5 + 0.2
for ax in axes:
    ax.set_ylim(-0.5, top_bar_edge)

# Create dummy handles for legend
media_timeout_handle = mlines.Line2D([], [], color='black', linestyle=':', label='Media Timeout')
foul_handle = mlines.Line2D([], [], color='black', marker='x', linestyle='None', label='Foul')

# Adjust legend positioning based on number of periods
if num_periods == 2:
    fig.legend(handles=[foul_handle, media_timeout_handle],
               loc='lower center', bbox_to_anchor=(0.58, 0.22), ncol=2)
elif num_periods == 3:
    fig.legend(handles=[foul_handle, media_timeout_handle],
               loc='lower center', bbox_to_anchor=(0.55, 0.25), ncol=2)
else:
    fig.legend(handles=[foul_handle, media_timeout_handle],
               loc='lower center', bbox_to_anchor=(0.55, 0.3), ncol=2)

for i, period in enumerate(periods):
    if period > 2:
        # Overtime period: different aspect ratio
        axes[i].set_aspect('23')  # smaller ratio for OT
    else:
        # Regular period: original aspect ratio
        axes[i].set_aspect('90')

plt.tight_layout()
return fig



