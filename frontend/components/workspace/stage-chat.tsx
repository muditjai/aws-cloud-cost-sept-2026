"use client";

import {
  Thread,
  type ThreadComponents,
} from "@/components/assistant-ui/elements/thread.aui";
import {
  getWorkflow,
  type WorkflowId,
  type WorkflowStep,
} from "@/lib/workflow";
import {
  AssistantRuntimeProvider,
  AuiConfig,
  AuiProvider,
  Suggestions,
  useAui,
} from "@assistant-ui/react";
import { useChatRuntime } from "@assistant-ui/ai-sdk";
import { createContext, Suspense, use, useMemo } from "react";

interface StageChatProps {
  readonly workflowId: WorkflowId;
}

interface ChatRuntimeProps {
  readonly workflow: WorkflowStep;
}

const WorkflowContext = createContext<WorkflowStep | undefined>(undefined);

function WorkflowWelcome() {
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
      <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">
        Move your cloud cost plan forward.
      </h2>
      <p className="mt-3 max-w-lg text-sm leading-6 text-slate-500">
        {workflow.description} Use this cloud cost reduction workflow to give
        the agent context, review its work, and collect evidence as the workflow
        progresses.
      </p>
    </div>
  );
}

const workflowThreadComponents = {
  Welcome: WorkflowWelcome,
} satisfies ThreadComponents;

function StageThread({ workflow }: ChatRuntimeProps) {
  const aui = useAui();
  const config = useMemo(
    () =>
      AuiConfig({
        suggestions: Suggestions([
          {
            title: `Start ${workflow.label.toLowerCase()}`,
            label: "with the information you need from me",
            prompt: `Help me begin the ${workflow.label} phase for my cloud cost workflow. What information do you need?`,
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
        <Thread components={workflowThreadComponents} />
      </AuiProvider>
    </WorkflowContext>
  );
}

function ChatRuntime({ workflow }: ChatRuntimeProps) {
  const runtime = useChatRuntime();

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <StageThread workflow={workflow} />
    </AssistantRuntimeProvider>
  );
}

function StageChatFallback() {
  return (
    <div
      className="flex h-full items-center justify-center text-sm text-slate-500"
      role="status"
    >
      Loading cloud cost reduction assistant…
    </div>
  );
}

export function StageChat({ workflowId }: StageChatProps) {
  const workflow = getWorkflow(workflowId);

  return (
    <Suspense fallback={<StageChatFallback />}>
      <ChatRuntime workflow={workflow} />
    </Suspense>
  );
}
