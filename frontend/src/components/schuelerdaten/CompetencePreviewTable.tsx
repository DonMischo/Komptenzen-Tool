"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { competenceApi, studentsApi } from "@/lib/api";
import { GradeMatrixResponse } from "@/types/api";

interface TopicPreview {
  title: string;
  block: string;
  topic_id: number | null;
  competences: string[];
  custom_competences: string[];
}

interface PreviewData {
  subject: string;
  topics: TopicPreview[];
}

const GRADE_HEADERS = ["sehr gut\nerfüllt", "gut\nerfüllt", "teilweise\nerfüllt", "nicht\nerfüllt"];

const NIVEAU_COLOR: Record<string, string> = {
  "1": "#27ae60",
  "2": "#2563eb",
  "3": "#c0392b",
};

function CheckRow({ grade }: { grade: string }) {
  const n = parseInt(grade);
  if (grade === "ne") {
    return (
      <td colSpan={4} style={{ textAlign: "center", border: "1.5px solid #4290b3", padding: "4px", fontSize: "12px" }}>
        nicht erteilt
      </td>
    );
  }
  if (grade === "HJ2") {
    return (
      <td colSpan={4} style={{ textAlign: "center", border: "1.5px solid #4290b3", padding: "4px", fontSize: "12px" }}>
        wird im 2.&nbsp;Halbjahr belegt
      </td>
    );
  }
  return (
    <>
      {[1, 2, 3, 4].map((col) => (
        <td
          key={col}
          style={{
            textAlign: "center",
            verticalAlign: "middle",
            border: "1.5px solid #4290b3",
            fontSize: "18px",
            width: "60px",
            padding: "4px",
          }}
        >
          {n === col ? "⊠" : "□"}
        </td>
      ))}
    </>
  );
}

function NiveauFooter({ niveau }: { niveau: string }) {
  const n = parseInt(niveau);
  if ([7, 8, 9].includes(n)) {
    return (
      <tr>
        <td colSpan={5} style={{ textAlign: "center", padding: "5px 10px", borderTop: "1.5px solid #4290b3", background: "#f8f8f8", fontSize: "12px" }}>
          bis&nbsp;Klasse&nbsp;{n} ohne Anforderungsebene
        </td>
      </tr>
    );
  }
  if (NIVEAU_COLOR[niveau]) {
    return (
      <tr>
        <td colSpan={5} style={{ textAlign: "center", padding: "5px 10px", borderTop: "1.5px solid #4290b3", background: "#f8f8f8", fontSize: "12px" }}>
          Du hast vorwiegend auf{" "}
          <span style={{ color: NIVEAU_COLOR[niveau] }}>Anforderungsebene&nbsp;{niveau}</span> gearbeitet.
        </td>
      </tr>
    );
  }
  return null;
}

interface Props {
  classNameValue: string;
  subject: string;
}

export function CompetencePreviewTable({ classNameValue, subject }: Props) {
  const [selectedStudentId, setSelectedStudentId] = useState<string>("");

  const { data: preview, isLoading: previewLoading } = useQuery<PreviewData>({
    queryKey: ["preview-table", classNameValue, subject],
    queryFn: () => competenceApi.preview(classNameValue, subject).then((r) => r.data),
  });

  const { data: matrix } = useQuery<GradeMatrixResponse>({
    queryKey: ["grade-matrix", classNameValue, subject],
    queryFn: () => studentsApi.matrix(classNameValue, subject).then((r) => r.data),
  });

  if (previewLoading) return <p className="text-sm text-muted-foreground animate-pulse">Laden…</p>;
  if (!preview || preview.topics.length === 0)
    return <p className="text-sm text-muted-foreground">Keine Kompetenzen ausgewählt.</p>;

  const students = matrix?.rows ?? [];
  const selectedRow = students.find((r) => String(r.student_id) === selectedStudentId);
  const grades: Record<string, string> = selectedRow?.grades ?? {};
  const niveau = selectedRow?.niveau ?? "";

  // Free-text niveau: show simple format (like myZeugnisTableSimple)
  const isSimple =
    selectedRow &&
    niveau &&
    !parseInt(niveau) &&
    niveau !== "ne";

  return (
    <div className="space-y-2">
      {/* Student selector */}
      {students.length > 0 && (
        <div className="flex items-center gap-2">
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Schüler/in:
          </label>
          <select
            value={selectedStudentId}
            onChange={(e) => setSelectedStudentId(e.target.value)}
            className="border rounded px-2 py-1 text-sm bg-white"
          >
            <option value="">— allgemein —</option>
            {students.map((r) => (
              <option key={r.student_id} value={String(r.student_id)}>
                {r.last_name}, {r.first_name}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Simple format for free-text niveau */}
      {isSimple ? (
        <table style={{ borderCollapse: "collapse", width: "100%", fontFamily: "serif", fontSize: "13px", border: "1.5px solid #4290b3" }}>
          <thead>
            <tr>
              <th style={{ background: "#4290b3", color: "white", textAlign: "left", padding: "6px 10px", fontSize: "15px", fontWeight: "bold" }}>
                {subject}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style={{ padding: "8px 10px", fontFamily: "serif", fontSize: "13px", lineHeight: "1.6" }}>
                {niveau}
              </td>
            </tr>
          </tbody>
        </table>
      ) : (
        <table style={{ borderCollapse: "collapse", width: "100%", fontFamily: "serif", fontSize: "13px", border: "1.5px solid #4290b3" }}>
          <thead>
            <tr>
              <th style={{ background: "#4290b3", color: "white", textAlign: "left", padding: "6px 10px", fontSize: "15px", fontWeight: "bold", border: "1.5px solid #4290b3" }}>
                {subject}
              </th>
              {GRADE_HEADERS.map((h) => (
                <th key={h} style={{ background: "#4290b3", color: "white", textAlign: "center", padding: "4px 8px", fontSize: "11px", fontWeight: "bold", whiteSpace: "pre-line", width: "60px", border: "1.5px solid white", verticalAlign: "middle" }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {preview.topics.map((topic, ti) => {
              const allComps = [...topic.competences, ...topic.custom_competences];
              const grade = topic.topic_id ? (grades[String(topic.topic_id)] ?? "") : "";
              return (
                <tr key={topic.title} style={{ borderTop: ti === 0 ? "none" : "1.5px solid #4290b3" }}>
                  <td style={{ padding: "6px 10px", verticalAlign: "top", border: "1.5px solid #4290b3", lineHeight: "1.5" }}>
                    <span style={{ fontWeight: "bold" }}>{topic.title}</span>
                    {allComps.map((text, i) => (
                      <div key={i} style={{ marginTop: "2px" }}>
                        {topic.custom_competences.includes(text) && (
                          <span style={{ color: "#2563eb", fontSize: "10px", marginRight: "4px" }}>[Eigen]</span>
                        )}
                        {text}
                      </div>
                    ))}
                  </td>
                  <CheckRow grade={grade} />
                </tr>
              );
            })}
            {selectedRow && <NiveauFooter niveau={niveau} />}
          </tbody>
        </table>
      )}
    </div>
  );
}
