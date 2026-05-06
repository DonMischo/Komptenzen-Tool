"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { competenceApi } from "@/lib/api";
import { ClassSubjectFilter } from "@/components/layout/ClassSubjectFilter";
import { TopicAccordion } from "@/components/kompetenzen/TopicAccordion";
import { GradeMatrixTable } from "@/components/schuelerdaten/GradeMatrixTable";
import { QK } from "@/lib/queries";
import { CompetenceListResponse } from "@/types/api";
import { Save, LogIn } from "lucide-react";
import api from "@/lib/api";

type Change = [number, boolean];
type Tab = "kompetenzen" | "schuelerdaten";

export default function PublicPage() {
  const qc = useQueryClient();
  const [dbReady, setDbReady] = useState(false);
  const [dbError, setDbError] = useState(false);

  const [tab, setTab] = useState<Tab>("kompetenzen");
  const [selectedClass, setSelectedClass] = useState("");
  const [selectedSubject, setSelectedSubject] = useState("");
  const [selectedBlock, setSelectedBlock] = useState("");
  const [pendingChanges, setPendingChanges] = useState<Map<number, boolean>>(new Map());

  // Auto-connect to latest DB on mount
  useEffect(() => {
    api.get("/public/latest-db").then((res) => {
      const db = res.data.db as string | null;
      if (!db) {
        setDbError(true);
        return;
      }
      if (typeof window !== "undefined") {
        localStorage.setItem("activeDb", db);
      }
      setDbReady(true);
    }).catch(() => setDbError(true));
  }, []);

  const canLoadComp = dbReady && !!selectedClass && !!selectedSubject && !!selectedBlock;

  const { data: compData, isLoading: compLoading } = useQuery<CompetenceListResponse>({
    queryKey: QK.competences(selectedClass, selectedSubject, selectedBlock),
    queryFn: () =>
      competenceApi.list(selectedClass, selectedSubject, selectedBlock).then((r) => r.data),
    enabled: canLoadComp && tab === "kompetenzen",
  });

  const saveMutation = useMutation({
    mutationFn: () => {
      const changes: Change[] = Array.from(pendingChanges.entries());
      return competenceApi.save(selectedClass, changes);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QK.competences(selectedClass, selectedSubject, selectedBlock) });
      setPendingChanges(new Map());
      toast.success("Auswahl gespeichert");
    },
    onError: () => toast.error("Fehler beim Speichern"),
  });

  const handleClassChange = (c: string) => {
    setSelectedClass(c);
    setPendingChanges(new Map());
    setSelectedBlock("");
  };

  const handleSubjectChange = (s: string) => {
    setSelectedSubject(s);
    setSelectedBlock("");
    setPendingChanges(new Map());
  };

  if (dbError) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center space-y-2">
          <p className="text-lg font-medium text-destructive">Keine Datenbank verfügbar</p>
          <p className="text-sm text-muted-foreground">
            Bitte den Administrator kontaktieren.
          </p>
        </div>
      </div>
    );
  }

  if (!dbReady) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-pulse text-muted-foreground">Laden…</div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-56 bg-slate-900 text-slate-100 flex flex-col shrink-0">
        <div className="px-4 py-5 border-b border-slate-700">
          <h1 className="font-bold text-base leading-tight">Kompetenzen-Tool</h1>
        </div>

        <nav className="flex-1 py-4 space-y-1 px-2">
          {(["kompetenzen", "schuelerdaten"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`w-full flex items-center px-3 py-2 rounded-md text-sm transition-colors text-left ${
                tab === t
                  ? "bg-slate-700 text-white"
                  : "text-slate-300 hover:bg-slate-800 hover:text-white"
              }`}
            >
              {t === "kompetenzen" ? "Kompetenzen" : "Schülerdaten"}
            </button>
          ))}
        </nav>

        <div className="px-4 py-4 space-y-4 border-t border-slate-700">
          <ClassSubjectFilter
            classValue={selectedClass}
            subjectValue={selectedSubject}
            blockValue={selectedBlock}
            onClassChange={handleClassChange}
            onSubjectChange={handleSubjectChange}
            onBlockChange={setSelectedBlock}
            showBlock={tab === "kompetenzen"}
          />
        </div>

        <div className="px-2 pb-4">
          <a
            href="/login"
            className="w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <LogIn className="h-4 w-4" />
            Admin-Login
          </a>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto bg-muted/20">
        <div className="max-w-6xl mx-auto p-6">
          {tab === "kompetenzen" && (
            <>
              {!selectedClass || !selectedSubject || !selectedBlock ? (
                <p className="text-sm text-muted-foreground">
                  Bitte Klasse, Fach und Block wählen.
                </p>
              ) : compLoading ? (
                <p className="text-sm text-muted-foreground animate-pulse">Laden…</p>
              ) : compData && compData.topics.length > 0 ? (
                <div className="space-y-4">
                  <div className="flex justify-end">
                    <button
                      onClick={() => saveMutation.mutate()}
                      disabled={pendingChanges.size === 0 || saveMutation.isPending}
                      className="flex items-center gap-2 bg-primary text-white px-4 py-2 rounded-md text-sm hover:bg-primary/90 disabled:opacity-40"
                    >
                      <Save className="h-4 w-4" />
                      Speichern ({pendingChanges.size})
                    </button>
                  </div>
                  {compData.topics.map((topic) => (
                    <TopicAccordion
                      key={topic.topic_id}
                      topic={topic}
                      className={selectedClass}
                      pendingChanges={pendingChanges}
                      onToggle={(id, val) =>
                        setPendingChanges((prev) => new Map(prev).set(id, val))
                      }
                      onRefresh={() =>
                        qc.invalidateQueries({
                          queryKey: QK.competences(selectedClass, selectedSubject, selectedBlock),
                        })
                      }
                    />
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Keine Kompetenzen gefunden.</p>
              )}
            </>
          )}

          {tab === "schuelerdaten" && (
            <>
              {!selectedClass || !selectedSubject ? (
                <p className="text-sm text-muted-foreground">
                  Bitte Klasse und Fach wählen.
                </p>
              ) : (
                <GradeMatrixTable
                  classNameValue={selectedClass}
                  subject={selectedSubject}
                />
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}
