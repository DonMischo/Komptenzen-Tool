"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { setupApi } from "@/lib/api";
import { QK } from "@/lib/queries";
import { ReportDayResponse } from "@/types/api";
import { Globe } from "lucide-react";

export function ReportDayPanel() {
  const qc = useQueryClient();
  const [dateInput, setDateInput] = useState("");

  const { data, isLoading } = useQuery<ReportDayResponse>({
    queryKey: QK.reportDay,
    queryFn: () => setupApi.getReportDay().then((r) => r.data),
    retry: false,
  });

  useEffect(() => {
    if (data?.report_day) setDateInput(data.report_day);
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: () => setupApi.setReportDay(dateInput),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QK.reportDay });
      toast.success("Zeugnistag gespeichert");
    },
    onError: () => toast.error("Fehler beim Speichern"),
  });

  const fetchMutation = useMutation({
    mutationFn: () =>
      setupApi.fetchReportDay(data?.is_endjahr ? "ej" : "hj"),
    onSuccess: (res) => {
      setDateInput(res.data.suggested);
      toast.success(`Vorschlag: ${res.data.suggested}`);
    },
    onError: () => toast.error("Ferien-Daten konnten nicht geladen werden"),
  });

  if (isLoading || !data) return null;

  return (
    <div className="bg-white rounded-xl border p-5 space-y-3">
      <h3 className="font-semibold text-lg">Zeugnistag</h3>
      <p className="text-sm text-muted-foreground">
        Schuljahr {data.school_year} — {data.is_endjahr ? "Endjahr" : "Halbjahr"}
      </p>

      <div className="flex gap-2 items-end">
        <div className="space-y-1">
          <label className="text-sm font-medium">Datum (DD.MM.YYYY)</label>
          <input
            type="text"
            value={dateInput}
            onChange={(e) => setDateInput(e.target.value)}
            placeholder="31.01.2026"
            className="border rounded-md px-3 py-1.5 text-sm w-40"
          />
        </div>
        <button
          onClick={() => fetchMutation.mutate()}
          disabled={fetchMutation.isPending}
          className="flex items-center gap-1.5 text-sm border px-3 py-1.5 rounded-md hover:bg-muted disabled:opacity-50"
        >
          <Globe className="h-4 w-4" />
          {fetchMutation.isPending ? "Laden…" : "Aus Internet"}
        </button>
        <button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending || !dateInput}
          className="bg-primary text-white text-sm px-3 py-1.5 rounded-md hover:bg-primary/90 disabled:opacity-50"
        >
          Speichern
        </button>
      </div>
    </div>
  );
}
