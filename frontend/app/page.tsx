"use client";

import {
  Thread,
  type ThreadComponents,
} from "@/components/assistant-ui/elements/thread.aui";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  AssistantRuntimeProvider,
  AuiConfig,
  AuiProvider,
  Suggestions,
  useAui,
} from "@assistant-ui/react";
import { useChatRuntime } from "@assistant-ui/ai-sdk";
import {
  Activity,
  BadgeDollarSign,
  CheckCircle2,
  ChevronLeft,
  DatabaseZap,
  FileText,
  FlaskConical,
  Lightbulb,
  PanelRightClose,
  PanelRightOpen,
  Plug,
  Rocket,
  SearchCheck,
  Settings2,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import { createContext, Suspense, use, useMemo, useState } from "react";

type WorkflowId =
  | "connect"
  | "ingest"
  | "audit"
  | "recommend"
  | "create-changes"
  | "test"
  | "deploy"
  | "live-validate"
  | "prove-savings";

interface WorkflowStep {
  readonly id: WorkflowId;
  readonly label: string;
  readonly description: string;
  readonly icon: LucideIcon;
}

interface ThreadWithSuggestionsProps {
  readonly workflow: WorkflowStep;
}

interface ChatWorkspaceProps {
  readonly workflow: WorkflowStep;
}

interface ArtifactPanelProps {
  readonly workflow: WorkflowStep;
  readonly onClose: () => void;
}

const WorkflowContext = createContext<WorkflowStep | undefined>(undefined);

const WORKFLOW_STEPS: readonly WorkflowStep[] = [
  { id: "connect", label: "Connect", description: "Link your cloud environment.", icon: Plug },
  { id: "ingest", label: "Ingest", description: "Collect billing and usage data.", icon: DatabaseZap },
  { id: "audit", label: "Audit", description: "Map spend and technical context.", icon: SearchCheck },
  { id: "recommend", label: "Recommend", description: "Prioritize savings opportunities.", icon: Lightbulb },
  { id: "create-changes", label: "Create Changes", description: "Draft implementation changes.", icon: Wrench },
  { id: "test", label: "Test", description: "Verify functionality and SLAs.", icon: FlaskConical },
  { id: "deploy", label: "Deploy", description: "Ship verified changes.", icon: Rocket },
  { id: "live-validate", label: "Live Validate", description: "Confirm production behavior.", icon: Activity },
  { id: "prove-savings", label: "Prove Savings", description: "Measure the realized outcome.", icon: BadgeDollarSign },
];

const getWorkflowStep = (workflowId: WorkflowId): WorkflowStep => {
  const step = WORKFLOW_STEPS.find((item) => item.id === workflowId);

  if (step === undefined) {
    throw new Error(`Unknown workflow step: ${workflowId}`);
  }

  return step;
};

const WorkflowWelcome = () => {
  const workflow = use(WorkflowContext);

  if (workflow === undefined) {
    throw new Error("WorkflowWelcome must be rendered within WorkflowContext.");
  }

  const WorkflowIcon = workflow.icon;

  return (
    <div className="mb-8 flex max-w-xl flex-col px-2">
      <div className="mb-5 flex size-11 items-center justify-center rounded-xl border border-sky-200 bg-sky-50 text-sky-700 shadow-sm">
        <WorkflowIcon className="size-5" aria-hidden="true" />
      </div>
      <p className="text-xs font-semibold tracking-[0.14em] text-sky-700 uppercase">
        {workflow.label}
      </p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">
        Move your cloud cost plan forward.
      </h1>
      <p className="mt-3 max-w-lg text-sm leading-6 text-slate-500">
        {workflow.description} Use the workspace to give the agent context, review its work, and collect evidence as the engagement progresses.
      </p>
    </div>
  );
};

const WORKFLOW_THREAD_COMPONENTS = {
  Welcome: WorkflowWelcome,
} satisfies ThreadComponents;

const ThreadWithSuggestions = ({ workflow }: ThreadWithSuggestionsProps) => {
  const aui = useAui();
  const config = useMemo(
    () =>
      AuiConfig({
        suggestions: Suggestions([
          {
            title: `Start ${workflow.label.toLowerCase()}`,
            label: "with the information you need from me",
            prompt: `Help me begin the ${workflow.label} phase for my cloud cost engagement. What information do you need?`,
          },
          {
            title: "Show me",
            label: `the expected outcome for ${workflow.label.toLowerCase()}`,
            prompt: `What should the ${workflow.label} phase produce, and how will we validate it?`,
          },
        ]),
      }),
    [workflow],
  );

  return (
    <WorkflowContext value={workflow}>
      <AuiProvider extends={aui} config={config}>
        <Thread components={WORKFLOW_THREAD_COMPONENTS} />
      </AuiProvider>
    </WorkflowContext>
  );
};

const ChatWorkspace = ({ workflow }: ChatWorkspaceProps) => {
  const runtime = useChatRuntime();

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <ThreadWithSuggestions workflow={workflow} />
    </AssistantRuntimeProvider>
  );
};

const ChatWorkspaceFallback = () => (
  <div
    className="flex h-full items-center justify-center text-sm text-slate-500"
    role="status"
  >
    Loading assistant workspace…
  </div>
);

const ArtifactPanel = ({ workflow, onClose }: ArtifactPanelProps) => {
  return (
    <aside className="flex h-full w-full flex-col bg-slate-50/70">
      <div className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 px-5">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">Artifacts</h2>
          <p className="mt-0.5 text-xs text-slate-500">Evidence and agent output</p>
        </div>
        <Button variant="ghost" size="icon-sm" onClick={onClose} aria-label="Close artifacts" title="Close artifacts">
          <ChevronLeft className="size-4" />
        </Button>
      </div>

      <div className="flex flex-1 flex-col gap-5 overflow-y-auto p-5">
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-4">
          <div className="flex items-start gap-3">
            <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
              <FileText className="size-4" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-900">{workflow.label} workspace</p>
              <p className="mt-1 text-xs leading-5 text-slate-500">
                Agent-generated plans, findings, and validation evidence will appear here.
              </p>
            </div>
          </div>
        </div>

        <div>
          <p className="mb-3 text-xs font-semibold tracking-[0.12em] text-slate-500 uppercase">Engagement status</p>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center gap-2 text-sm font-medium text-slate-900">
              <CheckCircle2 className="size-4 text-emerald-600" />
              Workspace ready
            </div>
            <p className="mt-2 text-xs leading-5 text-slate-500">
              Select a phase and send a message to begin generating artifacts.
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
};

export default function Home() {
  const [activeWorkflowId, setActiveWorkflowId] = useState<WorkflowId>("connect");
  const [isArtifactPanelOpen, setIsArtifactPanelOpen] = useState(true);
  const activeWorkflow = getWorkflowStep(activeWorkflowId);

  return (
    <main className="flex h-full min-w-0 overflow-hidden bg-white text-slate-900">
        <aside className="flex w-64 shrink-0 flex-col border-r border-slate-200 bg-slate-950 text-slate-200">
          <div className="flex h-16 items-center gap-3 border-b border-white/10 px-5">
            <div className="flex size-8 items-center justify-center rounded-lg bg-sky-400 text-slate-950 shadow-sm">
              <Settings2 className="size-4" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-semibold text-white">Runway</p>
              <p className="text-xs text-slate-400">Cloud cost workspace</p>
            </div>
          </div>

          <nav className="flex-1 overflow-y-auto px-3 py-5" aria-label="Engagement phases">
            <p className="mb-3 px-2 text-[11px] font-semibold tracking-[0.14em] text-slate-500 uppercase">Engagement</p>
            <div className="space-y-1">
              {WORKFLOW_STEPS.map((step) => {
                const StepIcon = step.icon;
                const isActive = step.id === activeWorkflowId;

                return (
                  <button
                    key={step.id}
                    type="button"
                    onClick={() => setActiveWorkflowId(step.id)}
                    className={`group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition-colors focus-visible:ring-2 focus-visible:ring-sky-300 focus-visible:outline-none ${
                      isActive ? "bg-white/12 text-white shadow-sm" : "text-slate-400 hover:bg-white/6 hover:text-slate-100"
                    }`}
                    aria-current={isActive ? "step" : undefined}
                  >
                    <StepIcon
                      className={`size-4 shrink-0 ${
                        isActive ? "text-sky-300" : "text-slate-500 group-hover:text-slate-300"
                      }`}
                      aria-hidden="true"
                    />
                    <span className="min-w-0 flex-1 truncate">{step.label}</span>
                    {isActive && <span className="size-1.5 rounded-full bg-sky-300" aria-hidden="true" />}
                  </button>
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

        <section className="flex min-w-0 flex-1 flex-col bg-white">
          <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 px-5 sm:px-7">
            <div className="min-w-0">
              <p className="text-xs font-medium text-slate-500">Cloud cost transformation</p>
              <p className="truncate text-sm font-semibold text-slate-900">{activeWorkflow.label}</p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsArtifactPanelOpen((isOpen) => !isOpen)}
              aria-expanded={isArtifactPanelOpen}
              aria-controls="artifact-panel"
            >
              {isArtifactPanelOpen ? <PanelRightClose /> : <PanelRightOpen />}
              Artifacts
            </Button>
          </header>

          <div className="min-h-0 flex-1">
            <Suspense fallback={<ChatWorkspaceFallback />}>
              <ChatWorkspace workflow={activeWorkflow} />
            </Suspense>
          </div>
        </section>

        {isArtifactPanelOpen && (
          <div id="artifact-panel" className="hidden w-80 shrink-0 border-l border-slate-200 lg:block">
            <ArtifactPanel workflow={activeWorkflow} onClose={() => setIsArtifactPanelOpen(false)} />
          </div>
        )}
    </main>
  );
}
