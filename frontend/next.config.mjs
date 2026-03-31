/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // "standalone" is required for Docker deployments (see frontend/Dockerfile).
  // On Vercel, NEXT_OUTPUT is unset so the standard build output is used instead,
  // which is what Vercel's hosting infrastructure expects.
  ...(process.env.NEXT_OUTPUT === "standalone" ? { output: "standalone" } : {}),
  images: {
    domains: [],
  },
};

export default nextConfig;
