"use client";

import { createContext, useContext } from "react";

interface ExportJobsCtx {
  addJob: (id: string, label: string, total: number) => void;
}

export const ExportJobsContext = createContext<ExportJobsCtx>({ addJob: () => {} });

export const useExportJobsContext = () => useContext(ExportJobsContext);
