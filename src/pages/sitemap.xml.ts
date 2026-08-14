import type { APIRoute } from "astro";
import { getCollection } from "astro:content";
import site from "../data/site.json";

export const GET: APIRoute = async () => {
  const posts = await getCollection("posts", ({ data }) => !data.draft);
  const pages = await getCollection("pages");
  const urls = [
    "",
    "/categories",
    ...pages.map((page) => `/${page.slug}`),
    ...posts.map((post) => `/posts/${post.data.wpId}`),
  ];
  const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls
  .map(
    (path) => `  <url><loc>${site.site}${path}</loc></url>`,
  )
  .join("\n")}
</urlset>
`;
  return new Response(body, {
    headers: { "Content-Type": "application/xml; charset=utf-8" },
  });
};
