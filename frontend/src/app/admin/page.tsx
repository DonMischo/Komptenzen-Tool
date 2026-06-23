"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { AppShell } from "@/components/layout/AppShell";
import { adminApi, competenceApi } from "@/lib/api";
import { QK } from "@/lib/queries";
import { AdminStudentItem } from "@/types/api";
import { ExportProgress } from "@/components/admin/ExportProgress";
import { UserManagement } from "@/components/admin/UserManagement";
import { useExportSSE } from "@/hooks/useExportSSE";
import { cn } from "@/lib/utils";
import { FileText, RefreshCw, AlertTriangle, CheckCircle } from "lucide-react";
import { HelpButton } from "@/components/help/HelpButton";

type Tab = "export" | "users" | "kompetenzdaten";

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>("export");

  // Export state
  const [selectedClass, setSelectedClass] = useState("");
  const [checkedIds, setCheckedIds] = useState<Set<number>>(new Set());
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobTotal, setJobTotal] = useState(0);

  const [syncConfirmed, setSyncConfirmed] = useState(false);

  const { data: syncDiff, isFetching: syncLoading, refetch: fetchDiff } = useQuery({
    queryKey: ["competence-sync-diff"],
    queryFn: () => adminApi.competenceSyncDiff().then((r) => r.data),
    enabled: tab === "kompetenzdaten",
    staleTime: 0,
  });

  const applyMutation = useMutation({
    mutationFn: () => adminApi.competenceSyncApply().then((r) => r.data),
    onSuccess: () => {
      toast.success("Kompetenzdaten erfolgreich synchronisiert");
      setSyncConfirmed(false);
      fetchDiff();
    },
    onError: () => toast.error("Synchronisation fehlgeschlagen"),
  });

  const { data: classesData } = useQuery({
    queryKey: QK.classes,
    queryFn: () => competenceApi.classes().then((r) => r.data),
  });

  const { data: students, isLoading } = useQuery<AdminStudentItem[]>({
    queryKey: QK.adminStudents(selectedClass),
    queryFn: () => adminApi.students(selectedClass).then((r) => r.data),
    enabled: !!selectedClass,
  });

  useEffect(() => {
    if (students) setCheckedIds(new Set());
  }, [students]);

  const prepareMutation = useMutation({
    mutationFn: (ids: number[]) =>
      adminApi.prepareExport(ids, selectedClass).then((r) => r.data),
    onSuccess: (data) => {
      setJobTotal(data.total);
      setJobId(data.job_id);
    },
    onError: () => toast.error("Export-Vorbereitung fehlgeschlagen"),
  });

  const { events, isDone, stop } = useExportSSE(jobId);

  const classes: string[] = classesData?.classes ?? [];
  const studentList: AdminStudentItem[] = students ?? [];

  const toggleCheck = (id: number) => {
    setCheckedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (checkedIds.size === studentList.length) {
      setCheckedIds(new Set());
    } else {
      setCheckedIds(new Set(studentList.map((s) => s.id)));
    }
  };

  const startExport = (ids: number[]) => {
    setJobId(null);
    prepareMutation.mutate(ids);
  };

  const closeExport = () => {
    stop();
    setJobId(null);
  };

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <h2 className="text-2xl font-bold">Admin</h2>
          <HelpButton
            title="Admin-Bereich"
            sections={[
              { heading: "Export-Tab", text: 'Klasse auswählen, Schüler per Checkbox markieren und "Exportieren" klicken. LuaLaTeX kompiliert die PDFs serverseitig. Die Dateien landen in ~/Zeugnisse/[Jahr]-[HJ|EJ]/[Klasse]/ auf dem Server.' },
              { heading: "Benutzer-Tab", text: "Neue Nutzer anlegen (Benutzername + Passwort + Rolle). Rolle Admin: voller Zugriff inkl. Setup und Übersicht. Rolle Lehrer: nur Kompetenzen, Schülerdaten und Stammdaten." },
              { heading: "Hinweis zum Export", text: "Vor dem Export sicherstellen, dass für alle Schüler Niveau, Themenurteile und Zeugnistext vollständig sind. Die Übersicht zeigt den aktuellen Stand." },
            ]}
          />
        </div>

        {/* Tabs */}
        <div className="flex gap-0 border-b">
          {(["export", "users", "kompetenzdaten"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                "px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors",
                tab === t
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              {t === "export" ? "Export" : t === "users" ? "Benutzer" : "Kompetenzdaten"}
            </button>
          ))}
        </div>

        {/* Export tab */}
        {tab === "export" && (
          <div className="space-y-6">
            {/* Class selector */}
            <div className="flex gap-3 items-center">
              <label className="text-sm font-medium">Klasse:</label>
              <select
                value={selectedClass}
                onChange={(e) => {
                  setSelectedClass(e.target.value);
                  setCheckedIds(new Set());
                  setJobId(null);
                }}
                className="border rounded-md px-2 py-1.5 text-sm"
              >
                <option value="">– Klasse –</option>
                {classes.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            {selectedClass && isLoading && (
              <p className="text-sm text-muted-foreground animate-pulse">Laden…</p>
            )}

            {studentList.length > 0 && (
              <div className={cn("gap-6", jobId ? "flex items-start" : "space-y-6")}>
                {/* Left: student list + buttons */}
                <div className="flex-1 space-y-4 min-w-0">
                  <div className="border rounded-xl overflow-hidden">
                    <table className="text-sm w-full border-collapse">
                      <thead>
                        <tr className="bg-muted/50">
                          <th className="px-3 py-2 border-b">
                            <input
                              type="checkbox"
                              checked={checkedIds.size === studentList.length}
                              onChange={toggleAll}
                              className="h-4 w-4"
                            />
                          </th>
                          <th className="text-left px-3 py-2 border-b font-medium">Nachname</th>
                          <th className="text-left px-3 py-2 border-b font-medium">Vorname</th>
                        </tr>
                      </thead>
                      <tbody>
                        {studentList.map((stu, ri) => (
                          <tr
                            key={stu.id}
                            className={`cursor-pointer ${ri % 2 === 0 ? "bg-white" : "bg-muted/20"} hover:bg-blue-50`}
                            onClick={() => toggleCheck(stu.id)}
                          >
                            <td className="px-3 py-2 border-b text-center">
                              <input
                                type="checkbox"
                                checked={checkedIds.has(stu.id)}
                                onChange={() => toggleCheck(stu.id)}
                                onClick={(e) => e.stopPropagation()}
                                className="h-4 w-4"
                              />
                            </td>
                            <td className="px-3 py-2 border-b font-medium">{stu.last_name}</td>
                            <td className="px-3 py-2 border-b">{stu.first_name}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="flex gap-3">
                    <button
                      onClick={() => startExport(Array.from(checkedIds))}
                      disabled={checkedIds.size === 0 || prepareMutation.isPending}
                      className="flex items-center gap-2 bg-primary text-white px-4 py-2 rounded-md text-sm hover:bg-primary/90 disabled:opacity-40"
                    >
                      <FileText className="h-4 w-4" />
                      Ausgewählte erstellen ({checkedIds.size})
                    </button>
                    <button
                      onClick={() => startExport(studentList.map((s) => s.id))}
                      disabled={prepareMutation.isPending}
                      className="flex items-center gap-2 border px-4 py-2 rounded-md text-sm hover:bg-muted"
                    >
                      <FileText className="h-4 w-4" />
                      Alle erstellen ({studentList.length})
                    </button>
                  </div>
                </div>

                {/* Right sidebar: export progress */}
                {jobId && (
                  <div className="w-80 shrink-0">
                    <ExportProgress
                      events={events}
                      total={jobTotal}
                      isDone={isDone}
                      onStop={stop}
                      onClose={closeExport}
                    />
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Users tab */}
        {tab === "users" && <UserManagement />}

        {/* Kompetenzdaten tab */}
        {tab === "kompetenzdaten" && (
          <div className="space-y-4 max-w-xl">
            <p className="text-sm text-muted-foreground">
              Vergleicht die Kompetenzdaten in <code>competence_data.py</code> mit der Datenbank und zeigt an, was sich geändert hat.
            </p>

            <button
              onClick={() => { setSyncConfirmed(false); fetchDiff(); }}
              disabled={syncLoading}
              className="flex items-center gap-2 border px-4 py-2 rounded-md text-sm hover:bg-muted disabled:opacity-40"
            >
              <RefreshCw className={cn("h-4 w-4", syncLoading && "animate-spin")} />
              Unterschiede prüfen
            </button>

            {syncDiff && (
              <div className="border rounded-xl p-4 space-y-3 text-sm">
                {!syncDiff.has_changes ? (
                  <div className="flex items-center gap-2 text-green-600">
                    <CheckCircle className="h-4 w-4" />
                    Datenbank ist aktuell – keine Änderungen notwendig.
                  </div>
                ) : (
                  <>
                    {syncDiff.subjects_added.length > 0 && (
                      <div><span className="font-medium text-green-700">+ Fächer neu:</span> {syncDiff.subjects_added.join(", ")}</div>
                    )}
                    {syncDiff.topics_added.length > 0 && (
                      <div><span className="font-medium text-green-700">+ Themen neu:</span> {syncDiff.topics_added.join(", ")}</div>
                    )}
                    {syncDiff.competences_added > 0 && (
                      <div><span className="font-medium text-green-700">+ Kompetenzen neu:</span> {syncDiff.competences_added}</div>
                    )}
                    {syncDiff.subjects_removed.length > 0 && (
                      <div><span className="font-medium text-red-700">− Fächer entfernt:</span> {syncDiff.subjects_removed.join(", ")}</div>
                    )}
                    {syncDiff.topics_removed.length > 0 && (
                      <div><span className="font-medium text-red-700">− Themen entfernt:</span> {syncDiff.topics_removed.join(", ")}</div>
                    )}
                    {syncDiff.competences_removed > 0 && (
                      <div><span className="font-medium text-red-700">− Kompetenzen entfernt:</span> {syncDiff.competences_removed}</div>
                    )}

                    {syncDiff.has_removals && (
                      <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg p-3 text-red-800">
                        <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                        <div>
                          <p className="font-semibold">Achtung – Datenverlust!</p>
                          <p>Durch das Entfernen gehen <strong>{syncDiff.class_selections_lost} Kompetenz-Auswahlen</strong> und <strong>{syncDiff.grades_lost} Benotungen</strong> unwiderruflich verloren.</p>
                        </div>
                      </div>
                    )}

                    <div className="pt-2 space-y-2">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={syncConfirmed}
                          onChange={(e) => setSyncConfirmed(e.target.checked)}
                          className="h-4 w-4"
                        />
                        <span>Ich habe die Änderungen geprüft und bestätige die Synchronisation.</span>
                      </label>
                      <button
                        onClick={() => applyMutation.mutate()}
                        disabled={!syncConfirmed || applyMutation.isPending}
                        className="flex items-center gap-2 bg-red-600 text-white px-4 py-2 rounded-md text-sm hover:bg-red-700 disabled:opacity-40"
                      >
                        <RefreshCw className={cn("h-4 w-4", applyMutation.isPending && "animate-spin")} />
                        Jetzt synchronisieren
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </AppShell>
  );
}
