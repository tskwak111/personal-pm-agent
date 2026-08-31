import type { NextConfig } from "next";

const apiBaseUrl = process.env.API_INTERNAL_BASE_URL;

const nextConfig: NextConfig = {
  async rewrites() {
    return apiBaseUrl ? [{ source: "/api/:path*", destination: `${apiBaseUrl}/api/:path*` }] : [];
  },
};

export default nextConfig;
