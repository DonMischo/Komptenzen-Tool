# generate_test_data.py
"""
Self-contained test data for class 7ef.
Creates the class and all students; safe to call multiple times (idempotent).
Run directly:  python generate_test_data.py
"""
from __future__ import annotations
import random
from datetime import date

from sqlalchemy import delete as sql_delete
from sqlalchemy.orm import Session

from db_schema import (
    ENGINE, Student, Subject, Topic,
    SchoolClass, ClassCompetence, StudentSubject, Grade,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BLOCK      = "7/8"
CLASS_NAME = "7ef"
LEBENSPRAXIS = "Lebenspraxis"

NO_NIVEAU = {
    "Wahlpflichtbereich - Darstellen und Gestalten",
    "Werkstätten",
    "Mitarbeit und Verhalten",
}
SPORT = "Sport"   # always niveau "9"

WAHLPFLICHT = [
    "Wahlpflichtbereich - Französisch",
    "Wahlpflichtbereich - Spanisch",
    "Wahlpflichtbereich - Darstellen und Gestalten",
    "Wahlpflichtbereich - Natur und Technik",
]

MAIN_SUBJECTS = [
    "Deutsch",
    "Mathematik",
    "Englisch",
    "MNT - Projekt Lutherpark",
    "Technisches Werken",
    "Geografie",
    "Chemie",
    "Physik",
    "Biologie",
    "Geschichte",
    "Evangelische Religionslehre",
    "Sport",
    "Werkstätten",
    "Mitarbeit und Verhalten",
]

FEMALE_FIRST_NAMES = {"Emma", "Mia", "Leonie", "Clara", "Marie"}

# ---------------------------------------------------------------------------
# Student definitions
# type: "focus"  = one of the 4 detailed normal students
#       "lb"     = LB student (mix of text + numeric grades)
#       "gb"     = GB student (text-only)
#       "normal" = additional standard student
# ---------------------------------------------------------------------------

STUDENTS_DEF: list[dict] = [
    # 4 focused normal students, one per Wahlpflicht
    {   # niveau "1", ne for whole subject (Chemie)
        "last": "Weber",    "first": "Jonas", "bday": date(2012, 3, 15),
        "wp": 0, "type": "focus", "niveau": "1",
        "ne_subj": "Chemie", "ne_topic": None,
    },
    {   # niveau "2", ne for single topic (Physik topic index 0)
        "last": "Schäfer",  "first": "Emma",  "bday": date(2012, 7, 22),
        "wp": 1, "type": "focus", "niveau": "2",
        "ne_subj": None, "ne_topic": ("Physik", 0),
    },
    {   # niveau "3", DuG → no niveau
        "last": "Neumann",  "first": "Lukas", "bday": date(2012, 11, 8),
        "wp": 2, "type": "focus", "niveau": "3",
        "ne_subj": None, "ne_topic": None,
    },
    {   # mixed niveaux 1/2/3
        "last": "Hoffmann", "first": "Mia",   "bday": date(2013, 1, 30),
        "wp": 3, "type": "focus", "niveau": "mix",
        "ne_subj": None, "ne_topic": None,
    },
    # LB student
    {
        "last": "Richter", "first": "Ben",   "bday": date(2012, 5, 12),
        "wp": 1, "type": "lb",
    },
    # GB student
    {
        "last": "Gruber",  "first": "Marie", "bday": date(2012, 9,  4),
        "wp": 0, "type": "gb",
    },
    # 5 additional normal students
    {"last": "Bauer",   "first": "Finn",   "bday": date(2012,  2, 18), "wp": 0, "type": "normal"},
    {"last": "Koch",    "first": "Leonie", "bday": date(2012,  6,  7), "wp": 1, "type": "normal"},
    {"last": "Braun",   "first": "Tim",    "bday": date(2013,  4, 25), "wp": 2, "type": "normal"},
    {"last": "Wagner",  "first": "Clara",  "bday": date(2012,  8, 13), "wp": 3, "type": "normal"},
    {"last": "Fischer", "first": "Max",    "bday": date(2012, 10,  3), "wp": 0, "type": "normal"},
]

# ---------------------------------------------------------------------------
# Text templates
# ---------------------------------------------------------------------------

REPORT_TEMPLATE = """\
{vorname} hat das vergangene Schulhalbjahr regelmäßig und mit erkennbarem \
Engagement absolviert. Die Mitarbeit im Unterricht war überwiegend aktiv \
und konstruktiv. {vorname} zeigt echtes Interesse an den behandelten Themen \
und beteiligt sich regelmäßig am Unterrichtsgespräch. Hausaufgaben wurden \
stets zuverlässig erledigt.

Im Fach Deutsch verfügt {vorname} über ein solides Sprachgefühl. \
Leseverständnis und schriftlicher Ausdruck entsprechen den Anforderungen der \
Jahrgangsstufe. Grammatikalische Strukturen werden sicher angewendet.

In Mathematik zeigt {vorname} ein gutes Verständnis für logische Zusammenhänge. \
Aufgaben werden methodisch und strukturiert bearbeitet; bei anspruchsvolleren \
Problemstellungen arbeitet {pron} ausdauernd und zielorientiert.

Im Englischunterricht kommuniziert {vorname} zunehmend sicherer in der \
Fremdsprache. Vokabular und Grammatik werden angemessen eingesetzt.

Im sozialen Miteinander verhält sich {vorname} respektvoll und kollegial. \
Die Zusammenarbeit mit Mitschülerinnen und Mitschülern gelingt gut.

Insgesamt hat {vorname} in diesem Schulhalbjahr erfreuliche Leistungen erbracht. \
Wir wünschen {vorname} für das weitere Schuljahr viel Erfolg und Freude am Lernen.\
"""

REPORT_LB = """\
{vorname} hat das vergangene Schulhalbjahr regelmäßig und pünktlich besucht. \
{pron_cap} besucht den Unterricht auf der Grundlage eines individuellen \
Förderplans mit dem Förderschwerpunkt Lernen. Die erbrachten Leistungen \
werden entsprechend {pron_gen} individuellen Lernziele bewertet und spiegeln \
{pron_akk} persönlichen Lernfortschritt wider.

{vorname} ist ein geschätztes Mitglied der Klassengemeinschaft. \
Wir ermutigen {vorname}, den eingeschlagenen Weg mit Zuversicht fortzusetzen.\
"""

REPORT_GB = """\
{vorname} hat das Schulhalbjahr regelmäßig besucht und zeigt eine freundliche, \
offene Grundhaltung. {pron_cap} besucht den Unterricht auf der Grundlage eines \
individuellen Förderplans mit dem Förderschwerpunkt geistige Entwicklung.

{vorname} nimmt aktiv am Unterrichtsgeschehen teil und zeigt Freude am \
gemeinsamen Lernen. Wir freuen uns über {vorname}s Entwicklung.\
"""

LP_LB_HTML = (
    "<p>{vorname} besucht das Fach <strong>Lebenspraxis</strong> auf Grundlage "
    "{pron_gen} individuellen Förderplans (Förderschwerpunkt Lernen).</p>"
    "<p>Inhalte umfassen praktische Alltagskompetenzen, soziale Interaktion und "
    "selbstständiges Handeln in verschiedenen Lebenssituationen. {vorname} entwickelt "
    "zunehmend Sicherheit im Umgang mit alltäglichen Anforderungen und zeigt "
    "erkennbare Fortschritte bei der Übernahme einfacher Verantwortung.</p>"
)

LP_GB_HTML = (
    "<p>{vorname} nimmt aktiv am Unterricht in <strong>Lebenspraxis</strong> teil.</p>"
    "<p>Schwerpunkte sind grundlegende Alltagskompetenzen und die Orientierung im "
    "schulischen und sozialen Umfeld. {vorname} zeigt Freude an praktischen "
    "Aktivitäten und reagiert positiv auf Zuwendung und Unterstützung.</p>"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pronouns(first: str) -> dict[str, str]:
    is_female = first in FEMALE_FIRST_NAMES
    return {
        "pron":     "sie"   if is_female else "er",
        "pron_cap": "Sie"   if is_female else "Er",
        "pron_akk": "ihr"   if is_female else "sein",
        "pron_gen": "ihrer" if is_female else "seiner",
    }


def _upsert_student(ses: Session, last: str, first: str, bday: date,
                    class_id: int) -> Student:
    stu = ses.query(Student).filter_by(
        last_name=last, first_name=first, birthday=bday
    ).first()
    if stu is None:
        stu = Student(last_name=last, first_name=first, birthday=bday, class_id=class_id)
        ses.add(stu)
        ses.flush()
    else:
        stu.class_id = class_id
    return stu


def _upsert_student_subject(ses: Session, student_id: int, subject_id: int,
                             niveau: str | None) -> StudentSubject:
    ss = ses.query(StudentSubject).filter_by(
        student_id=student_id, subject_id=subject_id
    ).first()
    if ss is None:
        ss = StudentSubject(student_id=student_id, subject_id=subject_id, niveau=niveau)
        ses.add(ss)
    else:
        ss.niveau = niveau
    ses.flush()
    return ss


def _upsert_grade(ses: Session, student_id: int, topic_id: int, value: str):
    g = ses.query(Grade).filter_by(student_id=student_id, topic_id=topic_id).first()
    if g is None:
        ses.add(Grade(student_id=student_id, topic_id=topic_id, value=value))
    else:
        g.value = value


def _select_random_competences(ses: Session, class_id: int,
                                subject_names: list[str], rng: random.Random):
    """Select ~20% of competences. Some topics skipped entirely."""
    TOPIC_SKIP_PROB  = 0.40
    COMP_SELECT_PROB = 0.33

    for name in subject_names:
        subj = ses.query(Subject).filter_by(name=name).first()
        if not subj:
            continue
        topics = ses.query(Topic).filter_by(subject_id=subj.id, block=BLOCK).all()
        if not topics:
            topics = ses.query(Topic).filter_by(subject_id=subj.id).all()
        for topic in topics:
            skip_topic = rng.random() < TOPIC_SKIP_PROB
            for comp in topic.competences:
                selected = (not skip_topic) and (rng.random() < COMP_SELECT_PROB)
                cc = ses.query(ClassCompetence).filter_by(
                    class_id=class_id, competence_id=comp.id
                ).first()
                if cc is None:
                    ses.add(ClassCompetence(class_id=class_id, competence_id=comp.id, selected=selected))
                else:
                    cc.selected = selected


def _topics_for(ses: Session, subject_id: int) -> list[Topic]:
    topics = ses.query(Topic).filter_by(subject_id=subject_id, block=BLOCK).all()
    if not topics:
        topics = ses.query(Topic).filter_by(subject_id=subject_id).all()
    return topics


def _lb_niveau_html(vorname: str, subj_name: str, topics: list, p: dict) -> str:
    """HTML-formatted niveau text for LB student, referencing actual topic names."""
    from html import escape as _he
    pron_gen = p["pron_gen"]
    pron_cap = p["pron_cap"]
    # Use <p> bullet lines instead of <ul>/<li> — avoids \begin{itemize} inside tabularray
    topic_lines = "".join(
        f"<p>· <strong>{_he(t.name)}</strong>: Grundlegende Inhalte auf adaptiertem Anforderungsniveau</p>"
        for t in topics[:4]
    )
    topic_block = (
        f"<p>{pron_cap} arbeitet an folgenden Themenbereichen des Regelunterrichts:</p>"
        f"{topic_lines}"
    ) if topic_lines else ""
    return (
        f"<p>{vorname} bearbeitet die Inhalte in <strong>{_he(subj_name)}</strong> auf Grundlage "
        f"{pron_gen} individuellen Förderplans (Förderschwerpunkt Lernen). Die Aufgaben sind "
        f"hinsichtlich Umfang und Komplexität individuell angepasst.</p>"
        f"{topic_block}"
        f"<p>Die Leistungsbewertung richtet sich nach {pron_gen} persönlichen Lernzielen und "
        f"spiegelt {pron_gen} individuellen Lernfortschritt wider.</p>"
    )


def _gb_niveau_html(vorname: str, subj_name: str, topics: list, p: dict) -> str:
    """HTML-formatted niveau text for GB student, referencing actual topic names."""
    from html import escape as _he
    pron_gen = p["pron_gen"]
    pron_cap = p["pron_cap"]
    topic_lines = "".join(
        f"<p>· Handlungsorientierte Aktivitäten zu <strong>{_he(t.name)}</strong></p>"
        for t in topics[:3]
    )
    return (
        f"<p>{vorname} nimmt am Unterricht in <strong>{_he(subj_name)}</strong> teil und wird durch "
        f"differenzierte, handlungsorientierte Aufgaben einbezogen. Die Bewertung basiert auf "
        f"{pron_gen} individuellen Förderzielen (Förderschwerpunkt geistige Entwicklung).</p>"
        f"{topic_lines}"
        f"<p>{pron_cap} zeigt Freude am Lernen und reagiert aufmerksam auf Unterrichtsimpulse.</p>"
    )


def _grade_for_focus(niveau_rule: str, rng: random.Random) -> str:
    if niveau_rule == "1":
        return rng.choice(["1", "1", "2", "ne"])
    if niveau_rule == "2":
        return rng.choice(["2", "2", "3", "4"])
    if niveau_rule == "3":
        return rng.choice(["1", "2", "3", "4"])
    return rng.choice(["1", "2", "3", "4", "ne"])  # "mix"


def _fill_student(ses: Session, stu: Student, sdef: dict,
                  all_subjects: dict, rng: random.Random):
    stype   = sdef["type"]
    vorname = stu.first_name
    p       = _pronouns(vorname)

    stu.lb = (stype == "lb")
    stu.gb = (stype == "gb")

    stu.days_absent_excused      = rng.randint(0, 6)
    stu.days_absent_unexcused    = rng.randint(0, 2)
    stu.lessons_absent_excused   = rng.randint(0, 12)
    stu.lessons_absent_unexcused = rng.randint(0, 4)

    if stype == "lb":
        stu.report_text = REPORT_LB.format(vorname=vorname, **p)
    elif stype == "gb":
        stu.report_text = REPORT_GB.format(vorname=vorname, **p)
    else:
        stu.report_text = REPORT_TEMPLATE.format(vorname=vorname, **p)

    # Lebenspraxis: HTML niveau text for LB/GB
    if stype in ("lb", "gb"):
        lp_subj = all_subjects.get(LEBENSPRAXIS)
        if lp_subj:
            lp_text = (
                LP_LB_HTML.format(vorname=vorname, **p)
                if stype == "lb"
                else LP_GB_HTML.format(vorname=vorname, **p)
            )
            _upsert_student_subject(ses, stu.id, lp_subj.id, lp_text)

    wp_name = WAHLPFLICHT[sdef["wp"]]
    student_subjects = [n for n in MAIN_SUBJECTS if n in all_subjects]
    if wp_name in all_subjects:
        student_subjects.append(wp_name)

    for subj_idx, subj_name in enumerate(student_subjects):
        subj    = all_subjects[subj_name]
        is_sport = subj_name == SPORT
        no_niv   = subj_name in NO_NIVEAU
        ne_whole = stype == "focus" and sdef.get("ne_subj") == subj_name

        # Niveau
        if ne_whole:
            niveau = "ne"
        elif is_sport:
            niveau = "9"
        elif no_niv:
            niveau = None
        elif stype == "gb":
            topics = _topics_for(ses, subj.id)
            niveau = _gb_niveau_html(vorname, subj_name, topics, p)
        elif stype == "lb":
            topics = _topics_for(ses, subj.id)
            niveau = _lb_niveau_html(vorname, subj_name, topics, p)
        elif stype == "focus":
            n_rule = sdef["niveau"]
            niveau = str((subj_idx % 3) + 1) if n_rule == "mix" else n_rule
        else:
            niveau = str(rng.randint(1, 3))

        _upsert_student_subject(ses, stu.id, subj.id, niveau)

        # LB/GB: no topic grades — text in niveau field is sufficient
        if stype in ("lb", "gb"):
            continue

        # Grades per topic
        ne_topic = sdef.get("ne_topic") if stype == "focus" else None

        for topic_idx, topic in enumerate(_topics_for(ses, subj.id)):
            if ne_whole:
                grade_val = "ne"
            elif ne_topic and subj_name == ne_topic[0] and topic_idx == ne_topic[1]:
                grade_val = "ne"
            elif stype == "focus":
                grade_val = _grade_for_focus(sdef["niveau"], rng)
            else:
                # ~8% chance of ne for normal students
                grade_val = "ne" if rng.random() < 0.08 else str(rng.randint(1, 4))

            _upsert_grade(ses, stu.id, topic.id, grade_val)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_class_7ef(seed: int = 42) -> str:
    """Populate test data for class 7ef. Idempotent."""
    rng = random.Random(seed)

    with Session(ENGINE) as ses:
        school_class = ses.query(SchoolClass).filter_by(name=CLASS_NAME).first()
        if school_class is None:
            school_class = SchoolClass(name=CLASS_NAME)
            ses.add(school_class)
            ses.flush()

        all_subjects = {s.name: s for s in ses.query(Subject).all()}
        missing = [n for n in MAIN_SUBJECTS + WAHLPFLICHT if n not in all_subjects]
        warnings = []
        if missing:
            warnings.append(f"Fehlende Fächer (übersprungen): {', '.join(missing)}")

        _select_random_competences(
            ses, school_class.id,
            [n for n in MAIN_SUBJECTS + WAHLPFLICHT if n in all_subjects],
            rng,
        )

        for sdef in STUDENTS_DEF:
            stu = _upsert_student(ses, sdef["last"], sdef["first"], sdef["bday"], school_class.id)
            _fill_student(ses, stu, sdef, all_subjects, rng)

        ses.commit()

    n = len(STUDENTS_DEF)
    msg = f"✅ Testdaten für Klasse {CLASS_NAME} generiert — {n} Schüler."
    if warnings:
        msg += "\n⚠️ " + "\n⚠️ ".join(warnings)
    return msg


def clear_class_7ef() -> str:
    """Remove class 7ef and all its data (students, grades, competence selections)."""
    with Session(ENGINE) as ses:
        school_class = ses.query(SchoolClass).filter_by(name=CLASS_NAME).first()
        if school_class is None:
            return f"ℹ️ Klasse {CLASS_NAME} nicht in der Datenbank."
        students = ses.query(Student).filter_by(class_id=school_class.id).all()
        count = len(students)
        for stu in students:
            ses.delete(stu)
        ses.flush()
        ses.execute(sql_delete(ClassCompetence).where(ClassCompetence.class_id == school_class.id))
        ses.delete(school_class)
        ses.commit()
    return f"✅ Klasse {CLASS_NAME} mit {count} Schüler(n) und Kompetenzdaten entfernt."


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(generate_class_7ef())
