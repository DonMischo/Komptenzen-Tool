"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { stammdatenApi } from "@/lib/api";
import { QK } from "@/lib/queries";
import { RichTextEditorModal } from "./RichTextEditorModal";

interface Props {
  studentId: number;
  studentName: string;
  onClose: () => void;
}

export function RemarksEditor({ studentId, studentName, onClose }: Props) {
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: QK.remarks(studentId),
    queryFn: () => stammdatenApi.getRemarks(studentId).then((r) => r.data),
  });

  const saveMutation = useMutation({
    mutationFn: (html: string) => stammdatenApi.saveRemarks(studentId, html),
    onSuccess: () => {
      toast.success("Bemerkungen gespeichert");
      // Refresh the stammdaten table so the remarks column stays in sync
      qc.invalidateQueries({ queryKey: ["stammdaten"] });
      onClose();
    },
    onError: () => toast.error("Fehler beim Speichern"),
  });

  if (isLoading) return null;

  return (
    <RichTextEditorModal
      title={`Bemerkungen — ${studentName}`}
      initialHtml={data?.remarks ?? ""}
      open
      saving={saveMutation.isPending}
      onSave={(html) => saveMutation.mutate(html)}
      onClose={onClose}
    />
  );
}
