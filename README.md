# FPL

This code transfers the lineups of all members of an FPL league to a Google spreadsheet.

Required packages:
- pandas
- numpy
- keyring
- selenium
- google-api-python-client
_______
To run the Google Spreadsheet API, you will need to set up OAuth 2.0 client ID.
1. Go to the Google Cloud Platform Console.
2. From the projects list, select a project or create a new one.
3. If the APIs & services page isn't already open, open the console left side menu and select APIs & services.
On the left, click Credentials.
4. Click New Credentials, then select OAuth client ID.
5. Select "Web Application" in the application type, and add "http://localhost:8080/" to Authorized redirect URIs.
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

To run the code, you need to download the latest release of Chrome WebDriver from here:
https://chromedriver.storage.googleapis.com/index.html

Place the WebDriver file in the repo folder. 
Then, change the name of the league in the SquadFPL class definition.
<pre>
fpl = SquadFPL(league_name=<b>"place name of league here"</b>)
</pre>


Then, set your secret parameters using *keyring* package. In python console, run the following:
<pre>
keyring.set_password('gsheetId', 'FPL', <b>'place Google spreadsheet ID here'</b>)
keyring.set_password('FPL', 'username', <b>'place your FPL username here'</b>)
keyring.set_password('FPL', 'password', <b>'place your FPL password here'</b>)
</pre>
Note: Google sheet ID can  be found in the Google spreadsheet URL:
*https<area>://docs.google.com/spreadsheets/d/**spreadsheetId**/edit#gid=0*
<br></br>

**Note:** 
- Currently, the code does not create a new sheet for each Gameweek, but it expects that the sheet already exists.
For example, it the last gameweek is gameweek 4, the code expects a sheet named "Gameweek 4".

- You can add conditional formatting to the Google sheet to add a colorful representation of the player points.
