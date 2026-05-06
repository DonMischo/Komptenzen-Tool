"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { setupApi } from "@/lib/api";
import { QK } from "@/lib/queries";
import { StudentImportResponse } from "@/types/api";
import { Upload } from "lucide-react";

export function StudentImportPanel() {
  const qc = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [removeMissing, setRemoveMissing] = useState(false);
  const [result, setResult] = useState<StudentImportResponse | null>(null);

  const uploadMutation = useMutation({
    mutationFn: () => setupApi.uploadStudents(file!, removeMissing),
    onSuccess: (res) => {
      setResult(res.data);
      qc.invalidateQueries({ queryKey: QK.schemaStatus });
      toast.success(
        `${res.data.added} hinzugefügt, ${res.data.updated} aktualisiert, ${res.data.removed} entfernt`
      );
    },
    onError: () => toast.error("Import fehlgeschlagen"),
  });

  return (
    <div className="bg-white rounded-xl border p-5 space-y-4">
      <h3 className="font-semibold text-lg">Schüler importieren</h3>
      <p className="text-xs text-muted-foreground">
        CSV-Spalten: Nachname, Vorname, Klasse, Geburtsdatum (Pflicht) + optionale Fehlzeit-Spalten
      </p>

      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 cursor-pointer border rounded-md px-3 py-1.5 text-sm hover:bg-muted">
            <Upload className="h-4 w-4" />
            {file ? file.name : "CSV auswählen…"}
            <input
              type="file"
              accept=".csv"
              className="hidden"
              onChange={(e) => {
                setFile(e.target.files?.[0] ?? null);
                setResult(null);
              }}
            />
          </label>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={removeMissing}
              onChange={(e) => setRemoveMissing(e.target.checked)}
              className="rounded"
            />
            Nicht enthaltene Schüler entfernen
          </label>
        </div>

        <button
          onClick={() => uploadMutation.mutate()}
          disabled={!file || uploadMutation.isPending}
          className="bg-primary text-white text-sm px-4 py-1.5 rounded-md hover:bg-primary/90 disabled:opacity-50"
        >
          {uploadMutation.isPending ? "Importiere…" : "Synchronisieren"}
        </button>
      </div>

      {result && (
        <div className="border rounded-md p-3 bg-muted/30 text-sm space-y-1">
          <p>✅ {result.added} hinzugefügt &nbsp;·&nbsp; {result.updated} aktualisiert &nbsp;·&nbsp; {result.removed} entfernt</p>
          {result.errors.length > 0 && (
            <details>
              <summary className="cursor-pointer text-amber-600">
                {result.errors.length} Warnung(en)
              </summary>
              <ul className="mt-1 space-y-0.5 text-xs text-muted-foreground">
                {result.errors.map((e, i) => <li key={i}>{e}</li>)}
              </ul>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
