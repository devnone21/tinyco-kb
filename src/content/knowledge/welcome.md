---
title: Welcome to your Knowledge Base
description: Quick orientation and how to add content.
pubDate: 2026-06-22
tags: [meta, getting-started]
---

# Welcome 👋

This is your private knowledge base. Everything behind a Cloudflare Access
gate that requires GitHub or Google login.

## How to add a knowledge article

1. Create a new `.md` (or `.mdx`) file in `src/content/knowledge/`.
2. Add the required frontmatter:
   ```yaml
   ---
   title: My article
   pubDate: 2026-06-22
   tags: [tag1, tag2]
   ---
   ```
3. Rebuild: `./rebuild.sh` (on the host) or `npm run build` locally.
4. Visit the new page at `/kb/my-article`.

## How to add an update

Same idea, but in `src/content/updates/`. The `source` frontmatter field
is freeform — use it to mark automation origin (e.g. `pve-morning-brief`).

## MDX charts

Inside any `.mdx` file:

```mdx
import Chart from '../../components/Chart.astro';

<Chart
  type="line"
  data={{
    labels: ['Mon', 'Tue', 'Wed'],
    datasets: [{ label: 'CPU %', data: [12, 18, 15] }],
  }}
/>
```
