/**
 * Site configuration for EchoTrace AI frontend.
 *
 * Centralized configuration for SEO, navigation, and app metadata.
 * Import from this file rather than hardcoding values.
 */

export type SiteConfig = typeof siteConfig;

const appUrl =
  process.env.NEXT_PUBLIC_APP_URL?.trim() || "http://localhost:3000";

const apiUrl =
  process.env.NEXT_PUBLIC_API_URL?.trim() || "http://localhost:8000/api/v1";

export const siteConfig = {
  name: "EchoTrace AI",
  description:
    "Production-grade traceability and knowledge graph platform powered by AI.",
  tagline: "Trace Everything. Know Anything.",

  url: appUrl,
  apiUrl: apiUrl,

  environment: process.env.NEXT_PUBLIC_ENVIRONMENT?.trim() || "development",

  links: {
    github: "https://github.com/pratyushsinghrathore/echotrace-ai",
    docs: "https://docs.echotrace.ai",
  },

  seo: {
    titleTemplate: "%s | EchoTrace AI",
    defaultTitle: "EchoTrace AI",
    description:
      "Production-grade traceability and knowledge graph platform powered by AI.",
    ogImage: "/og-image.png",
  },
} as const;
