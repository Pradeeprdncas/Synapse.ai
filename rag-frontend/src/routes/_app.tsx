import { createFileRoute, Navigate, Outlet, redirect, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { getStoredToken } from "@/lib/api/client";
import { useAuthStore } from "@/store/authStore";
import { Skeleton } from "@/components/common/Primitives";

export const Route = createFileRoute("/_app")({
  beforeLoad: async ({ location }) => {
    if (typeof window === "undefined") return;
    const token = getStoredToken();
    if (!token) {
      throw redirect({ to: "/login", search: { redirect: location.href } });
    }
    const auth = useAuthStore.getState();
    if (auth.status === "idle" || (auth.status === "unauthenticated" && token)) {
      await auth.hydrate();
    }
    if (useAuthStore.getState().status === "unauthenticated") {
      throw redirect({ to: "/login", search: { redirect: location.href } });
    }
  },
  component: AppLayout,
});

function AppLayout() {
  const navigate = useNavigate();
  const status = useAuthStore((s) => s.status);
  const hydrate = useAuthStore((s) => s.hydrate);

  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      void navigate({ to: "/login" });
      return;
    }
    if (status === "idle") void hydrate();
  }, [hydrate, navigate, status]);

  if (status === "loading" || status === "idle") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-6">
        <Skeleton className="h-12 w-64" />
      </div>
    );
  }


  return (
    <div className="flex min-h-screen w-full bg-background text-foreground">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="relative flex-1 overflow-x-hidden">
          <div className="grid-bg pointer-events-none absolute inset-0 -z-10 opacity-40" />
          <div className="mx-auto w-full max-w-[1400px] px-3 py-5 sm:px-6 sm:py-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
