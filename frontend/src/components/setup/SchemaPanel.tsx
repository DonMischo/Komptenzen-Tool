"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { setupApi } from "@/lib/api";
import { QK } from "@/lib/queries";
import { SchemaStatusResponse } from "@/types/api";
import { CheckCircle, AlertCircle } from "lucide-react";
import api from "@/lib/api";

export function SchemaPanel() {
  const qc = useQueryClient();

  const { data, isLoading } = useQuery<SchemaStatusResponse>({
    queryKey: QK.schemaStatus,
    queryFn: () => setupApi.schemaStatus().then((r) => r.data),
    retry: false,
  });

  const initMutation = useMutation({
    mutationFn: () => setupApi.initSchema(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QK.schemaStatus });
      toast.success("Schema initialisiert");
    },
    onError: () => toast.error("Schema-Initialisierung fehlgeschlagen"),
  });

  const testdataMutation = useMutation({
    mutationFn: () => api.post("/setup/testdata").then((r) => r.data),
    onSuccess: (data) => toast.success(data.message),
    onError: () => toast.error("Testdaten-Generierung fehlgeschlagen"),
  });

  if (isLoading) return null;

  const ready = data?.schema_ready ?? false;

  return (
    <div className="bg-white rounded-xl border p-5 space-y-3">
      <h3 className="font-semibold text-lg">Schema</h3>

      {data ? (
        <div className="flex items-center gap-3">
          {ready ? (
            <span className="flex items-center gap-1.5 text-green-600 text-sm">
              <CheckCircle className="h-4 w-4" />
              Schema bereit — {data.student_count} Schüler
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-amber-600 text-sm">
              <AlertCircle className="h-4 w-4" />
              Kein Schema in &ldquo;{data.db_name}&rdquo;
            </span>
          )}

          {!ready && (
            <button
              onClick={() => initMutation.mutate()}
              disabled={initMutation.isPending}
              className="bg-primary text-white text-sm px-3 py-1.5 rounded-md hover:bg-primary/90 disabled:opacity-50"
            >
              {initMutation.isPending ? "Initialisiere…" : "Schema initialisieren"}
            </button>
          )}

          {ready && (
            <button
              onClick={() => testdataMutation.mutate()}
              disabled={testdataMutation.isPending}
              className="border text-sm px-3 py-1.5 rounded-md hover:bg-muted disabled:opacity-50"
            >
              {testdataMutation.isPending ? "Generiere…" : "Testdaten 7a"}
            </button>
          )}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">Keine aktive Datenbank ausgewählt.</p>
      )}
    </div>
  );
}
