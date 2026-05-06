"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { stammdatenApi } from "@/lib/api";
import { QK } from "@/lib/queries";
import { Save } from "lucide-react";

interface Props {
  studentId: number;
  studentName: string;
}

export function ReportTextEditor({ studentId, studentName }: Props) {
  const [text, setText] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: QK.reportText(studentId),
    queryFn: () => stammdatenApi.getReportText(studentId).then((r) => r.data),
  });

  useEffect(() => {
    if (data) setText(data.report_text ?? "");
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: () => stammdatenApi.saveReportText(studentId, text),
    onSuccess: () => toast.success("Zeugnistext gespeichert"),
    onError: () => toast.error("Fehler beim Speichern"),
  });

  return (
    <div className="bg-white border rounded-xl p-5 space-y-3">
      <h3 className="font-semibold">📝 Zeugnistext — {studentName}</h3>
      {isLoading ? (
        <p className="text-sm text-muted-foreground animate-pulse">Laden…</p>
      ) : (
        <>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={6}
            className="w-full border rounded-md px-3 py-2 text-sm resize-y focus:outline-none focus:ring-2 focus:ring-primary"
            placeholder="Zeugnistext eingeben…"
          />
          <button
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending}
            className="flex items-center gap-2 bg-primary text-white px-4 py-1.5 rounded-md text-sm hover:bg-primary/90 disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            {saveMutation.isPending ? "Speichern…" : "Text speichern"}
          </button>
        </>
      )}
    </div>
  );
}
