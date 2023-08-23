"""
Script to get data from an FPL league, using FPL API, and write it into a Google Sheet.

Usage:
set Google Spreadsheet ID using keyring.set_password()
keyring.set_password('FPL', 'spreadsheet_id', '')
keyring.set_password('FPL', 'base_sheet_id', '')

The Google Spreadsheet ID can be found in the URL:
docs.google.com/spreadsheets/d/{Google Spreadsheet ID}/edit#gid={Base Sheet ID}


Author:
Abdullah Alhashim
Created on Sat Aug 12, 2023
"""
import numpy as np
import requests
import pickle
import pydash as _
import pandas as pd
import keyring
from alive_progress import alive_it
from Utils import Utils

spreadsheet_id = keyring.get_password('FPL', 'spreadsheet_id')
base_sheet_id = keyring.get_password('FPL', 'base_sheet_id')
utils = Utils(spreadsheet_id, base_sheet_id)

base = 'https://fantasy.premierleague.com/api'
boot = requests.get(f'{base}/bootstrap-static/').json()

# league_id = '776661'  # Mr. Shawarma League
league_id = '669630'  # Al Laith League
# league_id = '923039'  # TOURS ART CHAMPIONS

league = requests.get(f'{base}/leagues-classic/{league_id}/standings').json()
standing = league['standings']['results']
page = 2
while league['standings']['has_next']:
    league = requests.get(f'{base}/leagues-classic/{league_id}/standings',
                          params={'page_standings': page}).json()
    standing += league['standings']['results']
    page += 1

managers_squads = {}
is_loaded_managers_squads = False
try:
    with open('managers_squads.pickle', 'rb') as f:
        managers_squads = pickle.load(f)
        is_loaded_managers_squads = True
except FileNotFoundError:
    pass

sheets_names = utils.get_sheets_names()
gameweeks = []
current_gameweek = None
for i in range(len(boot['events'])):
    if boot['events'][i]['is_previous']:
        gameweeks += [boot['events'][i]['id']]
    elif boot['events'][i]['is_current']:
        current_gameweek = boot['events'][i]['id']
    else:
        break
assert current_gameweek is not None
# exclude gameweeks that already exist
gameweeks = list(set(gameweeks) - set([int(name[2:]) for name in sheets_names if name != 'base']))

# always include current gameweek
gameweeks += [current_gameweek]
if is_loaded_managers_squads and not (min(gameweeks) - 1) in managers_squads.keys():
    gameweeks += [min(gameweeks) - 1] if min(gameweeks) != 1 else []
gameweeks = sorted(np.unique(gameweeks))

chips = {'3xc': 'Triple Captain', 'bboost': 'Bench Boost',
         'freehit': 'Free Hit', 'wildcard': 'Wildcard', None: ''}
for gameweek in gameweeks:
    print(f'GW{gameweek}')
    managers_squads[gameweek] = {}
    squads = pd.DataFrame(index=range(21), columns=range(len(standing) * 2))
    for user_i in alive_it(range(len(standing)), theme='classic', force_tty=True):
        # for user_i in range(len(standing)):  # without progress bar
        manager_id = str(standing[user_i]['entry'])
        manager = requests.get(f'{base}/entry/{manager_id}/').json()
        if manager['started_event'] > gameweek:
            squads.drop([user_i * 2, user_i * 2 + 1], axis=1, inplace=True)
            continue

        manager_name = manager['name']
        if manager_name not in managers_squads[gameweek].keys():
            managers_squads[gameweek][manager_name] = {}
        if gameweek == current_gameweek:
            manager_rank = standing[user_i]['rank']
        elif gameweek == current_gameweek - 1:
            manager_rank = standing[user_i]['last_rank']
        else:
            manager_rank = ''  # if 2 gameweeks pass without updating, the rank is lost. The sorting done later.
        manager_picks = requests.get(f'{base}/entry/{manager_id}/event/{gameweek}/picks/').json()
        manager_total_pts = manager_picks['entry_history']['total_points']
        manager_gameweek_pts = manager_picks['entry_history']['points']
        manager_bench_pts = manager_picks['entry_history']['points_on_bench']
        manager_active_chip = chips[manager_picks['active_chip']]
        squad_ids = [pick['element'] for pick in manager_picks['picks']]
        squad_names = [_.find(boot['elements'], {'id': i})['web_name'] for i in squad_ids]
        managers_squads[gameweek][manager_name]['names'] = squad_names

        if gameweek == current_gameweek:
            squad_gw_pts = [_.find(boot['elements'], {'id': i})['event_points'] for i in squad_ids]
            squad_gw_minutes = [_.find(boot['elements'], {'id': i})['minutes'] for i in squad_ids]
        else:  # this step takes a long time
            squad_gw_data = [requests.get(f"{base}/element-summary/{i}/").json()['history'][gameweek - 1]
                             for i in squad_ids]
            squad_gw_pts = [player['total_points'] for player in squad_gw_data]
            squad_gw_minutes = [player['minutes'] for player in squad_gw_data]

        squad_df = pd.DataFrame(columns=['name', 'pts'], index=range(15))
        for i in range(15):
            try:
                if squad_names[i] not in managers_squads[gameweek - 1][manager_name]['names']:
                    squad_df.loc[i, 'name'] = squad_names[i] + ' (new)'
                else:
                    squad_df.loc[i, 'name'] = squad_names[i]
            except KeyError:
                squad_df.loc[i, 'name'] = squad_names[i]

            if manager_picks['picks'][i]['is_captain']:
                squad_df.loc[i] = [squad_df.loc[i, 'name'] + ' (C)',
                                   squad_gw_pts[i] * manager_picks['picks'][i]['multiplier']]
            elif manager_picks['picks'][i]['is_vice_captain']:
                squad_df.loc[i] = [squad_df.loc[i, 'name'] + ' (V)',
                                   squad_gw_pts[i] * manager_picks['picks'][i]['multiplier']]
            else:
                squad_df.loc[i, 'pts'] = squad_gw_pts[i]

            if squad_gw_minutes[i] == 0:
                squad_df.loc[i, 'name'] = squad_df.loc[i, 'name'] + ' **'

        # add data to Google sheet (first run should ask for permission and .pickle file will be created)
        manager_col1 = pd.DataFrame([manager_rank] +
                                    [manager_name] +
                                    [f"{manager['player_first_name']} {manager['player_last_name']}"] +
                                    ['Starters:'] +
                                    squad_df.loc[:10, 'name'].tolist() +
                                    ['Subs:'] +
                                    squad_df.loc[11:, 'name'].tolist() +
                                    [manager_active_chip])
        manager_col2 = pd.DataFrame([''] +
                                    [manager_total_pts] +
                                    [''] +
                                    [manager_gameweek_pts] +
                                    squad_df.loc[:10, 'pts'].tolist() +
                                    [manager_bench_pts] +
                                    squad_df.loc[11:, 'pts'].tolist() +
                                    [''])
        squads.loc[:, user_i*2] = manager_col1
        squads.loc[:, user_i*2 + 1] = manager_col2
    if gameweek != current_gameweek:
        squads_sorted = pd.DataFrame(index=range(21), columns=range(int(len(squads.columns)/2)))
        for i, ind in enumerate(range(1, len(squads.columns), 2)):
            argsort = list(np.argsort(squads.iloc[1, range(1, len(squads.columns), 2)])[::-1])[i]
            squads_sorted.loc[:, ind - 1] = squads.loc[:, argsort * 2]
            squads_sorted.loc[:, ind] = squads.loc[:, argsort * 2 + 1]
        squads = squads_sorted
    managers_squads[gameweek]['squads'] = squads
    last_col_index = len(squads.columns) + 1

    with open('./managers_squads.pickle', 'wb') as f:
        pickle.dump(managers_squads, f)

    utils.df_to_spreadsheet(squads, f'GW{str(gameweek)}', last_col_index)
