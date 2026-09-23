import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
import { workflowSteps, type WorkflowId } from "@/lib/workflow";
import Link from "next/link";
import { Settings2 } from "lucide-react";

interface WorkspaceSidebarProps {
  readonly activeWorkflowId: WorkflowId;
}

export function WorkspaceSidebar({ activeWorkflowId }: WorkspaceSidebarProps) {
  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-slate-200 bg-slate-950 text-slate-200">
      <div className="flex h-16 items-center gap-3 border-b border-white/10 px-5">
        <div className="flex size-8 items-center justify-center rounded-lg bg-sky-400 text-slate-950 shadow-sm">
          <Settings2 className="size-4" aria-hidden="true" />
        </div>
        <div>
          <p className="text-sm font-semibold text-white">Migracle AI</p>
          <p className="text-xs text-slate-400">Cloud cost workspace</p>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-5" aria-label="Workflow stages">
        <div className="flex flex-col gap-1">
          {workflowSteps.map((step) => {
            const StepIcon = step.icon;
            const isActive = step.id === activeWorkflowId;

            return (
              <Link
                key={step.id}
                href={`/${step.id}`}
                className={cn(
                  "group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition-colors focus-visible:ring-2 focus-visible:ring-sky-300 focus-visible:outline-none",
                  isActive
                    ? "bg-white/12 text-white shadow-sm"
                    : "text-slate-400 hover:bg-white/6 hover:text-slate-100",
                )}
                aria-current={isActive ? "page" : undefined}
              >
                <StepIcon
                  className={cn(
                    "size-4 shrink-0",
                    isActive
                      ? "text-sky-300"
                      : "text-slate-500 group-hover:text-slate-300",
                  )}
                  aria-hidden="true"
                />
                <span className="min-w-0 flex-1 truncate">{step.label}</span>
                {isActive ? (
                  <span className="size-1.5 rounded-full bg-sky-300" aria-hidden="true" />
                ) : null}
              </Link>
            );
          })}
        </div>
      </nav>

      <div className="border-t border-white/10 p-4">
        <div className="flex items-center gap-3 rounded-lg px-2 py-1.5">
          <Avatar size="sm">
            <AvatarFallback className="bg-slate-700 text-slate-100">AC</AvatarFallback>
          </Avatar>
          <div className="min-w-0">
            <p className="truncate text-xs font-medium text-slate-200">Acme Cloud</p>
            <p className="truncate text-xs text-slate-500">Cost transformation</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
