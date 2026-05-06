"use client";

import { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { ClassSubjectFilter } from "@/components/layout/ClassSubjectFilter";
import { GradeMatrixTable } from "@/components/schuelerdaten/GradeMatrixTable";

export default function SchuelerdatenPage() {
  const [selectedClass, setSelectedClass] = useState("");
  const [selectedSubject, setSelectedSubject] = useState("");

  const handleSubjectChange = (s: string) => {
    setSelectedSubject(s);
  };

  return (
    <AppShell>
      <div className="flex gap-6">
        {/* Sidebar filter — no block needed for grade matrix */}
        <aside className="w-48 shrink-0">
          <ClassSubjectFilter
            classValue={selectedClass}
            subjectValue={selectedSubject}
            blockValue=""
            onClassChange={setSelectedClass}
            onSubjectChange={handleSubjectChange}
            onBlockChange={() => {}}
            showBlock={false}
          />
        </aside>

        <div className="flex-1">
          <h2 className="text-2xl font-bold mb-4">Schülerdaten</h2>
          {selectedClass && selectedSubject ? (
            <GradeMatrixTable
              classNameValue={selectedClass}
              subject={selectedSubject}
            />
          ) : (
            <p className="text-muted-foreground text-sm">
              Bitte Klasse und Fach auswählen.
            </p>
          )}
        </div>
      </div>
    </AppShell>
  );
}
