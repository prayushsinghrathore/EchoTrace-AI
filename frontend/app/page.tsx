import Link from "next/link";
import { siteConfig } from "@/config/site";

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="glass sticky top-0 z-50 w-full border-b">
        <div className="container flex h-16 items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-primary" />
            <span className="text-lg font-semibold">{siteConfig.name}</span>
          </div>
          <nav className="flex items-center gap-6">
            <Link
              href="/dashboard"
              className="text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              Dashboard
            </Link>
            <Link
              href={siteConfig.apiUrl.replace("/api/v1", "")}
              className="text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              API
            </Link>
          </nav>
        </div>
      </header>

      <main className="flex-1">
        <section className="container flex min-h-[calc(100vh-4rem)] flex-col items-center justify-center text-center">
          <div className="animate-in space-y-6">
            <div className="inline-flex items-center rounded-full border bg-muted/50 px-4 py-1.5 text-sm">
              <span className="mr-2 h-2 w-2 rounded-full bg-green-500" />
              {siteConfig.environment} mode
            </div>

            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl lg:text-7xl">
              {siteConfig.tagline}
            </h1>

            <p className="mx-auto max-w-2xl text-lg text-muted-foreground sm:text-xl">
              {siteConfig.description}
            </p>

            <div className="flex items-center justify-center gap-4">
              <Link
                href="/dashboard"
                className="inline-flex h-11 items-center justify-center rounded-md bg-primary px-8 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90"
              >
                Get Started
              </Link>
              <Link
                href={`${siteConfig.apiUrl}/health`}
                className="inline-flex h-11 items-center justify-center rounded-md border bg-background px-8 text-sm font-medium shadow-sm transition-colors hover:bg-accent"
              >
                Health Check
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t py-6">
        <div className="container flex flex-col items-center justify-between gap-4 md:flex-row">
          <p className="text-sm text-muted-foreground">
            &copy; {new Date().getFullYear()} {siteConfig.name}. All rights reserved.
          </p>
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span>v0.1.0</span>
            <span>Next.js 15</span>
            <span>FastAPI</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
