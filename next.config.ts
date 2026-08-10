import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "placehold.co",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "media.sunnekatha.com",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "d3dazzi8rnwbjc.cloudfront.net",
        pathname: "/**",
      },
    ],
  },
};

export default nextConfig;
