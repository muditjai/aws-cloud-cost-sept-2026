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
import { WorkspaceSidebar } from "@/components/layout/workspace-sidebar";
import { Button } from "@/components/ui/button";
import { Drawer, DrawerContent, DrawerTrigger } from "@/components/ui/drawer";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import type { ArtifactPanelProps } from "@/lib/artifacts";
import { getWorkflowFromPathname, type WorkflowId } from "@/lib/workflow";
import { PanelRightOpen } from "lucide-react";
import { usePathname } from "next/navigation";
import { type ComponentType, useState } from "react";

interface WorkspaceShellProps {
  readonly children: React.ReactNode;
}

type ArtifactPanelDictionary = {
  [workflowId in WorkflowId]: ComponentType<ArtifactPanelProps>;
};

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
} satisfies ArtifactPanelDictionary;

export function WorkspaceShell({ children }: WorkspaceShellProps) {
  const pathname = usePathname();
  const workflow = getWorkflowFromPathname(pathname);
  const ArtifactPanel = artifactPanels[workflow.id];
  const [isArtifactDrawerOpen, setIsArtifactDrawerOpen] = useState(false);

  return (
    <SidebarProvider>
      <WorkspaceSidebar activeWorkflowId={workflow.id} />
      <SidebarInset className="h-dvh min-w-0 overflow-hidden bg-white text-slate-900">
        <Drawer
          direction="right"
          open={isArtifactDrawerOpen}
          onOpenChange={setIsArtifactDrawerOpen}
        >
          <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 px-5 sm:px-7">
            <div className="min-w-0">
              <p className="text-xs font-medium text-slate-500">
                Cloud cost transformation
              </p>
              <h1 className="truncate text-sm font-semibold text-slate-900">
                {workflow.label}
              </h1>
            </div>
            <DrawerTrigger asChild>
              <Button variant="outline" size="sm">
                <PanelRightOpen data-icon="inline-start" aria-hidden="true" />
                Artifacts
              </Button>
            </DrawerTrigger>
          </header>

          <div className="min-h-0 flex-1">{children}</div>
          <DrawerContent className="h-dvh max-h-none sm:max-w-md">
            <ArtifactPanel onClose={() => setIsArtifactDrawerOpen(false)} />
          </DrawerContent>
        </Drawer>
      </SidebarInset>
    </SidebarProvider>
  );
}
