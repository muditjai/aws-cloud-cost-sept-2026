"use client";

import { WorkspaceArtifactDrawer } from "@/components/layout/workspace-artifact-drawer";
import { WorkspaceSidebar } from "@/components/layout/workspace-sidebar";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { getWorkflowFromPathname } from "@/lib/workflow";
import { usePathname } from "next/navigation";
import { Suspense } from "react";

interface WorkspaceShellProps {
  readonly children: React.ReactNode;
}

export function WorkspaceShell({ children }: WorkspaceShellProps) {
  return (
    <Suspense fallback={<WorkspaceShellFallback />}>
      <WorkspaceShellContent>{children}</WorkspaceShellContent>
    </Suspense>
  );
}

function WorkspaceShellContent({ children }: WorkspaceShellProps) {
  const pathname = usePathname();
  const workflow = getWorkflowFromPathname(pathname);

  return (
    <SidebarProvider>
      <WorkspaceSidebar activeWorkflowId={workflow.id} />
      <SidebarInset className="h-dvh min-w-0 overflow-hidden bg-white text-slate-900">
        <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 px-5 sm:px-7">
          <div className="min-w-0">
            <p className="text-xs font-medium text-slate-500">
              Cloud cost reduction
            </p>
            <h1 className="truncate text-sm font-semibold text-slate-900">
              {workflow.label}
            </h1>
          </div>
        </header>

        <div className="min-h-0 flex-1">{children}</div>
        <WorkspaceArtifactDrawer workflowId={workflow.id} />
      </SidebarInset>
    </SidebarProvider>
  );
}

function WorkspaceShellFallback() {
  return (
    <div
      className="flex h-dvh items-center justify-center text-sm text-slate-500"
      role="status"
    >
      Loading cloud cost reduction…
    </div>
  );
}
