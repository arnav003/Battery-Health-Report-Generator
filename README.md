# Battery-Health-Report-Generator
 
### To create .exe file
`pyinstaller --onefile app.py clean.py extract.py generate.py load_json.py`

Note: *To make it window-based. Add the -w (a.k.a. --windowed) option. Then your executable will start without the console attached.*

### Current design
![Design](design.png)