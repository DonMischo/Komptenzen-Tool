"use client";

import { AppShell } from "@/components/layout/AppShell";
import { DatabasePanel } from "@/components/setup/DatabasePanel";
import { SchemaPanel } from "@/components/setup/SchemaPanel";
import { ReportDayPanel } from "@/components/setup/ReportDayPanel";
import { StudentImportPanel } from "@/components/setup/StudentImportPanel";
import { BackupPanel } from "@/components/setup/BackupPanel";

export default function SetupPage() {
  return (
    <AppShell>
      <div className="space-y-6">
        <h2 className="text-2xl font-bold">⚙️ Setup</h2>
        <DatabasePanel />
        <SchemaPanel />
        <ReportDayPanel />
        <StudentImportPanel />
        <BackupPanel />
      </div>
    </AppShell>
  );
}
