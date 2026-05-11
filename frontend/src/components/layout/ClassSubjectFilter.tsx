"use client";

import { useQuery } from "@tanstack/react-query";
import { competenceApi } from "@/lib/api";
import { QK } from "@/lib/queries";

interface Props {
  classValue: string;
  subjectValue: string;
  blockValue: string;
  onClassChange: (v: string) => void;
  onSubjectChange: (v: string) => void;
  onBlockChange: (v: string) => void;
  showBlock?: boolean;
  selectClassName?: string;
}

export function ClassSubjectFilter({
  classValue,
  subjectValue,
  blockValue,
  onClassChange,
  onSubjectChange,
  onBlockChange,
  showBlock = true,
  selectClassName = "",
}: Props) {
  const { data: classesData } = useQuery({
    queryKey: QK.classes,
    queryFn: () => competenceApi.classes().then((r) => r.data),
  });

  const { data: subjectsData } = useQuery({
    queryKey: QK.subjects,
    queryFn: () => competenceApi.subjects().then((r) => r.data),
  });

  const { data: blocksData } = useQuery({
    queryKey: QK.blocks(subjectValue),
    queryFn: () => competenceApi.blocks(subjectValue).then((r) => r.data),
    enabled: !!subjectValue && showBlock,
  });

  const classes: string[] = classesData?.classes ?? [];
  const subjects: string[] = subjectsData?.subjects ?? [];
  const blocks: string[] = blocksData?.blocks ?? [];

  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Klasse
        </label>
        <select
          value={classValue}
          onChange={(e) => onClassChange(e.target.value)}
          className={`w-full border rounded-md px-2 py-1.5 text-sm bg-white ${selectClassName}`}
        >
          <option value="">– Klasse –</option>
          {classes.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-1">
        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Fach
        </label>
        <select
          value={subjectValue}
          onChange={(e) => onSubjectChange(e.target.value)}
          className={`w-full border rounded-md px-2 py-1.5 text-sm bg-white ${selectClassName}`}
        >
          <option value="">– Fach –</option>
          {subjects.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      {showBlock && (
        <div className="space-y-1">
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Block
          </label>
          <select
            value={blockValue}
            onChange={(e) => onBlockChange(e.target.value)}
            className={`w-full border rounded-md px-2 py-1.5 text-sm bg-white ${selectClassName}`}
            disabled={!subjectValue}
          >
            <option value="">– Block –</option>
            {blocks.map((b) => (
              <option key={b} value={b}>
                {b}
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
}
