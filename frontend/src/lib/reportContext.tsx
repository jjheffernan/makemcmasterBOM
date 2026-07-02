import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { ReportMatchErrorDialog } from "@/components/ReportMatchErrorDialog";
import type { Part, Project } from "@/lib/api";

export interface BomReportContext {
  projectId: string;
  project: Project;
  parts: Part[];
}

interface ReportMatchErrorContextValue {
  openReport: (options?: { partIndex?: number | null }) => void;
  registerBomContext: (context: BomReportContext | null) => void;
}

const ReportMatchErrorContext = createContext<ReportMatchErrorContextValue | null>(
  null,
);

export function ReportMatchErrorProvider({ children }: { children: ReactNode }) {
  const [bomContext, setBomContext] = useState<BomReportContext | null>(null);
  const [open, setOpen] = useState(false);
  const [partIndex, setPartIndex] = useState<number | null>(null);

  const registerBomContext = useCallback((context: BomReportContext | null) => {
    setBomContext(context);
  }, []);

  const openReport = useCallback((options?: { partIndex?: number | null }) => {
    setPartIndex(options?.partIndex ?? null);
    setOpen(true);
  }, []);

  const value = useMemo(
    () => ({ openReport, registerBomContext }),
    [openReport, registerBomContext],
  );

  const emptyProject: Project = {
    title: "",
    makerworld_url: "",
    description: "",
    parts: [],
  };

  return (
    <ReportMatchErrorContext.Provider value={value}>
      {children}
      <ReportMatchErrorDialog
        open={open}
        onClose={() => setOpen(false)}
        projectId={bomContext?.projectId ?? ""}
        project={bomContext?.project ?? emptyProject}
        parts={bomContext?.parts ?? []}
        initialPartIndex={partIndex}
      />
    </ReportMatchErrorContext.Provider>
  );
}

export function useReportMatchError() {
  const ctx = useContext(ReportMatchErrorContext);
  if (!ctx) {
    throw new Error("useReportMatchError must be used within ReportMatchErrorProvider");
  }
  return ctx;
}
