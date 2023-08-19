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

import requests
import pydash as _
import pandas as pd
import keyring
from alive_progress import alive_it
from string import ascii_uppercase
from Utils import utils


spreadsheet_id = keyring.get_password('FPL', 'spreadsheet_id')
base_sheet_id = keyring.get_password('FPL', 'base_sheet_id')
spreadsheet = utils.create_spreadsheet()

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

sheets_names = utils.get_sheets_names(spreadsheet_id, base_sheet_id)
gameweeks = []
for i in range(len(boot['events'])):
    if boot['events'][i]['is_previous']:
        gameweeks += [boot['events'][i]['id']]
    elif boot['events'][i]['is_current']:
        gameweeks += [boot['events'][i]['id']]
    else:
        break
# exclude gameweeks that already exist
gameweeks = list(set(gameweeks) - set([int(sheets_names[i][2:]) for i in range(len(sheets_names))]))

colNames = [letter + letter2
            for letter in [''] + list(ascii_uppercase[:int(len(standing) * 2 / 26 // 1 + 1)])
            for letter2 in list(ascii_uppercase)]
chips = {'3xc': 'Triple Captain', 'bboost': 'Bench Boost',
         'freehit': 'Free Hit', 'wildcard': 'Wildcard', None: ''}
for gameweek in gameweeks:
    squads = pd.DataFrame()
    managers_picks = []
    for user_i in alive_it(range(1, len(standing) + 1), theme='classic', force_tty=True):
        # for user_i in range(1, len(standing)):
        manager_id = str(standing[user_i - 1]['entry'])
        manager = requests.get(f'{base}/entry/{manager_id}/').json()
        if manager['started_event'] > gameweek:
            continue
        # manager_history = requests.get(f'{base}/entry/{manager_id}/history/').json()
        manager_name = manager['name']
        manager_total_pts = standing[user_i - 1]['total']
        manager_gameweek_pts = standing[user_i - 1]['event_total']
        manager_rank = standing[user_i - 1]['rank']
        manager_picks = requests.get(f'{base}/entry/{manager_id}/event/{gameweek}/picks/').json()
        manager_bench_pts = manager_picks['entry_history']['points_on_bench']
        manager_active_chip = chips[manager_picks['active_chip']]
        managers_picks += [manager_picks]
        manager_squad = [_.find(boot['elements'], {'id': pick['element']})
                         for pick in manager_picks['picks']]
        squad_df = pd.DataFrame(columns=['name', 'pts'])
        for i in range(len(manager_squad)):
            if manager_picks['picks'][i]['is_captain']:
                if manager_picks['picks'][i]['multiplier'] == 3:
                    squad_df.loc[i] = [manager_squad[i]['web_name'] + ' (3*C)',
                                       manager_squad[i]['event_points'] * manager_picks['picks'][i]['multiplier']]
                else:
                    squad_df.loc[i] = [manager_squad[i]['web_name'] + ' (C)',
                                       manager_squad[i]['event_points'] * manager_picks['picks'][i]['multiplier']]
            elif manager_picks['picks'][i]['is_vice_captain']:
                if manager_picks['picks'][i]['multiplier'] == 3:
                    squad_df.loc[i] = [manager_squad[i]['web_name'] + ' (3*V)',
                                       manager_squad[i]['event_points'] * manager_picks['picks'][i]['multiplier']]
                else:
                    squad_df.loc[i] = [manager_squad[i]['web_name'] + ' (V)',
                                       manager_squad[i]['event_points'] * manager_picks['picks'][i]['multiplier']]
            else:
                squad_df.loc[i] = [manager_squad[i]['web_name'], manager_squad[i]['event_points']]

            if manager_squad[i]['minutes'] == 0:
                squad_df.loc[i, 'name'] = squad_df.loc[i, 'name'] + ' **'

        # add data to Google sheet (first run should ask for permission and .pickle file will be created)
        squad_names = pd.DataFrame([manager_rank] +
                                   [manager_name] +
                                   [f"{manager['player_first_name']} {manager['player_last_name']}"] +
                                   ['Starters:'] +
                                   squad_df.loc[:10, 'name'].tolist() +
                                   ['Subs:'] +
                                   squad_df.loc[11:, 'name'].tolist() +
                                   [manager_active_chip])
        squad_pts = pd.DataFrame([''] +
                                 [manager_total_pts] +
                                 [''] +
                                 [manager_gameweek_pts] +
                                 squad_df.loc[:10, 'pts'].tolist() +
                                 [manager_bench_pts] +
                                 squad_df.loc[11:, 'pts'].tolist() +
                                 [''])
        squads = pd.concat([squads, squad_names, squad_pts], axis=1)

    utils.df_to_spreadsheet(spreadsheet_id, base_sheet_id, squads, f'GW{str(gameweek)}', 'A')
