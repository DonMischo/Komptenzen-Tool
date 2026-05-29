"use client";

import { useQuery } from "@tanstack/react-query";
import { overviewApi } from "@/lib/api";
import { QK } from "@/lib/queries";
import { CompetenceStatusResponse } from "@/types/api";

interface Props {
  classNameValue: string;
}

function StatusIcon({ count }: { count: number }) {
  if (count >= 5) return <span className="text-green-600 font-semibold">✓ {count}</span>;
  if (count >= 1) return <span className="text-yellow-600 font-semibold">⚠ {count}</span>;
  return <span className="text-red-500 font-semibold">✗ 0</span>;
}

export function KompetenzTab({ classNameValue }: Props) {
  const { data, isLoading } = useQuery<CompetenceStatusResponse>({
    queryKey: QK.overviewCompetences(classNameValue),
    queryFn: () => overviewApi.competences(classNameValue).then((r) => r.data),
    enabled: !!classNameValue,
  });

  if (isLoading) return <p className="text-sm text-muted-foreground animate-pulse">Laden…</p>;
  if (!data) return null;

  const total = data.subjects.length;
  const done = data.subjects.filter((s) => s.selected_count >= 5).length;
  const warn = data.subjects.filter((s) => s.selected_count >= 1 && s.selected_count < 5).length;
  const missing = data.subjects.filter((s) => s.selected_count === 0).length;

  return (
    <div className="space-y-3">
      <div className="flex gap-4 text-sm">
        <span className="text-green-600 font-medium">✓ {done} vollständig</span>
        {warn > 0 && <span className="text-yellow-600 font-medium">⚠ {warn} unvollständig</span>}
        {missing > 0 && <span className="text-red-500 font-medium">✗ {missing} ohne Auswahl</span>}
        <span className="text-muted-foreground">/ {total} Fächer</span>
      </div>

      <div className="overflow-x-auto border rounded-xl">
        <table className="text-sm w-full border-collapse">
          <thead>
            <tr className="bg-muted/50">
              <th className="text-left px-3 py-2 font-medium border-b">Fach</th>
              <th className="text-left px-3 py-2 font-medium border-b">Ausgewählte Kompetenzen</th>
            </tr>
          </thead>
          <tbody>
            {data.subjects.map((s, i) => (
              <tr key={s.name} className={i % 2 === 0 ? "bg-white" : "bg-muted/20"}>
                <td className="px-3 py-1.5 border-b">{s.name}</td>
                <td className="px-3 py-1.5 border-b">
                  <StatusIcon count={s.selected_count} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
