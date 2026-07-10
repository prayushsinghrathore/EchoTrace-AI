# ⚡ EchoTrace AI — Frontend Performance Guide

Performance optimization guidance for the Next.js frontend.

---

## Current Configuration

The Next.js app is already configured with:

- **Standalone output** for optimized Docker deployment (`output: "standalone"`)
- **Image optimization** with AVIF/WebP formats
- **Optimized package imports** for React component libraries

---

## Bundle Optimization

### Code Splitting

The Next.js App Router automatically handles route-based code splitting. Dynamic imports should be used for heavy components:

```typescript
// Recommended for large visualization libraries
const GraphViewer = dynamic(() => import("@/components/features/GraphViewer"), {
  loading: () => <GraphSkeleton />,
  ssr: false,
});

const ThreeScene = dynamic(() => import("@/components/features/ThreeScene"), {
  ssr: false,
});
```

### Package Import Optimization

Already configured in `next.config.ts`:

```typescript
experimental: {
  optimizePackageImports: [
    "lucide-react",           // Icon library
    "@radix-ui/react-dialog",
    "@radix-ui/react-dropdown-menu",
  ],
}
```

### Tree Shaking

Ensure imports are specific (not barrel files):

```typescript
// ✅ Good — tree-shakable
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";

// ❌ Avoid — pulls in unused components
import * from "@/components/ui";
```

---

## Asset Optimization

### Image Optimization

Next.js Image component is preferred over `<img>`:

```typescript
import Image from "next/image";

// ✅ Automatic optimization, lazy loading, responsive sizes
<Image
  src="/evidence/screenshot.png"
  alt="Evidence screenshot"
  width={1200}
  height={800}
  priority={false}           // Lazy load by default
  placeholder="blur"         // Show blur-up placeholder
/>
```

### Font Loading

```typescript
// Use next/font for optimized font loading
import { Inter } from "next/font/google";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",           // Prevent FOIT
  variable: "--font-inter",  // CSS variable
});
```

### Static Assets

- Place static files in `public/` directory
- Use `.svg` files for icons (lucide-react handles this)
- Optimize raster images before adding to `public/`

---

## Rendering Strategy

### App Router Patterns

```typescript
// Server Components (default) — ideal for data fetching
async function EvidenceList() {
  const data = await fetchEvidence(); // Runs on server
  return <div>{/* render */}</div>;
}

// Client Components — only when interactivity is needed
"use client";
function EvidenceActions() {
  const [loading, setLoading] = useState(false);
  // ...
}
```

### Streaming & Suspense

```typescript
import { Suspense } from "react";

// Stream content as it becomes available
<Suspense fallback={<LoadingSkeleton />}>
  <SlowComponent />
</Suspense>
```

---

## Lighthouse Targets

| Metric | Target |
|--------|--------|
| Performance Score | > 90 |
| First Contentful Paint (FCP) | < 1.5s |
| Largest Contentful Paint (LCP) | < 2.5s |
| Time to Interactive (TTI) | < 3.5s |
| Cumulative Layout Shift (CLS) | < 0.1 |
| First Input Delay (FID) | < 100ms |

---

## Bundle Size Budgets

| Asset | Budget |
|-------|--------|
| Initial JS (gzipped) | < 150 KB |
| Initial CSS | < 20 KB |
| Total page JS (gzipped) | < 300 KB |
| Font files | < 50 KB |

### Checking Bundle Size

```bash
# Analyze bundle
npm run build
npx next-bundle-analyzer

# Check individual page sizes
du -sh .next/static/chunks/pages/
```

---

## Performance Monitoring

### Web Vitals

```typescript
// Track Core Web Vitals
export function reportWebVitals(metric: any) {
  console.log(metric);
  // Send to analytics:
  // fetch("/api/v1/analytics/web-vitals", { method: "POST", body: JSON.stringify(metric) });
}
```

### Real User Monitoring (RUM)

Consider adding:
- Next.js Analytics (Vercel)
- Sentry Performance
- OpenTelemetry RUM instrumentation

---

## Development Best Practices

```bash
# Build with production optimization
npm run build -- --debug

# Check for unused exports
npx next-unused

# Audit dependencies
npm audit

# Check bundle
next build && npx next-bundle-analyzer
```

---

## References

- [Next.js Optimization Docs](https://nextjs.org/docs/app/building-your-application/optimizing)
- [Web Vitals](https://web.dev/vitals/)
- [Monitoring Guide](monitoring.md)
- [Performance Baselines](performance-baseline.md)
