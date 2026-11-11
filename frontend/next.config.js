/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
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
        source: '/geo/:path*',
        destination: `${backendUrl}/geo/:path*`,
      },
      {
        source: '/scenarios/:path*',
        destination: `${backendUrl}/scenarios/:path*`,
      },
      {
        source: '/ledger/:path*',
        destination: `${backendUrl}/ledger/:path*`,
      },
      {
        source: '/policy/:path*',
        destination: `${backendUrl}/policy/:path*`,
      },
      {
        source: '/admin/:path*',
        destination: `${backendUrl}/admin/:path*`,
      },
      {
        source: '/agent-runs/:path*',
        destination: `${backendUrl}/agent-runs/:path*`,
      },
      {
        source: '/runs/:path*',
        destination: `${backendUrl}/runs/:path*`,
      },
      {
        source: '/reports/:path*',
        destination: `${backendUrl}/reports/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
