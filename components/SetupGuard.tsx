"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { api } from "@/lib/api";

export function SetupGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    // If we're already on the setup page, just render it immediately.
    if (pathname === "/setup") {
      setIsReady(true);
      return;
    }

    let mounted = true;
    api
      .getSetupStatus()
      .then((status) => {
        if (!mounted) return;
        if (status.needs_setup) {
          router.replace("/setup");
        } else {
          setIsReady(true);
        }
      })
      .catch((err) => {
        // If the backend isn't ready yet, we might want to poll or just assume it's loading.
        // For now, just allow render, or wait. If we fail, maybe the backend is booting.
        console.error("Failed to check setup status:", err);
        if (mounted) setIsReady(true); 
      });

    return () => {
      mounted = false;
    };
  }, [pathname, router]);

  if (!isReady) {
    return (
      <div className="min-h-screen bg-base-bg flex flex-col items-center justify-center">
        <p className="text-[11px] font-mono uppercase tracking-wideish text-ink-muted animate-pulse">
          Initializing W.A.G.E.
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
