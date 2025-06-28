from jinja2 import Template
from weasyprint import HTML

from pathlib import Path

base_path = Path(__file__).parent.resolve()

with open("school_report_template.html", encoding="utf-8") as f:
    template = Template(f.read())
    
data = {
    "first_name": "Vorname",
    "last_name": "Nachname",
    "classRoom": "5c",
    "date_of_birth": "29.12.2013",
    "school_year": "2023/2024",
    "location": "Erfurt",
    "report_date": "19.06.2024",
    "personal_text": "Dein erstes Schuljahr an der EGS geht zu Ende...",
    "participation": 2,
    "behavior": 3,
    "days_absent": 6,
    "days_unexcused": 0,
    "subjects": [
        {
            "name": "Deutsch",
            "areas": [
                {
                    "title": "Lese- / Hörverstehen",
                    "competences": [
                        {
                            "description": "Ich kann Hör- und Hör-Seh-Texte zu vertrauten Themen verstehen und das Thema sowie Kernaussagen wiedergeben.",
                            "level": 1
                        },
                        {
                            "description": "Ich kann Texte flüssig und ausdrucksvoll vorlesen.",
                            "level": 2
                        }
                    ]
                },
                {
                    "title": "Texte produzieren - Sprechen",
                    "competences": [
                        {
                            "description": "Ich kann Erlebnisse frei erzählen und kurze Vorträge halten.",
                            "level": 2
                        }
                    ]
                }
            ]
        },
        {
            "name": "Mathematik",
            "areas": [
                {
                    "title": "Arithmetik / Algebra",
                    "competences": [
                        {
                            "description": "Ich kann Bruchteile zeichnerisch darstellen sowie kürzen und erweitern.",
                            "level": 3
                        },
                        {
                            "description": "Ich kann Rechengesetze gezielt einsetzen.",
                            "level": 1
                        }
                    ]
                },
                {
                    "title": "Geometrie",
                    "competences": [
                        {
                            "description": "Ich kann Umfang und Flächeninhalt von Rechtecken berechnen.",
                            "level": 2
                        }
                    ]
                }
            ]
        }
    ]
}


rendered_html = template.render(data,
    image_top=base_path / "Logotop_mit_ESM_zeugnis.png",
    image_bottom=base_path / "Stiftung.png")

HTML(string=rendered_html).write_pdf("schoolReport_Vorname_Nachname.pdf")
