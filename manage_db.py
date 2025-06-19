# manage_db.py
# -----------------------------------------------
import argparse, sys
from sqlalchemy.orm import Session
from db_schema import ENGINE, init_db, populate_from_dict, COMPETENCES

def main():
    ap = argparse.ArgumentParser(
        description="DB initialisieren / updaten")
    ap.add_argument("cmd", choices=["init", "drop", "populate"])
    ap.add_argument("--force", action="store_true",
                    help="bestehende DB beim init/drop löschen")
    args = ap.parse_args()

    if args.cmd == "init":
        init_db(drop=args.force)
        print("✔ Datenbank-Schema angelegt.")
    elif args.cmd == "drop":
        init_db(drop=True)
        print("✔ Datenbank gelöscht.")
    elif args.cmd == "populate":
        with Session(ENGINE) as ses:
            populate_from_dict(COMPETENCES, ses)
            print("✔ Kompetenzen eingelesen.")

if __name__ == "__main__":
    main()
