import { withAui } from "@assistant-ui/next";
import path from "node:path";

const nextConfig = {
  transpilePackages: ["@assistant-ui/react", "@assistant-ui/ai-sdk"],
  turbopack: {
    root: path.join(import.meta.dirname, ".."),
  },
  logging: {
    browsertoterminal: true,
    fetches: {
      fullUrl: true,
    },
  },
};

export default withAui(nextConfig);
