import type { APIRoute } from 'astro';

export const GET: APIRoute = async () => {
  // Build-time generation. The build timestamp reflects the last successful
  // rebuild, which is what you want for monitoring ("is the site fresh?").
  const now = new Date();
  return new Response(
    JSON.stringify(
      {
        ok: true,
        service: 'kb-site',
        build_iso: now.toISOString(),
        build_unix: Math.floor(now.getTime() / 1000),
      },
      null,
      2
    ),
    {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }
  );
};
