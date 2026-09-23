import type { Metadata } from "next";
import { WorkspaceShell } from "@/components/layout/workspace-shell";
import "./globals.css";

export const metadata: Metadata = {
  title: "Migracle AI | Cloud Cost Reduction",
  description: "An AI-native cloud cost reduction service.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <WorkspaceShell>{children}</WorkspaceShell>
      </body>
    </html>
  );
}
