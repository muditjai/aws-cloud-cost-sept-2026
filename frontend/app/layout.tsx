import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Runway | Cloud Cost Workspace",
  description: "An AI-native cloud cost transformation workspace.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="h-dvh">{children}</body>
    </html>
  );
}
