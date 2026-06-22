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
  previewStudents: (file: File, remove_missing: boolean, update_fields: string[]) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("remove_missing", String(remove_missing));
    fd.append("update_fields", update_fields.join(","));
    return api.post("/setup/students/preview", fd);
  },
  uploadStudents: (file: File, remove_missing: boolean, update_fields: string[]) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("remove_missing", String(remove_missing));
    fd.append("update_fields", update_fields.join(","));
    return api.post("/setup/students/upload", fd);
  },
  generateTestdata: () => api.post("/setup/testdata"),
  removeTestdata: () => api.delete("/setup/testdata"),
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
  updateCustom: (id: number, text: string) =>
    api.put(`/overview/custom-competences/${id}`, { text }),
  deleteCustom: (id: number) => api.delete(`/competences/custom/${id}`),
  preview: (class_name: string, subject: string) =>
    api.get("/competences/preview", { params: { class_name, subject } }),
  syncToParallel: (class_name: string, target_classes?: string[]) =>
    api.post("/competences/sync-to-parallel",
      target_classes && target_classes.length > 0 ? { target_classes } : null,
      { params: { class_name } }
    ),
};

// ---------------------------------------------------------------------------
// Students (grade matrix)
// ---------------------------------------------------------------------------
export const studentsApi = {
  matrix: (class_name: string, subject: string) =>
    api.get("/students/matrix", { params: { class_name, subject } }),
  saveMatrix: (class_name: string, subject: string, rows: import("@/types/api").GradeMatrixRow[]) =>
    api.post("/students/matrix", { class_name, subject, rows }),
  lbProfile: (student_id: number) =>
    api.get(`/students/${student_id}/lb-profile`),
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
  getRemarks: (student_id: number) =>
    api.get(`/stammdaten/${student_id}/remarks`),
  saveRemarks: (student_id: number, remarks: string) =>
    api.put(`/stammdaten/${student_id}/remarks`, { remarks }),
};

// ---------------------------------------------------------------------------
// Admin
// ---------------------------------------------------------------------------
export const adminApi = {
  students: (class_name: string) =>
    api.get("/admin/students", { params: { class_name } }),
  prepareExport: (student_ids: number[], classroom: string) =>
    api.post("/admin/export/prepare", { student_ids, classroom }),
  competenceSyncDiff: () => api.get("/admin/competence-sync/diff"),
  competenceSyncApply: () => api.post("/admin/competence-sync/apply"),
};

// ---------------------------------------------------------------------------
// Overview
// ---------------------------------------------------------------------------
export const overviewApi = {
  competences: (class_name: string) =>
    api.get("/overview/competences", { params: { class_name } }),
  grades: (class_name: string) =>
    api.get("/overview/grades", { params: { class_name } }),
  customCompetences: (class_name: string) =>
    api.get("/overview/custom-competences", { params: { class_name } }),
  updateCustom: (id: number, text: string) =>
    api.put(`/overview/custom-competences/${id}`, { text }),
  deleteCustom: (id: number) =>
    api.delete(`/competences/custom/${id}`),
};

// ---------------------------------------------------------------------------
// User management
// ---------------------------------------------------------------------------
export const usersApi = {
  list: () => api.get("/admin/users"),
  create: (username: string, password: string, role: string) =>
    api.post("/admin/users", { username, password, role }),
  delete: (username: string) => api.delete(`/admin/users/${username}`),
};
