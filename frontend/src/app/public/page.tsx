"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { competenceApi, stammdatenApi, authApi } from "@/lib/api";
import { ClassSubjectFilter } from "@/components/layout/ClassSubjectFilter";
import { TopicAccordion } from "@/components/kompetenzen/TopicAccordion";
import { GradeMatrixTable } from "@/components/schuelerdaten/GradeMatrixTable";
import { ReportTextEditor } from "@/components/stammdaten/ReportTextEditor";
import { QK } from "@/lib/queries";
import { AuthStatusResponse, CompetenceListResponse, StudentBaseData } from "@/types/api";
import { Save, LogOut } from "lucide-react";
import api from "@/lib/api";
import { useRouter } from "next/navigation";

type Change = [number, boolean];
type Tab = "kompetenzen" | "schuelerdaten" | "stammdaten";

export default function PublicPage() {
  const qc = useQueryClient();
  const router = useRouter();
  const [dbReady, setDbReady] = useState(false);
  const [dbError, setDbError] = useState(false);

  const [tab, setTab] = useState<Tab>("kompetenzen");
  const [selectedClass, setSelectedClass] = useState("");
  const [selectedSubject, setSelectedSubject] = useState("");
  const [selectedBlock, setSelectedBlock] = useState("");
  const [pendingChanges, setPendingChanges] = useState<Map<number, boolean>>(new Map());

  const { data: auth } = useQuery<AuthStatusResponse>({
    queryKey: QK.authStatus,
    queryFn: () => authApi.me().then((r) => r.data),
  });

  const logoutMutation = useMutation({
    mutationFn: () => authApi.logout(),
    onSuccess: () => { qc.clear(); router.replace("/login"); },
  });

  // Redirect if not authenticated
  useEffect(() => {
    if (!auth) return;
    if (!auth.authenticated) router.replace("/login");
  }, [auth, router]);

  // Auto-connect to latest DB once authenticated
  useEffect(() => {
    if (!auth?.authenticated) return;
    api.get("/public/latest-db").then((res) => {
      const db = res.data.db as string | null;
      if (!db) { setDbError(true); return; }
      if (typeof window !== "undefined") localStorage.setItem("activeDb", db);
      setDbReady(true);
    }).catch(() => setDbError(true));
  }, [auth?.authenticated]);

  // Stammdaten state
  const [stammdatenClass, setStammdatenClass] = useState("");
  const [editRows, setEditRows] = useState<StudentBaseData[]>([]);
  const [stammdatenDirty, setStammdatenDirty] = useState(false);
  const [selectedStudentId, setSelectedStudentId] = useState<number | null>(null);

  const { data: stammdatenData, isLoading: stammdatenLoading } = useQuery<StudentBaseData[]>({
    queryKey: QK.stammdaten(stammdatenClass),
    queryFn: () => stammdatenApi.list(stammdatenClass).then((r) => r.data),
    enabled: dbReady && !!stammdatenClass && tab === "stammdaten",
  });

  useEffect(() => {
    if (stammdatenData) {
      setEditRows(stammdatenData.map((s) => ({ ...s })));
      setStammdatenDirty(false);
    }
  }, [stammdatenData]);

  const updateStammdatenField = (id: number, field: keyof StudentBaseData, value: unknown) => {
    setEditRows((prev) => prev.map((s) => (s.id === id ? { ...s, [field]: value } : s)));
    setStammdatenDirty(true);
  };

  const saveStammdatenMutation = useMutation({
    mutationFn: () => stammdatenApi.saveBatch(editRows),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QK.stammdaten(stammdatenClass) });
      setStammdatenDirty(false);
      toast.success("Stammdaten gespeichert");
    },
    onError: () => toast.error("Fehler beim Speichern"),
  });

  const { data: classesData } = useQuery({
    queryKey: QK.classes,
    queryFn: () => competenceApi.classes().then((r) => r.data),
    enabled: dbReady,
  });

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
          {(["kompetenzen", "schuelerdaten", "stammdaten"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`w-full flex items-center px-3 py-2 rounded-md text-sm transition-colors text-left ${
                tab === t
                  ? "bg-slate-700 text-white"
                  : "text-slate-300 hover:bg-slate-800 hover:text-white"
              }`}
            >
              {t === "kompetenzen" ? "Kompetenzen" : t === "schuelerdaten" ? "Schülerdaten" : "Stammdaten"}
            </button>
          ))}
        </nav>

        {tab !== "stammdaten" && (
          <div className="px-4 py-4 space-y-4 border-t border-slate-700">
            <ClassSubjectFilter
              classValue={selectedClass}
              subjectValue={selectedSubject}
              blockValue={selectedBlock}
              onClassChange={handleClassChange}
              onSubjectChange={handleSubjectChange}
              onBlockChange={setSelectedBlock}
              showBlock={tab === "kompetenzen"}
              selectClassName="text-gray-600"
            />
          </div>
        )}

        <div className="px-2 pb-4 border-t border-slate-700 pt-4">
          <button
            onClick={() => logoutMutation.mutate()}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <LogOut className="h-4 w-4" />
            Abmelden
          </button>
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

          {tab === "stammdaten" && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold">Stammdaten</h2>
                {stammdatenDirty && (
                  <button
                    onClick={() => saveStammdatenMutation.mutate()}
                    disabled={saveStammdatenMutation.isPending}
                    className="flex items-center gap-2 bg-primary text-white px-4 py-1.5 rounded-md text-sm hover:bg-primary/90 disabled:opacity-50"
                  >
                    <Save className="h-4 w-4" />
                    {saveStammdatenMutation.isPending ? "Speichern…" : "Änderungen speichern"}
                  </button>
                )}
              </div>

              <div className="flex gap-3 items-center">
                <label className="text-sm font-medium">Klasse:</label>
                <select
                  value={stammdatenClass}
                  onChange={(e) => {
                    setStammdatenClass(e.target.value);
                    setSelectedStudentId(null);
                  }}
                  className="border rounded-md px-2 py-1.5 text-sm text-gray-600"
                >
                  <option value="">– Klasse –</option>
                  {(classesData?.classes ?? []).map((c: string) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>

              {stammdatenClass && stammdatenLoading && (
                <p className="text-muted-foreground text-sm animate-pulse">Laden…</p>
              )}

              {editRows.length > 0 && (
                <div className="overflow-x-auto border rounded-xl">
                  <table className="text-sm w-full border-collapse">
                    <thead>
                      <tr className="bg-muted/50 text-xs">
                        <th className="text-left px-3 py-2 border-b font-medium">Nachname</th>
                        <th className="text-left px-3 py-2 border-b font-medium">Vorname</th>
                        <th className="px-2 py-2 border-b font-medium">Geb.</th>
                        <th className="px-2 py-2 border-b font-medium">T.e.</th>
                        <th className="px-2 py-2 border-b font-medium">T.u.</th>
                        <th className="px-2 py-2 border-b font-medium">S.e.</th>
                        <th className="px-2 py-2 border-b font-medium">S.u.</th>
                        <th className="px-2 py-2 border-b font-medium">LB</th>
                        <th className="px-2 py-2 border-b font-medium">GB</th>
                        <th className="text-left px-2 py-2 border-b font-medium">Bemerkungen</th>
                        <th className="px-2 py-2 border-b font-medium">Text</th>
                      </tr>
                    </thead>
                    <tbody>
                      {editRows.map((stu, ri) => (
                        <tr key={stu.id} className={ri % 2 === 0 ? "bg-white" : "bg-muted/20"}>
                          <td className="px-3 py-1 border-b font-medium">{stu.last_name}</td>
                          <td className="px-3 py-1 border-b">{stu.first_name}</td>
                          <td className="px-1 py-1 border-b">
                            <input
                              type="text"
                              value={stu.birthday ?? ""}
                              onChange={(e) => updateStammdatenField(stu.id, "birthday", e.target.value)}
                              className="w-24 border rounded px-1 py-0.5 text-xs"
                              placeholder="TT.MM.JJJJ"
                            />
                          </td>
                          {(["days_absent_excused", "days_absent_unexcused", "lessons_absent_excused", "lessons_absent_unexcused"] as const).map((f) => (
                            <td key={f} className="px-1 py-1 border-b">
                              <input
                                type="number"
                                min={0}
                                value={stu[f]}
                                onChange={(e) => updateStammdatenField(stu.id, f, parseInt(e.target.value) || 0)}
                                className="w-12 border rounded px-1 py-0.5 text-xs text-center"
                              />
                            </td>
                          ))}
                          <td className="px-2 py-1 border-b text-center">
                            <input
                              type="checkbox"
                              checked={stu.lb}
                              onChange={(e) => updateStammdatenField(stu.id, "lb", e.target.checked)}
                              className="h-4 w-4"
                            />
                          </td>
                          <td className="px-2 py-1 border-b text-center">
                            <input
                              type="checkbox"
                              checked={stu.gb}
                              onChange={(e) => updateStammdatenField(stu.id, "gb", e.target.checked)}
                              className="h-4 w-4"
                            />
                          </td>
                          <td className="px-1 py-1 border-b">
                            <input
                              type="text"
                              value={stu.remarks}
                              onChange={(e) => updateStammdatenField(stu.id, "remarks", e.target.value)}
                              className="w-32 border rounded px-1 py-0.5 text-xs"
                            />
                          </td>
                          <td className="px-2 py-1 border-b text-center">
                            <button
                              onClick={() => setSelectedStudentId(stu.id === selectedStudentId ? null : stu.id)}
                              className="text-xs text-blue-600 hover:underline"
                            >
                              {stu.id === selectedStudentId ? "▲" : "✏️"}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {selectedStudentId && (
                <ReportTextEditor
                  studentId={selectedStudentId}
                  studentName={
                    editRows.find((s) => s.id === selectedStudentId)
                      ? `${editRows.find((s) => s.id === selectedStudentId)!.last_name}, ${editRows.find((s) => s.id === selectedStudentId)!.first_name}`
                      : ""
                  }
                />
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
