from dotenv import load_dotenv
load_dotenv()

from db_schema import switch_engine, list_report_dbs

# Auto-connect to the latest report DB (alphabetically last = most recent)
dbs = sorted(list_report_dbs())
if dbs:
    switch_engine(dbs[-1])

import ui_public as ui
ui.run_ui()
