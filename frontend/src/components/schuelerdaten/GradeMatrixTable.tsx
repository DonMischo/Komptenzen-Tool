"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { studentsApi } from "@/lib/api";
import { QK } from "@/lib/queries";
import { GradeMatrixResponse, GradeMatrixRow } from "@/types/api";
import { Save } from "lucide-react";

interface Props {
  classNameValue: string;
  subject: string;
}

export function GradeMatrixTable({ classNameValue, subject }: Props) {
  const qc = useQueryClient();

  const { data, isLoading } = useQuery<GradeMatrixResponse>({
    queryKey: QK.matrix(classNameValue, subject),
    queryFn: () =>
      studentsApi.matrix(classNameValue, subject).then((r) => r.data),
  });

  const [rows, setRows] = useState<GradeMatrixRow[]>([]);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (data) {
      setRows(data.rows.map((r) => ({ ...r, grades: { ...r.grades } })));
      setDirty(false);
    }
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: () => studentsApi.saveMatrix(classNameValue, subject, rows),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QK.matrix(classNameValue, subject) });
      setDirty(false);
      toast.success("Änderungen gespeichert");
    },
    onError: () => toast.error("Fehler beim Speichern"),
  });

  const updateNiveau = (studentId: number, value: string) => {
    setRows((prev) =>
      prev.map((r) => (r.student_id === studentId ? { ...r, niveau: value } : r))
    );
    setDirty(true);
  };

  const updateGrade = (studentId: number, topicId: string, value: string) => {
    setRows((prev) =>
      prev.map((r) =>
        r.student_id === studentId
          ? { ...r, grades: { ...r.grades, [topicId]: value } }
          : r
      )
    );
    setDirty(true);
  };

  if (isLoading) {
    return <p className="text-muted-foreground text-sm animate-pulse">Laden…</p>;
  }

  if (!data || data.columns.length === 0) {
    return (
      <p className="text-muted-foreground text-sm">
        Keine Themen mit ausgewählten Kompetenzen gefunden. Zuerst Kompetenzen auswählen.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {rows.length} Schüler · {data.columns.length} Themen
        </p>
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

      <div className="overflow-x-auto border rounded-xl">
        <table className="text-sm w-full border-collapse">
          <thead>
            <tr className="bg-muted/50">
              <th className="text-left px-3 py-2 font-medium border-b whitespace-nowrap sticky left-0 bg-muted/50">
                Nachname
              </th>
              <th className="text-left px-3 py-2 font-medium border-b whitespace-nowrap">
                Vorname
              </th>
              <th className="text-left px-3 py-2 font-medium border-b whitespace-nowrap">
                Niveau
              </th>
              {data.columns.map((col) => (
                <th
                  key={col.topic_id}
                  className="text-left px-2 py-2 font-medium border-b whitespace-nowrap max-w-[140px]"
                  title={col.label}
                >
                  <span className="block truncate max-w-[120px] text-xs">{col.label}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, ri) => (
              <tr
                key={row.student_id}
                className={ri % 2 === 0 ? "bg-white" : "bg-muted/20"}
              >
                <td className="px-3 py-1 border-b font-medium whitespace-nowrap sticky left-0 bg-inherit">
                  {row.last_name}
                </td>
                <td className="px-3 py-1 border-b whitespace-nowrap">
                  {row.first_name}
                </td>
                <td className="px-2 py-1 border-b">
                  <input
                    type="text"
                    value={row.niveau}
                    onChange={(e) => updateNiveau(row.student_id, e.target.value)}
                    className="w-20 border rounded px-1.5 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </td>
                {data.columns.map((col) => (
                  <td key={col.topic_id} className="px-2 py-1 border-b">
                    <input
                      type="text"
                      value={row.grades[String(col.topic_id)] ?? ""}
                      onChange={(e) =>
                        updateGrade(row.student_id, String(col.topic_id), e.target.value)
                      }
                      className="w-14 border rounded px-1.5 py-0.5 text-xs text-center focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
