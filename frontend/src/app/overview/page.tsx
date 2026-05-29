"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { competenceApi } from "@/lib/api";
import { QK } from "@/lib/queries";
import { AppShell } from "@/components/layout/AppShell";
import { KompetenzTab } from "@/components/overview/KompetenzTab";
import { NotenTab } from "@/components/overview/NotenTab";
import { EigeneKompetenzenTab } from "@/components/overview/EigeneKompetenzenTab";
import { cn } from "@/lib/utils";

type Tab = "kompetenzen" | "noten" | "eigene";

const TABS: { id: Tab; label: string }[] = [
  { id: "kompetenzen", label: "Kompetenzen" },
  { id: "noten",       label: "Noten" },
  { id: "eigene",      label: "Eigene Kompetenzen" },
];

export default function OverviewPage() {
  const [className, setClassName] = useState("");
  const [tab, setTab] = useState<Tab>("kompetenzen");

  const { data: classData } = useQuery<{ classes: string[] }>({
    queryKey: QK.classes,
    queryFn: () => competenceApi.classes().then((r) => r.data),
  });

  return (
    <AppShell>
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-1">Übersicht</h1>
        <p className="text-sm text-muted-foreground">Vollständigkeitsprüfung je Klasse</p>
      </div>

      {/* Class selector */}
      <div>
        <label className="text-sm font-medium mr-2">Klasse:</label>
        <select
          value={className}
          onChange={(e) => setClassName(e.target.value)}
          className="border rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
        >
          <option value="">— Klasse wählen —</option>
          {classData?.classes.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      {!className && (
        <p className="text-sm text-muted-foreground">Bitte zuerst eine Klasse auswählen.</p>
      )}

      {className && (
        <>
          {/* Tab bar */}
          <div className="flex gap-1 border-b">
            {TABS.map(({ id, label }) => (
              <button
                key={id}
                onClick={() => setTab(id)}
                className={cn(
                  "px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors",
                  tab === id
                    ? "border-primary text-primary"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                )}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div>
            {tab === "kompetenzen" && <KompetenzTab classNameValue={className} />}
            {tab === "noten"       && <NotenTab classNameValue={className} />}
            {tab === "eigene"      && <EigeneKompetenzenTab classNameValue={className} />}
          </div>
        </>
      )}
    </div>
    </AppShell>
  );
}
