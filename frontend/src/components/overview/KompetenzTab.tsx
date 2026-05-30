"use client";

import { useQuery } from "@tanstack/react-query";
import { overviewApi } from "@/lib/api";
import { QK } from "@/lib/queries";
import { CompetenceStatusResponse, CompetenceStatusItem } from "@/types/api";

interface Props {
  classNameValue: string;
}

function itemColor(item: CompetenceStatusItem): string {
  if (item.total_count === 0 || item.selected_count === 0) return "text-red-500";
  if (item.selected_count / item.total_count >= 0.2) return "text-green-600";
  return "text-orange-500";
}

function ItemLabel({ item }: { item: CompetenceStatusItem }) {
  const color = itemColor(item);
  const custom = item.custom_count > 0 ? `(${item.custom_count})` : "";
  return (
    <span className={`font-semibold ${color}`}>
      {item.selected_count}{custom}/{item.total_count}
    </span>
  );
}

export function KompetenzTab({ classNameValue }: Props) {
  const { data, isLoading } = useQuery<CompetenceStatusResponse>({
    queryKey: QK.overviewCompetences(classNameValue),
    queryFn: () => overviewApi.competences(classNameValue).then((r) => r.data),
    enabled: !!classNameValue,
  });

  if (isLoading) return <p className="text-sm text-muted-foreground animate-pulse">Laden…</p>;
  if (!data) return null;

  const green  = data.subjects.filter((s) => s.total_count > 0 && s.selected_count / s.total_count >= 0.2).length;
  const orange = data.subjects.filter((s) => s.total_count > 0 && s.selected_count > 0 && s.selected_count / s.total_count < 0.2).length;
  const red    = data.subjects.filter((s) => s.selected_count === 0).length;

  return (
    <div className="space-y-3">
      <div className="flex gap-4 text-sm">
        <span className="text-green-600 font-medium">● {green} ≥ 20 %</span>
        {orange > 0 && <span className="text-orange-500 font-medium">● {orange} &lt; 20 %</span>}
        {red    > 0 && <span className="text-red-500 font-medium">● {red} keine</span>}
        <span className="text-muted-foreground">/ {data.subjects.length} Fächer</span>
      </div>

      <div className="overflow-x-auto border rounded-xl">
        <table className="text-sm w-full border-collapse">
          <thead>
            <tr className="bg-muted/50">
              <th className="text-left px-3 py-2 font-medium border-b">Fach</th>
              <th className="text-left px-3 py-2 font-medium border-b">
                Kompetenzen <span className="font-normal text-muted-foreground">(ausgewählt(eigen)/gesamt)</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {data.subjects.map((s, i) => (
              <tr key={s.name} className={i % 2 === 0 ? "bg-white" : "bg-muted/20"}>
                <td className="px-3 py-1.5 border-b">{s.name}</td>
                <td className="px-3 py-1.5 border-b">
                  <ItemLabel item={s} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
