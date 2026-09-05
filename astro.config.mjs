import { defineConfig, fontProviders } from "astro/config";
import sitemap from "@astrojs/sitemap";

const site = process.env.SITE_URL ?? "https://kaggle.farid.one";

export default defineConfig({
  site,
  output: "static",
  compressHTML: true,
  build: {
    format: "preserve",
    inlineStylesheets: "always",
  },
  fonts: [
    {
      provider: fontProviders.google(),
      name: "Inter",
      cssVariable: "--font-inter",
      weights: ["400 800"],
      styles: ["normal"],
      display: "optional",
    },
  ],
  integrations: [sitemap({ filter: (page) => !page.endsWith("/archive") })],
});
