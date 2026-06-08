import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      // Notion 파일 업로드 (S3 presigned URL)
      {
        protocol: "https",
        hostname: "prod-files-secure.s3.us-west-2.amazonaws.com",
      },
      {
        protocol: "https",
        hostname: "s3.us-west-2.amazonaws.com",
      },
      // 일반 AWS S3 (모든 리전)
      {
        protocol: "https",
        hostname: "**.amazonaws.com",
      },
      // 기타 외부 이미지
      {
        protocol: "https",
        hostname: "images.unsplash.com",
      },
      {
        protocol: "https",
        hostname: "**.notion.so",
      },
    ],
  },
};

export default nextConfig;
