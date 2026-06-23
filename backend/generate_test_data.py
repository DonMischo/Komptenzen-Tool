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
    SchoolClass, ClassCompetence, StudentSubject, Grade, CustomCompetence,
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
    "Medienbildung und Informatik",
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

FEMALE_FIRST_NAMES = {"Emma", "Mia", "Leonie", "Clara", "Marie", "Miya"}

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
    # HJ2: elective not yet taught this half-year → all topics in WP get "HJ2"
    {
        "last": "Lange",      "first": "Nora",  "bday": date(2012,  4, 10),
        "wp": 1, "type": "focus", "niveau": "2",
        "ne_subj": None, "ne_topic": None,
        "hj2_subj": "Wahlpflichtbereich - Spanisch",
    },
    # cycle_grades: grades 1→2→3→4→ne cycle explicitly across topics, niveau always 1
    {
        "last": "Zimmermann", "first": "Leo",   "bday": date(2013,  2,  5),
        "wp": 2, "type": "cycle_grades",
    },
    # 2nd LB student: shorter HTML text so preview hits the simple-table path
    {
        "last": "Schulz",     "first": "Anna",  "bday": date(2012,  7, 19),
        "wp": 3, "type": "lb",
    },
    # par_mode test students — one per html_to_latex input path
    {"last": "Tepes",    "first": "Miya", "bday": date(2012, 11, 17), "wp": 0, "type": "par_html_p"},
    {"last": "Amalthea", "first": "Miya", "bday": date(2012, 11, 17), "wp": 1, "type": "par_html_br"},
    {"last": "Solair",   "first": "Miya", "bday": date(2012, 11, 17), "wp": 2, "type": "par_plain"},
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

MIYA_PARAS = [
    "Liebe {vorname},",
    "dein drittes Schuljahr an der Evangelischen Gemeinschaftsschule Erfurt hast du erfolgreich gemeistert.",
    "Es war ein aufregendes Schuljahr, in dem wir viel erlebt haben. Mit unserer Klassenfahrt im September nach Oberhof starteten wir gemeinsam in das neue Schuljahr und hatten viel Spaß zusammen. Im BOx-Projekt konntet ihr eure Fähigkeiten besser kennenlernen und in der Berufsfelderkundung das erste Mal in die Berufswelt schnuppern. Zum Weihnachtsbasar war unser Stand ein voller Erfolg und unsere kleine Weihnachtsfeier sehr gemütlich.",
    "{vorname}, du bist eine freundliche und höfliche Schülerin, die mit ihrer offenen und angenehmen Art zu einem guten Miteinander in unserer Klasse beiträgt. Im Umgang mit deinen Mitschüler*innen und Lehrkräften begegnest du anderen respektvoll und hilfsbereit. Durch deine nette Art wirst du von vielen geschätzt und trägst dazu bei, dass sich andere in deiner Gegenwart wohlfühlen.",
    "Im Unterricht zeigst du immer wieder, dass du über gute Fähigkeiten verfügst und durchaus in der Lage bist, Aufgaben erfolgreich zu bewältigen. Besonders bei Themen, die dein Interesse wecken, arbeitest du engagiert mit und bringst dich mit guten Gedanken und Ideen ein. In diesen Momenten wird deutlich, welches Potenzial in dir steckt.",
    "Gleichzeitig fällt es dir nicht immer leicht, dich auf alle Aufgaben mit der gleichen Ausdauer einzulassen. Manchmal benötigst du etwas Zeit, um ins Arbeiten zu kommen, und nicht jedes Thema kann dich gleichermaßen begeistern. Es wäre schön, wenn du dich noch häufiger darauf einlassen würdest, Herausforderungen anzunehmen und auch bei weniger spannenden Aufgaben dranzubleiben.",
    "Für das kommende Schuljahr wünschen wir dir, dass du deine Motivation noch stärker aus dir selbst heraus entwickelst und Schule zunehmend als Chance begreifst, Neues zu entdecken und eigene Stärken weiter auszubauen. Du besitzt viele Fähigkeiten und darfst darauf vertrauen, dass sich Anstrengung und Durchhaltevermögen lohnen.",
    "In diesem Schuljahr hast du interessiert und freudig an den Werkstätten Salsa, Schach, Hip-Hop, Dot Painting, Schmuckgestaltung und Mandala teilgenommen.",
    "Jetzt hast du dir erholsame, aber auch spannende Sommerferien verdient! Genieße die freie Zeit, tanke neue Energie und erlebe schöne Momente mit Familie und Freunden. Wir freuen uns sehr darauf, dich nach den Ferien gesund und gut gelaunt im neuen Schuljahr wiederzusehen.",
    "Viele Grüße von Herrn Lachmann und Frau Reschke",
]


def _miya_text_html_p(vorname: str) -> str:
    """HTML <p> paragraphs — proper TipTap output path."""
    return "".join(f"<p>{p.format(vorname=vorname)}</p>" for p in MIYA_PARAS)


def _miya_text_html_br(vorname: str) -> str:
    """HTML <br> line breaks — text pasted as one block with <br> separators."""
    return "<p>" + "<br><br>".join(p.format(vorname=vorname) for p in MIYA_PARAS) + "</p>"


def _miya_text_plain(vorname: str) -> str:
    """Legacy plain text — stored before rich-text editor existed."""
    return "\n\n".join(p.format(vorname=vorname) for p in MIYA_PARAS)


LP_LB_HTML = (
    "<p>{vorname} besucht das Fach <strong>Lebenspraxis</strong> auf Grundlage "
    "{pron_gen} individuellen Förderplans (<em>Förderschwerpunkt Lernen</em>).</p>"
    "<p>Inhalte umfassen praktische Alltagskompetenzen, soziale Interaktion und "
    "selbstständiges Handeln. {vorname} zeigt <u>erkennbare Fortschritte</u> "
    "bei der Übernahme einfacher Verantwortung im Alltag.</p>"
)

LP_GB_HTML = (
    "<p>{vorname} nimmt aktiv am Unterricht in <strong>Lebenspraxis</strong> teil.</p>"
    "<p>Schwerpunkte sind <u>grundlegende Alltagskompetenzen</u> und die Orientierung im "
    "schulischen und sozialen Umfeld. {vorname} zeigt <em>Freude an praktischen "
    "Aktivitäten</em> und reagiert positiv auf Zuwendung und Unterstützung.</p>"
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


# Subjects with <5% competence selection — to exercise the "incomplete" state in admin UI.
SPARSE_SUBJECTS = {"Geografie", "Biologie"}

# Subjects where every competence should be selected (tiny catalogues, always used).
FULL_SUBJECTS = {"Werkstätten", "Mitarbeit und Verhalten"}


def _select_random_competences(ses: Session, class_id: int,
                                subject_names: list[str], rng: random.Random):
    """Select competences for the class with three tiers:

    - FULL_SUBJECTS   → 100 % selected (Werkstätten, Mitarbeit und Verhalten)
    - SPARSE_SUBJECTS → 1–2 competences total (<5 %) to test incomplete-state UI
    - Everything else → 20–25 % selected, floored at 15 % of the catalogue
    """
    TARGET_RATE = 0.22   # aim for ~22 %
    MIN_RATE    = 0.15   # floor: never go below 15 %

    for name in subject_names:
        subj = ses.query(Subject).filter_by(name=name).first()
        if not subj:
            continue

        topics = ses.query(Topic).filter_by(subject_id=subj.id, block=BLOCK).all()
        if not topics:
            topics = ses.query(Topic).filter_by(subject_id=subj.id).all()

        all_comps = [comp for t in topics for comp in t.competences]
        if not all_comps:
            continue

        if name in FULL_SUBJECTS:
            selected_ids = {c.id for c in all_comps}
        elif name in SPARSE_SUBJECTS:
            n = rng.randint(1, 2)
            selected_ids = {c.id for c in rng.sample(all_comps, min(n, len(all_comps)))}
        else:
            selected_ids = {c.id for c in all_comps if rng.random() < TARGET_RATE}
            # enforce minimum 15 %
            target_min = max(3, int(len(all_comps) * MIN_RATE))
            if len(selected_ids) < target_min:
                pool = [c for c in all_comps if c.id not in selected_ids]
                extras = rng.sample(pool, min(target_min - len(selected_ids), len(pool)))
                selected_ids.update(c.id for c in extras)

        for topic in topics:
            for comp in topic.competences:
                selected = comp.id in selected_ids
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
    items = "".join(
        f"<li><strong>{_he(t.name)}</strong>: Grundlegende Inhalte auf adaptiertem Niveau</li>"
        for t in topics[:4]
    )
    topic_block = (
        f"<p>{pron_cap} arbeitet an folgenden Themenbereichen:</p><ul>{items}</ul>"
    ) if items else ""
    return (
        f"<p>{vorname} bearbeitet <strong>{_he(subj_name)}</strong> auf Grundlage "
        f"{pron_gen} individuellen Förderplans (<em>Förderschwerpunkt Lernen</em>). "
        f"Die Aufgaben sind <u>hinsichtlich Umfang und Komplexität</u> individuell angepasst.</p>"
        f"{topic_block}"
        f"<p>Die Leistungsbewertung richtet sich nach {pron_gen} persönlichen Lernzielen.</p>"
    )


def _gb_niveau_html(vorname: str, subj_name: str, topics: list, p: dict) -> str:
    """HTML-formatted niveau text for GB student, referencing actual topic names."""
    from html import escape as _he
    pron_gen = p["pron_gen"]
    pron_cap = p["pron_cap"]
    items = "".join(
        f"<li>Handlungsorientierte Aktivitäten zu <strong>{_he(t.name)}</strong></li>"
        for t in topics[:3]
    )
    item_block = f"<ul>{items}</ul>" if items else ""
    return (
        f"<p>{vorname} nimmt am Unterricht in <strong>{_he(subj_name)}</strong> teil und wird durch "
        f"<em>differenzierte, handlungsorientierte</em> Aufgaben einbezogen. Die Bewertung basiert auf "
        f"{pron_gen} individuellen Förderzielen (<em>Förderschwerpunkt geistige Entwicklung</em>).</p>"
        f"{item_block}"
        f"<p>{pron_cap} zeigt <u>Freude am Lernen</u> und reagiert aufmerksam auf Unterrichtsimpulse.</p>"
    )


def _add_custom_only_topic(ses: Session, class_id: int, subject_name: str):
    """Find the first topic of subject_name, deselect ALL its regular competences,
    and add custom competences — so the preview must render from custom-only data."""
    subj = ses.query(Subject).filter_by(name=subject_name).first()
    if not subj:
        return
    topic = ses.query(Topic).filter_by(subject_id=subj.id, block=BLOCK).first()
    if not topic:
        topic = ses.query(Topic).filter_by(subject_id=subj.id).first()
    if not topic:
        return

    # Deselect all regular competences for this topic in this class
    for comp in topic.competences:
        cc = ses.query(ClassCompetence).filter_by(
            class_id=class_id, competence_id=comp.id
        ).first()
        if cc is None:
            ses.add(ClassCompetence(class_id=class_id, competence_id=comp.id, selected=False))
        else:
            cc.selected = False

    # Add custom competences (idempotent: skip if text already exists)
    existing_texts = {
        c.text for c in ses.query(CustomCompetence).filter_by(
            class_id=class_id, topic_id=topic.id
        ).all()
    }
    for text in [
        f"Eigene Kompetenz 1 für {topic.name}",
        f"Eigene Kompetenz 2 für {topic.name}",
    ]:
        if text not in existing_texts:
            ses.add(CustomCompetence(class_id=class_id, topic_id=topic.id, text=text))


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
    elif stype == "par_html_p":
        stu.report_text = _miya_text_html_p(vorname)
    elif stype == "par_html_br":
        stu.report_text = _miya_text_html_br(vorname)
    elif stype == "par_plain":
        stu.report_text = _miya_text_plain(vorname)
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
        elif stype == "cycle_grades":
            niveau = "1"
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
        ne_topic  = sdef.get("ne_topic")  if stype == "focus" else None
        hj2_subj  = sdef.get("hj2_subj") if stype == "focus" else None
        _cycle    = ["1", "2", "3", "4", "ne"]

        for topic_idx, topic in enumerate(_topics_for(ses, subj.id)):
            if ne_whole:
                grade_val = "ne"
            elif hj2_subj and subj_name == hj2_subj:
                grade_val = "HJ2"
            elif ne_topic and subj_name == ne_topic[0] and topic_idx == ne_topic[1]:
                grade_val = "ne"
            elif stype == "cycle_grades":
                grade_val = _cycle[topic_idx % len(_cycle)]
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

        # Custom-only topic: deselect all regulars on the first Biologie topic,
        # then add custom competences — exercises the preview custom-only path.
        _add_custom_only_topic(ses, school_class.id, "Biologie")

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
