import type { NextConfig } from "next";
import path from "path";

// Static export mode is used only by the Docker image build
// (NEXT_STATIC_EXPORT=1), where the Python API server serves the export and
// handles /api/* itself. Static exports do not support `rewrites()`, so the
// local dev proxy is omitted in that mode.
const isStaticExport = process.env.NEXT_STATIC_EXPORT === "1";

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
              destination: "http://127.0.0.1:8000/api/:path*",
            },
          ];
        },
      }),
};

export default nextConfig;
