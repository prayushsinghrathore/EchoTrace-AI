"use client";

import { ProtectedRoute } from "@/components/shared/protected-route";
import { SidebarNav } from "@/components/shared/sidebar-nav";
import { type ReactNode } from "react";

export default function NotificationsLayout({ children }: { children: ReactNode }) {
  return (
    <ProtectedRoute>
      <div className="flex h-screen overflow-hidden">
        <SidebarNav />
        <main className="flex-1 overflow-y-auto bg-background p-8">{children}</main>
      </div>
    </ProtectedRoute>
  );
}
