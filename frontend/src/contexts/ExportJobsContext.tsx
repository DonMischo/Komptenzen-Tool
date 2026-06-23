"use client";

import { createContext, useContext } from "react";
import type { ExportJob } from "@/hooks/useExportJobs";

interface ExportJobsCtx {
  jobs: ExportJob[];
  addJob: (id: string, label: string, total: number) => void;
  cancelJob: (id: string) => void;
  dismissJob: (id: string) => void;
}

export const ExportJobsContext = createContext<ExportJobsCtx>({
  jobs: [],
  addJob: () => {},
  cancelJob: () => {},
  dismissJob: () => {},
});

export const useExportJobsContext = () => useContext(ExportJobsContext);
