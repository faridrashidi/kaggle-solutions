import { copyFileSync, existsSync } from "node:fs";

const sitemapIndexPath = new URL("../dist/sitemap-index.xml", import.meta.url);
const sitemapAliasPath = new URL("../dist/sitemap.xml", import.meta.url);

if (existsSync(sitemapIndexPath)) {
  copyFileSync(sitemapIndexPath, sitemapAliasPath);
}
