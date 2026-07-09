/**
 * Site configuration for EchoTrace AI frontend.
 *
 * Centralized configuration for SEO, navigation, and app metadata.
 * Import from this file rather than hardcoding values.
 */

export type SiteConfig = typeof siteConfig;

export const siteConfig = {
  name: "EchoTrace AI",
  description:
    "Production-grade traceability and knowledge graph platform powered by AI.",
  tagline: "Trace Everything. Know Anything.",

  url: process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000",
  apiUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1",

  environment: process.env.NEXT_PUBLIC_ENVIRONMENT ?? "development",

  links: {
    github: "https://github.com/echotrace-ai/echotrace",
    docs: "https://docs.echotrace.ai",
  },

  nav: {
    main: [
      {
        label: "Dashboard",
        href: "/dashboard",
        icon: "LayoutDashboard",
      },
      {
        label: "Graph",
        href: "/graph",
        icon: "GitBranch",
      },
      {
        label: "Traces",
        href: "/traces",
        icon: "Search",
      },
    ],
  },

  seo: {
    titleTemplate: "%s | EchoTrace AI",
    defaultTitle: "EchoTrace AI",
    description:
      "Production-grade traceability and knowledge graph platform powered by AI.",
    ogImage: "/og-image.png",
  },
} as const;
