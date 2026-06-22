# Tony's Knowledge Base

A static, self-hosted knowledge base + updates feed built with Astro.

## Stack
- **Astro 5** (static output) + **MDX** for content
- **Pagefind** for full-text search
- **nginx alpine** to serve static files (in Docker)
- **Cloudflare Tunnel** for HTTPS exposure
- **Cloudflare Access** for GitHub/Google OAuth login + email allowlist

## Project layout
```
kb-site/
├── src/
│   ├── content/
│   │   ├── knowledge/         # long-form articles (manual)
│   │   └── updates/           # short updates (script-generated OK)
│   ├── layouts/Base.astro
│   ├── components/
│   │   ├── Nav.astro
│   │   ├── Footer.astro
│   │   ├── Chart.astro        # MDX chart component (Chart.js)
│   │   └── Search.astro       # Pagefind UI
│   ├── styles/global.css
│   └── pages/
│       ├── index.astro
│       ├── kb/[index|[...slug]].astro
│       ├── updates/[index|[...slug]].astro
│       └── search.astro
├── public/
├── Dockerfile                 # multi-stage: build + serve
├── docker-compose.yml
├── nginx.conf
└── rebuild.sh                 # rebuild & restart on content change
```

## Local dev
```bash
npm install
npm run dev                   # http://localhost:4321
```

## Build & run
```bash
npm run build                 # → dist/ (static + pagefind index)
docker compose up -d --build  # serves dist/ via nginx on :8080
```

## Deploy on Proxmox LXC `docker`
See [DEPLOY.md](DEPLOY.md).

## Cloudflare Access setup
See top-level guide (one-time dashboard config). No code changes needed.
