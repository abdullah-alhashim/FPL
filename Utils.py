import pickle
import os
from glob import glob
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError


class Utils:
    def __init__(self, spreadsheet_id, base_sheet_id):
        self.spreadsheet_id = spreadsheet_id
        self.base_sheet_id = base_sheet_id
        self.service = self.create_spreadsheet()
        self.spreadsheet = self.service.get(spreadsheetId=self.spreadsheet_id).execute()

    @staticmethod
    def create_service(client_secret_file, api_name, api_version, *scopes):
        CLIENT_SECRET_FILE = client_secret_file
        API_SERVICE_NAME = api_name
        API_VERSION = api_version
        SCOPES = [scope for scope in scopes[0]]
        # print(SCOPES)

        cred = None

        pickle_file = f'token_{API_SERVICE_NAME}_{API_VERSION}.pickle'
        # print(pickle_file)

        if os.path.exists(pickle_file):
            with open(pickle_file, 'rb') as token:
                cred = pickle.load(token)

        if not cred or not cred.valid:
            if cred and cred.expired and cred.refresh_token:
                cred.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
                cred = flow.run_local_server()

            with open(pickle_file, 'wb') as token:
                pickle.dump(cred, token)

        try:
            service = build(API_SERVICE_NAME, API_VERSION, credentials=cred)
            # print(API_SERVICE_NAME, 'service created successfully')
            return service
        except Exception as e:
            print('Unable to connect.')
            print(e)
            return None

    def create_spreadsheet(self):
        CLIENT_SECRET_FILE = 'client_secret.json'
        API_SERVICE_NAME = 'sheets'
        API_VERSION = 'v4'
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

        try:
            service = self.create_service(CLIENT_SECRET_FILE, API_SERVICE_NAME, API_VERSION, SCOPES)
            return service.spreadsheets()
        except RefreshError:
            print('\033[33m RefreshError: Removing pickle file and trying again... \033[0m')  # print in orange
            os.remove(glob('./*.pickle')[0])
            service = self.create_service(CLIENT_SECRET_FILE, API_SERVICE_NAME, API_VERSION, SCOPES)
            return service.spreadsheets()

    def write_data(self, df, gw, last_col_index):
        # clear old data before writing the new data
        self.service.values().clear(spreadsheetId=self.spreadsheet_id, range=f'{gw}!1:{len(df.index)}').execute()

        # write data to spreadsheet
        self.service.values().append(
            spreadsheetId=self.spreadsheet_id,
            valueInputOption='RAW',
            range=f'{gw}!A1',
            body=dict(
                majorDimension='COLUMNS',
                values=df.T.values.tolist())
        ).execute()

        # delete extra columns
        sheet_id, col_count = None, None
        for sheet in self.spreadsheet['sheets']:
            if sheet['properties']['title'] == gw:
                sheet_id = sheet['properties']['sheetId']
                col_count = sheet['properties']['gridProperties']['columnCount']
        if sheet_id:
            body = {
                "requests": [{"deleteDimension": {"range": {"sheetId": sheet_id,
                                                            "dimension": "COLUMNS",
                                                            "startIndex": last_col_index,
                                                            "endIndex": col_count}}}]}
            self.service.batchUpdate(spreadsheetId=self.spreadsheet_id, body=body).execute()

    def df_to_spreadsheet(self, df, gw, last_col_index):
        try:
            self.write_data(df, gw, last_col_index)
        except HttpError as e:
            if 'Unable to parse range' in e.error_details:  # probably the sheet does not exist
                # duplicate base sheet to get the same formatting
                body = {'requests': [{'duplicateSheet': {'sourceSheetId': self.base_sheet_id,
                                                         'insertSheetIndex': 0,
                                                         'newSheetName': gw}}]}
                self.service.batchUpdate(spreadsheetId=self.spreadsheet_id, body=body).execute()
                self.spreadsheet = self.service.get(spreadsheetId=self.spreadsheet_id).execute()

                self.write_data(df, gw, last_col_index)

    def get_sheets_names(self):
        sheets_names = [self.spreadsheet['sheets'][i]['properties']['title']
                        for i in range(len(self.spreadsheet['sheets']))]
        return sheets_names
