"use client";

import { ProtectedRoute } from "@/components/shared/protected-route";
import { SidebarNav } from "@/components/shared/sidebar-nav";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode } from "react";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
});

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <ProtectedRoute>
      <QueryClientProvider client={queryClient}>
        <div className="flex h-screen overflow-hidden">
          <SidebarNav />
          <main className="flex-1 overflow-y-auto bg-background p-8">{children}</main>
        </div>
      </QueryClientProvider>
    </ProtectedRoute>
  );
}
