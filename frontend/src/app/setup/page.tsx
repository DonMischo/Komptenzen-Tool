"use client";

import { AppShell } from "@/components/layout/AppShell";
import { HelpButton } from "@/components/help/HelpButton";
import { DatabasePanel } from "@/components/setup/DatabasePanel";
import { SchemaPanel } from "@/components/setup/SchemaPanel";
import { ReportDayPanel } from "@/components/setup/ReportDayPanel";
import { StudentImportPanel } from "@/components/setup/StudentImportPanel";
import { BackupPanel } from "@/components/setup/BackupPanel";

export default function SetupPage() {
  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <h2 className="text-2xl font-bold">⚙️ Setup</h2>
          <HelpButton
            title="Setup & Konfiguration"
            sections={[
              { heading: "Datenbank wählen / anlegen", text: "Jede Datenbank entspricht einem Schuljahr oder einer Klassengruppe. Neue Datenbank anlegen → Namen vergeben (z. B. reports_2026_hj1) → Erstellen." },
              { heading: "Schema initialisieren", text: "Nach dem ersten Anlegen einer neuen Datenbank muss das Schema initialisiert werden, damit Tabellen und Fächer angelegt werden." },
              { heading: "Zeugnistag", text: "Das Datum, das auf der Rückseite jedes Zeugnisses erscheint. Format: TT.MM.JJJJ." },
              { heading: "Schülerimport", text: "CSV-Datei hochladen: Nachname;Vorname;Klasse;Geburtsdatum (TT.MM.JJJJ). Eine Zeile pro Schüler, keine Kopfzeile nötig." },
              { heading: "Backup", text: "Erstellt eine Sicherungskopie der aktuellen Datenbank. Empfohlen vor größeren Änderungen oder Schuljahresende." },
            ]}
          />
        </div>
        <DatabasePanel />
        <SchemaPanel />
        <ReportDayPanel />
        <StudentImportPanel />
        <BackupPanel />
      </div>
    </AppShell>
  );
}
