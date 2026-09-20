import type { NextConfig } from "next";
import path from "path";

// Static export mode is used only by the Docker image build
// (NEXT_STATIC_EXPORT=1), where the Python API server serves the export and
// handles /api/* itself. Static exports do not support `rewrites()`, so the
// local dev proxy is omitted in that mode.
const isStaticExport = process.env.NEXT_STATIC_EXPORT === "1";

const BACKEND_URL = (
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  process.env.BACKEND_URL ||
  "http://127.0.0.1:8000"
)
  .trim()
  .replace(/\/$/, "");

const nextConfig: NextConfig = {
  turbopack: {
    root: path.join(__dirname),
  },
  ...(isStaticExport
    ? { output: "export" as const }
    : {
        async rewrites() {
          return [
            {
              source: "/api/:path*",
              destination: `${BACKEND_URL}/api/:path*`,
            },
            {
              source: "/demo-data/:site(custom_live[^/]*)/:file*",
              destination: `${BACKEND_URL}/api/images/:site/:file*`,
            },
          ];
        },
      }),
};

export default nextConfig;
