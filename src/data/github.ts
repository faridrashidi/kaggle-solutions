import { siteConfig } from "../config/site";

interface GithubRepositoryApiResponse {
  stargazers_count?: number;
}

export interface GithubRepositoryStats {
  starCount: number | null;
  formattedStarCount: string | null;
}

const numberFormatter = new Intl.NumberFormat("en-US");

const resolveRepositoryPath = () => {
  try {
    const repositoryUrl = new URL(siteConfig.repositoryUrl);
    const segments = repositoryUrl.pathname.replace(/^\/+|\/+$/g, "").split("/");

    if (segments.length >= 2) {
      return {
        owner: segments[0],
        repo: segments[1].replace(/\.git$/, ""),
      };
    }
  } catch {
    // Ignore invalid repository URLs and fall back to an empty response.
  }

  return null;
};

const repositoryPath = resolveRepositoryPath();
const repositoryApiUrl = repositoryPath
  ? `https://api.github.com/repos/${repositoryPath.owner}/${repositoryPath.repo}`
  : null;

let githubRepositoryStatsPromise: Promise<GithubRepositoryStats> | null = null;

const fetchGithubRepositoryStats = async (): Promise<GithubRepositoryStats> => {
  if (!repositoryApiUrl) {
    return {
      starCount: null,
      formattedStarCount: null,
    };
  }

  try {
    const response = await fetch(repositoryApiUrl, {
      headers: {
        Accept: "application/vnd.github+json",
        "User-Agent": "kaggle-solutions-site",
      },
    });

    if (!response.ok) {
      throw new Error(`GitHub API request failed with ${response.status}`);
    }

    const repository = (await response.json()) as GithubRepositoryApiResponse;

    if (typeof repository.stargazers_count === "number") {
      return {
        starCount: repository.stargazers_count,
        formattedStarCount: numberFormatter.format(repository.stargazers_count),
      };
    }
  } catch {
    // Keep the header usable even when the GitHub API is unavailable.
  }

  return {
    starCount: null,
    formattedStarCount: null,
  };
};

export const getGithubRepositoryStats = () => {
  githubRepositoryStatsPromise ??= fetchGithubRepositoryStats();
  return githubRepositoryStatsPromise;
};
