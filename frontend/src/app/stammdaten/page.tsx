"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AppShell } from "@/components/layout/AppShell";
import { stammdatenApi, competenceApi } from "@/lib/api";
import { QK } from "@/lib/queries";
import { StudentBaseData } from "@/types/api";
import { ReportTextEditor } from "@/components/stammdaten/ReportTextEditor";
import { Save } from "lucide-react";

export default function StammdatenPage() {
  const qc = useQueryClient();
  const [selectedClass, setSelectedClass] = useState("");
  const [editRows, setEditRows] = useState<StudentBaseData[]>([]);
  const [dirty, setDirty] = useState(false);
  const [selectedStudentId, setSelectedStudentId] = useState<number | null>(null);

  const { data: classesData } = useQuery({
    queryKey: QK.classes,
    queryFn: () => competenceApi.classes().then((r) => r.data),
  });

  const { data, isLoading } = useQuery<StudentBaseData[]>({
    queryKey: QK.stammdaten(selectedClass),
    queryFn: () => stammdatenApi.list(selectedClass).then((r) => r.data),
    enabled: !!selectedClass,
  });

  useEffect(() => {
    if (data) {
      setEditRows(data.map((s) => ({ ...s })));
      setDirty(false);
    }
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: () => stammdatenApi.saveBatch(editRows),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QK.stammdaten(selectedClass) });
      setDirty(false);
      toast.success("Stammdaten gespeichert");
    },
    onError: () => toast.error("Fehler beim Speichern"),
  });

  const updateField = (id: number, field: keyof StudentBaseData, value: unknown) => {
    setEditRows((prev) =>
      prev.map((s) => (s.id === id ? { ...s, [field]: value } : s))
    );
    setDirty(true);
  };

  const classes: string[] = classesData?.classes ?? [];

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">Stammdaten</h2>
          {dirty && (
            <button
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending}
              className="flex items-center gap-2 bg-primary text-white px-4 py-1.5 rounded-md text-sm hover:bg-primary/90 disabled:opacity-50"
            >
              <Save className="h-4 w-4" />
              {saveMutation.isPending ? "Speichern…" : "Änderungen speichern"}
            </button>
          )}
        </div>

        {/* Class selector */}
        <div className="flex gap-3 items-center">
          <label className="text-sm font-medium">Klasse:</label>
          <select
            value={selectedClass}
            onChange={(e) => {
              setSelectedClass(e.target.value);
              setSelectedStudentId(null);
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
                        onChange={(e) => updateField(stu.id, "birthday", e.target.value)}
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
                          onChange={(e) => updateField(stu.id, f, parseInt(e.target.value) || 0)}
                          className="w-12 border rounded px-1 py-0.5 text-xs text-center"
                        />
                      </td>
                    ))}
                    <td className="px-2 py-1 border-b text-center">
                      <input
                        type="checkbox"
                        checked={stu.lb}
                        onChange={(e) => updateField(stu.id, "lb", e.target.checked)}
                        className="h-4 w-4"
                      />
                    </td>
                    <td className="px-2 py-1 border-b text-center">
                      <input
                        type="checkbox"
                        checked={stu.gb}
                        onChange={(e) => updateField(stu.id, "gb", e.target.checked)}
                        className="h-4 w-4"
                      />
                    </td>
                    <td className="px-1 py-1 border-b">
                      <input
                        type="text"
                        value={stu.remarks}
                        onChange={(e) => updateField(stu.id, "remarks", e.target.value)}
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

        {/* Report text editor */}
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
    </AppShell>
  );
}
