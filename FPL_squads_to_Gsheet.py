"""
Script to scrape data from an FPL league and write into a Google Sheet

Usage:
set Google Sheet ID, FPL username and FPL password using keyring.set_password()


Author:
Abdullah Alhashim
Created on Sat Aug 14, 2021
"""

from time import time
import pandas as pd
import numpy as np
import keyring
from string import ascii_uppercase
from selenium import webdriver
from Google import Create_Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

start_time = time()


class SquadFPL:
    def __init__(self, league_name):
        self.league_name = league_name
        self.vars = {}
        self.driver = webdriver.Chrome(r"/Users/abdullahalhashim/PycharmProjects/FPL/chromedriver")
        self.name = []
        self.totalpts = None
        self.GW = None
        self.squad = []
        self.subsquad = []
        self.colNames = list(ascii_uppercase)
        self.colNames.extend(['A' + x for x in list(ascii_uppercase)])
        self.colNames.extend(['B' + x for x in list(ascii_uppercase)])
        self.is_first = True

    def df_to_gsheet(self, df2, GW, col):
        CLIENT_SECRET_FILE = 'client_secret.json'
        API_SERVICE_NAME = 'sheets'
        API_VERSION = 'v4'
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        gsheetId = keyring.get_password('gsheetId', 'FPL')

        service = Create_Service(CLIENT_SECRET_FILE, API_SERVICE_NAME, API_VERSION, SCOPES)

        # clear old data before writing the new data
        if self.is_first:
            service.spreadsheets().values().clear(
                spreadsheetId=gsheetId,
                range=GW + '!' + '1:18'
            ).execute()
            self.is_first = False

        # write data to spreadsheet
        service.spreadsheets().values().append(
            spreadsheetId=gsheetId,
            valueInputOption='RAW',
            range=GW + '!' + col + '1',
            body=dict(
                majorDimension='COLUMNS',
                values=df2.T.values.tolist())
        ).execute()

    def squads(self):
        try:
            self.driver.get("https://fantasy.premierleague.com/")
            login = len(self.driver.find_elements(By.XPATH, "//input[@id=\'loginUsername\']"))
            if login > 0:
                self.driver.find_element(By.ID, "loginUsername").send_keys(keyring.get_password('FPL', 'username'))
                self.driver.find_element(By.ID, "loginPassword").send_keys(keyring.get_password('FPL', 'password'))
                self.driver.find_element(By.ID, "loginPassword").send_keys(Keys.ENTER)
            self.driver.find_element(By.LINK_TEXT, "Leagues & Cups").click()
            self.driver.find_element(By.LINK_TEXT, self.league_name).click()
            self.driver.implicitly_wait(5)

            members = self.driver.find_element_by_xpath('//*[@id="root"]/div[2]/div[2]/div[1]/div/table/tbody')
            for i in range(1, int(members.text.splitlines()[-3]) + 1):
                # click on each member
                self.driver.find_element(By.CSS_SELECTOR,
                                         ".StandingsRow-fwk48s-0:nth-child(" + str(i) + ") strong").click()
                self.driver.find_element(By.LINK_TEXT, "List View").click()  # display list view

                # self.name = self.driver.find_element(By.CSS_SELECTOR, ".Title-sc-9c7mfn-0").text[9:]  # squad name
                self.name = self.driver.find_element(By.CSS_SELECTOR,
                                                     '.Entry__EntryName-sc-1kf863-0').text  # player name

                self.squad = self.driver.find_element(By.CSS_SELECTOR, ".ichxnR > div").text  # squad table
                self.totalpts = self.driver.find_element(By.CSS_SELECTOR,
                                                         ".sc-bdnxRM:nth-child(2) .Entry__DataListItem-sc-1kf863-1:"
                                                         "nth-child(1) > .Entry__DataListValue-sc-1kf863-3").text
                self.GW = self.driver.find_element(By.CSS_SELECTOR, ".Pager__PagerHeading-s2eddx-5").text  # GameWeek

                # convert squad table from string to numpy array
                self.squad = np.array(self.squad.splitlines())
                self.squad = np.delete(self.squad, [i for i, s in enumerate(self.squad)
                                                    if ('View' in s) or ('playing' in s) or ('injury' in s)
                                                    or ('Expected' in s) or ('Transferred' in s) or ('loan' in s)
                                                    or ('Unknown' in s) or ('Left' in s)])  # exclude player status
                self.subsquad = self.squad[34:]  # substitutes squad
                self.squad = self.squad[:34]  # starting 11 squad

                # split player statistics and rearrange
                x = np.concatenate(np.char.split(self.squad[::3]), dtype='<U30')
                x = np.insert(x, 1, 'teamPos')
                x = np.insert(x, list(range(20, 218, 18)), self.squad[1::3])
                x = np.insert(x, list(range(21, 218, 19)), self.squad[2::3])
                self.squad = np.split(x, 12)

                x = np.concatenate(np.char.split(self.subsquad[::3]), dtype='<U30')
                x = np.insert(x, 1, 'teamPos')
                x = np.insert(x, list(range(20, 92, 18)), self.subsquad[1::3])
                x = np.insert(x, list(range(21, 92, 19)), self.subsquad[2::3])
                self.subsquad = np.split(x, 5)

                # convert from numpy array to pandas data frame
                squad_df = pd.DataFrame(self.squad[1:], columns=self.squad[0])
                subsquad_df = pd.DataFrame(self.subsquad[1:], columns=self.subsquad[0])

                # find captain and vice captain
                is_triple_captain = False
                captain = self.driver.find_element_by_css_selector('.TableCaptains__StyledCaptain-sc-1ub910p-0')
                if captain.get_attribute('class')[-5:] == 'GtDAO':
                    is_triple_captain = True
                captain = captain.find_element_by_xpath('../..').text
                captain = np.array(captain.splitlines())
                captain = np.delete(captain, [i for i, s in enumerate(captain)
                                              if ('View' in s) or ('playing' in s) or ('injury' in s)
                                              or ('Expected' in s) or ('Transferred' in s) or ('loan' in s)
                                              or ('Unknown' in s) or ('Left' in s)])
                captainIndex = np.where(squad_df['Starters'] == captain[0])[0][0] + 1
                vice = self.driver.find_element_by_css_selector(
                    '.TableCaptains__StyledViceCaptain-sc-1ub910p-1').find_element_by_xpath('../..').text
                vice = np.array(vice.splitlines())
                vice = np.delete(vice, [i for i, s in enumerate(vice)
                                        if ('View' in s) or ('playing' in s) or ('injury' in s)
                                        or ('Expected' in s) or ('Transferred' in s) or ('loan' in s)
                                        or ('Unknown' in s) or ('Left' in s)])
                viceIndex = np.where(squad_df['Starters'] == vice[0])[0][0] + 1

                # add text to captain and vice captain
                if is_triple_captain:
                    squad_df['Starters'][captainIndex - 1] = squad_df['Starters'][captainIndex - 1] + ' (3*C)'
                    squad_df['Starters'][viceIndex - 1] = squad_df['Starters'][viceIndex - 1] + ' (3*V)'
                else:
                    squad_df['Starters'][captainIndex - 1] = squad_df['Starters'][captainIndex - 1] + ' (C)'
                    squad_df['Starters'][viceIndex - 1] = squad_df['Starters'][viceIndex - 1] + ' (V)'

                # prepare data to be inserted to Google sheet
                playersOnly = [self.name]
                playersOnly.extend(['Starters:'])
                squad_df['Starters'] = [
                    squad_df['Starters'][i] + ' **' if (squad_df['MP'][i] == '0') else squad_df['Starters'][i]
                    for i in range(0, 11)]
                playersOnly.extend(squad_df['Starters'].to_list())
                playersOnly.extend(['Subs:'])
                subsquad_df['Substitutes'] = [
                    subsquad_df['Substitutes'][i] + ' **' if (subsquad_df['MP'][i] == '0') else
                    subsquad_df['Substitutes'][i] for i in range(0, 4)]  # add '**' to players who did not play
                playersOnly.extend(subsquad_df['Substitutes'].to_list())
                playersOnly = pd.DataFrame(playersOnly)

                playersPts = [str(self.totalpts)]
                playersPts.extend([int(squad_df['Pts'].astype('int').sum())])
                playersPts.extend([int(x) for x in squad_df['Pts'].to_list()])
                playersPts.extend([int(subsquad_df['Pts'].astype('int').sum())])
                playersPts.extend([int(x) for x in subsquad_df['Pts'].to_list()])
                playersPts = pd.DataFrame(playersPts)

                # add data to Google sheet (first run should ask for permission and .pickle file will be created)
                self.df_to_gsheet(playersOnly, self.GW, self.colNames[(i - 1) * 2])
                self.df_to_gsheet(playersPts, self.GW, self.colNames[i * 2 - 1])
                self.driver.back()
        finally:
            self.driver.quit()


if __name__ == '__main__':
    fpl = SquadFPL(league_name='شباب الليث')
    fpl.squads()
    end_time = time()
    print("time consumed %.2f minutes" % ((end_time - start_time) / 60))
