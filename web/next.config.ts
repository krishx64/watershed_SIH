import type { NextConfig } from "next";
import path from "path";

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
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND_URL.replace(/\/$/, "")}/api/:path*`,
      },
      {
        source: "/demo-data/:site(custom_live[^/]*)/:file*",
        destination: `${BACKEND_URL.replace(/\/$/, "")}/api/images/:site/:file*`,
      },
    ];
  },
};

export default nextConfig;
