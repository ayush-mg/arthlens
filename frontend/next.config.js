/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Next's parallel output writers can race on Windows when creating the
  // nested .next route directories. Serializing the build avoids transient
  // EPERM mkdir failures while keeping development/runtime behavior unchanged.
  experimental: {
    cpus: 1,
  },
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
    return [
      {
        source: '/api/v1/:path*',
        destination: `${backendUrl}/:path*`,
      },
      {
        source: '/auth/:path*',
        destination: `${backendUrl}/auth/:path*`,
      },
      {
        source: '/businesses/:path*',
        destination: `${backendUrl}/businesses/:path*`,
      },
      {
        source: '/admin/:path*',
        destination: `${backendUrl}/admin/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
