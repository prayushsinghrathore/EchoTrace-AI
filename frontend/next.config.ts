import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* ── Build Configuration ──────────────────────────────────────────── */

  // Enable React strict mode for development
  reactStrictMode: true,

  // Output as standalone for Docker deployment
  output: process.env.NODE_ENV === "production" ? "standalone" : undefined,

  /* ── Image Configuration ──────────────────────────────────────────── */
  images: {
    formats: ["image/avif", "image/webp"],
    deviceSizes: [375, 768, 1280, 1536],
    minimumCacheTTL: 60 * 60 * 24, // 24 hours
  },

  /* ── Experimental Features ────────────────────────────────────────── */
  experimental: {
    optimizePackageImports: [
      "lucide-react",
      "@radix-ui/react-dialog",
      "@radix-ui/react-dropdown-menu",
    ],
    turbo: {
      resolveAlias: {
        // Turbo-specific configuration
      },
    },
  },

  /* ── Compiler Options ─────────────────────────────────────────────── */
  compiler: {
    removeConsole: process.env.NODE_ENV === "production",
  },

  /* ── Headers ──────────────────────────────────────────────────────── */
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
