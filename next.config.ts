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
        hostname: "sunnekatha-prod-media-533463644243-ap-south-1.s3.amazonaws.com",
        pathname: "/**",
      },
    ],
  },
};

export default nextConfig;
