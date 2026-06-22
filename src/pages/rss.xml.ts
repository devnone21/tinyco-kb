import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';
import type { APIContext } from 'astro';

export async function GET(context: APIContext) {
  const updates = (await getCollection('updates'))
    .sort((a, b) => +b.data.pubDate - +a.data.pubDate);

  return rss({
    title: "Tony's KB — Updates",
    description: 'Latest updates from the knowledge base and homelab automations.',
    site: context.site!,
    items: updates.map((entry) => ({
      title: `[${entry.data.severity ?? 'info'}] ${entry.data.title}`,
      pubDate: entry.data.pubDate,
      description: entry.data.source
        ? `source: ${entry.data.source}`
        : 'manual entry',
      link: `/updates/${entry.slug}/`,
      categories: entry.data.tags,
    })),
    customData: '<language>en-us</language>',
  });
}
