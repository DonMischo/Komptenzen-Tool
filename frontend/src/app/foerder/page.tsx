"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { AppShell } from "@/components/layout/AppShell";
import { competenceApi, stammdatenApi, studentsApi } from "@/lib/api";
import { NiveauSelect, isNiveauCustom, NIVEAU_OPTIONS } from "@/components/schuelerdaten/NiveauSelect";
import { RichTextEditorModal } from "@/components/stammdaten/RichTextEditorModal";
import { Save, Pencil } from "lucide-react";

const GRADE_OPTS = ["", "1", "2", "3", "4", "ne"];

interface LbTopic {
  topic_id: number;
  label: string;
  grade: string;
}

interface LbSubject {
  name: string;
  niveau: string;
  topics: LbTopic[];
}

interface LbProfile {
  student_id: number;
  first_name: string;
  last_name: string;
  class_name: string;
  student_type: "lb" | "gb";
  subjects: LbSubject[];
}

// Local mutable state for one subject
interface SubjectState {
  niveau: string;
  grades: Record<string, string>; // topic_id → grade
}

function RichTextCell({ value, label, onChange }: { value: string; label: string; onChange: (html: string) => void }) {
  const [open, setOpen] = useState(false);
  const isEmpty = !value || value === "<p></p>";
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex items-center gap-1.5 text-xs border rounded px-2 py-1 hover:bg-muted transition-colors w-full max-w-[300px] text-left"
      >
        <Pencil className="h-3 w-3 shrink-0 text-muted-foreground" />
        <span className={`truncate ${isEmpty ? "text-muted-foreground italic" : ""}`}>
          {isEmpty ? "Text eingeben…" : value.replace(/<[^>]+>/g, " ").trim().slice(0, 60)}
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

function SubjectBlock({
  subj,
  studentType,
  state,
  onChange,
}: {
  subj: LbSubject;
  studentType: "lb" | "gb";
  state: SubjectState;
  onChange: (next: SubjectState) => void;
}) {
  const isGb = studentType === "gb";
  const isTextMode = isGb || isNiveauCustom(state.niveau);

  return (
    <div className="border rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <h3 className="font-semibold text-sm">{subj.name}</h3>
        {isGb ? (
          <RichTextCell
            value={state.niveau}
            label={`Niveau – ${subj.name}`}
            onChange={(html) => onChange({ ...state, niveau: html })}
          />
        ) : (
          <NiveauSelect
            value={state.niveau}
            studentName={subj.name}
            onChange={(v) => onChange({ ...state, niveau: v })}
          />
        )}
      </div>

      {!isTextMode && subj.topics.length > 0 && (
        <table className="text-sm w-full border-collapse">
          <thead>
            <tr className="bg-muted/40">
              <th className="text-left px-2 py-1 text-xs font-medium border-b">Thema</th>
              <th className="text-left px-2 py-1 text-xs font-medium border-b w-24">Note</th>
            </tr>
          </thead>
          <tbody>
            {subj.topics.map((t, ri) => (
              <tr key={t.topic_id} className={ri % 2 === 0 ? "bg-white" : "bg-muted/20"}>
                <td className="px-2 py-1 border-b text-xs">{t.label}</td>
                <td className="px-2 py-1 border-b">
                  <select
                    value={state.grades[String(t.topic_id)] ?? ""}
                    onChange={(e) =>
                      onChange({
                        ...state,
                        grades: { ...state.grades, [String(t.topic_id)]: e.target.value },
                      })
                    }
                    className="w-20 border rounded px-1 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    {GRADE_OPTS.map((o) => (
                      <option key={o} value={o}>{o || "—"}</option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {isTextMode && subj.name !== "Lebenspraxis" && (
        <p className="text-xs text-muted-foreground italic">
          Freitext-Modus — Themenurteile werden nicht erfasst.
        </p>
      )}
    </div>
  );
}

function SaveButton({ onClick, isPending }: { onClick: () => void; isPending: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={isPending}
      className="flex items-center gap-2 bg-primary text-white px-4 py-2 rounded-md text-sm hover:bg-primary/90 disabled:opacity-40"
    >
      <Save className="h-4 w-4" />
      {isPending ? "Speichern…" : "Speichern"}
    </button>
  );
}

export default function FoerderPage() {
  const [selectedClass, setSelectedClass] = useState("");
  const [selectedStudentId, setSelectedStudentId] = useState<number | null>(null);
  const [subjectStates, setSubjectStates] = useState<Record<string, SubjectState>>({});
  const [dirty, setDirty] = useState(false);

  const { data: classesData } = useQuery<{ classes: string[] }>({
    queryKey: ["classes"],
    queryFn: () => competenceApi.classes().then((r) => r.data),
  });

  const { data: studentsData } = useQuery({
    queryKey: ["stammdaten", selectedClass],
    queryFn: () => stammdatenApi.list(selectedClass).then((r) => r.data),
    enabled: !!selectedClass,
  });

  const lbGbStudents = (studentsData as { id: number; last_name: string; first_name: string; lb: boolean; gb: boolean }[] | undefined)
    ?.filter((s) => s.lb || s.gb) ?? [];

  const { data: profile, isLoading: profileLoading } = useQuery<LbProfile>({
    queryKey: ["lb-profile", selectedStudentId],
    queryFn: () => studentsApi.lbProfile(selectedStudentId!).then((r) => r.data),
    enabled: selectedStudentId !== null,
  });

  // Initialise local state when profile loads
  useEffect(() => {
    if (!profile) return;
    const states: Record<string, SubjectState> = {};
    for (const s of profile.subjects) {
      states[s.name] = {
        niveau: s.niveau,
        grades: Object.fromEntries(s.topics.map((t) => [String(t.topic_id), t.grade])),
      };
    }
    setSubjectStates(states);
    setDirty(false);
  }, [profile]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (!profile) return;
      const stu = profile;
      // Save each subject via the existing matrix endpoint
      for (const subj of profile.subjects) {
        const state = subjectStates[subj.name];
        if (!state) continue;
        const row = {
          student_id: stu.student_id,
          last_name: stu.last_name,
          first_name: stu.first_name,
          niveau: state.niveau,
          grades: state.grades,
          student_type: stu.student_type,
        };
        await studentsApi.saveMatrix(stu.class_name, subj.name, [row]);
      }
    },
    onSuccess: () => {
      setDirty(false);
      toast.success("Gespeichert");
    },
    onError: () => toast.error("Fehler beim Speichern"),
  });

  const handleSubjectChange = (name: string, next: SubjectState) => {
    setSubjectStates((prev) => ({ ...prev, [name]: next }));
    setDirty(true);
  };

  return (
    <AppShell>
      <div className="space-y-4 max-w-3xl">
        <h2 className="text-2xl font-bold">LB/GB – Förderung</h2>

        {/* Filters */}
        <div className="flex gap-3 flex-wrap">
          <select
            value={selectedClass}
            onChange={(e) => { setSelectedClass(e.target.value); setSelectedStudentId(null); }}
            className="border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="">Klasse wählen…</option>
            {classesData?.classes.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>

          {selectedClass && (
            <select
              value={selectedStudentId ?? ""}
              onChange={(e) => setSelectedStudentId(e.target.value ? Number(e.target.value) : null)}
              className="border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="">Schüler/in wählen…</option>
              {lbGbStudents.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.last_name}, {s.first_name} ({s.gb ? "GB" : "LB"})
                </option>
              ))}
            </select>
          )}
        </div>

        {selectedClass && lbGbStudents.length === 0 && !profileLoading && (
          <p className="text-sm text-muted-foreground">Keine LB/GB-Schüler in dieser Klasse.</p>
        )}

        {profileLoading && (
          <p className="text-sm text-muted-foreground animate-pulse">Laden…</p>
        )}

        {profile && (
          <>
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-lg">
                  {profile.last_name}, {profile.first_name}
                </h3>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                  profile.student_type === "gb"
                    ? "bg-orange-700/20 text-orange-700"
                    : "bg-green-800/20 text-green-800"
                }`}>
                  {profile.student_type === "gb" ? "GB" : "LB"}
                </span>
              </div>
              <SaveButton onClick={() => saveMutation.mutate()} isPending={saveMutation.isPending} />
            </div>

            <div className="space-y-3">
              {profile.subjects.map((subj) => (
                <SubjectBlock
                  key={subj.name}
                  subj={subj}
                  studentType={profile.student_type}
                  state={subjectStates[subj.name] ?? { niveau: subj.niveau, grades: {} }}
                  onChange={(next) => handleSubjectChange(subj.name, next)}
                />
              ))}
            </div>

            <SaveButton onClick={() => saveMutation.mutate()} isPending={saveMutation.isPending} />
          </>
        )}
      </div>
    </AppShell>
  );
}
