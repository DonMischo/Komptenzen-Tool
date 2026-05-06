"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { AppShell } from "@/components/layout/AppShell";
import { adminApi, competenceApi } from "@/lib/api";
import { QK } from "@/lib/queries";
import { AdminStudentItem } from "@/types/api";
import { ExportProgress } from "@/components/admin/ExportProgress";
import { useExportSSE } from "@/hooks/useExportSSE";
import { FileText } from "lucide-react";

export default function AdminPage() {
  const [selectedClass, setSelectedClass] = useState("");
  const [checkedIds, setCheckedIds] = useState<Set<number>>(new Set());
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobTotal, setJobTotal] = useState(0);

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
        <h2 className="text-2xl font-bold">Admin / Export</h2>

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

        {studentList.length > 0 && !jobId && (
          <>
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
          </>
        )}

        {/* Export progress */}
        {jobId && (
          <ExportProgress
            events={events}
            total={jobTotal}
            isDone={isDone}
            onStop={stop}
            onClose={closeExport}
          />
        )}
      </div>
    </AppShell>
  );
}
