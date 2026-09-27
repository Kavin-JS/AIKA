/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The API base URL is read at request time via process.env in
  // lib/api.ts (server components) rather than baked in here, so it
  // stays a genuine runtime/env-driven value inside Docker Compose
  // rather than a build-time constant.
};

module.exports = nextConfig;
