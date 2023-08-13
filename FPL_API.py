import requests
import pydash as _

base = 'https://fantasy.premierleague.com/api'
boot = requests.get(f'{base}/bootstrap-static/').json()

league_id = ''  

league = requests.get(f'{base}/leagues-classic/{league_id}/standings').json()
event_id = 1  # Gameweek
for player in league['standings']['results']:
    manager_id = str(player['entry'])
    manager = requests.get(f'{base}/entry/{manager_id}/').json()
    # manager_history = requests.get(f'{base}/entry/{manager_id}/history/').json()
    manager_name = manager['name']
    manager_picks = requests.get(f'{base}/entry/{manager_id}/event/{event_id}/picks/').json()
    manager_squad = [_.find(boot['elements'], {'id': pick['element']})
                     for pick in manager_picks['picks']]
