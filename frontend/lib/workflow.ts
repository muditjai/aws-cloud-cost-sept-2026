import {
  Activity,
  BadgeDollarSign,
  DatabaseZap,
  FlaskConical,
  Lightbulb,
  Plug,
  Rocket,
  SearchCheck,
  Wrench,
  type LucideIcon,
} from "lucide-react";

const workflowIds = [
  "connect",
  "ingest",
  "audit",
  "recommend",
  "create-changes",
  "test",
  "deploy",
  "live-validate",
  "prove-savings",
] as const;

export type WorkflowId = (typeof workflowIds)[number];

export interface WorkflowStep {
  readonly id: WorkflowId;
  readonly label: string;
  readonly description: string;
  readonly icon: LucideIcon;
}

export const workflowSteps = [
  { id: "connect", label: "Connect", description: "Link your cloud environment.", icon: Plug },
  { id: "ingest", label: "Ingest", description: "Collect billing and usage data.", icon: DatabaseZap },
  { id: "audit", label: "Audit", description: "Map spend and technical context.", icon: SearchCheck },
  { id: "recommend", label: "Recommend", description: "Prioritize savings opportunities.", icon: Lightbulb },
  { id: "create-changes", label: "Create Changes", description: "Draft implementation changes.", icon: Wrench },
  { id: "test", label: "Test", description: "Verify functionality and SLAs.", icon: FlaskConical },
  { id: "deploy", label: "Deploy", description: "Ship verified changes.", icon: Rocket },
  { id: "live-validate", label: "Live Validate", description: "Confirm production behavior.", icon: Activity },
  { id: "prove-savings", label: "Prove Savings", description: "Measure the realized outcome.", icon: BadgeDollarSign },
] as const satisfies readonly WorkflowStep[];

export function getWorkflow(workflowId: WorkflowId) {
  const workflow = workflowSteps.find((step) => step.id === workflowId);

  if (workflow === undefined) {
    throw new Error(`Unknown workflow step: ${workflowId}`);
  }

  return workflow;
}

export function getWorkflowFromPathname(pathname: string) {
  const workflowId = pathname.split("/").filter(Boolean)[0];
  const workflow = workflowSteps.find((step) => step.id === workflowId);

  return workflow ?? workflowSteps[0];
}
