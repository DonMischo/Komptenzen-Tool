import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  withCredentials: true, // send httpOnly cookies
});

// Attach X-Active-DB header from localStorage on every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const activeDb = localStorage.getItem("activeDb");
    if (activeDb) {
      config.headers["x-active-db"] = activeDb;
    }
  }
  return config;
});

export default api;

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------
export const authApi = {
  status: () => api.get("/auth/status"),
  me: () => api.get("/auth/me"),
  login: (username: string, password: string) =>
    api.post("/auth/login", { username, password }),
  logout: () => api.post("/auth/logout"),
  setup: (username: string, password: string) =>
    api.post("/auth/setup", { username, password }),
};

// ---------------------------------------------------------------------------
// Databases / Setup
// ---------------------------------------------------------------------------
export const setupApi = {
  listDatabases: () => api.get("/databases"),
  createDatabase: (name: string) => api.post("/databases", { name }),
  selectDatabase: (name: string) => api.post("/databases/select", { name }),
  deleteDatabase: (name: string) => api.delete(`/databases/${name}`),
  suggestDatabase: (term: string) =>
    api.get("/databases/suggest", { params: { term } }),
  schemaStatus: () => api.get("/setup/schema-status"),
  initSchema: () => api.post("/setup/init-schema"),
  getReportDay: () => api.get("/setup/report-day"),
  setReportDay: (report_day: string) =>
    api.put("/setup/report-day", { report_day }),
  fetchReportDay: (type: "hj" | "ej") =>
    api.get("/setup/report-day/fetch", { params: { type } }),
  uploadStudents: (file: File, remove_missing: boolean) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("remove_missing", String(remove_missing));
    return api.post("/setup/students/upload", fd);
  },
  backupUrl: () => `/api/setup/backup`,
};

// ---------------------------------------------------------------------------
// Competences
// ---------------------------------------------------------------------------
export const competenceApi = {
  classes: () => api.get("/classes"),
  subjects: () => api.get("/subjects"),
  blocks: (subject: string) => api.get(`/subjects/${encodeURIComponent(subject)}/blocks`),
  list: (class_name: string, subject: string, block: string) =>
    api.get("/competences", { params: { class_name, subject, block } }),
  save: (class_name: string, changes: [number, boolean][]) =>
    api.post("/competences/save", { class_name, changes }),
  toggleTopic: (class_name: string, topic_id: number, value: boolean) =>
    api.post("/competences/toggle-topic", { class_name, topic_id, value }),
  addCustom: (class_name: string, topic_id: number, text: string) =>
    api.post("/competences/custom", { class_name, topic_id, text }),
  deleteCustom: (id: number) => api.delete(`/competences/custom/${id}`),
};

// ---------------------------------------------------------------------------
// Students (grade matrix)
// ---------------------------------------------------------------------------
export const studentsApi = {
  matrix: (class_name: string, subject: string) =>
    api.get("/students/matrix", { params: { class_name, subject } }),
  saveMatrix: (class_name: string, subject: string, rows: import("@/types/api").GradeMatrixRow[]) =>
    api.post("/students/matrix", { class_name, subject, rows }),
};

// ---------------------------------------------------------------------------
// Stammdaten
// ---------------------------------------------------------------------------
export const stammdatenApi = {
  list: (class_name: string) =>
    api.get("/stammdaten", { params: { class_name } }),
  saveBatch: (data: import("@/types/api").StudentBaseData[]) =>
    api.post("/stammdaten/batch", data),
  getReportText: (student_id: number) =>
    api.get(`/stammdaten/${student_id}/report-text`),
  saveReportText: (student_id: number, report_text: string) =>
    api.put(`/stammdaten/${student_id}/report-text`, { report_text }),
};

// ---------------------------------------------------------------------------
// Admin
// ---------------------------------------------------------------------------
export const adminApi = {
  students: (class_name: string) =>
    api.get("/admin/students", { params: { class_name } }),
  prepareExport: (student_ids: number[], classroom: string) =>
    api.post("/admin/export/prepare", { student_ids, classroom }),
};
