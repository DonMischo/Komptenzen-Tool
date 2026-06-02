// TypeScript types matching the FastAPI Pydantic schemas

export interface AuthStatusResponse {
  authenticated: boolean;
  username: string | null;
  needs_setup: boolean;
  role: string | null;
}

export interface DatabaseListResponse {
  databases: string[];
  current: string | null;
}

export interface SchemaStatusResponse {
  db_name: string;
  schema_ready: boolean;
  student_count: number;
}

export interface ReportDayResponse {
  report_day: string | null;
  school_year: string;
  is_endjahr: boolean;
}

export interface StudentImportResponse {
  added: number;
  updated: number;
  removed: number;
  errors: string[];
}

export interface CustomCompetenceItem {
  id: number;
  text: string;
}

export interface CompetenceRow {
  competence_id: number;
  topic_name: string;
  text: string;
  selected: boolean;
}

export interface TopicGroup {
  topic_name: string;
  topic_id: number;
  competences: CompetenceRow[];
  custom_competences: CustomCompetenceItem[];
}

export interface CompetenceListResponse {
  class_name: string;
  subject: string;
  block: string;
  topics: TopicGroup[];
}

export interface GradeMatrixColumn {
  topic_id: number;
  label: string;
}

export interface GradeMatrixRow {
  student_id: number;
  last_name: string;
  first_name: string;
  niveau: string;
  grades: Record<string, string>;
  student_type: "normal" | "lb" | "gb";
}

export interface GradeMatrixResponse {
  columns: GradeMatrixColumn[];
  rows: GradeMatrixRow[];
}

export interface StudentBaseData {
  id: number;
  last_name: string;
  first_name: string;
  birthday: string | null;
  days_absent_excused: number;
  days_absent_unexcused: number;
  lessons_absent_excused: number;
  lessons_absent_unexcused: number;
  remarks: string;
  lb: boolean;
  gb: boolean;
  report_text: string;
}

export interface AdminStudentItem {
  id: number;
  last_name: string;
  first_name: string;
  class_name: string;
}

export interface ExportPrepareResponse {
  job_id: string;
  cl_dir: string;
  total: number;
}

// ---------------------------------------------------------------------------
// Overview
// ---------------------------------------------------------------------------

export interface CompetenceStatusItem {
  name: string;
  selected_count: number;
  custom_count: number;
  total_count: number;
}

export interface CompetenceStatusResponse {
  subjects: CompetenceStatusItem[];
}

export interface SubjectGradeStatus {
  has_niveau: boolean;
  grades_given: number;
  total_grades: number;
  is_text_mode: boolean;
}

export interface StudentGradeStatus {
  student_id: number;
  last_name: string;
  first_name: string;
  lb: boolean;
  gb: boolean;
  has_report_text: boolean;
  subjects: Record<string, SubjectGradeStatus>;
  wahlpflicht: Record<string, SubjectGradeStatus>;
}

export interface GradeStatusResponse {
  students: StudentGradeStatus[];
  relevant_subjects: string[];
  wahlpflicht_subjects: string[];
  wp_no_niveau: string[];
  no_niveau_subjects: string[];
}

export interface CustomCompetenceGroup {
  subject: string;
  topic_id: number;
  topic_name: string;
  customs: CustomCompetenceItem[];
}

export interface ExportProgressEvent {
  type: "progress" | "done" | "error";
  index: number;
  total: number;
  basename?: string;
  success?: boolean;
  error?: string | null;
}
