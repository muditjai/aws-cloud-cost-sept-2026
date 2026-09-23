"use client";

import { AuditArtifactPanel } from "@/app/audit/artifact-panel";
import { ConnectArtifactPanel } from "@/app/connect/artifact-panel";
import { CreateChangesArtifactPanel } from "@/app/create-changes/artifact-panel";
import { DeployArtifactPanel } from "@/app/deploy/artifact-panel";
import { IngestArtifactPanel } from "@/app/ingest/artifact-panel";
import { LiveValidateArtifactPanel } from "@/app/live-validate/artifact-panel";
import { ProveSavingsArtifactPanel } from "@/app/prove-savings/artifact-panel";
import { RecommendArtifactPanel } from "@/app/recommend/artifact-panel";
import { TestArtifactPanel } from "@/app/test/artifact-panel";
import type { ArtifactPanelProps } from "@/components/layout/artifact-panel-frame";
import { WorkspaceSidebar } from "@/components/layout/workspace-sidebar";
import { Button } from "@/components/ui/button";
import { getWorkflowFromPathname, type WorkflowId } from "@/lib/workflow";
import { PanelRightClose, PanelRightOpen } from "lucide-react";
import { usePathname } from "next/navigation";
import { type ComponentType, useState } from "react";

interface WorkspaceShellProps {
  readonly children: React.ReactNode;
}

const artifactPanels = {
  connect: ConnectArtifactPanel,
  ingest: IngestArtifactPanel,
  audit: AuditArtifactPanel,
  recommend: RecommendArtifactPanel,
  "create-changes": CreateChangesArtifactPanel,
  test: TestArtifactPanel,
  deploy: DeployArtifactPanel,
  "live-validate": LiveValidateArtifactPanel,
  "prove-savings": ProveSavingsArtifactPanel,
} satisfies Record<WorkflowId, ComponentType<ArtifactPanelProps>>;

export function WorkspaceShell({ children }: WorkspaceShellProps) {
  const pathname = usePathname();
  const workflow = getWorkflowFromPathname(pathname);
  const ArtifactPanel = artifactPanels[workflow.id];
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
          <ArtifactPanel onClose={() => setIsArtifactPanelOpen(false)} />
        </div>
      ) : null}
    </main>
  );
}
