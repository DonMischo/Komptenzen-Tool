"use client";

import { useQuery } from "@tanstack/react-query";
import { overviewApi } from "@/lib/api";
import { QK } from "@/lib/queries";
import { GradeStatusResponse, StudentGradeStatus, SubjectGradeStatus } from "@/types/api";

interface Props {
  classNameValue: string;
}

// Short subject labels for table headers
function shortLabel(name: string): string {
  const MAP: Record<string, string> = {
    "Deutsch": "DE",
    "Mathematik": "MA",
    "Englisch": "EN",
    "Evangelische Religionslehre": "RE",
    "MNT - Projekt Lutherpark": "MNT",
    "Geschichte": "GE",
    "Geografie": "GEO",
    "Werkstätten": "WER",
    "Technisches Werken": "TW",
    "Sport": "SP",
    "Physik": "PH",
    "Chemie": "CH",
    "Biologie": "BI",
  };
  return MAP[name] ?? name.slice(0, 6);
}

// Short codes for Wahlpflicht subjects shown inside the single WP cell
const WP_SHORT: Record<string, string> = {
  "Wahlpflichtbereich - Französisch": "FR",
  "Wahlpflichtbereich - Spanisch": "SP",
  "Wahlpflichtbereich - Darstellen und Gestalten": "DG",
  "Wahlpflichtbereich - Natur und Technik": "NT",
};

function isDone(s: SubjectGradeStatus | undefined, noNiveau: boolean): boolean {
  if (!s) return false;
  return noNiveau ? s.has_grade : (s.has_niveau && s.has_grade);
}

function isPartial(s: SubjectGradeStatus | undefined, noNiveau: boolean): boolean {
  if (!s || isDone(s, noNiveau)) return false;
  return s.has_grade || s.has_niveau;
}

// Regular subject cell
function SubjectCell({
  status,
  lb,
  gb,
  noNiveau,
}: {
  status: SubjectGradeStatus | undefined;
  lb: boolean;
  gb: boolean;
  noNiveau: boolean;
}) {
  if (lb || gb) {
    return (
      <td className="px-2 py-1 border-b text-center">
        <span className="text-xs text-slate-400">{lb ? "LB" : "GB"}</span>
      </td>
    );
  }
  if (isDone(status, noNiveau)) return <td className="px-2 py-1 border-b text-center text-green-600">✓</td>;
  if (isPartial(status, noNiveau)) return <td className="px-2 py-1 border-b text-center text-yellow-500">⚠</td>;
  return <td className="px-2 py-1 border-b text-center text-red-400">✗</td>;
}

// Single WP cell: find the active WP subject and show its short code
function WPCell({
  stu,
  wpSubjects,
  wpNoNiveauSet,
}: {
  stu: StudentGradeStatus;
  wpSubjects: string[];
  wpNoNiveauSet: Set<string>;
}) {
  if (stu.lb || stu.gb) {
    return (
      <td className="px-2 py-1 border-b text-center">
        <span className="text-xs text-slate-400">{stu.lb ? "LB" : "GB"}</span>
      </td>
    );
  }

  // Find the WP subject with any data
  for (const name of wpSubjects) {
    const s = stu.wahlpflicht[name];
    if (!s || (!s.has_grade && !s.has_niveau)) continue;
    const noNiveau = wpNoNiveauSet.has(name);
    const done = isDone(s, noNiveau);
    const short = WP_SHORT[name] ?? name.slice(0, 2);
    return (
      <td className="px-2 py-1 border-b text-center">
        <span className={`text-xs font-semibold ${done ? "text-green-600" : "text-red-500"}`}>
          {short}
        </span>
      </td>
    );
  }

  return <td className="px-2 py-1 border-b text-center text-red-400 text-xs">✗</td>;
}

export function NotenTab({ classNameValue }: Props) {
  const { data, isLoading } = useQuery<GradeStatusResponse>({
    queryKey: QK.overviewGrades(classNameValue),
    queryFn: () => overviewApi.grades(classNameValue).then((r) => r.data),
    enabled: !!classNameValue,
  });

  if (isLoading) return <p className="text-sm text-muted-foreground animate-pulse">Laden…</p>;
  if (!data || data.students.length === 0) {
    return <p className="text-sm text-muted-foreground">Keine Schüler gefunden.</p>;
  }

  const { students, relevant_subjects, wahlpflicht_subjects, wp_no_niveau, no_niveau_subjects } = data;
  const wpNoNiveauSet = new Set(wp_no_niveau);
  const noNiveauRegularSet = new Set(no_niveau_subjects);
  const hasWP = wahlpflicht_subjects.length > 0;

  function countDone(stu: StudentGradeStatus) {
    if (stu.lb || stu.gb) return null;
    let total = 0, done = 0;
    for (const name of relevant_subjects) {
      total++;
      if (isDone(stu.subjects[name], noNiveauRegularSet.has(name))) done++;
    }
    if (hasWP) {
      total++;
      const wpDone = wahlpflicht_subjects.some((name) =>
        isDone(stu.wahlpflicht[name], wpNoNiveauSet.has(name))
      );
      if (wpDone) done++;
    }
    return { done, total };
  }

  return (
    <div className="overflow-x-auto border rounded-xl">
      <table className="text-sm w-full border-collapse">
        <thead>
          <tr className="bg-muted/50">
            <th className="text-left px-3 py-2 font-medium border-b whitespace-nowrap sticky left-0 bg-muted/50">
              Nachname
            </th>
            <th className="text-left px-3 py-2 font-medium border-b whitespace-nowrap">Vorname</th>
            {relevant_subjects.map((name) => (
              <th
                key={name}
                title={name}
                className="px-2 py-2 font-medium border-b text-center text-xs whitespace-nowrap"
              >
                {shortLabel(name)}
              </th>
            ))}
            {hasWP && (
              <th className="px-2 py-2 font-medium border-b text-center text-xs whitespace-nowrap text-slate-500">
                WP
              </th>
            )}
            <th className="px-3 py-2 font-medium border-b text-center text-xs whitespace-nowrap">
              Gesamt
            </th>
          </tr>
        </thead>
        <tbody>
          {students.map((stu, ri) => {
            const summary = countDone(stu);
            const allDone = summary ? summary.done === summary.total : null;
            return (
              <tr key={stu.student_id} className={ri % 2 === 0 ? "bg-white" : "bg-muted/20"}>
                <td className="px-3 py-1 border-b font-medium whitespace-nowrap sticky left-0 bg-inherit">
                  {stu.last_name}
                  {(stu.lb || stu.gb) && (
                    <span className="ml-1 text-xs text-slate-400">[{stu.lb ? "LB" : "GB"}]</span>
                  )}
                </td>
                <td className="px-3 py-1 border-b whitespace-nowrap">{stu.first_name}</td>
                {relevant_subjects.map((name) => (
                  <SubjectCell
                    key={name}
                    status={stu.subjects[name]}
                    lb={stu.lb}
                    gb={stu.gb}
                    noNiveau={noNiveauRegularSet.has(name)}
                  />
                ))}
                {hasWP && (
                  <WPCell
                    stu={stu}
                    wpSubjects={wahlpflicht_subjects}
                    wpNoNiveauSet={wpNoNiveauSet}
                  />
                )}
                <td className="px-3 py-1 border-b text-center text-xs whitespace-nowrap">
                  {summary === null ? (
                    <span className="text-slate-400">–</span>
                  ) : (
                    <span className={allDone ? "text-green-600 font-medium" : "text-red-500 font-medium"}>
                      {summary.done}/{summary.total}
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
