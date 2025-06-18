# yaml2csv.py
# ------------------------------------------------------------
from pathlib import Path
import yaml, csv
from collections import OrderedDict

SAVE_DIR = Path("saved")           #  dort liegen die YAML-Dateien
DELIM    = ";"                     #  CSV-Trennzeichen

def merge_unique(lst):
    """Reihenfolge wahren, Duplikate kicken."""
    return list(OrderedDict.fromkeys(lst))

def build_cell(subject, topic, competences):
    """Fach + Thema + Leerzeile + Kompetenzen   →   Einzell-Cell."""
    text = (
        f"{subject}\n{topic}\n\n"       # Überschrift
        + "\n".join(merge_unique(competences))
    )
    return text

def convert_yaml(yaml_path: Path):
    with yaml_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    row = ["", "Niveau"]  # erste beiden Spalten
    for subject, topics in data.items():
        for topic, comps in topics.items():
            row.append(build_cell(subject, topic, comps))

    csv_path = yaml_path.with_suffix(".csv")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=DELIM)
        writer.writerow(row)
    print(f"✔  {csv_path.name} erzeugt")

if __name__ == "__main__":
    for yfile in SAVE_DIR.glob("kompetenzen_*.yaml"):
        convert_yaml(yfile)
