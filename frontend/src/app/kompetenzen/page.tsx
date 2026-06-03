"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AppShell } from "@/components/layout/AppShell";
import { ClassSubjectFilter } from "@/components/layout/ClassSubjectFilter";
import { competenceApi } from "@/lib/api";
import { QK } from "@/lib/queries";
import { TopicAccordion } from "@/components/kompetenzen/TopicAccordion";
import { CompetenceListResponse } from "@/types/api";
import { Save, Copy } from "lucide-react";
import { HelpButton } from "@/components/help/HelpButton";

type Change = [number, boolean];

export default function KompetenzenPage() {
  const qc = useQueryClient();
  const [selectedClass, setSelectedClass] = useState("");
  const [selectedSubject, setSelectedSubject] = useState("");
  const [selectedBlock, setSelectedBlock] = useState("");
  const [pendingChanges, setPendingChanges] = useState<Map<number, boolean>>(new Map());

  const canLoad = !!selectedClass && !!selectedSubject && !!selectedBlock;

  // Detect parallel classes (same year digit, e.g. 7a → 7b, 7c)
  const { data: allClassesData } = useQuery<{ classes: string[] }>({
    queryKey: ["classes"],
    queryFn: () => competenceApi.classes().then((r) => r.data),
  });
  const parallelClasses = (allClassesData?.classes ?? []).filter(
    (c) => c !== selectedClass && selectedClass.split("").some((ch) => /\d/.test(ch) && c.includes(ch))
  );

  const { data, isLoading } = useQuery<CompetenceListResponse>({
    queryKey: QK.competences(selectedClass, selectedSubject, selectedBlock),
    queryFn: () =>
      competenceApi
        .list(selectedClass, selectedSubject, selectedBlock)
        .then((r) => r.data),
    enabled: canLoad,
  });

  const saveMutation = useMutation({
    mutationFn: () => {
      const changes: Change[] = Array.from(pendingChanges.entries());
      return competenceApi.save(selectedClass, changes);
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: QK.competences(selectedClass, selectedSubject, selectedBlock),
      });
      setPendingChanges(new Map());
      toast.success("Auswahl gespeichert");
    },
    onError: () => toast.error("Fehler beim Speichern"),
  });

  const syncMutation = useMutation({
    mutationFn: () => competenceApi.syncToParallel(selectedClass),
    onSuccess: (res) => {
      const names: string[] = res.data?.synced_to ?? [];
      toast.success(`Kompetenzen übertragen auf: ${names.join(", ")}`);
    },
    onError: () => toast.error("Fehler beim Übertragen"),
  });

  const handleToggle = (compId: number, value: boolean) => {
    setPendingChanges((prev) => new Map(prev).set(compId, value));
  };

  const handleSubjectChange = (s: string) => {
    setSelectedSubject(s);
    setSelectedBlock("");
    setPendingChanges(new Map());
  };

  const handleClassChange = (c: string) => {
    setSelectedClass(c);
    setPendingChanges(new Map());
  };

  return (
    <AppShell>
      <div className="flex gap-6">
        {/* Sidebar filter */}
        <aside className="w-48 shrink-0 space-y-4">
          <ClassSubjectFilter
            classValue={selectedClass}
            subjectValue={selectedSubject}
            blockValue={selectedBlock}
            onClassChange={handleClassChange}
            onSubjectChange={handleSubjectChange}
            onBlockChange={setSelectedBlock}
          />
        </aside>

        {/* Main content */}
        <div className="flex-1 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h2 className="text-2xl font-bold">Kompetenzen</h2>
              <HelpButton
                title="Kompetenzen auswählen"
                sections={[
                  { heading: "Was hier passiert", text: "Sie legen fest, welche Kompetenzen für diese Klasse in jedem Fach bewertet werden. Nur ausgewählte Kompetenzen erscheinen im Zeugnis." },
                  { heading: "Fach & Block wählen", text: "Links Klasse, Fach und Lernblock auswählen. Die Themen-Akkordeons zeigen alle verfügbaren Kompetenzen." },
                  { heading: "Kompetenzen anhaken", text: "Einzelne Kompetenzen auswählen oder ein ganzes Thema per Titelklick aus-/abwählen." },
                  { heading: "Werkstätten", text: "Werkstätten ist immer vollständig und unveränderlich ausgewählt." },
                  { heading: "Eigene Kompetenzen", text: "Am Ende jedes Themas können klassenspezifische Kompetenzen ergänzt werden." },
                  { heading: "Auf Parallelklassen übertragen", text: 'Der Pfeil-Button (→ 7ef, 7gh …) überträgt die aktuellen Kompetenz-Auswahlen dieses Fachs auf alle erkannten Parallelklassen. Parallelklassen werden automatisch anhand des gleichen Buchstabenmusters erkannt (z. B. 7e und 7f → Parallelklassen). Achtung: Bestehende Auswahlen der Zielklassen werden dabei überschrieben.' },
                  { heading: "Speichern", text: "Der Speichern-Button erscheint, sobald Änderungen vorliegen. Nicht gespeicherte Änderungen gehen beim Verlassen verloren." },
                ]}
              />
            </div>
            <div className="flex items-center gap-2">
              {parallelClasses.length > 0 && pendingChanges.size === 0 && selectedClass && (
                <button
                  onClick={() => {
                    if (confirm(
                      `Alle Kompetenz-Auswahlen von ${selectedClass} auf ${parallelClasses.join(", ")} übertragen?\n\nBestehende Auswahlen der Parallelklassen werden überschrieben.`
                    )) syncMutation.mutate();
                  }}
                  disabled={syncMutation.isPending}
                  title={`Auf Parallelklassen übertragen: ${parallelClasses.join(", ")}`}
                  className="flex items-center gap-2 bg-muted border text-muted-foreground px-3 py-2 rounded-md text-sm hover:bg-muted/80 disabled:opacity-50"
                >
                  <Copy className="h-4 w-4" />
                  {syncMutation.isPending ? "Übertragen…" : `→ ${parallelClasses.join(", ")}`}
                </button>
              )}
              {pendingChanges.size > 0 && (
                <button
                  onClick={() => saveMutation.mutate()}
                  disabled={saveMutation.isPending}
                  className="flex items-center gap-2 bg-primary text-white px-4 py-2 rounded-md text-sm hover:bg-primary/90 disabled:opacity-50"
                >
                  <Save className="h-4 w-4" />
                  {saveMutation.isPending
                    ? "Speichern…"
                    : `Auswahl speichern (${pendingChanges.size})`}
                </button>
              )}
            </div>
          </div>

          {!canLoad && (
            <p className="text-muted-foreground text-sm">
              Bitte Klasse, Fach und Block auswählen.
            </p>
          )}

          {canLoad && isLoading && (
            <p className="text-muted-foreground text-sm animate-pulse">Laden…</p>
          )}

          {data && (
            <div className="space-y-3">
              {data.topics.map((topic) => (
                <TopicAccordion
                  key={topic.topic_id}
                  topic={topic}
                  className={selectedClass}
                  pendingChanges={pendingChanges}
                  onToggle={handleToggle}
                  forceSelected={selectedSubject === "Werkstätten"}
                  onRefresh={() =>
                    qc.invalidateQueries({
                      queryKey: QK.competences(selectedClass, selectedSubject, selectedBlock),
                    })
                  }
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
