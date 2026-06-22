"use client";

import { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { ClassSubjectFilter } from "@/components/layout/ClassSubjectFilter";
import { GradeMatrixTable } from "@/components/schuelerdaten/GradeMatrixTable";
import { CompetencePreviewTable } from "@/components/schuelerdaten/CompetencePreviewTable";
import { HelpButton } from "@/components/help/HelpButton";
import { Eye, EyeOff } from "lucide-react";

export default function SchuelerdatenPage() {
  const [selectedClass, setSelectedClass] = useState(
    () => (typeof window !== "undefined" ? localStorage.getItem("nav_class") ?? "" : "")
  );
  const [selectedSubject, setSelectedSubject] = useState(
    () => (typeof window !== "undefined" ? localStorage.getItem("nav_subject") ?? "" : "")
  );
  const [showPreview, setShowPreview] = useState(false);

  const handleSubjectChange = (s: string) => {
    setSelectedSubject(s);
    if (typeof window !== "undefined") localStorage.setItem("nav_subject", s);
  };

  const handleClassChange = (c: string) => {
    setSelectedClass(c);
    if (typeof window !== "undefined") localStorage.setItem("nav_class", c);
  };

  const canPreview = !!selectedClass && !!selectedSubject;

  return (
    <AppShell>
      <div className="flex gap-6">
        <aside className="w-48 shrink-0">
          <ClassSubjectFilter
            classValue={selectedClass}
            subjectValue={selectedSubject}
            blockValue=""
            onClassChange={handleClassChange}
            onSubjectChange={handleSubjectChange}
            onBlockChange={() => {}}
            showBlock={false}
          />
        </aside>

        <div className="flex-1">
          <div className="flex items-center gap-3 mb-4">
            <h2 className="text-2xl font-bold">Schülerdaten</h2>
            <HelpButton
              title="Schülerdaten – Noten & Niveau"
              sections={[
                { heading: "Fach & Klasse wählen", text: "Wählen Sie links Klasse und Fach aus. Die Tabelle zeigt alle Schüler mit ihren Bewertungsfeldern." },
                { heading: "Niveau (1–3)", text: 'Die Anforderungsebene des Schülers in diesem Fach. Sport erhält immer 9, Werkstätten und DuG kein Niveau. "ne" = nicht erteilt.' },
                { heading: "Themenurteile (1–4, ne)", text: 'Note pro Thema: 1 (sehr gut) bis 4 (nicht ausreichend). "ne" = nicht erteilt, erzeugt im PDF einen Blockeintrag.' },
                { heading: "LB-Schüler (grün)", text: "LB-Schüler haben Freitext-Felder statt Noten-Dropdowns. Der Text erscheint im Niveau-Feld des Zeugnisses." },
                { heading: "GB-Schüler (orange)", text: "GB-Schüler erhalten ausschließlich Freitext im Niveau-Feld (über den Stift-Button). Keine Themenurteile." },
                { heading: "Lebenspraxis", text: "Erscheint nur bei LB- und GB-Schülern. Kein Themen-Raster, nur ein Freitext-Feld." },
              ]}
            />
            {canPreview && (
              <button
                onClick={() => setShowPreview((v) => !v)}
                title={showPreview ? "Vorschau ausblenden" : "Zeugnistabelle vorschauen"}
                className="ml-auto flex items-center gap-1.5 border px-3 py-1.5 rounded text-sm hover:bg-muted text-muted-foreground"
              >
                {showPreview ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                Vorschau
              </button>
            )}
          </div>

          {selectedClass && selectedSubject ? (
            <div className="space-y-6">
              <GradeMatrixTable
                classNameValue={selectedClass}
                subject={selectedSubject}
              />
              {showPreview && (
                <div>
                  <p className="text-xs text-muted-foreground mb-2 font-medium uppercase tracking-wide">
                    Zeugnistabellen-Vorschau
                  </p>
                  <CompetencePreviewTable
                    classNameValue={selectedClass}
                    subject={selectedSubject}
                  />
                </div>
              )}
            </div>
          ) : (
            <p className="text-muted-foreground text-sm">
              Bitte Klasse und Fach auswählen.
            </p>
          )}
        </div>
      </div>
    </AppShell>
  );
}
