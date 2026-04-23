import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { load } from "js-yaml";
import { siteConfig } from "../config/site";

export type SolutionKind = "code" | "description" | "kernel";
export type SolutionTone = "gold" | "silver" | "bronze" | "ink" | "neutral";
export type CompetitionStatus = "curated" | "missing";
export type ReviewState = "curated" | "needs-review" | "missing";

export interface RawSolution {
  rank: string;
  link: string;
  kind: SolutionKind;
}

export interface RawCompetition {
  number: string;
  title: string;
  desc: string;
  kind: string;
  prize: string;
  team: string;
  metric: string;
  link: string;
  image: string;
  year: string;
  isHot: string;
  done: string;
  solutions?: RawSolution[];
}

interface RawCompetitionFile {
  competitions: RawCompetition[];
}

export interface Solution {
  rank: string;
  link: string;
  kind: SolutionKind;
  kindLabel: "Code" | "Write-up" | "Notebook";
  label: string;
  tone: SolutionTone;
  sortRank: number | null;
}

export interface Competition {
  number: number;
  title: string;
  description: string;
  kind: string;
  prize: string;
  team: string;
  teamCount: number | null;
  metric: string;
  link: string;
  image: string;
  year: number;
  isHot: boolean;
  done: boolean;
  status: CompetitionStatus;
  reviewState: ReviewState;
  solutions: Solution[];
  solutionCount: number;
  searchText: string;
}

export interface CompetitionStats {
  total: number;
  curated: number;
  missing: number;
  hot: number;
  firstYear: number;
  latestYear: number;
}

const repoRoot = process.cwd();
const competitionsPath = resolve(repoRoot, "data/competitions.yml");
const publicDir = resolve(repoRoot, "public");

function parseCompetitionFile(): RawCompetitionFile {
  const fileContents = readFileSync(competitionsPath, "utf-8");
  const parsed = load(fileContents);

  if (!parsed || typeof parsed !== "object" || !("competitions" in parsed)) {
    throw new Error("Expected data/competitions.yml to contain a competitions list.");
  }

  return parsed as RawCompetitionFile;
}

function parseBoolean(value: string): boolean {
  return value.trim().toLowerCase() === "true";
}

function parseInteger(value: string): number {
  const parsed = Number.parseInt(value, 10);

  if (Number.isNaN(parsed)) {
    throw new Error(`Expected "${value}" to be a valid integer.`);
  }

  return parsed;
}

function parseTeamCount(value: string): number | null {
  const digits = value.replace(/[^\d]/g, "");

  if (!digits) {
    return null;
  }

  const parsed = Number.parseInt(digits, 10);
  return Number.isNaN(parsed) ? null : parsed;
}

function normalizeImagePath(image: string): string {
  const withoutBasePath = image.replace(/^\/kaggle-solutions(?=\/)/, "");

  return withoutBasePath.replace(/^\/assets\/(images|logos)\//, "/$1/");
}

function isLocalImagePath(image: string): boolean {
  return image.startsWith("/images/") || image.startsWith("/logos/");
}

function validateImagePath(image: string, title: string): string {
  const normalized = normalizeImagePath(image);

  if (!isLocalImagePath(normalized)) {
    return normalized;
  }

  const imageFile = resolve(publicDir, normalized.slice(1));

  if (!existsSync(imageFile)) {
    throw new Error(`Missing local image for "${title}": ${normalized}`);
  }

  return normalized;
}

function buildCompetitionImageUrl(image: string, title: string): string {
  const normalized = validateImagePath(image, title);

  if (normalized.startsWith("/logos/")) {
    return `${siteConfig.competitionImagesBaseUrl}${normalized}`;
  }

  return normalized;
}

function kindLabel(kind: SolutionKind): Solution["kindLabel"] {
  if (kind === "code") {
    return "Code";
  }

  if (kind === "kernel") {
    return "Notebook";
  }

  return "Write-up";
}

function ordinalSuffix(value: number): string {
  const remainder = value % 100;

  if (remainder >= 11 && remainder <= 13) {
    return "th";
  }

  switch (value % 10) {
    case 1:
      return "st";
    case 2:
      return "nd";
    case 3:
      return "rd";
    default:
      return "th";
  }
}

function formatRankLabel(rank: string): string {
  if (rank === "all solutions") {
    return "All solutions";
  }

  if (rank === "?") {
    return "Community pick";
  }

  const numericRank = Number.parseInt(rank, 10);

  if (Number.isNaN(numericRank)) {
    return rank;
  }

  return `${numericRank}${ordinalSuffix(numericRank)} place`;
}

function solutionTone(rank: string): SolutionTone {
  if (rank === "all solutions" || rank === "?") {
    return "neutral";
  }

  const numericRank = Number.parseInt(rank, 10);

  if (numericRank === 1) {
    return "gold";
  }

  if (numericRank === 2) {
    return "silver";
  }

  if (numericRank === 3) {
    return "bronze";
  }

  return "ink";
}

function normalizeSolution(rawSolution: RawSolution): Solution {
  const rank = rawSolution.rank.trim();
  const parsedRank = Number.parseInt(rank, 10);

  return {
    rank,
    link: rawSolution.link.trim(),
    kind: rawSolution.kind,
    kindLabel: kindLabel(rawSolution.kind),
    label: formatRankLabel(rank),
    tone: solutionTone(rank),
    sortRank: Number.isNaN(parsedRank) ? null : parsedRank,
  };
}

function reviewState(done: boolean, solutionCount: number): ReviewState {
  if (done) {
    return "curated";
  }

  if (solutionCount > 0) {
    return "needs-review";
  }

  return "missing";
}

function normalizeCompetition(rawCompetition: RawCompetition): Competition {
  const done = parseBoolean(rawCompetition.done);
  const solutions = (rawCompetition.solutions ?? []).map(normalizeSolution);

  const normalized: Competition = {
    number: parseInteger(rawCompetition.number),
    title: rawCompetition.title.trim(),
    description: rawCompetition.desc.trim(),
    kind: rawCompetition.kind.trim(),
    prize: rawCompetition.prize.trim(),
    team: rawCompetition.team.trim(),
    teamCount: parseTeamCount(rawCompetition.team),
    metric: rawCompetition.metric.trim(),
    link: rawCompetition.link.trim(),
    image: buildCompetitionImageUrl(rawCompetition.image.trim(), rawCompetition.title.trim()),
    year: parseInteger(rawCompetition.year),
    isHot: parseBoolean(rawCompetition.isHot),
    done,
    status: done ? "curated" : "missing",
    reviewState: reviewState(done, solutions.length),
    solutions,
    solutionCount: solutions.length,
    searchText: [
      rawCompetition.title,
      rawCompetition.desc,
      rawCompetition.kind,
      rawCompetition.prize,
      rawCompetition.team,
      rawCompetition.metric,
      rawCompetition.year,
      ...solutions.map((solution) => `${solution.label} ${solution.kindLabel}`),
    ]
      .join(" ")
      .toLowerCase(),
  };

  return normalized;
}

function loadCompetitions(): Competition[] {
  const { competitions: rawCompetitions } = parseCompetitionFile();

  return rawCompetitions
    .map(normalizeCompetition)
    .sort((left, right) => right.number - left.number);
}

function createStats(entries: Competition[]): CompetitionStats {
  const years = entries.map((entry) => entry.year);

  return {
    total: entries.length,
    curated: entries.filter((entry) => entry.done).length,
    missing: entries.filter((entry) => !entry.done).length,
    hot: entries.filter((entry) => entry.isHot).length,
    firstYear: Math.min(...years),
    latestYear: Math.max(...years),
  };
}

export const competitions = loadCompetitions();
export const competitionStats = createStats(competitions);
export const competitionKinds = [...new Set(competitions.map((item) => item.kind))].sort();
export const competitionYears = [...new Set(competitions.map((item) => item.year))].sort(
  (left, right) => right - left,
);
