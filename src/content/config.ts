import { defineCollection, z } from 'astro:content';

const knowledge = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    description: z.string().optional(),
    pubDate: z.coerce.date(),
    updated: z.coerce.date().optional(),
    tags: z.array(z.string()).default([]),
    draft: z.boolean().default(false),
  }),
});

const updates = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    pubDate: z.coerce.date(),
    source: z.string().optional(),   // e.g. "pve-morning-brief", "manual"
    severity: z.enum(['info', 'warn', 'alert']).default('info'),
    tags: z.array(z.string()).default([]),
  }),
});

export const collections = { knowledge, updates };
