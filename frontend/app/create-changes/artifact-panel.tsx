"use client";

import { DrawerDescription, DrawerTitle } from "@/components/ui/drawer";
import { Button } from "@/components/ui/button";
import type { ArtifactPanelProps } from "@/lib/artifacts";
import { FileText, X } from "lucide-react";

export function CreateChangesArtifactPanel({ onClose }: ArtifactPanelProps) {
  return (
    <aside className="flex min-h-0 flex-1 flex-col bg-slate-50/70">
      <div className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 px-5">
        <div>
          <DrawerTitle className="text-sm text-slate-900">
            Artifacts
          </DrawerTitle>
          <DrawerDescription className="mt-0.5 text-xs text-slate-500">
            Evidence and agent output
          </DrawerDescription>
        </div>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onClose}
          aria-label="Close artifacts"
        >
          <X aria-hidden="true" />
        </Button>
      </div>
      <div className="flex flex-1 flex-col gap-5 overflow-y-auto p-5">
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-4">
          <div className="flex items-start gap-3">
            <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
              <FileText className="size-4" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-900">
                Change artifacts
              </p>
              <p className="mt-1 text-xs leading-5 text-slate-500">
                Implementation plans and generated changes will appear here.
              </p>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
