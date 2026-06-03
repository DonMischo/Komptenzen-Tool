"use client";

import { useState } from "react";
import { X, HelpCircle, ChevronDown, ChevronRight } from "lucide-react";

interface FaqItem {
  q: string;
  a: string;
}

const FAQ: FaqItem[] = [
  {
    q: "Wie ist das Tool erreichbar?",
    a: "Nur im lokalen Schulnetz – per WLAN oder VPN. Adresse: http://zeugnistool.tgsef.intern",
  },
  {
    q: "Was ist der Unterschied zwischen LB und GB?",
    a: "LB (Lernschwäche): Schüler erhalten entweder reguläre Noten oder individuelle Freitexte – je nach Fach. GB (Geistige Behinderung): Ausschließlich Freitexte, keine Noten.",
  },
  {
    q: 'Was bedeutet "Niveau" bei den Schülerdaten?',
    a: 'Das Niveau gibt die Anforderungsebene an: 1, 2 oder 3. Sport: immer 9. Werkstätten & DuG: kein Niveau. "ne" = nicht erteilt (Fach wurde nicht benotet).',
  },
  {
    q: 'Was bedeutet "ne" bei der Note?',
    a: '"ne" steht für nicht erteilt. Im PDF wird das gesamte Thema mit einem Blockeintrag "nicht erteilt" dargestellt statt einzelner Checkboxen.',
  },
  {
    q: "Wie wähle ich Kompetenzen aus?",
    a: 'Im Menü "Kompetenzen": Klasse und Fach wählen, dann Themen aufklappen und die passenden Kompetenzen anhaken. Werkstätten ist immer vollständig ausgewählt.',
  },
  {
    q: "Kann ich Kompetenz-Auswahlen auf Parallelklassen übertragen?",
    a: 'Ja. In "Kompetenzen" erscheint oben rechts ein Pfeil-Button (z. B. → 7ef), sobald Parallelklassen erkannt werden. Ein Klick überträgt alle Auswahlen des aktuellen Fachs auf die Parallelklassen. Achtung: Bestehende Auswahlen der Zielklassen werden dabei überschrieben.',
  },
  {
    q: "Wie importiere ich Schüler?",
    a: "Setup → Schülerimport: CSV-Datei hochladen. Format: Nachname;Vorname;Klasse;Geburtsdatum (TT.MM.JJJJ). Eine Zeile pro Schüler.",
  },
  {
    q: "Wie schreibe ich den Zeugnistext?",
    a: 'Stammdaten → einen Schüler auswählen → "Zeugnistext" klicken. Der Editor unterstützt Fett, Kursiv, Unterstrichen, Listen und Tabellen.',
  },
  {
    q: "Welche Formatierung ist im Zeugnistext möglich?",
    a: "Fett (Strg+B), Kursiv (Strg+I), Unterstrichen (Strg+U), Durchgestrichen, Aufzählungslisten, nummerierte Listen. Alles wird korrekt in LaTeX umgewandelt.",
  },
  {
    q: "Was ist Lebenspraxis?",
    a: "Ein Zusatzfach, das nur für LB- und GB-Schüler erscheint. Es hat keine Kompetenzen, sondern nur ein Freitextfeld für die Bewertung.",
  },
  {
    q: "Wie exportiere ich Zeugnisse als PDF?",
    a: 'Admin → Export: Klasse auswählen, Schüler markieren, "Exportieren" klicken. Die PDFs werden im Verzeichnis ~/Zeugnisse auf dem Server gespeichert.',
  },
  {
    q: "Wie setze ich das Zeugnisdatum?",
    a: "Setup → Zeugnistag: Datum im Format TT.MM.JJJJ eingeben. Dieses Datum erscheint auf der Rückseite des Zeugnisses.",
  },
  {
    q: "Wie lege ich eine neue Datenbank für ein neues Schuljahr an?",
    a: 'Setup → Datenbanken → Neu erstellen. Pro Schuljahr/Halbjahr empfiehlt sich eine eigene Datenbank. Den Namen z. B. "reports_2026_hj1" wählen.',
  },
  {
    q: "Wie erstelle ich zusätzliche Kompetenzen?",
    a: "Kompetenzen auswählen → am Ende jedes Themas gibt es ein Eingabefeld für eigene Kompetenzen, die nur für diese Klasse gelten.",
  },
  {
    q: 'Was bedeuten die Abkürzungen T.e., T.u., S.e., S.u. in den Stammdaten?',
    a: 'T.e. = Fehltage entschuldigt, T.u. = Fehltage unentschuldigt, S.e. = Fehlstunden entschuldigt, S.u. = Fehlstunden unentschuldigt. Alle vier Werte erscheinen auf der Rückseite des Zeugnisses.',
  },
  {
    q: "Was zeigt die Übersicht?",
    a: "Der Bearbeitungsstand jedes Schülers: Noten (Bruch: eingetragen/gesamt), Zeugnistext (✓/✗), Gesamt-Fortschritt. Grün = vollständig, Rot = fehlend.",
  },
  {
    q: "Wer kann sich anmelden?",
    a: "Nutzer werden von einem Admin angelegt (Admin → Benutzer). Es gibt zwei Rollen: Admin (voller Zugriff) und Lehrer (nur Kompetenzen, Schülerdaten, Stammdaten).",
  },
  {
    q: "Was bedeuten die grünen/orangen Zeilen in der Tabelle?",
    a: "Grün = LB-Schüler (Förderschwerpunkt Lernen). Orange = GB-Schüler (Förderschwerpunkt geistige Entwicklung). Die Legende ist über der Tabelle sichtbar.",
  },
];

interface Props {
  open: boolean;
  onClose: () => void;
}

export function FaqModal({ open, onClose }: Props) {
  const [expanded, setExpanded] = useState<number | null>(null);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="bg-slate-800 px-5 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-white">
            <HelpCircle className="h-5 w-5 shrink-0" />
            <span className="font-semibold text-base">Häufige Fragen (FAQ)</span>
          </div>
          <button
            onClick={onClose}
            className="text-white/70 hover:text-white transition-colors"
            aria-label="Schließen"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Accordion */}
        <div className="overflow-y-auto max-h-[70vh] divide-y divide-border">
          {FAQ.map((item, i) => (
            <div key={i}>
              <button
                className="w-full flex items-center justify-between px-5 py-3.5 text-left hover:bg-muted/40 transition-colors gap-3"
                onClick={() => setExpanded(expanded === i ? null : i)}
              >
                <span className="text-sm font-medium text-foreground">{item.q}</span>
                {expanded === i ? (
                  <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
                )}
              </button>
              {expanded === i && (
                <div className="px-5 pb-4">
                  <p className="text-sm text-muted-foreground leading-relaxed">{item.a}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
