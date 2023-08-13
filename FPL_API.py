"""
Script to get data from an FPL league, using FPL API, and write it into a Google Sheet.

Usage:
set Google Sheet ID using keyring.set_password()
keyring.set_password('FPL', 'gsheetId', '')  # found after 'gid=' in url


Author:
Abdullah Alhashim
Created on Sat Aug 12, 2023
"""

import requests
import pydash as _
import pandas as pd
import keyring
import os
from glob import glob
from alive_progress import alive_it
from string import ascii_uppercase
from Google import Create_Service
from google.auth.exceptions import RefreshError


def df_to_gsheet(s, df2, gw, col, first):
    if first:
        # clear old data before writing the new data
        s.spreadsheets().values().clear(
            spreadsheetId=gsheetId,
            range=gw + '!' + '1:20'
        ).execute()

    # write data to spreadsheet
    s.spreadsheets().values().append(
        spreadsheetId=gsheetId,
        valueInputOption='RAW',
        range=gw + '!' + col + '1',
        body=dict(
            majorDimension='COLUMNS',
            values=df2.T.values.tolist())
    ).execute()


CLIENT_SECRET_FILE = 'client_secret.json'
API_SERVICE_NAME = 'sheets'
API_VERSION = 'v4'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
gsheetId = keyring.get_password('FPL', 'gsheetId')

try:
    service = Create_Service(CLIENT_SECRET_FILE, API_SERVICE_NAME, API_VERSION, SCOPES)
except RefreshError:
    os.remove(glob('./*.pickle')[0])
    service = Create_Service(CLIENT_SECRET_FILE, API_SERVICE_NAME, API_VERSION, SCOPES)


base = 'https://fantasy.premierleague.com/api'
boot = requests.get(f'{base}/bootstrap-static/').json()

league_id = ''

league = requests.get(f'{base}/leagues-classic/{league_id}/standings').json()
standing = league['standings']['results']
while league['standings']['has_next']:
    page = 2
    league = requests.get(f'{base}/leagues-classic/{league_id}/standings',
                          params={'page_standings': page}).json()
    standing += league['standings']['results']
    page += 1

event_id = 1  # Gameweek

colNames = [letter + letter2
            for letter in [''] + list(ascii_uppercase[:int(len(standing)*2/26 // 1 + 1)])
            for letter2 in list(ascii_uppercase)]
squads = pd.DataFrame()
for user_i in alive_it(range(1, len(standing) + 1), theme='classic', force_tty=True):
    # for user_i in range(1, len(standing)):
    is_first = True if user_i == 1 else False
    manager_id = str(standing[user_i - 1]['entry'])
    manager = requests.get(f'{base}/entry/{manager_id}/').json()
    # manager_history = requests.get(f'{base}/entry/{manager_id}/history/').json()
    manager_name = manager['name']
    manager_league_total_pts = standing[user_i - 1]['total']
    manager_picks = requests.get(f'{base}/entry/{manager_id}/event/{event_id}/picks/').json()
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
    squad_names = pd.DataFrame([user_i] +
                               [manager_name] +
                               [f"{manager['player_first_name']} {manager['player_last_name']}"] +
                               ['Starters:'] +
                               squad_df.loc[:10, 'name'].tolist() +
                               ['Subs:'] +
                               squad_df.loc[11:, 'name'].tolist())
    squad_pts = pd.DataFrame([''] +
                             [manager_league_total_pts] +
                             [''] +
                             [sum(squad_df.loc[:10, 'pts'].tolist())] +
                             squad_df.loc[:10, 'pts'].tolist() +
                             [sum(squad_df.loc[11:, 'pts'].tolist())] +
                             squad_df.loc[11:, 'pts'].tolist())
    squads = pd.concat([squads, squad_names, squad_pts], axis=1)
df_to_gsheet(service, squads, f'GW{str(event_id)}', 'A', True)
