import type { Metadata } from "next";
import "./globals.css";

import { SetupGuard } from "@/components/SetupGuard";

export const metadata: Metadata = {
  title: "WAGE",
  description: "Pre-application strategy mission control"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-base-bg text-ink-primary font-sans antialiased">
        <SetupGuard>{children}</SetupGuard>
      </body>
    </html>
  );
}
