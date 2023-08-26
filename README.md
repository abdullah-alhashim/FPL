# FPL

This code transfers the lineups of all members of an FPL league to a Google spreadsheet for all previous gameweeks.

Required packages:
- pandas
- numpy
- pydash
- requests
- google-api-python-client
- google_auth_oauthlib
_______
To run the Google Spreadsheet API, you will need to set up OAuth 2.0 client ID.
1. Go to the Google Cloud Platform Console.
2. From the projects list, select a project or create a new one.
3. If the APIs & services page isn't already open, open the console left side menu and select APIs & services.
On the left, click Credentials.
4. Click New Credentials, then select OAuth client ID.
5. Select "Web Application" in the application type, and add "http<area>://localhost:8080/" to Authorized redirect URIs.
6. If this is your first time creating a client ID, you can also configure your consent screen by clicking Consent Screen. 
    - Go to the Google API Console OAuth consent screen page.
    - Add required information like a product name and support email address.
    - Click Add Scope.
    - Search for "spreadsheets", choose ".../auth/spreadsheets" and click Update.
    - I did not want to publish the app, so I added my email to the test users and submitted it for verification.
    - A Verification required window displays.
    - Add scopes justification, a contact email address, and any other information that can help the team with verification, then click Submit.
7. After setting up the OAuth client ID, click on the download icon (⬇) next to your OAuth client ID.
8. Finally, click on Download JSON,  and rename the file to "client_secret.json"
_______

To run the code, provide the Google Spreadsheet ID and the base sheet ID using arguments.. In terminal, run the code like this:
<pre>
>> python FPL_API.py <b>spreadsheet_id</b> <b>base_sheet_id</b>
</pre>
Replacing <b>spreadsheet_id</b> and <b>base_sheet_id</b> with the appropriate strings.
Note: The Google Spreadsheet ID can be found in the URL:
*https<area>://docs.google.com/spreadsheets/d/**spreadsheetId**/edit#gid=baseSheetId*
<br></br>

**Note:** 
- The code expects a <b>base</b> sheet that contains the formatting that you want for the points and the players. You have to provide this base sheet's ID as an argument.
- The code can be run at anytime and it will get the points and squads of each player for all previous gameweeks plus updating the current gameweek.