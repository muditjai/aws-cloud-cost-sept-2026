import type { Metadata } from "next";
import { WorkspaceShell } from "@/components/layout/workspace-shell";
import { Suspense } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "Migracle AI | Cloud Cost Workspace",
  description: "An AI-native cloud cost transformation workspace.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <Suspense fallback={<WorkspaceShellFallback />}>
          <WorkspaceShell>{children}</WorkspaceShell>
        </Suspense>
      </body>
    </html>
  );
}

function WorkspaceShellFallback() {
  return (
    <div className="flex h-dvh items-center justify-center text-sm text-slate-500" role="status">
      Loading workspace…
    </div>
  );
}
