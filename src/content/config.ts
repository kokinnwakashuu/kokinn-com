import { defineCollection, z } from "astro:content";

const posts = defineCollection({
  type: "content",
  schema: z.object({
    title: z.string(),
    description: z.string(),
    pubDate: z.string(),
    updatedDate: z.string().optional(),
    categories: z.array(z.string()).default([]),
    categorySlugs: z.array(z.string()).default([]),
    tags: z.array(z.string()).default([]),
    heroImage: z.string().optional(),
    wpId: z.number(),
    draft: z.boolean().default(false),
  }),
});

const pages = defineCollection({
  type: "content",
  schema: z.object({
    title: z.string(),
    description: z.string(),
    wpId: z.number(),
    menuOrder: z.number().default(0),
  }),
});

export const collections = { posts, pages };
