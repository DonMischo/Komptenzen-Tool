// TanStack Query key constants

export const QK = {
  authStatus: ["auth", "status"] as const,
  databases: ["databases"] as const,
  schemaStatus: ["setup", "schema"] as const,
  reportDay: ["setup", "reportDay"] as const,
  classes: ["classes"] as const,
  subjects: ["subjects"] as const,
  blocks: (subject: string) => ["subjects", subject, "blocks"] as const,
  competences: (cls: string, subject: string, block: string) =>
    ["competences", cls, subject, block] as const,
  matrix: (cls: string, subject: string) => ["matrix", cls, subject] as const,
  stammdaten: (cls: string) => ["stammdaten", cls] as const,
  reportText: (studentId: number) => ["reportText", studentId] as const,
  adminStudents: (cls: string) => ["admin", "students", cls] as const,
};
