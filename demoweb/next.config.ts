import type { NextConfig } from "next";
import { networkInterfaces } from "node:os";
import { resolve } from "node:path";

const repositoryRoot = resolve(process.cwd(), "..");

function getAllowedDevOrigins() {
  const addresses = new Set<string>(["localhost", "127.0.0.1"]);

  for (const network of Object.values(networkInterfaces())) {
    for (const address of network ?? []) {
      if (address.family === "IPv4" && !address.internal) {
        addresses.add(address.address);
      }
    }
  }

  return [...addresses];
}

const nextConfig: NextConfig = {
  allowedDevOrigins: getAllowedDevOrigins(),
  output: "standalone",
  outputFileTracingRoot: repositoryRoot,
  turbopack: {
    root: repositoryRoot,
  },
};

export default nextConfig;
