import { withAui } from "@assistant-ui/next";
import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@assistant-ui/react", "@assistant-ui/ai-sdk"],
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
