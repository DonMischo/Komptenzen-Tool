"use client";

import { useQuery } from "@tanstack/react-query";
import { overviewApi } from "@/lib/api";
import { QK } from "@/lib/queries";
import { GradeStatusResponse, StudentGradeStatus, SubjectGradeStatus } from "@/types/api";

interface Props {
  classNameValue: string;
}

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

const WP_SHORT: Record<string, string> = {
  "Wahlpflichtbereich - Französisch": "FR",
  "Wahlpflichtbereich - Spanisch": "SP",
  "Wahlpflichtbereich - Darstellen und Gestalten": "DG",
  "Wahlpflichtbereich - Natur und Technik": "NT",
};

// Fraction label + colour
function GradeFraction({ s }: { s: SubjectGradeStatus }) {
  if (s.total_grades === 0) return <span className="text-slate-300 text-xs">–</span>;
  const allDone = s.grades_given === s.total_grades;
  const color = allDone ? "text-green-600" : s.grades_given === 0 ? "text-red-400" : "text-slate-600";
  return <span className={`text-xs font-medium ${color}`}>{s.grades_given}/{s.total_grades}</span>;
}

// Orange ! if niveau missing and subject requires one
function NiveauWarn({ has_niveau, noNiveau }: { has_niveau: boolean; noNiveau: boolean }) {
  if (noNiveau || has_niveau) return null;
  return <span className="ml-0.5 text-orange-500 text-xs font-bold">!</span>;
}

function TextDone({ set }: { set: boolean }) {
  return set
    ? <span className="text-green-600 text-sm">✓</span>
    : <span className="text-red-400 text-sm">✗</span>;
}

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
  // GB: always text-only — show ✓/✗ based on niveau text being set
  if (gb) {
    return (
      <td className="px-2 py-1 border-b text-center">
        <TextDone set={!!status?.has_niveau} />
      </td>
    );
  }
  // LB text-mode subject: show ✓/✗ based on niveau text
  if (lb && status?.is_text_mode) {
    return (
      <td className="px-2 py-1 border-b text-center">
        <TextDone set={!!status.has_niveau} />
      </td>
    );
  }
  // LB grade-mode subject: show fraction like normal students
  if (!status) return <td className="px-2 py-1 border-b text-center text-slate-300 text-xs">–</td>;
  return (
    <td className="px-2 py-1 border-b text-center whitespace-nowrap">
      <GradeFraction s={status} />
      <NiveauWarn has_niveau={status.has_niveau} noNiveau={noNiveau} />
    </td>
  );
}

function WPCell({
  stu,
  wpSubjects,
  wpNoNiveauSet,
}: {
  stu: StudentGradeStatus;
  wpSubjects: string[];
  wpNoNiveauSet: Set<string>;
}) {
  if (stu.gb) {
    const s = wpSubjects.map((n) => stu.wahlpflicht[n]).find((s) => s);
    return (
      <td className="px-2 py-1 border-b text-center">
        <TextDone set={!!s?.has_niveau} />
      </td>
    );
  }
  if (stu.lb) {
    for (const name of wpSubjects) {
      const s = stu.wahlpflicht[name];
      if (!s) continue;
      if (s.is_text_mode) {
        return (
          <td className="px-2 py-1 border-b text-center">
            <TextDone set={s.has_niveau} />
          </td>
        );
      }
      // grade mode — fall through to normal rendering below
      break;
    }
  }

  for (const name of wpSubjects) {
    const s = stu.wahlpflicht[name];
    if (!s || (s.grades_given === 0 && !s.has_niveau)) continue;
    const noNiveau = wpNoNiveauSet.has(name);
    const short = WP_SHORT[name] ?? name.slice(0, 2);
    const allDone = s.total_grades > 0 && s.grades_given === s.total_grades;
    const codeColor = allDone ? "text-green-600" : "text-orange-500";
    return (
      <td className="px-2 py-1 border-b text-center whitespace-nowrap">
        <span className={`text-xs font-semibold ${codeColor}`}>{short} </span>
        <GradeFraction s={s} />
        <NiveauWarn has_niveau={s.has_niveau} noNiveau={noNiveau} />
      </td>
    );
  }

  return <td className="px-2 py-1 border-b text-center text-red-400 text-xs">✗</td>;
}

function isDone(s: SubjectGradeStatus | undefined, noNiveau: boolean): boolean {
  if (!s) return false;
  if (s.total_grades === 0) return true;
  return s.grades_given === s.total_grades && (noNiveau || s.has_niveau);
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
      if (wahlpflicht_subjects.some((n) => isDone(stu.wahlpflicht[n], wpNoNiveauSet.has(n)))) done++;
    }
    total++;
    if (stu.has_report_text) done++;
    return { done, total };
  }

  const hasLB = students.some((s) => s.lb);
  const hasGB = students.some((s) => s.gb);

  const rowBg = (stu: StudentGradeStatus, ri: number) => {
    if (stu.lb) return ri % 2 === 0 ? "bg-green-800/10" : "bg-green-800/20";
    if (stu.gb) return ri % 2 === 0 ? "bg-orange-700/10" : "bg-orange-700/20";
    return ri % 2 === 0 ? "bg-white" : "bg-muted/20";
  };

  return (
    <div className="space-y-3">
      {(hasLB || hasGB) && (
        <div className="flex items-center gap-3">
          {hasLB && (
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span className="inline-block w-3 h-3 rounded-sm bg-green-800/40 border border-green-800/30" />
              LB
            </span>
          )}
          {hasGB && (
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span className="inline-block w-3 h-3 rounded-sm bg-orange-700/40 border border-orange-700/30" />
              GB
            </span>
          )}
        </div>
      )}
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
            <th title="Zeugnistext" className="px-2 py-2 font-medium border-b text-center text-xs whitespace-nowrap">
              ZT
            </th>
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
              <tr key={stu.student_id} className={rowBg(stu, ri)}>
                <td className="px-3 py-1 border-b font-medium whitespace-nowrap sticky left-0 bg-inherit">
                  {stu.last_name}
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
                  <WPCell stu={stu} wpSubjects={wahlpflicht_subjects} wpNoNiveauSet={wpNoNiveauSet} />
                )}
                <td className="px-2 py-1 border-b text-center">
                  {stu.has_report_text
                    ? <span className="text-green-600 text-sm">✓</span>
                    : <span className="text-red-400 text-sm">✗</span>}
                </td>
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
    </div>
  );
}
