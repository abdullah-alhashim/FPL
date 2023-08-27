"""
Script to get data from an FPL league, using FPL API, and write it into a Google Sheet.

Usage:
provide the Google Spreadsheet ID and the base sheet ID using arguments. In the terminal use this command:
>> python FPL_API.py spreadsheet_id base_sheet_id
replace spreadsheet_id base_sheet_id with the actual ids

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
from sys import argv
from Utils import Utils

spreadsheet_id = argv[1]
base_sheet_id = argv[2]
utils = Utils(spreadsheet_id, base_sheet_id)

base = 'https://fantasy.premierleague.com/api'
boot = requests.get(f'{base}/bootstrap-static/').json()
fixtures = requests.get(f'{base}/fixtures/').json()

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
    if not boot['events'][i]['is_next']:
        gameweeks += [boot['events'][i]['id']]
        if boot['events'][i]['is_current']:
            current_gameweek = boot['events'][i]['id']
    else:
        break
assert current_gameweek is not None
# exclude gameweeks that already exist
gameweeks = list(set(gameweeks) - set([int(name[2:]) for name in sheets_names if name != 'base']))

# always include current gameweek
gameweeks += [current_gameweek]
if all([is_loaded_managers_squads,
        not (min(gameweeks) - 1) in managers_squads.keys(),
        min(gameweeks) != 1]):
    gameweeks += [min(gameweeks) - 1]
gameweeks = sorted(np.unique(gameweeks))

chips = {'3xc': 'Triple Captain', 'bboost': 'Bench Boost',
         'freehit': 'Free Hit', 'wildcard': 'Wildcard', None: ''}
for gameweek in gameweeks:
    print(f'GW{gameweek}')
    managers_squads[gameweek] = {}
    squads = pd.DataFrame(index=range(21), columns=range(len(standing) * 2))
    print(f'>> updating {len(standing)} members:')
    manager_ids = []
    managers_picks = []
    squads_ids = []
    print('Getting squads IDs ', end='')
    for user_i in range(len(standing)):
        print('.', end='' if user_i + 1 != len(standing) else '\n')
        manager_id = str(standing[user_i]['entry'])
        manager_ids += [manager_id]
        manager_picks = requests.get(f'{base}/entry/{manager_id}/event/{gameweek}/picks/').json()
        managers_picks += [manager_picks]
        if 'detail' in manager_picks.keys():
            pass  # this manager did not join before this gameweek
        else:
            squad_ids = [pick['element'] for pick in manager_picks['picks']]
            squads_ids.extend(squad_ids)
    # this step was seperated to save time because element-summary requests take some time
    squads_ids = list(np.unique(squads_ids))
    gw_data = []
    print('Loading Gameweek data ', end='')
    for i in squads_ids:
        print('.', end='' if i != squads_ids[-1] else '\n')
        element_summary = requests.get(f"{base}/element-summary/{i}/").json()['history']
        if gameweek <= len(element_summary):
            gw_data += [element_summary[gameweek - 1]]
        else:
            gw_data += [None]

    print('Updating squads ', end='')
    for user_i in range(len(standing)):
        print('.', end='' if user_i + 1 != len(standing) else '\n')
        manager = requests.get(f'{base}/entry/{manager_ids[user_i]}/').json()
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

        manager_total_pts = managers_picks[user_i]['entry_history']['total_points']
        manager_gameweek_pts = managers_picks[user_i]['entry_history']['points']
        manager_bench_pts = managers_picks[user_i]['entry_history']['points_on_bench']
        manager_active_chip = chips[managers_picks[user_i]['active_chip']]

        squad_ids = [pick['element'] for pick in managers_picks[user_i]['picks']]
        squad_names = [_.find(boot['elements'], {'id': i})['web_name'] for i in squad_ids]
        squad_gw_data = [_.find(gw_data, {'element': i}) for i in squad_ids]

        managers_squads[gameweek][manager_name]['names'] = squad_names

        squad_df = pd.DataFrame(columns=['name', 'pts'], index=range(15))
        for i in range(15):
            try:
                if squad_names[i] not in managers_squads[gameweek - 1][manager_name]['names']:
                    squad_df.loc[i, 'name'] = squad_names[i] + ' (new)'
                else:
                    squad_df.loc[i, 'name'] = squad_names[i]
            except KeyError:
                squad_df.loc[i, 'name'] = squad_names[i]

            if managers_picks[user_i]['picks'][i]['is_captain']:
                squad_df.loc[i, 'name'] = squad_df.loc[i, 'name'] + ' (C)'
            elif managers_picks[user_i]['picks'][i]['is_vice_captain']:
                squad_df.loc[i, 'name'] = squad_df.loc[i, 'name'] + ' (V)'
            if squad_gw_data[i] is not None:
                if managers_picks[user_i]['picks'][i]['is_captain']:
                    squad_df.loc[i, 'pts'] = squad_gw_data[i]['total_points'] * managers_picks[user_i]['picks'][i]['multiplier']
                elif managers_picks[user_i]['picks'][i]['is_vice_captain']:
                    squad_df.loc[i, 'pts'] = squad_gw_data[i]['total_points'] * managers_picks[user_i]['picks'][i]['multiplier']
                else:
                    squad_df.loc[i, 'pts'] = squad_gw_data[i]['total_points']

                if squad_gw_data[i]['minutes'] == 0 and _.find(fixtures, {'id': squad_gw_data[i]['fixture']})['finished']:
                    squad_df.loc[i, 'name'] = squad_df.loc[i, 'name'] + ' **'
            else:
                squad_df.loc[i, 'pts'] = '-'

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

        ranks = list(range(1, int(len(squads.columns)/2) + 1))
        range_previous = list(range(-2, len(squads.columns) - 2, 2))
        range_current = list(range(0, len(squads.columns), 2))
        for i in range(len(ranks)):
            if i == 0:
                squads.loc[0, range_current[i]] = ranks[i]
            elif squads.loc[1, range_current[i] + 1] == squads.loc[1, range_previous[i] + 1]:
                squads.loc[0, range_current[i]] = squads.loc[0, range_previous[i]]
            else:
                squads.loc[0, range_current[i]] = ranks[i]

    managers_squads[gameweek]['squads'] = squads
    last_col_index = len(squads.columns) + 1

    utils.df_to_spreadsheet(squads, f'GW{str(gameweek)}', last_col_index)
    print(f'GW{str(gameweek)} updated.\n')

with open('./managers_squads.pickle', 'wb') as f:
    pickle.dump(managers_squads, f)
