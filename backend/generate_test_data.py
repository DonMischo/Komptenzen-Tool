# generate_test_data.py
"""
Generates realistic test data for class 7a.
Run from setup_ui or directly:  python generate_test_data.py
"""
from __future__ import annotations
import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from db_schema import (
    ENGINE, Student, Subject, Topic,
    SchoolClass, ClassCompetence, StudentSubject, Grade,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BLOCK = "7/8"

# Subjects without a numeric Niveau
NO_NIVEAU = {
    "Sport",
    "Wahlpflichtbereich - Darstellen und Gestalten",
    "Werkstätten",
    "Mitarbeit und Verhalten",
}

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

FEMALE_FIRST_NAMES = {
    "Friederike", "Lina", "Hanni", "Lana", "Lucie",
    "Kira", "Leony", "Larissa", "Bisan",
}

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
Jahrgangsstufe. Grammatikalische Strukturen werden sicher angewendet, und im \
mündlichen Bereich äußert sich {vorname} klar und verständlich. Die \
Aufsatzerziehung hat im Laufe des Halbjahres sichtbare Fortschritte gemacht.

In Mathematik zeigt {vorname} ein gutes Verständnis für logische Zusammenhänge \
und algebraische Strukturen. Aufgaben werden methodisch und strukturiert \
bearbeitet; bei anspruchsvolleren Problemstellungen arbeitet {pron} ausdauernd \
und zielorientiert. Die Grundrechenarten sowie der Umgang mit Variablen werden \
sicher beherrscht.

Im Englischunterricht kommuniziert {vorname} zunehmend sicherer in der \
Fremdsprache. Vokabular und Grammatik werden angemessen eingesetzt, und das \
Hörverstehen hat sich spürbar verbessert. Schriftliche Arbeiten zeigen eine \
gute Grundkompetenz; kreative Schreibanlässe werden mit Freude wahrgenommen.

Im naturwissenschaftlichen Bereich zeichnet sich {vorname} durch Neugier und \
sorgfältige Beobachtungsgabe aus. Experimente werden gewissenhaft durchgeführt \
und Ergebnisse nachvollziehbar dokumentiert. Das Verständnis für \
naturwissenschaftliche Zusammenhänge wächst kontinuierlich.

Im sozialen Miteinander verhält sich {vorname} respektvoll und kollegial. \
Die Zusammenarbeit mit Mitschülerinnen und Mitschülern gelingt gut; {pron} \
übernimmt Verantwortung für das eigene Handeln und ist bereit, anderen zu \
helfen. Das Klassenklima wird durch {vorname} positiv beeinflusst.

Insgesamt hat {vorname} in diesem Schulhalbjahr erfreuliche Leistungen erbracht. \
Mit weiterhin konsequentem Einsatz und Lernbereitschaft ist {vorname} auf einem \
guten Weg, die gesetzten Ziele zu erreichen und {pron_akk} Potenzial voll \
auszuschöpfen. Wir wünschen {vorname} für das weitere Schuljahr viel Erfolg \
und Freude am Lernen.\
"""

REPORT_ALEXANDER = """\
Alexander hat das vergangene Schulhalbjahr regelmäßig und pünktlich besucht. \
Seine Teilnahme am Unterricht war stets engagiert und von Lernbereitschaft \
geprägt. Er zeigt eine positive Grundeinstellung gegenüber schulischen \
Anforderungen und arbeitet motiviert mit, auch wenn einzelne \
Aufgabenstellungen besondere Herausforderungen darstellen.

Alexander besucht den Unterricht auf der Grundlage eines individuellen \
Förderplans mit dem Förderschwerpunkt Lernen. Die erbrachten Leistungen \
werden entsprechend seiner individuellen Lernziele bewertet und spiegeln \
seinen persönlichen Lernfortschritt wider. Im Rahmen seiner Möglichkeiten \
zeigt Alexander bemerkenswerte und ermutigende Fortschritte.

Im Fach Mathematik arbeitet Alexander mit großem Einsatz. Grundlegende \
Rechenoperationen führt er mit wachsender Sicherheit durch. Bei komplexeren \
Aufgaben nimmt er gezielte Unterstützung gut an und arbeitet dann ausdauernd \
weiter. Sein Verständnis für mathematische Zusammenhänge hat sich im Laufe \
des Halbjahres schrittweise weiterentwickelt.

Im Englischunterricht zeigt Alexander Mut zur Kommunikation und beteiligt \
sich am mündlichen Unterrichtsgeschehen. Er erweitert seinen Wortschatz \
kontinuierlich und versteht einfache Sätze und Anweisungen sicher. \
Schriftliche Aufgaben bewältigt er mit Hilfestellung zunehmend \
selbstständiger.

Alexander ist ein geschätztes Mitglied der Klassengemeinschaft. Er verhält \
sich gegenüber Mitschülerinnen, Mitschülern und Lehrkräften stets \
respektvoll und freundlich. Die Zusammenarbeit in der Gruppe gelingt ihm gut, \
und er bringt sich aktiv in das Klassengeschehen ein.

Wir freuen uns über Alexanders Entwicklung und ermutigen ihn, seinen \
eingeschlagenen Weg mit Zuversicht und Ausdauer fortzusetzen. Mit der \
Unterstützung aller Beteiligten wird Alexander seine individuellen Ziele \
weiter voranbringen. Wir wünschen ihm für das kommende Schulhalbjahr \
alles Gute und weiterhin viel Freude am Lernen.\
"""

NIVEAU_WORTURTEIL_ALEXANDER = (
    "Alexander besucht den Unterricht auf der Grundlage eines individuellen "
    "Förderplans mit dem Förderschwerpunkt Lernen. Die Leistungsbewertung "
    "erfolgt auf Basis individueller Lernziele. Er zeigt erkennbare Fortschritte "
    "und arbeitet mit großem Einsatz. Praktisches und handlungsorientiertes "
    "Lernen gelingt ihm besonders gut. Mit gezielter Unterstützung bewältigt "
    "er Aufgaben zunehmend selbstständig."
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

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


def _select_all_competences_for_class(ses: Session, class_id: int,
                                       subject_names: list[str]):
    """
    Mark all block-7/8 competences as selected for the given class.
    Falls back to all blocks if a subject has no 7/8 topics.
    """
    for name in subject_names:
        subj = ses.query(Subject).filter_by(name=name).first()
        if not subj:
            continue
        topics = ses.query(Topic).filter_by(subject_id=subj.id, block=BLOCK).all()
        if not topics:                          # fallback: any block
            topics = ses.query(Topic).filter_by(subject_id=subj.id).all()
        for topic in topics:
            for comp in topic.competences:
                cc = ses.query(ClassCompetence).filter_by(
                    class_id=class_id, competence_id=comp.id
                ).first()
                if cc is None:
                    ses.add(ClassCompetence(
                        class_id=class_id, competence_id=comp.id, selected=True
                    ))
                else:
                    cc.selected = True


def _topics_for(ses: Session, subject_id: int) -> list[Topic]:
    """Return block-7/8 topics, falling back to all topics."""
    topics = ses.query(Topic).filter_by(subject_id=subject_id, block=BLOCK).all()
    if not topics:
        topics = ses.query(Topic).filter_by(subject_id=subject_id).all()
    return topics


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_class_7a(seed: int = 42) -> str:
    """
    Populate test data for class 7a.
    Idempotent — safe to call multiple times (overwrites existing values).
    Returns a human-readable status string.
    """
    rng = random.Random(seed)

    with Session(ENGINE) as ses:
        # --- resolve class ---
        school_class = ses.query(SchoolClass).filter_by(name="7a").first()
        if not school_class:
            return "❌ Klasse 7a nicht gefunden."

        students = list(ses.query(Student).filter_by(class_id=school_class.id)
                          .order_by(Student.last_name, Student.first_name).all())
        if not students:
            return "❌ Keine Schüler in Klasse 7a. Bitte zuerst Schülerdaten importieren."

        # --- resolve subjects ---
        all_subjects = {s.name: s for s in ses.query(Subject).all()}
        missing = [n for n in MAIN_SUBJECTS + WAHLPFLICHT if n not in all_subjects]
        warnings = []
        if missing:
            warnings.append(f"Fehlende Fächer (übersprungen): {', '.join(missing)}")

        # --- 1. Select competences for whole class (all subjects) ---
        _select_all_competences_for_class(
            ses, school_class.id,
            [n for n in MAIN_SUBJECTS + WAHLPFLICHT if n in all_subjects]
        )

        # --- 2. Per-student data ---
        for idx, student in enumerate(students):
            is_alexander = (
                student.first_name == "Alexander"
                and student.last_name == "Herrmann"
            )
            vorname = student.first_name

            # Wahlpflichtfach — one per student, cycled
            wp_name = WAHLPFLICHT[idx % len(WAHLPFLICHT)]
            student_subjects = [n for n in MAIN_SUBJECTS if n in all_subjects]
            if wp_name in all_subjects:
                student_subjects.append(wp_name)

            # Report text
            if is_alexander:
                student.report_text = REPORT_ALEXANDER
                student.lb = True
            else:
                pron     = "sie" if vorname in FEMALE_FIRST_NAMES else "er"
                pron_akk = "ihr" if pron == "sie" else "sein"
                student.report_text = REPORT_TEMPLATE.format(
                    vorname=vorname, pron=pron, pron_akk=pron_akk
                )

            # Absence data
            student.days_absent_excused      = rng.randint(0, 6)
            student.days_absent_unexcused    = rng.randint(0, 2)
            student.lessons_absent_excused   = rng.randint(0, 12)
            student.lessons_absent_unexcused = rng.randint(0, 4)

            # --- per subject ---
            for subj_name in student_subjects:
                subj = all_subjects[subj_name]
                no_niveau = subj_name in NO_NIVEAU

                # Niveau
                if no_niveau:
                    niveau = None
                elif is_alexander and subj_name in ("Mathematik", "Englisch"):
                    niveau = NIVEAU_WORTURTEIL_ALEXANDER
                else:
                    niveau = str(rng.randint(1, 3))

                _upsert_student_subject(ses, student.id, subj.id, niveau)

                # Grades per topic — always numeric 1–4 (Worturteile live in niveau)
                for topic in _topics_for(ses, subj.id):
                    value = str(rng.randint(1, 4))
                    _upsert_grade(ses, student.id, topic.id, value)

        ses.commit()

    n = len(students)
    msg = f"✅ Testdaten für Klasse 7a generiert — {n} Schüler, Niveaus 1–3, Noten 1–4."
    if warnings:
        msg += "\n⚠️ " + "\n⚠️ ".join(warnings)
    return msg


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print(generate_class_7a())
