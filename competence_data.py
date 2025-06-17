from typing import Dict, List

# ---------------------------------------------------------------------------
#  Datenbasis (kürzbar/erweiterbar)
# ---------------------------------------------------------------------------
SUBJECTS = [
    "Deutsch",
    "Mathematik",
    "Englisch",
    "Wahlpflichtbereich - Französisch",
    "Wahlpflichtbereich - Spanisch",
    "Wahlpflichtbereich - Darstellen und Gestalten",
    "Wahlpflichtbereich - Natur und Technik",
    "MNT - Projekt Lutherpark",
    "Technisches Werken",
    "Geografie",
    "Chemmie",
    "Physik",
    "Biologie",
    "Geschichte",
    "Evangelische Religionslehre",
    "Sport",
    "Werkstätten",
]

COMPETENCES: Dict[str, Dict[str, Dict[str, List[str]]]] = {
        "Deutsch": {
            "5/6": {
                "Hör- / Hör-Sehverstehen": [
                    "Ich kann Hör- und Hör-Seh-Texte zu vertrauten Themen verstehen und das Thema sowie Kernaussagen wiedergeben.",  # :contentReference[oaicite:0]{index=0}
                    "Ich kann Inhalte global, selektiv und detailliert erfassen und sprachliche + nicht-sprachliche Mittel in ihrer Wirkung benennen.",  # :contentReference[oaicite:1]{index=1}
                    "Ich kann die Absicht des Sprechers erkennen.",  # :contentReference[oaicite:2]{index=2}
                ],
                "Leseverstehen": [
                    "Ich kann altersgemäße Sach- und literarische Texte sinnerfassend lesen und zentrale Informationen ordnen.",  # :contentReference[oaicite:3]{index=3}
                    "Ich kann Textsorten unterscheiden und ihre Funktion erklären.",  # :contentReference[oaicite:4]{index=4}
                    "Ich kann Texte flüssig und ausdrucksvoll vorlesen.",  # :contentReference[oaicite:5]{index=5}
                ],
                "Sprechen": [
                    "Ich kann in Gesprächen Informationen austauschen und meine Meinung einfach begründet äußern.",  # :contentReference[oaicite:6]{index=6}
                    "Ich kann Erlebnisse frei erzählen und kurze Vorträge halten.",  # :contentReference[oaicite:7]{index=7}
                    "Ich kann Rollen spielen und Texte szenisch darstellen.",  # :contentReference[oaicite:8]{index=8}
                ],
                "Schreiben": [
                    "Ich kann Berichte, Beschreibungen und Geschichten adressatengerecht verfassen.",  # :contentReference[oaicite:9]{index=9}
                    "Ich kann Texte planen, gliedern und sprachlich überarbeiten – auch mit Rechtschreib­hilfen.",  # :contentReference[oaicite:10]{index=10}
                ],
                "Sprachreflexion": [
                    "Ich kann Wortarten und Satzglieder bestimmen und Regeln korrekt anwenden.",  # :contentReference[oaicite:11]{index=11}
                    "Ich kann Wortbedeutungen erschließen und Wortfamilien nutzen.",  # :contentReference[oaicite:12]{index=12}
                    "Ich kann Satzarten unterscheiden und Satzzeichen richtig setzen.",  # :contentReference[oaicite:13]{index=13}
                ],
            },
            "7/8": {
                "Hör- / Hör-Sehverstehen": [
                    "Ich kann Hör- und Hör-Seh-Texte zu weniger vertrauten Themen mit teilweise komplexer Sprache verstehen.",  # :contentReference[oaicite:14]{index=14}
                    "Ich kann Thema, Kernaussagen und Details detailliert wiedergeben sowie die Kommunikations­absicht deuten.",  # :contentReference[oaicite:15]{index=15}
                ],
                "Leseverstehen": [
                    "Ich kann Texte mit komplexerer Struktur verstehen, zentrale Inhalte erschließen und Textintention, Funktion und Wirkung erläutern.",  # :contentReference[oaicite:16]{index=16}
                    "Ich kann literarische Texte analysieren und Sachtexte kritisch auswerten.",  # :contentReference[oaicite:17]{index=17}
                ],
                "Sprechen": [
                    "Ich kann Gespräche führen, meinen Standpunkt begründet vertreten und Diskussionen leiten.",  # :contentReference[oaicite:18]{index=18}
                    "Ich kann Kurzvorträge und Referate adressaten­gerecht halten und Rollen gestaltend vortragen.",  # :contentReference[oaicite:19]{index=19}
                ],
                "Schreiben": [
                    "Ich kann argumentierende, appellierende und gestaltende Texte selbstständig verfassen.",  # :contentReference[oaicite:20]{index=20}
                    "Ich kann formalisierte Texte wie Briefe oder Protokolle normgerecht schreiben und Texte strukturiert überarbeiten.",  # :contentReference[oaicite:21]{index=21}
                ],
                "Sprachreflexion": [
                    "Ich kann komplexe Satzstrukturen analysieren und Interpunktion korrekt anwenden.",  # :contentReference[oaicite:22]{index=22}
                    "Ich kann Fremd- und Fachwörter korrekt verwenden und die Wirkung sprachlicher Mittel reflektieren.",  # :contentReference[oaicite:23]{index=23}
                    "Ich kann Sprachvarianten erkennen und den Sprachwandel beschreiben.",  # :contentReference[oaicite:24]{index=24}
                ],
            },
        },
        "Mathematik": {
            "5/6": {
                "Arithmetik / Algebra": [
                    "Ich kann natürliche, gebrochene und negative Zahlen lesen, ordnen und runden.",           # :contentReference[oaicite:0]{index=0}
                    "Ich kann Bruchteile zeichnerisch darstellen sowie kürzen und erweitern.",                    # :contentReference[oaicite:1]{index=1}
                    "Ich kann die vier Grundrechenarten schriftlich, halbschriftlich und im Kopf anwenden.",     # :contentReference[oaicite:2]{index=2}
                    "Ich kann Rechengesetze (Kommutativ-, Assoziativ-, Distributiv) gezielt einsetzen.",          # :contentReference[oaicite:3]{index=3}
                    "Ich kann einfache Terme aufstellen und Gleichungen/​Ungleichungen durch Probieren lösen.",  # :contentReference[oaicite:4]{index=4}
                ],
                "Funktionen": [
                    "Ich kann alltagsbezogene Zuordnungen (z. B. Weg-Zeit) erkennen, beschreiben und darstellen.",# :contentReference[oaicite:5]{index=5}
                    "Ich kann Tabellen, Texte, Diagramme und Graphen zielgerecht wählen und wechseln.",           # :contentReference[oaicite:6]{index=6}
                    "Ich kann Muster bei Zahlen und Figuren erkennen, verbal beschreiben und fortsetzen.",        # :contentReference[oaicite:7]{index=7}
                ],
                "Geometrie": [
                    "Ich kann Grundbegriffe wie Punkt, Strecke und Winkel korrekt verwenden.",                   # :contentReference[oaicite:8]{index=8}
                    "Ich kann Figuren zeichnen, verschieben und spiegeln, auch im Koordinaten­system.",          # :contentReference[oaicite:9]{index=9}
                    "Ich kann Umfang und Flächeninhalt von Quadraten, Rechtecken und zusammengesetzten Figuren berechnen.",  # :contentReference[oaicite:10]{index=10}
                    "Ich kann Würfel, Quader, Pyramiden, Zylinder etc. erkennen, Netze zuordnen und Modelle bauen.",         # :contentReference[oaicite:11]{index=11}
                ],
                "Stochastik": [
                    "Ich kann Daten in Ur- und Strichlisten erfassen, ordnen und in Diagrammen darstellen.",      # :contentReference[oaicite:12]{index=12}
                    "Ich kann Mittelwert, Median, Modalwert und Spannweite bestimmen und vergleichen.",           # :contentReference[oaicite:13]{index=13}
                    "Ich kann einfache Zufallsexperimente durchführen und Wahrscheinlichkeiten als sicher/​unmöglich/​wahrscheinlich beschreiben.",  # :contentReference[oaicite:14]{index=14}
                ],
            },
            "7/8": {
                "Arithmetik / Algebra": [
                    "Ich kann rationale Zahlen darstellen, ordnen, runden und in Potenz­schreibweise angeben.",  # :contentReference[oaicite:15]{index=15}
                    "Ich kann Terme umformen (ausmultiplizieren, Klammern auflösen, zusammenfassen) und Werte berechnen.",  # :contentReference[oaicite:16]{index=16}
                    "Ich kann lineare Gleichungen sowie einfache lineare Gleichungs­systeme lösen.",             # :contentReference[oaicite:17]{index=17}
                    "Ich kann Quadratzahlen, Quadrat- und Kubik­wurzeln bestimmen und nutzen.",                  # :contentReference[oaicite:18]{index=18}
                ],
                "Funktionen": [
                    "Ich kann proportionale und umgekehrt proportionale Zuordnungen erkennen und darstellen.",   # :contentReference[oaicite:19]{index=19}
                    "Ich kann lineare und nicht-lineare Zuordnungen unterscheiden und mit dem Dreisatz rechnen.",# :contentReference[oaicite:20]{index=20}
                    "Ich kann Prozent-, Promille- und Zins­aufgaben analysieren, lösen und grafisch präsentieren.",# :contentReference[oaicite:21]{index=21}
                ],
                "Geometrie": [
                    "Ich kann mit Kongruenz­sätzen Dreiecke konstruieren und kongruente Figuren erkennen.",      # :contentReference[oaicite:22]{index=22}
                    "Ich kann den Satz des Thales und den Satz des Pythagoras anwenden.",                        # :contentReference[oaicite:23]{index=23}
                    "Ich kann Flächen- und Volumen­formeln für Prismen, Zylinder, Kegel und Kugeln anwenden.",   # :contentReference[oaicite:24]{index=24}
                ],
                "Stochastik": [
                    "Ich kann Daten systematisch sammeln, tabellarisch erfassen und mit Kenngrößen auswerten.",  # :contentReference[oaicite:25]{index=25}
                    "Ich kann relative Häufigkeiten bestimmen und den Zusammenhang zur Wahrscheinlichkeit erklären.",  # :contentReference[oaicite:26]{index=26}
                    "Ich kann einstufige Zufallsexperimente planen, durchführen und Wahrscheinlichkeiten mit Laplace-Begriffen beschreiben.",  # :contentReference[oaicite:27]{index=27}
                ],
            },
        },
        "Englisch": {
            "5/6": {
                "Hörverstehen": [
                    "Ich kann bekannte Wörter und einfache Sätze verstehen, die sich auf mich, meine Familie oder auf konkrete Dinge aus meinem Alltag beziehen.",
                    "Ich kann Hauptinformationen von alltäglichen Gesprächen, Vorträgen und medialen Beiträgen erfassen.",
                ],
                "Leseverstehen": [
                    "Ich kann Arbeitsanweisungen verstehen und umsetzen.",
                    "Ich kann einfache Texte lesen und ihnen Detailinformationen zu Themen wie Wetter, Urlaub, Wochenende, Schule, Freizeit, Nachbarschaft und Tieren entnehmen.",
                ],
                "Schreiben": [
                    "Ich kann kurze Informationen, Mitteilungen, Gedanken und Texte schreiben.",
                    "Ich kann einen Brief in der einfachen Vergangenheit (Simple Past) schreiben.",
                ],
                "Sprechen": [
                    "Ich kann mich in vertrauten Routinesituationen verständigen.",
                    "Ich kann mich vorstellen, einfache Fragen stellen und beantworten.",
                    "Ich kann vorbereitete Präsentationen zu vertrauten Themen vortragen.",
                    "Ich kann Tiere beschreiben.",
                ],
                "Wortschatz": [
                    "Ich kann mir Vokabeln merken und korrekt in Sätzen anwenden.",
                    "Ich kann neue Vokabeln richtig schreiben.",
                ],
                "Sprachmittlung": [
                    "Ich kann Vokabeln korrekt übersetzen.",
                    "Ich kann sprachliche Äußerungen und kurze Texte sinngemäß übertragen.",
                ],
                "Grammatische Schwerpunkte": [
                    "Ich kenne die englische Satzstellung und kann korrekte Sätze bilden.",
                    "Ich kann Aussagesätze im Simple Past bilden.",
                    "Ich kenne Fragewörter und kann Fragesätze im Simple Past bilden.",
                    "Ich kann regelmäßige und unregelmäßige Verben unterscheiden und in Sätzen anwenden.",
                ],
            }
        },
        "Wahlpflichtbereich - Französisch": {
            "7/8": {
                "Texte rezipieren – Hör- / Hör-Sehverstehen": [
                    "Ich kann vertraute Wörter und einfache Sätze verstehen, die sich auf mich selbst, meine Familie oder konkrete Dinge in meiner Umgebung beziehen.",
                ],
                "Texte rezipieren – Leseverstehen": [
                    "Ich kann kurze, einfache Texte lesen und ihnen Detailinformationen entnehmen.",
                ],
                "Texte produzieren – Sprechen": [
                    "Ich kenne die französischen Ausspracheregeln.",
                    "Ich kann mich auf einfache Art verständigen und ein kurzes Kontaktgespräch führen.",
                    "Ich kann einfache Fragen stellen und beantworten, sofern es sich um vertraute Dinge handelt.",
                ],
                "Texte produzieren – Schreiben": [
                    "Ich kann eine kurze, einfache Postkarte oder E-Mail schreiben und dabei Auskunft über meine Person geben.",
                    "Ich kann mir neue Vokabeln merken und orthographisch korrekt wiedergeben.",
                ],
                "Grammatische Schwerpunkte": [
                    "Ich kann den bestimmten und unbestimmten Artikel korrekt verwenden.",
                    "Ich kann regelmäßige Verben der 1. Gruppe (-er) sowie die unregelmäßigen Verben être und avoir im Präsens und Imperativ konjugieren.",
                    "Ich kann einfache Aussagesätze und Fragesätze bilden.",
                    "Ich kann Kardinal- und Ordinalzahlen bis 60 korrekt verwenden.",
                ],
            }
        },
        "Wahlpflichtbereich - Spanisch": {
            "7/8": {
                "Texte rezipieren – Hör- / Hör-Sehverstehen": [
                    "Ich kann Äußerungen zu vertrauten Themen verstehen und wesentliche Aussagen sowie Detailinformationen entnehmen.",
                ],
                "Texte rezipieren – Leseverstehen": [
                    "Ich kann Texte zu vertrauten Themen verstehen und dabei wesentliche Aussagen sowie Detailinformationen entnehmen.",
                    "Ich kann die Bedeutung vertrauter oder bildlich unterstützter Wörter und einfacher Sätze erschließen.",
                ],
                "Texte produzieren – Sprechen": [
                    "Ich kann in Gesprächen Informationen über mich, meine Umgebung, meine Familie und meine Freunde übermitteln.",
                    "Ich kann mein Viertel und Orte in meinem Viertel vorstellen.",
                    "Ich kann einen situationsadäquaten Wortschatz verwenden und sprachliche Strukturen funktional einsetzen.",
                ],
                "Texte produzieren – Schreiben": [
                    "Ich kann kurze Texte über mich, meine Umgebung, meine Familie und meine Freunde mit einem passenden Wortschatz verfassen.",
                    "Ich kann in vorgefertigten Texten sinnvolle Ergänzungen vornehmen.",
                ],
                "Verfügung über Sprachmittel (Wortschatz & Grammatik)": [
                    "Ich verfüge über Wortschatz zu: persönliche Daten, Familie, unmittelbare Umgebung, Zahlen bis 20, Haustiere, Orte in der Stadt, Ortsangaben.",
                    "Ich kann regelmäßige Verben auf -ar, -er, -ir im Präsens konjugieren sowie die unregelmäßigen Verben ser, estar, ir und tener verwenden.",
                    "Ich kann bestimmte und unbestimmte Artikel korrekt einsetzen, den Plural bilden und Adjektive angleichen.",
                ],
            }
        },
        "Wahlpflichtbereich - Darstellen und Gestalten": {
            "7/8": {
                "Darstellendes Spiel": [
                    "Ich kann Elemente der Körpersprache (Mimik, Gestik, Haltung, Bewegung) bewusst einsetzen und zwischen Alltag / Bühne unterscheiden.",
                    "Ich kann Atem- und Stimmbildungstechniken anwenden und meine Stimme auch nonverbal als Gestaltungsmittel nutzen.",
                    "Ich kann kurze lyrische oder epische Texte in dialogische bzw. szenische Formen umgestalten.",
                    "Ich kann Impulse in Impro-Übungen geben und annehmen, Impro-Regeln anwenden und einfache Szenen entwickeln.",
                    "Ich kann Bühnen- und Spielformen (Figuren-, Masken-, Schatten-, Tanz-, Musiktheater …) unterscheiden und erste Inszenierungs­ideen umsetzen.",
                ],  # :contentReference[oaicite:0]{index=0}
                "Musik": [
                    "Ich kann meine Stimme differenziert nutzen (solistisch & chorisch) und einfache Gesangsparts in Szenen einbauen.",
                    "Ich kann Rhythmen schlagen, improvisieren und rhythmische Begleitungen gestalten.",
                    "Ich kann Klänge / Rhythmen in Bewegung oder Tanz umsetzen und einfache Schrittfolgen ausführen.",
                    "Ich kann Musikstücke in ihrer Wirkung auf Personen / Situationen beschreiben und gezielt einsetzen.",
                ],  # :contentReference[oaicite:1]{index=1}
                "Kunst": [
                    "Ich kann Kostüm, Maske oder Puppen nutzen, um Rollen visuell zu charakterisieren.",
                    "Ich kann grundlegende Bühnen- und Raum­formen unterscheiden und einfache Bühnenbilder entwerfen.",
                    "Ich kann Licht als Mittel zur Raum- und Stimmungs­gestaltung erkennen und erproben.",
                    "Ich kann einfache Werbemittel (Plakat, Flyer) für eine Aufführung gestalten.",
                ],  # :contentReference[oaicite:2]{index=2}
            },
        },
        "Wahlpflichtbereich - Natur und Technik": {
            "7/8": {
                "Leben im privaten Haushalt": [
                    "Ich kann Grundsätze gesunder Ernährung nennen und die Angaben auf Lebensmittel- etiketten auswerten.",
                    "Ich kann Lebensmittel nach Inhaltsstoffen und Energiegehalt charakterisieren.",
                    "Ich kann meine eigenen Ernährungs­gewohnheiten beschreiben und unterschiedliche Esskulturen vergleichen.",
                    "Ich kann eine einfache Mahlzeit planen und zubereiten.",
                    "Ich kann Haushaltstechnik im Wandel der Zeit sowie Funktionalität von Kleidung erklären.",
                ],  # :contentReference[oaicite:0]{index=0}
                "Fortbewegung und Mobilität": [
                    "Ich kann Stoff- und Lichtbewegungen bei Pflanzen experimentell nachweisen.",
                    "Ich kann Bewegungs­prinzipien aus der Natur als Vorbild für technische Fortbewegung erläutern.",
                    "Ich kann die geschichtliche Entwicklung von Verkehrsmitteln und Verkehrsnetzen beschreiben.",
                    "Ich kann umwelt­bewusste Antriebe (Elektro, Hybrid, Brennstoff­zelle) charakterisieren.",
                    "Ich kann Funktionsmodelle zur Fortbewegung planen, bauen und deren Funktion erklären.",
                ],  # :contentReference[oaicite:1]{index=1}
                "Versorgung & Entsorgung – Elektroenergie": [
                    "Ich kann fossile, regenerative, alternative und Kern-Energieträger benennen und zuordnen.",
                    "Ich kann die Umwandlung von Primär- in Sekundär­energie und wesentliche Stufen der Strom­übertragung beschreiben.",
                    "Ich kann Aufbau und Wirkungsweise von Windkraftanlage, Wasserkraftanlage oder Solarzelle erklären.",
                    "Ich kann ein Modell einer Elektroenergie­versorgung planen und aufbauen.",
                ],  # :contentReference[oaicite:2]{index=2}
                "Versorgung & Entsorgung – Wasser": [
                    "Ich kann weltweite Wasser­vorkommen und Wasser­verbrauch darstellen und unterscheiden.",
                    "Ich kann den Weg des Wassers von der Quelle bis zum Verbraucher sowie die Stufen der Abwasser­reinigung erklären.",
                    "Ich kann Regenwasser­aufbereitung beschreiben und eigene Beiträge zum sparsamen Wasser­umgang formulieren.",
                ],  # :contentReference[oaicite:3]{index=3}
            },
        },
        "MNT - Projekt Lutherpark": {
            "5/6": {
                "Naturwissenschaftliches Denken und Arbeiten": [
                    "Ich kann Sachverhalte aus meinem Alltag den Bereichen Mensch, Natur und Technik zuordnen.",
                    "Ich kann den Weg naturwissenschaftlichen Arbeitens (Fragen – Vermuten – Beobachten/Experimentieren – Auswerten) an Beispielen erläutern.",
                    "Ich kann Messgeräte wie Thermometer, Waage oder Bandmaß sachgerecht benutzen.",
                ],
                "Samenpflanzen und Stoffkonzepte": [
                    "Ich kann Bau, Fortpflanzung und Entwicklung von Samenpflanzen beschreiben (Vielfalt – gleicher Grundaufbau).",
                    "Ich kann Keimungs- und Wachstumsbedingungen experimentell untersuchen.",
                    "Ich kann Stoffe an ihren Eigenschaften erkennen, Stoffgemische trennen und Umwandlungen (z. B. Verbrennung) beschreiben.",
                ],
                "Wirbeltiere und Bewegung": [
                    "Ich kann Bau, Ernährung, Atmung, Fortpflanzung und Fortbewegung verschiedener Wirbeltiere vergleichen.",
                    "Ich kann Kräfte, Auftrieb, Strömungen und einfache Bewegungen experimentell untersuchen und erklären.",
                    "Ich kann Verbrennung als Stoffumwandlung mit Energie­freisetzung beschreiben.",
                ],
                "Gesundheit, Wärme und Energie": [
                    "Ich kann Maßnahmen zur Gesunderhaltung (Ernährung, Haltung, Hygiene, Suchtprävention) begründen.",
                    "Ich kann das Hebelgesetz anwenden und Beispiele aus Alltag/Technik erläutern.",
                    "Ich kann Wärme, Wärmeübertragung und Wärmedämmung erklären und geeignete Materialien nennen.",
                ],
                "Lebensraum, Umwelt und Technik": [
                    "Ich kann einen Lebensraum untersuchen, typische Pflanzen/Tiere bestimmen und ihre Anpassungen erklären.",
                    "Ich kann einfache mikroskopische Präparate anfertigen und beschreiben.",
                    "Ich kann Eingriffe des Menschen in die Natur bewerten und Umweltschutz­maßnahmen begründen.",
                    "Ich kann den Weg ‚vom Rohstoff zum Endprodukt‘ an einem Beispiel nachvollziehen und technische Regelkreise erläutern.",
                ],
            },
        },
        "Technisches Werken": {
            "5/6": {
                "Werkstoff Holz": [
                    "Ich kann wichtige Eigenschaften von Holz (Härte, Stabilität, Quellen, Schwinden) experimentell untersuchen und begründen.",  # :contentReference[oaicite:0]{index=0}
                    "Ich kann Hartholz- und Weichholzarten vergleichen und geeignete Verwendungen ableiten.",  # :contentReference[oaicite:1]{index=1}
                    "Ich kann Maßnahmen zum Schutz des Werkstoffs Holz auswählen und begründen.",  # :contentReference[oaicite:2]{index=2}
                    "Ich kann einen Gebrauchsgegenstand planen (Skizze, Ablaufplan, Stückliste) und anhand dieser Unterlagen fertigen.",  # :contentReference[oaicite:3]{index=3}
                    "Ich kann Trenn-, Füge- und Beschichtungsverfahren (Sägen, Feilen, Bohren, Kleben, Schrauben, Streichen) fachgerecht anwenden.",  # :contentReference[oaicite:4]{index=4}
                    "Ich kann den hergestellten Gegenstand nach funktionalen, ökonomischen und ökologischen Kriterien bewerten.",  # :contentReference[oaicite:5]{index=5}
                ],
                "Weitere Werkstoffe (Metall, Kunststoff, Ton, Textil, Lebensmittel)": [
                    "Ich kann typische Eigenschaften der Werkstoffe Metall, Kunststoff, Ton, Textil und Lebensmittel experimentell ermitteln.",  # :contentReference[oaicite:6]{index=6}
                    "Ich kann geeignete Fertigungsverfahren (z. B. Biegen, Nieten, Nähen, Mischen, Backen) auswählen und durchführen.",  # :contentReference[oaicite:7]{index=7}
                    "Ich kann Werkzeuge und Maschinen sicher bedienen und deren Funktionsweise erklären.",  # :contentReference[oaicite:8]{index=8}
                    "Ich kann Planungsunterlagen erstellen und einen Gebrauchsgegenstand aus mindestens zwei unterschiedlichen Werkstoffen herstellen.",  # :contentReference[oaicite:9]{index=9}
                    "Ich kann Produkte hinsichtlich Funktion, Gestaltung, Materialeinsatz und Umweltverträglichkeit beurteilen.",  # :contentReference[oaicite:10]{index=10}
                ],
                "Technischer Modellbau": [
                    "Ich kann Realobjekte und Modelle anhand charakteristischer Merkmale unterscheiden.",  # :contentReference[oaicite:11]{index=11}
                    "Ich kann die Wirkung einfacher Getriebe und Antriebe sowie Grundschaltungen erläutern und experimentell nachweisen.",  # :contentReference[oaicite:12]{index=12}
                    "Ich kann Montage- und Schaltpläne lesen und daraus Modelle bzw. Schaltungen aufbauen.",  # :contentReference[oaicite:13]{index=13}
                    "Ich kann eigene Modell-Konstruktionen planen, fertigen, präsentieren und nach technischen sowie ökologischen Kriterien bewerten.",  # :contentReference[oaicite:14]{index=14}
                ],
            },
        },
        "Medienbildung und Informatik": {
            "5/6": {
                "Informatiksysteme kompetent nutzen": [
                    "Ich kann die Bestandteile eines Computers nennen und ihre Aufgaben beschreiben (Hardware / Software / Netzwerk).",  # :contentReference[oaicite:0]{index=0}
                    "Ich kann das EVAS-Prinzip erklären (Eingabe – Verarbeitung – Ausgabe – Speicherung).",  # :contentReference[oaicite:1]{index=1}
                    "Ich kann sichere Passwörter erstellen und die Folgen unsicherer Passwörter beurteilen.",  # :contentReference[oaicite:2]{index=2}
                ],
                "Algorithmen in Informatikprojekten": [
                    "Ich kann Abläufe analysieren und daraus einfache Algorithmen in einer grafischen Programmier­umgebung (z. B. Scratch) umsetzen.",  # :contentReference[oaicite:3]{index=3}
                    "Ich kann Programmparameter verändern und beobachten, wie sich der Ablauf ändert.",  # :contentReference[oaicite:4]{index=4}
                    "Ich kann Wiederholungsstrukturen einsetzen, um wiederkehrende Sequenzen zu verkürzen.",  # :contentReference[oaicite:5]{index=5}
                ],
                "Bilder und Grafiken gestalten": [
                    "Ich kann erklären, wie eine Rastergrafik aus Pixeln aufgebaut ist und wie Auflösung und Dateigröße zusammenhängen.",  # :contentReference[oaicite:6]{index=6}
                    "Ich kann Bilder aufnehmen, importieren und mit geeigneten Werkzeugen bearbeiten (z. B. zuschneiden, retuschieren, filtern).",  # :contentReference[oaicite:7]{index=7}
                    "Ich kann Bildmanipulationen erkennen, bewerten und deren Auswirkungen kritisch reflektieren.",  # :contentReference[oaicite:8]{index=8}
                ],
                "Präsentationen unter Beachtung des Urheberrechts": [
                    "Ich kann gezielt Informationen recherchieren und ihre Zuverlässigkeit bewerten.",  # :contentReference[oaicite:9]{index=9}
                    "Ich kann Präsentationsfolien adressatengerecht gestalten (klare Struktur, passende Medien, Barrierefreiheit).",  # :contentReference[oaicite:10]{index=10}
                    "Ich kann Bilder und Texte rechtssicher nutzen und Quellen korrekt angeben.",  # :contentReference[oaicite:11]{index=11}
                ],
                "Texte strukturieren und gestalten": [
                    "Ich kann umfangreiche Texte mit Format­vorlagen strukturieren und gestalten.",  # :contentReference[oaicite:12]{index=12}
                    "Ich kann Objekt- und Absatzattribute anpassen (Schrift, Abstände, Aufzählungen).",  # :contentReference[oaicite:13]{index=13}
                    "Ich kann Zitate und Quellen normgerecht einfügen und Rechtschreib­prüfungen nutzen.",  # :contentReference[oaicite:14]{index=14}
                ],
                "In der vernetzten Welt kommunizieren": [
                    "Ich kann Suchmaschinen mit Filtern/Operatoren gezielt nutzen und die Qualität von Treffern einschätzen.",  # :contentReference[oaicite:15]{index=15}
                    "Ich kann sicher in Netzwerken kommunizieren (Passwortschutz, Netiquette, Datenschutz).",  # :contentReference[oaicite:16]{index=16}
                    "Ich kann Cybermobbing und Fakenews erkennen und Strategien zum Umgang damit entwickeln.",  # :contentReference[oaicite:17]{index=17}
                ],
                "Projektarbeit – Multimedia": [
                    "Ich kann Audio- oder Videodateien aufnehmen, schneiden und mit Effekten bearbeiten.",  # :contentReference[oaicite:18]{index=18}
                    "Ich kann Aufnahme­techniken (Sprechtechnik, Kameraführung) benennen und anwenden.",  # :contentReference[oaicite:19]{index=19}
                    "Ich kann mein Multimedia-Projekt planen, durchführen und präsentieren.",  # :contentReference[oaicite:20]{index=20}
                ],
                "Projektarbeit – Computerspiele": [
                    "Ich kann reale und virtuelle Identitäten unterscheiden und mein Spielverhalten reflektieren.",  # :contentReference[oaicite:21]{index=21}
                    "Ich kann zu einfachen Spielsituationen Varianten entwickeln und diskutieren.",  # :contentReference[oaicite:22]{index=22}
                ],
                "Projektarbeit – Informatik historisch": [
                    "Ich kann wichtige Stationen der Informatik­geschichte beschreiben (z. B. Entwicklung des Rechners, bedeutende Persönlichkeiten).",  # :contentReference[oaicite:23]{index=23}
                    "Ich kann historische Geräte/Quellen recherchieren und mein Wissen präsentieren.",  # :contentReference[oaicite:24]{index=24}
                ],
            },
        },
        "Geografie": {
            "5/6": {
                "Die Erde als Planet und Lebensraum": [
                    "Ich kann erläutern, was das Fach Geografie untersucht und warum Raumbezüge wichtig sind.",  # :contentReference[oaicite:0]{index=0}
                    "Ich kann Gestalt, Rotation und Revolution der Erde sowie die unterschiedliche Beleuchtung erklären.",  # :contentReference[oaicite:1]{index=1}
                    "Ich kann beschreiben, wie Menschen in verschiedenen Klimazonen leben.",  # :contentReference[oaicite:2]{index=2}
                ],
                "Leben mit Naturrisiken": [
                    "Ich kann Küstenformen und ihre Dynamik erklären und Schutzmaßnahmen ableiten.",  # :contentReference[oaicite:3]{index=3}
                    "Ich kann Vulkanausbrüche und Erdbeben als Gefährdungen erklären.",  # :contentReference[oaicite:4]{index=4}
                    "Ich kann Flussdynamik und Hochwassergefahren beschreiben und Schutzmaßnahmen nennen.",  # :contentReference[oaicite:5]{index=5}
                    "Ich kann Wetterextreme und Massenbewegungen analysieren und deren Folgen für Menschen erläutern.",  # :contentReference[oaicite:6]{index=6}
                ],
                "Wirtschaftliches Handeln – Ökonomie vs. Ökologie": [
                    "Ich kann regenerative und nicht regenerative Energieerzeugung vergleichen.",  # :contentReference[oaicite:7]{index=7}
                    "Ich kann ökologische mit konventioneller Land- und Forstwirtschaft vergleichen.",  # :contentReference[oaicite:8]{index=8}
                    "Ich kann sanften Tourismus und Massentourismus gegenüberstellen.",  # :contentReference[oaicite:9]{index=9}
                    "Ich kann unterschiedliche Verkehrskonzepte beschreiben.",  # :contentReference[oaicite:10]{index=10}
                ],
                "Stadt- und Landleben": [
                    "Ich kann die räumliche Organisation sowie Lebensweisen in Städten und ländlichen Regionen vergleichen.",  # :contentReference[oaicite:11]{index=11}
                    "Ich kann Merkmale von Metropolen nennen und Stadt-Umland-Beziehungen erklären.",  # :contentReference[oaicite:12]{index=12}
                    "Ich kann Siedlungen als Ergebnis ihrer Entwicklung beschreiben und Ideen für lebenswerte Räume diskutieren.",  # :contentReference[oaicite:13]{index=13}
                ],
            },
            "7/8": {
                "Die Erde als Naturraum": [
                    "Ich kann den inneren Aufbau der Erde und plattentektonische Prozesse beschreiben.",  # :contentReference[oaicite:14]{index=14}
                    "Ich kann klimabestimmende Faktoren erklären.",  # :contentReference[oaicite:15]{index=15}
                    "Ich kann Wechselwirkungen zwischen Klima und Vegetation in verschiedenen Zonen beschreiben.",  # :contentReference[oaicite:16]{index=16}
                ],
                "Tourismus und Freizeit": [
                    "Ich kann weltweite Reiseströme und Tourismusarten erläutern.",  # :contentReference[oaicite:17]{index=17}
                    "Ich kann Tourismuskonzepte auf Nachhaltigkeit prüfen und beurteilen.",  # :contentReference[oaicite:18]{index=18}
                    "Ich kann Beispiele touristischer Entwicklung vergleichen und die Kommerzialisierung von Lebenswelten diskutieren.",  # :contentReference[oaicite:19]{index=19}
                ],
                "Landwirtschaft und Ernährungssicherung": [
                    "Ich kann verschiedene Formen landwirtschaftlicher Nutzung beschreiben.",  # :contentReference[oaicite:20]{index=20}
                    "Ich kann Ursachen und Folgen nicht angepasster Nutzung beurteilen und alternative Konzepte erklären.",  # :contentReference[oaicite:21]{index=21}
                    "Ich kann die Rolle globaler Nahrungsmittelkonzerne und Konsumenten diskutieren.",  # :contentReference[oaicite:22]{index=22}
                ],
                "Energetische Ressourcen": [
                    "Ich kann Entstehung, Förderung und Transport von Kohle und Erdöl erklären.",  # :contentReference[oaicite:23]{index=23}
                    "Ich kann Umweltfolgen fossiler Energiegewinnung diskutieren und regenerative vs. nicht regenerative Energieträger bewerten.",  # :contentReference[oaicite:24]{index=24}
                    "Ich kann soziale und wirtschaftliche Veränderungen durch Erdölförderung in verschiedenen Regionen vergleichen.",  # :contentReference[oaicite:25]{index=25}
                ],
            },
        },
        "Chemie": {
            "7/8": {
                "Chemie – eine Naturwissenschaft": [
                    "Ich kann die Chemie als Naturwissenschaft kennzeichnen und ihre Bedeutung für Alltag, Technik und Umwelt erläutern.",  # :contentReference[oaicite:0]{index=0}
                    "Ich kann Stoffe an Eigenschaften erkennen, Gefahrenpiktogramme deuten und Sicherheitsvorschriften einhalten.",  # :contentReference[oaicite:1]{index=1}
                    "Ich kann chemische Reaktionen von physikalischen Vorgängen über Stoff- und Energieumwandlung unterscheiden.",  # :contentReference[oaicite:2]{index=2}
                    "Ich kann den energetischen Verlauf von Reaktionen als exotherm oder endotherm beschreiben und den Einfluss eines Katalysators erklären.",  # :contentReference[oaicite:3]{index=3}
                    "Ich kann einfache Versuchsprotokolle anfertigen und Experimente fachgerecht durchführen.",  # :contentReference[oaicite:4]{index=4}
                ],
                "Atombau – Periodensystem": [
                    "Ich kann Atome mit Kugel-, Kern-Hülle- und Schalenmodell beschreiben und Bauteilchen nennen.",  # :contentReference[oaicite:5]{index=5}
                    "Ich kann Ordnungsprinzipien des PSE erklären und Valenzelektronen angeben.",  # :contentReference[oaicite:6]{index=6}
                    "Ich kann Lewis-Formeln für Hauptgruppenelemente zeichnen und Ion, Molekül sowie Oktettregel erklären.",  # :contentReference[oaicite:7]{index=7}
                    "Ich kann Stoffmenge, molare Masse und Masse berechnen.",  # :contentReference[oaicite:8]{index=8}
                ],
                "Molekülsubstanzen (O2, H2, H2O)": [
                    "Ich kann Bau, Eigenschaften und Verwendung von Sauerstoff, Wasserstoff und Wasser erläutern.",  # :contentReference[oaicite:9]{index=9}
                    "Ich kann Oxidation als Verbrennung beschreiben, Wort- und Formelgleichungen aufstellen und die Glimmspan- bzw. Knallgasprobe erklären.",  # :contentReference[oaicite:10]{index=10}
                    "Ich kann das Wassermolekül als Dipol deuten und daraus besondere Eigenschaften ableiten.",  # :contentReference[oaicite:11]{index=11}
                ],
                "Metalle und Metalloxide": [
                    "Ich kann Aufbau, Eigenschaften und Verwendung von Metallen und Legierungen erklären und Metallbindung beschreiben.",  # :contentReference[oaicite:12]{index=12}
                    "Ich kann Metalloxide als Ionenverbindungen deuten, Oxidation / Reduktion formulieren und das Hochofen-Verfahren skizzieren.",  # :contentReference[oaicite:13]{index=13}
                    "Ich kann Korrosion erklären und Schutzmaßnahmen begründen.",  # :contentReference[oaicite:14]{index=14}
                ],
                "Säuren, Basen, Neutralisation (*Salze*)": [
                    "Ich kann saure und basische Lösungen anhand von Nachweisen, pH-Wert und elektrischer Leitfähigkeit charakterisieren.",  # :contentReference[oaicite:15]{index=15}
                    "Ich kann Entstehung starker Säuren / Basen durch Oxide beschreiben und Dissoziationsgleichungen aufstellen.",  # :contentReference[oaicite:16]{index=16}
                    "Ich kann Neutralisations- und Fällungsreaktionen erklären, Wort-/Ionengleichungen formulieren und Anwendungsbeispiele nennen.",  # :contentReference[oaicite:17]{index=17}
                    "Ich kann Formeln von Salzen aus Ionenladungen erstellen und Eigenschaften ableiten.",  # :contentReference[oaicite:18]{index=18}
                ],
                "Systematisierung": [
                    "Ich kann Teilchen-, Bindungs- und Stoffarten miteinander vergleichen (Atom, Molekül, Ion / EP-, Metall-, Ionenbindung / Metalle, Molekül-, Ionen­substanzen).",  # :contentReference[oaicite:19]{index=19}
                    "Ich kann Merkmale chemischer Reaktionen (Stoff-/Energie­umwandlung, Bindungsumbau) erläutern.",  # :contentReference[oaicite:20]{index=20}
                ],
            },
        },
        "Physik": {
            "7/8": {
                "Kraft, Druck und mechanische Energie": [
                    "Ich kann Masse, Volumen und Dichte messen, grafisch darstellen und die Dichte eines Körpers experimentell bestimmen.",
                    "Ich kann Reibungs- und Gewichtskraft messen, Kraftarten unterscheiden und Kräfte vektoriell darstellen.",
                    "Ich kann Druck berechnen und Druck in Flüssigkeiten/Gasen mithilfe des Teilchenmodells erklären.",
                    "Ich kann mechanische Arbeit, Leistung sowie potenzielle und kinetische Energie berechnen und den Energie­erhaltungssatz anwenden.",
                ],  # :contentReference[oaicite:0]{index=0}

                "Geladene Körper, Stromkreise und elektrische Größen": [
                    "Ich kann Ladungsarten durch Kraftwirkungen charakterisieren und das elektrische Feld beschreiben.",
                    "Ich kann Stromkreise mit Schaltzeichen skizzieren, aufbauen und Reihen- bzw. Parallelschaltungen unterscheiden.",
                    "Ich kann Stromstärke und Spannung messen und den elektrischen Widerstand berechnen.",
                    "Ich kann Leitungsvorgänge in Metallen, Gasen und Halbleitern an Beispielen erklären.",
                ],  # :contentReference[oaicite:1]{index=1}

                "Temperatur, Wärme und Zustandsänderungen": [
                    "Ich kann Temperatur messen, Temperaturskalen vergleichen und den absoluten Nullpunkt erklären.",
                    "Ich kann Wärme als Energieform beschreiben, die spezifische Wärmekapazität nutzen und die Wärmegleichung anwenden.",
                    "Ich kann Aggregatzustands­änderungen mit dem Teilchenmodell erklären und Umwandlungs­wärmen experimentell nachweisen.",
                ],  # :contentReference[oaicite:2]{index=2}

                "Lichtausbreitung und Bildentstehung": [
                    "Ich kann Lichtquellen, beleuchtete Körper und geradlinige Lichtausbreitung beschreiben sowie Schattenbildung darstellen.",
                    "Ich kann Reflexion und Brechung experimentell untersuchen, Reflexions- und Brechungsgesetz anwenden.",
                    "Ich kann Sammellinsen charakterisieren, Strahlengänge zeichnen und Bildentstehung für optische Geräte erklären.",
                ],  # :contentReference[oaicite:3]{index=3}
            },
        },
        "Biologie": {
            "7/8": {
                "Wirbellose in ihren Lebensräumen": [
                    "Ich kann Wirbellose anhand ihres Stützsystems eindeutig von Wirbeltieren abgrenzen.",
                    "Ich kann äußere Merkmale von Weichtieren, Ringelwürmern und Gliederfüßern beschreiben und Vertreter diesen Tiergruppen zuordnen.",
                    "Ich kann die Rolle von Wirbellosen in Nahrungsketten sowie als Bestäuber oder Krankheitsüberträger erläutern.",
                    "Ich kann Eingriffe des Menschen in Lebensräume von Wirbellosen bewerten und geeignete Schutz-­maßnahmen begründen.",
                    "Ich kann Bau, Atmung, Fortbewegung und Entwicklung der Insekten (z. B. Metamorphose, Insektenstaat) erklären.",
                ],  # :contentReference[oaicite:0]{index=0}

                "Zellen als Lebensbausteine": [
                    "Ich kann die grundlegenden Merkmale des Lebens nennen.",
                    "Ich kann Aufbau und Funktion pflanzlicher und tierischer Zellen beschreiben und einander gegenüberstellen.",
                    "Ich kann erläutern, wie Zellbau und Ernährungsweise (autotroph / heterotroph) zusammenhängen.",
                    "Ich kann Bakterien von Eukaryoten abgrenzen und ihre Bedeutung als Zersetzer, Produzenten oder Krankheitserreger erklären.",
                    "Ich kann anhand der Grünalgen den Übergang vom Einzeller zum Vielzeller darstellen.",
                ],  # :contentReference[oaicite:1]{index=1}

                "Biologie des Menschen": [
                    "Ich kann die hormonell gesteuerten Veränderungen der Pubertät – einschließlich Menstruationszyklus – beschreiben.",
                    "Ich kann Sexualität, unterschiedliche Geschlechtsidentitäten sowie Verhütungs- und Präventions­möglichkeiten erklären.",
                    "Ich kann Aufbau und Arbeitsweise des Nervensystems inklusive Reiz-Reaktions-Kette darlegen.",
                    "Ich kann Verdauungs-, Atmungs-, Blut-, Kreislauf-, Ausscheidungs- und Abwehrsystem in Bau und Funktion erläutern und ihr Zusammenwirken erklären.",
                    "Ich kann Maßnahmen zu Gesunderhaltung (Ernährung, Bewegung, Sucht­prävention, Impfungen) begründen.",
                ],  # :contentReference[oaicite:2]{index=2}
            },
        },
        "Geschichte": {
            "5/6": {
                "Erste Begegnung mit dem Unterrichtsfach Geschichte": [
                    "Ich kann Lebens- und Familiengeschichten als Teil der Geschichte erkennen.",
                    "Ich kann Zeugnisse der Vergangenheit von gegenwärtigen Objekten unterscheiden.",
                    "Ich kann einfache Zeitbegriffe (Jahr, Jahrhundert) anwenden und die Funktion von Zeitleisten erklären.",
                ],  # :contentReference[oaicite:0]{index=0}
                "Kind sein – heute und in der Vergangenheit": [
                    "Ich kann vergleichen, wie Kinder in verschiedenen Zeiten lebten, lernten und arbeiteten.",
                    "Ich kann Konstanten und Veränderungen des Alltagslebens benennen (Wohnen, Kleidung, Freizeit).",
                ],  # :contentReference[oaicite:1]{index=1}
                "Lebensbedingungen und Lebensweisen – Dauer und Wandel": [
                    "Ich kann erklären, wie Umwelt und Technik den Alltag von Menschen in Vor- und Frühgeschichte, Hochkulturen und Antike prägten.",
                    "Ich kann Sesshaftwerdung und Staatenbildung als historische Zäsuren beschreiben.",
                ],  # :contentReference[oaicite:2]{index=2}
                "Aufstieg und Fall einer Großmacht – Das Römische Reich": [
                    "Ich kann die Ausbreitung und Verwaltung des Römischen Reiches skizzieren.",
                    "Ich kann Beispiele römischer Spuren in Europa nennen (Sprache, Recht, Architektur).",
                    "Ich kann Ursachen des Zerfalls des Weströmischen Reiches erklären.",
                ],  # :contentReference[oaicite:3]{index=3}
                "Welt- und Menschenbilder": [
                    "Ich kann mythische und religiöse Vorstellungen früher Kulturen beschreiben.",
                    "Ich kann erklären, wie Kulturbegegnungen zwischen Christen, Juden und Muslimen verliefen.",
                ],  # :contentReference[oaicite:4]{index=4}
            },
            "7/8": {
                "Europa im Mittelalter": [
                    "Ich kann mittelalterliche Lebenswelten (Kloster, Burg, Stadt, Dorf) vergleichen.",
                    "Ich kann Machtstrukturen und Konflikte zwischen weltlicher und geistlicher Herrschaft erklären.",
                    "Ich kann Begegnungen und Konflikte zwischen Christen, Juden und Muslimen beschreiben.",
                ],  # :contentReference[oaicite:5]{index=5}
                "Welt- und Menschenbilder – Eine „neue“ Zeit bricht an": [
                    "Ich kann zentrale Ideen des Humanismus und der Renaissance erläutern.",
                    "Ich kann Auswirkungen der Entdeckungsfahrten auf Europa und die ‚Neue Welt‘ erklären.",
                    "Ich kann Ursachen und Folgen der Reformation zusammenfassen.",
                ],  # :contentReference[oaicite:6]{index=6}
                "Formen der Herrschaft – Absolutismus": [
                    "Ich kann Merkmale des französischen Absolutismus beschreiben.",
                    "Ich kann aufgeklärten Absolutismus an einem Beispiel erläutern.",
                ],  # :contentReference[oaicite:7]{index=7}
                "Französische Revolution – Ideen und Auswirkungen": [
                    "Ich kann die Ziele der Aufklärung und ihre Umsetzung in der Französischen Revolution erklären.",
                    "Ich kann politische Veränderungen durch Napoleon und den Wiener Kongress beschreiben.",
                ],  # :contentReference[oaicite:8]{index=8}
                "Nation und Nationalstaat – Deutschland im 19. Jh.": [
                    "Ich kann liberale und nationale Bewegungen sowie den Reichseinigungs­prozess darstellen.",
                    "Ich kann Politik und Gesellschaft im Deutschen Kaiserreich charakterisieren.",
                ],  # :contentReference[oaicite:9]{index=9}
                "Wirtschaft und Gesellschaft – Dauer und Wandel": [
                    "Ich kann Wirtschaftsformen vom Mittelalter bis zur Industrialisierung vergleichen.",
                    "Ich kann soziale Folgen der Industrialisierung für Arbeit, Wohnen, Familie und Umwelt erklären.",
                ],  # :contentReference[oaicite:10]{index=10}
                "Konflikte und Konfliktlösungen – Imperialismus und Erster Weltkrieg": [
                    "Ich kann Motive und Methoden des Imperialismus beschreiben.",
                    "Ich kann Ursachen, Verlauf und Folgen des Ersten Weltkriegs erläutern.",
                    "Ich kann die Friedensordnung von Versailles beurteilen und ihre Bedeutung für Europa erklären.",
                ],  # :contentReference[oaicite:11]{index=11}
            },
        },
        "Evangelische Religionslehre": {
            "5/6": {
                "Die Frage nach gelingendem menschlichen Leben": [
                    "Ich kann erklären, dass jeder Mensch im christlichen Glauben als einmaliges Geschöpf Gottes gilt und daraus Menschenwürde erwächst.",
                    "Ich kann aus den Zehn Geboten Regeln für ein gelingendes Miteinander ableiten.",
                    "Ich kann Beispiele biblischer Gottes­zuwendung nennen und diakonisches Handeln als menschliche Antwort darauf einordnen.",
                ],  # :contentReference[oaicite:0]{index=0}
                "Die Frage nach der Vielfalt der Religionen": [
                    "Ich kann Grundzüge jüdischen Glaubens (Gottesbild, Heilige Orte, Schrift) beschreiben.",
                    "Ich kann wichtige Stationen der jüdischen Geschichte erläutern und Spuren jüdischen Lebens in Deutschland erkennen.",
                    "Ich kann Feste, Rituale und Symbole im Judentum mit christlichen vergleichen.",
                ],  # :contentReference[oaicite:1]{index=1}
                "Die Frage nach Gott": [
                    "Ich kann eigene Gottesvorstellungen formulieren und mit alttestamentlichen sowie neutestamentlichen Gottesbildern vergleichen.",
                    "Ich kann Entstehung, Aufbau und Verbreitung der Bibel erläutern und Bibelstellen selbständig auffinden.",
                    "Ich kann aus den Schöpfungstexten die Verantwortung des Menschen für Natur und Umwelt ableiten.",
                ],  # :contentReference[oaicite:2]{index=2}
                "Die Frage nach Jesus Christus": [
                    "Ich kann das Leben Jesu in Grundzügen nacherzählen und Gleichnisse als Botschaften für ein gelingendes Miteinander deuten.",
                    "Ich kann zeigen, wie Jesu Wirken in seine jüdische Umwelt eingebettet war.",
                    "Ich kann Gleichnisse methodisch erschließen und Kernaussagen formulieren.",
                ],  # :contentReference[oaicite:3]{index=3}
                "Die Frage nach der Kirche in Geschichte und Gegenwart": [
                    "Ich kann die Entstehung des frühen Christentums bis zur Konstantinischen Wende beschreiben.",
                    "Ich kann kirchliche Feiertage erklären und in den Jahresfestkreis einordnen.",
                    "Ich kann Ausdrucksformen des Glaubens (Gebet, Gottesdienst) deuten und selbst gestalten.",
                ],  # :contentReference[oaicite:4]{index=4}
            },
            "7/8": {
                "Die Frage nach gelingendem menschlichen Leben": [
                    "Ich kann biblische Geschichten als Beispiele göttlicher Zuwendung deuten und auf heutige Konflikte übertragen.",
                    "Ich kann Bedeutung und Grenzen von Familie, Freundschaft, Liebe und Medien kritisch reflektieren.",
                    "Ich kann Konfliktpotenziale erkennen und Lösungswege aus christlicher Perspektive entwickeln.",
                ],  # :contentReference[oaicite:5]{index=5}
                "Die Frage nach der Vielfalt der Religionen": [
                    "Ich kann Entstehung und Grundzüge des Islam erläutern und Gemeinsamkeiten mit Christentum und Judentum benennen.",
                    "Ich kann muslimische Glaubenspraxis (Feste, Symbole, Heilige Schrift) beschreiben.",
                    "Ich kann Möglichkeiten des Zusammenlebens mit Muslimen in Deutschland reflektieren und vorurteilsbewusst diskutieren.",
                ],  # :contentReference[oaicite:6]{index=6}
                "Die Frage nach Gott": [
                    "Ich kann eigene Erfahrungen von Gerechtigkeit/​Ungerechtigkeit mit prophetischen Botschaften (Amos) verknüpfen.",
                    "Ich kann biblische Metaphern zur Gerechtigkeit Gottes deuten und kreativ umsetzen.",
                    "Ich kann das evangelische Verständnis der Rechtfertigung durch Gott erklären.",
                ],  # :contentReference[oaicite:7]{index=7}
                "Die Frage nach Jesus Christus": [
                    "Ich kann Gleichnisse und Wunder als Reich-Gottes-Botschaften erschließen.",
                    "Ich kann ihre Bedeutung für Menschen zur Zeit Jesu und für heutiges Handeln erläutern.",
                    "Ich kann Aufbau und Aussageabsicht von Wundergeschichten analysieren.",
                ],  # :contentReference[oaicite:8]{index=8}
                "Die Frage nach der Kirche in Geschichte und Gegenwart": [
                    "Ich kann mittelalterliche Frömmigkeitsformen erklären und die reformatorische ‚Entdeckung‘ Luthers beschreiben.",
                    "Ich kann Gemeinsamkeiten und Unterschiede der Konfessionen darstellen und den ökumenischen Auftrag erläutern.",
                    "Ich kann kirchengeschichtliche Ereignisse chronologisch einordnen und an Lernorten der Reformation erkunden.",
                ],  # :contentReference[oaicite:9]{index=9}
            },
        },
        "Sport": {
            "5/6": {
                "Gesundheit und Fitness": [
                    "Ich kann meinen Puls vor / nach Belastung messen und Veränderungen erklären.",
                    "Ich kann Aufwärm- und Dehnübungen selbst anleiten und Verletzungsrisiken benennen.",
                    "Ich kann 12 Minuten ohne Pause in einem für mich passenden Tempo laufen.",
                ],  # :contentReference[oaicite:0]{index=0}
                "Sportspiele": [
                    "Ich kann in vereinfachten Zielschussspielen (z. B. 4-gegen-4 Fußball) Ball annehmen, führen und kontrolliert abspielen.",
                    "Ich kann grundlegende Regeln und Fair-Play-Regeln wiedergeben und einhalten.",
                    "Ich kann einfache Spielzüge beobachten und den Mitspielern konstruktiv Rückmeldung geben.",
                ],  # :contentReference[oaicite:1]{index=1}
                "Gerätturnen": [
                    "Ich kann Fallrolle, Handstand anstellen und Felgumschwung in der Grobform turnen.",
                    "Ich kann zwei Stützsprünge über den Kasten (Hocke, Grätsche) sicher ausführen.",
                    "Ich kann beim Helfen / Sichern die wichtigsten Griff- und Stütztechniken anwenden.",
                ],  # :contentReference[oaicite:2]{index=2}
                "Leichtathletik": [
                    "Ich kann 50 m aus dem Tiefstart sprinten und den Startablauf beschreiben.",
                    "Ich kann aus der Absprungzone weit springen und meine Weite messen.",
                    "Ich kann Schlagball aus dem Stand zielgenau werfen und meine Technik verbessern.",
                ],  # :contentReference[oaicite:3]{index=3}
                "Schwimmen": [
                    "Ich kann 15 Minuten ausdauernd Brust schwimmen.",
                    "Ich kann bis zu 10 m weit tauchen und einen Gegenstand heraufholen.",
                    "Ich kann Baderegeln nennen und mein Verhalten im Wasser danach ausrichten.",
                ],  # :contentReference[oaicite:4]{index=4}
            },
            "7/8": {
                "Gesundheit und Fitness": [
                    "Ich kann 20 Minuten im aeroben Bereich joggen und mein Tempo über Pulswerte steuern.",
                    "Ich kann einen kleinen Circuit zur Kraft- und Beweglichkeitsschulung planen und durchführen.",
                    "Ich kann Gesundheitsrisiken und -chancen verschiedener Sportarten erläutern.",
                ],  # :contentReference[oaicite:5]{index=5}
                "Sportspiele": [
                    "Ich kann in einem Zielschussspiel (z. B. 7-gegen-7 Fußball) Überzahlsituationen herausspielen und nutzen.",
                    "Ich kann fliegende Wechsel bei Staffeln (Außen-/Innenwechsel) sicher ausführen.",
                    "Ich kann Spielleistungen beobachten, nach einfachen Kriterien bewerten und korrigieren.",
                ],  # :contentReference[oaicite:6]{index=6}
                "Gerätturnen": [
                    "Ich kann eine Kür mit mind. 4 Elementen an zwei Geräten gestalten und präsentieren.",
                    "Ich kann Felgumschwung, Kehre verbinden und sicher landen.",
                    "Ich kann Partner sichern und Bewegungsfehler sachgerecht korrigieren.",
                ],  # :contentReference[oaicite:7]{index=7}
                "Leichtathletik": [
                    "Ich kann 75 m sprinten, Startblock nutzen und eine saubere Anlauf-Wende laufen.",
                    "Ich kann Hochsprung im Schersprung aus dem Anlauf überqueren und meine Höhe messen.",
                    "Ich kann mit dem Schleuderball aus ganzer Drehung weit werfen und Windrichtung beachten.",
                ],  # :contentReference[oaicite:8]{index=8}
                "Schwimmen": [
                    "Ich kann in zwei Schwimmarten (Brust + Rücken oder Kraul) insgesamt 30 Minuten sicher schwimmen.",
                    "Ich kann Startsprung vom Block und Rollwende anwenden.",
                    "Ich kann Gefahren an offenen Gewässern erklären und geeignete Rettungshilfen einsetzen.",
                ],  # :contentReference[oaicite:9]{index=9}
            },
        },
        "Werkstätten": {
            "5/6": {
                "Technisches Werken": [
                    "Werkstatt",
                ], # :contentReference[oaicite:1]{index=1}
                "Musik": [
                    "Werkstatt",
                ], # :contentReference[oaicite:2]{index=2}
                "Kunst": [
                    "Werkstatt",
                ], # :contentReference[oaicite:3]{index=3}
                "Sport": [
                    "Werkstatt",
                ], # :contentReference[oaicite:4]{index=4}
            },
        },
    }