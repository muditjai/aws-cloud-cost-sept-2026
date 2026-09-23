import { withAui } from "@assistant-ui/next";
import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  cacheComponents: true,
  allowedDevOrigins: ["127.0.0.1"],
  transpilePackages: ["@assistant-ui/react", "@assistant-ui/ai-sdk"],
  async redirects() {
    return [
      {
        source: "/",
        destination: "/connect",
        permanent: false,
      },
    ];
  },
  turbopack: {
    root: path.join(import.meta.dirname, ".."),
  },
  logging: {
    browserToTerminal: true,
    fetches: {
      fullUrl: true,
    },
  },
};

export default withAui(nextConfig);
