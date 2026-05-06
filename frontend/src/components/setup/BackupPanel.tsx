"use client";

import { setupApi } from "@/lib/api";
import { Download } from "lucide-react";

export function BackupPanel() {
  const activeDb = typeof window !== "undefined" ? localStorage.getItem("activeDb") ?? "" : "";

  const handleDownload = () => {
    if (!activeDb) return;
    const url = setupApi.backupUrl();
    const headers: Record<string, string> = { "x-active-db": activeDb };
    fetch(url, { headers, credentials: "include" })
      .then((res) => {
        if (!res.ok) throw new Error("Backup fehlgeschlagen");
        return res.blob();
      })
      .then((blob) => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        const today = new Date().toISOString().slice(0, 10).replace(/-/g, "");
        a.download = `${activeDb}_${today}.sql`;
        a.click();
      })
      .catch((e) => alert(String(e)));
  };

  return (
    <div className="bg-white rounded-xl border p-5 space-y-3">
      <h3 className="font-semibold text-lg">Backup</h3>
      <button
        onClick={handleDownload}
        disabled={!activeDb}
        className="flex items-center gap-2 border text-sm px-3 py-1.5 rounded-md hover:bg-muted disabled:opacity-40"
      >
        <Download className="h-4 w-4" />
        pg_dump herunterladen
      </button>
    </div>
  );
}
