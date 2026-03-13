import { execSync } from "node:child_process";

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "long",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});

const resolveLastUpdated = () => {
  try {
    const lastCommitDate = execSync("git log -1 --format=%cI", {
      encoding: "utf8",
    }).trim();

    if (lastCommitDate) {
      return dateFormatter.format(new Date(lastCommitDate));
    }
  } catch {
    // Fall back to the current date when git metadata is unavailable.
  }

  return dateFormatter.format(new Date());
};

export const siteConfig = {
  title: "Kaggle Solutions",
  description:
    "A curated archive of Kaggle competition write-ups, codebases, notebooks, interviews, and learning resources.",
  author: "Farid Rashidi",
  authorUrl: "https://farid.one",
  repositoryUrl: "https://github.com/faridrashidi/kaggle-solutions",
  keywords: [
    "Kaggle",
    "machine learning",
    "data science",
    "competition solutions",
    "winning solutions",
    "notebooks",
  ],
  lastUpdated: resolveLastUpdated(),
  ogImage: "/assets/images/logo.png",
  competitionImagesBaseUrl:
    "https://cdn.jsdelivr.net/gh/faridrashidi/kaggle-solutions@main/public",
  resourceCards: [
    {
      href: "/resources/videos.html",
      title: "Top Kagglers Interviews",
      summary:
        "Talks, panel discussions, and long-form interviews with competition veterans and grandmasters.",
    },
    {
      href: "/resources/kernels.html",
      title: "Kernels of The Week",
      summary:
        "A lightweight archive of standout Kaggle notebooks and tutorials worth revisiting.",
    },
    {
      href: "/resources/symbols.html",
      title: "Legend and Symbols",
      summary:
        "Badge meanings, curation rules, and a quick guide to how solution links are categorized.",
    },
  ],
} as const;

export type ResourceCard = (typeof siteConfig.resourceCards)[number];
