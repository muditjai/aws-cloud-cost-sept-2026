"use client";

import { ArtifactPanel } from "@/components/layout/artifact-panel";
import { WorkspaceSidebar } from "@/components/layout/workspace-sidebar";
import { Button } from "@/components/ui/button";
import { getWorkflowFromPathname } from "@/lib/workflow";
import { PanelRightClose, PanelRightOpen } from "lucide-react";
import { usePathname } from "next/navigation";
import { useState } from "react";

interface WorkspaceShellProps {
  readonly children: React.ReactNode;
}

export function WorkspaceShell({ children }: WorkspaceShellProps) {
  const pathname = usePathname();
  const workflow = getWorkflowFromPathname(pathname);
  const [isArtifactPanelOpen, setIsArtifactPanelOpen] = useState(true);

  return (
    <main className="flex h-dvh min-w-0 overflow-hidden bg-white text-slate-900">
      <WorkspaceSidebar activeWorkflowId={workflow.id} />

      <section className="flex min-w-0 flex-1 flex-col bg-white">
        <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 px-5 sm:px-7">
          <div className="min-w-0">
            <p className="text-xs font-medium text-slate-500">Cloud cost transformation</p>
            <h1 className="truncate text-sm font-semibold text-slate-900">{workflow.label}</h1>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsArtifactPanelOpen((isOpen) => !isOpen)}
            aria-expanded={isArtifactPanelOpen}
            aria-controls="artifact-panel"
          >
            {isArtifactPanelOpen ? (
              <PanelRightClose data-icon="inline-start" aria-hidden="true" />
            ) : (
              <PanelRightOpen data-icon="inline-start" aria-hidden="true" />
            )}
            Artifacts
          </Button>
        </header>

        <div className="min-h-0 flex-1">{children}</div>
      </section>

      {isArtifactPanelOpen ? (
        <div id="artifact-panel" className="hidden w-80 shrink-0 border-l border-slate-200 lg:block">
          <ArtifactPanel workflow={workflow} onClose={() => setIsArtifactPanelOpen(false)} />
        </div>
      ) : null}
    </main>
  );
}
