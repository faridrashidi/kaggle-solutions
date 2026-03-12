import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";

const site = process.env.SITE_URL ?? "https://kaggle.farid.one";

export default defineConfig({
  site,
  output: "static",
  build: {
    format: "preserve",
  },
  integrations: [sitemap()],
});
