# Battery-Health-Report-Generator
 
### To create .exe file
`pyinstaller --name="Battery Health Report Generator" --icon="app_icon.ico" --add-data="battery_icon.png;." --add-data="app_icon.ico;." --windowed app.py clean.py extract.py generate.py load_json.py`

Note: *To make it window-based. Add the -w (a.k.a. --windowed) option. Then your executable will start without the console attached.*

### Current design
![Design](design.png)