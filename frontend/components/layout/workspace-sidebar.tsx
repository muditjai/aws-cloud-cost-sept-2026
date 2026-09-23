import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { cn } from "@/lib/utils";
import { workflowSteps, type WorkflowId } from "@/lib/workflow";
import { Settings2 } from "lucide-react";
import Link from "next/link";

interface WorkspaceSidebarProps {
  readonly activeWorkflowId: WorkflowId;
}

export function WorkspaceSidebar({ activeWorkflowId }: WorkspaceSidebarProps) {
  return (
    <Sidebar
      collapsible="offcanvas"
      className="border-r border-slate-200 [&_[data-slot=sidebar-inner]]:bg-slate-950 [&_[data-slot=sidebar-inner]]:text-slate-200"
    >
      <SidebarHeader className="h-16 justify-center border-b border-white/10 px-5">
        <div className="flex items-center gap-3">
          <div className="flex size-8 items-center justify-center rounded-lg bg-sky-400 text-slate-950 shadow-sm">
            <Settings2 className="size-4" aria-hidden="true" />
          </div>
          <div>
            <p className="text-sm font-semibold text-white">Migracle AI</p>
            <p className="text-xs text-slate-400">Cloud cost workspace</p>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup className="py-5">
          <SidebarGroupLabel className="px-3 text-slate-500">
            Workflow stages
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {workflowSteps.map((step) => {
                const StepIcon = step.icon;
                const isActive = step.id === activeWorkflowId;

                return (
                  <SidebarMenuItem key={step.id}>
                    <SidebarMenuButton
                      asChild
                      isActive={isActive}
                      tooltip={step.label}
                      className={cn(
                        "h-10 gap-3 px-3 text-slate-400 hover:bg-white/6 hover:text-slate-100",
                        "data-[active=true]:bg-white/12 data-[active=true]:text-white",
                      )}
                    >
                      <Link
                        href={`/${step.id}`}
                        aria-current={isActive ? "page" : undefined}
                      >
                        <StepIcon
                          className={cn(
                            "size-4 shrink-0",
                            isActive
                              ? "text-sky-300"
                              : "text-slate-500 group-hover/menu-button:text-slate-300",
                          )}
                          aria-hidden="true"
                        />
                        <span>{step.label}</span>
                        {isActive ? (
                          <span
                            className="ml-auto size-1.5 rounded-full bg-sky-300"
                            aria-hidden="true"
                          />
                        ) : null}
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t border-white/10 p-4">
        <div className="flex items-center gap-3 rounded-lg px-2 py-1.5">
          <Avatar size="sm">
            <AvatarFallback className="bg-slate-700 text-slate-100">
              AC
            </AvatarFallback>
          </Avatar>
          <div className="min-w-0">
            <p className="truncate text-xs font-medium text-slate-200">
              Acme Cloud
            </p>
            <p className="truncate text-xs text-slate-500">
              Cost transformation
            </p>
          </div>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
