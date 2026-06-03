"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { studentsApi } from "@/lib/api";
import { QK } from "@/lib/queries";
import { GradeMatrixResponse, GradeMatrixRow } from "@/types/api";
import { NiveauSelect } from "./NiveauSelect";
import { RichTextEditorModal } from "@/components/stammdaten/RichTextEditorModal";
import { Save, Pencil } from "lucide-react";

// Button that opens a TipTap modal for editing rich text
function RichTextCell({
  value,
  label,
  onChange,
}: {
  value: string;
  label: string;
  onChange: (html: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const isEmpty = !value || value === "<p></p>";
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex items-center gap-1.5 text-xs border rounded px-2 py-1 hover:bg-muted transition-colors max-w-[220px] w-full text-left"
      >
        <Pencil className="h-3 w-3 shrink-0 text-muted-foreground" />
        <span className={`truncate ${isEmpty ? "text-muted-foreground italic" : ""}`}>
          {isEmpty ? "Text eingeben…" : value.replace(/<[^>]+>/g, " ").trim().slice(0, 40)}
        </span>
      </button>
      <RichTextEditorModal
        title={label}
        initialHtml={value}
        open={open}
        onSave={(html) => { onChange(html); setOpen(false); }}
        onClose={() => setOpen(false)}
      />
    </>
  );
}

const GRADE_OPTS = ["", "1", "2", "3", "4", /* "nb", */ "ne"];

interface Props {
  classNameValue: string;
  subject: string;
}

export function GradeMatrixTable({ classNameValue, subject }: Props) {
  const qc = useQueryClient();
  const isLebenspraxis = subject === "Lebenspraxis";

  const { data, isLoading } = useQuery<GradeMatrixResponse>({
    queryKey: QK.matrix(classNameValue, subject),
    queryFn: () =>
      studentsApi.matrix(classNameValue, subject).then((r) => r.data),
  });

  const [rows, setRows] = useState<GradeMatrixRow[]>([]);
  const [dirty, setDirty] = useState(false);

  const NO_NIVEAU_SUBJECTS = new Set([
    "Sport",
    "Werkstätten",
    "Wahlpflichtbereich - Darstellen und Gestalten",
  ]);
  const defaultNiveau = NO_NIVEAU_SUBJECTS.has(subject) ? "" : "2";

  useEffect(() => {
    if (data) {
      setRows(data.rows.map((r) => ({
        ...r,
        grades: { ...r.grades },
        niveau: r.niveau || (r.student_type === "normal" ? defaultNiveau : ""),
      })));
      setDirty(false);
    }
  }, [data]); // eslint-disable-line react-hooks/exhaustive-deps

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

  // Lebenspraxis: no topics, LB/GB students only — show Niveau free text only
  if (isLebenspraxis) {
    if (!data || data.rows.length === 0) {
      return (
        <p className="text-muted-foreground text-sm">
          Keine Schüler mit Förderbedarf (LB/GB) in dieser Klasse.
        </p>
      );
    }
    return (
      <div className="space-y-3">
        <p className="text-sm text-muted-foreground">
          Lebenspraxis – nur Schüler mit Förderbedarf. Text wird im Niveau-Feld gespeichert.
        </p>
        <div className="flex items-center gap-4">
          <button
            onClick={() => saveMutation.mutate()}
            disabled={!dirty || saveMutation.isPending}
            className="flex items-center gap-2 bg-primary text-white px-4 py-1.5 rounded-md text-sm hover:bg-primary/90 disabled:opacity-40"
          >
            <Save className="h-4 w-4" />
            {saveMutation.isPending ? "Speichern…" : "Speichern"}
          </button>
        </div>
        {/* Legend */}
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          {rows.some((r) => r.student_type === "lb") && (
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-3 h-3 rounded-sm bg-green-800/40 border border-green-800/30" />
              LB
            </span>
          )}
          {rows.some((r) => r.student_type === "gb") && (
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-3 h-3 rounded-sm bg-orange-700/40 border border-orange-700/30" />
              GB
            </span>
          )}
        </div>
        <div className="border rounded-xl overflow-hidden">
          <table className="text-sm w-full border-collapse">
            <thead>
              <tr className="bg-muted/50">
                <th className="text-left px-3 py-2 font-medium border-b">Nachname</th>
                <th className="text-left px-3 py-2 font-medium border-b">Vorname</th>
                <th className="text-left px-3 py-2 font-medium border-b">Text</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, ri) => {
                const bg = row.student_type === "lb"
                  ? ri % 2 === 0 ? "bg-green-800/10" : "bg-green-800/20"
                  : ri % 2 === 0 ? "bg-orange-700/10" : "bg-orange-700/20";
                return (
                  <tr key={row.student_id} className={bg}>
                    <td className="px-3 py-1 border-b font-medium">{row.last_name}</td>
                    <td className="px-3 py-1 border-b">{row.first_name}</td>
                    <td className="px-2 py-1 border-b">
                      <RichTextCell
                        value={row.niveau}
                        label={`Lebenspraxis – ${row.last_name}, ${row.first_name}`}
                        onChange={(html) => updateNiveau(row.student_id, html)}
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  if (!data || data.columns.length === 0) {
    return (
      <p className="text-muted-foreground text-sm">
        Keine Themen mit ausgewählten Kompetenzen gefunden. Zuerst Kompetenzen auswählen.
      </p>
    );
  }

  // Group rows by type for sectioned display
  const normalRows = rows.filter((r) => r.student_type === "normal");
  const lbRows     = rows.filter((r) => r.student_type === "lb");
  const gbRows     = rows.filter((r) => r.student_type === "gb");

  const renderGradeCell = (row: GradeMatrixRow, topicId: number) => {
    const tid = String(topicId);
    const val = row.grades[tid] ?? "";

    if (row.student_type === "normal") {
      return (
        <select
          value={val}
          onChange={(e) => updateGrade(row.student_id, tid, e.target.value)}
          className="w-16 border rounded px-1 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
        >
          {GRADE_OPTS.map((o) => (
            <option key={o} value={o}>{o || "—"}</option>
          ))}
        </select>
      );
    }
    // LB and GB: free text
    return (
      <input
        type="text"
        value={val}
        onChange={(e) => updateGrade(row.student_id, tid, e.target.value)}
        className="w-24 border rounded px-1.5 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
      />
    );
  };

  const renderNiveauCell = (row: GradeMatrixRow) => {
    if (row.student_type === "gb") {
      return (
        <RichTextCell
          value={row.niveau}
          label={`Niveau – ${row.last_name}, ${row.first_name}`}
          onChange={(html) => updateNiveau(row.student_id, html)}
        />
      );
    }
    return (
      <NiveauSelect
        value={row.niveau}
        studentName={`${row.last_name}, ${row.first_name}`}
        onChange={(v) => updateNiveau(row.student_id, v)}
      />
    );
  };

  const rowBg = (row: GradeMatrixRow, ri: number) => {
    if (row.student_type === "lb") return ri % 2 === 0 ? "bg-green-800/10" : "bg-green-800/20";
    if (row.student_type === "gb") return ri % 2 === 0 ? "bg-orange-700/10" : "bg-orange-700/20";
    return ri % 2 === 0 ? "bg-white" : "bg-muted/20";
  };

  const renderSection = (sectionRows: GradeMatrixRow[], label?: string, startIndex = 0) => (
    <>
      {label && (
        <tr>
          <td
            colSpan={3 + data.columns.length}
            className="px-3 py-1 text-xs font-semibold text-muted-foreground bg-muted/30 border-b"
          >
            {label}
          </td>
        </tr>
      )}
      {sectionRows.map((row, ri) => (
        <tr key={row.student_id} className={rowBg(row, startIndex + ri)}>
          <td className="px-3 py-1 border-b font-medium whitespace-nowrap sticky left-0 bg-inherit">
            {row.last_name}
          </td>
          <td className="px-3 py-1 border-b whitespace-nowrap">{row.first_name}</td>
          <td className="px-2 py-1 border-b">{renderNiveauCell(row)}</td>
          {data.columns.map((col) => (
            <td key={col.topic_id} className="px-2 py-1 border-b">
              {renderGradeCell(row, col.topic_id)}
            </td>
          ))}
        </tr>
      ))}
    </>
  );

  const hasMultipleGroups = lbRows.length > 0 || gbRows.length > 0;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-4 flex-wrap">
        <button
          onClick={() => saveMutation.mutate()}
          disabled={!dirty || saveMutation.isPending}
          className="flex items-center gap-2 bg-primary text-white px-4 py-1.5 rounded-md text-sm hover:bg-primary/90 disabled:opacity-40"
        >
          <Save className="h-4 w-4" />
          {saveMutation.isPending ? "Speichern…" : "Speichern"}
        </button>
        <p className="text-sm text-muted-foreground">
          {rows.length} Schüler · {data.columns.length} Themen
        </p>
        {hasMultipleGroups && (
          <div className="flex items-center gap-3 ml-2">
            {lbRows.length > 0 && (
              <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <span className="inline-block w-3 h-3 rounded-sm bg-green-800/40 border border-green-800/30" />
                LB
              </span>
            )}
            {gbRows.length > 0 && (
              <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <span className="inline-block w-3 h-3 rounded-sm bg-orange-700/40 border border-orange-700/30" />
                GB
              </span>
            )}
          </div>
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
            {renderSection(normalRows, undefined, 0)}
            {renderSection(lbRows, undefined, normalRows.length)}
            {renderSection(gbRows, undefined, normalRows.length + lbRows.length)}
          </tbody>
        </table>
      </div>
    </div>
  );
}
