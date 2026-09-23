import { Button } from "@/components/ui/button";

interface StagePageProps {
  readonly title: string;
}

export function StagePage({ title }: StagePageProps) {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-6 bg-background px-6 text-center text-foreground">
      <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
      <Button type="button">Start</Button>
    </main>
  );
}
