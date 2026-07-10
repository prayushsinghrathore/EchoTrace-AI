"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/auth-context";

const navItems = [
  { label: "Dashboard", href: "/dashboard", icon: "📊" },
  { label: "Organizations", href: "/organizations", icon: "🏢" },
  { label: "Workspaces", href: "/workspaces", icon: "📁" },
  { label: "Projects", href: "/projects", icon: "📋" },
  { label: "Evidence", href: "/evidence", icon: "📎" },
  { label: "Upload", href: "/evidence/upload", icon: "⬆️" },
  { label: "Investigations", href: "/investigations", icon: "🔍" },
  { label: "AI Engine", href: "/ai", icon: "🤖" },
];

export function SidebarNav() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="flex h-full w-64 flex-col border-r bg-card">
      <div className="flex h-16 items-center gap-2 border-b px-6">
        <div className="h-8 w-8 rounded-lg bg-primary" />
        <span className="text-lg font-semibold">EchoTrace AI</span>
      </div>

      <nav className="flex-1 space-y-1 p-4">
        {navItems.map((item) => {
          const isActive = pathname.startsWith(item.href);
          return (
            <Link key={item.href} href={item.href}>
              <span
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                )}
              >
                <span>{item.icon}</span>
                {item.label}
              </span>
            </Link>
          );
        })}
      </nav>

      <div className="border-t p-4">
        <div className="mb-2 text-xs text-muted-foreground">
          {user?.email}
        </div>
        <Button variant="outline" size="sm" className="w-full" onClick={logout}>
          Sign Out
        </Button>
      </div>
    </aside>
  );
}
