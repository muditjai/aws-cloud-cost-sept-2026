import { withAui } from "@assistant-ui/next";
import path from "node:path";
/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ["@assistant-ui/react", "@assistant-ui/ai-sdk"],
  turbopack: {
    root: path.join(import.meta.dirname, ".."),
  },
};

export default withAui(nextConfig);
