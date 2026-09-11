export type OllamaMode = "local" | "cloud";

export interface DiscoverResult {
  title: string;
  url: string;
  snippet: string;
}

export interface EmbeddingStatus {
  status: "not_started" | "loading" | "ready" | "error";
  error: string | null;
}

export interface OllamaStatus {
  mode: OllamaMode;
  model: string;
  connected: boolean;
}

export interface Persona {
  id: string;
  name: string;
  salaryFloor: number;
  workModes: WorkMode[];
  excludedIndustries: string[];
}

export type WorkMode = "remote" | "hybrid" | "onsite";

export type FeedSource = "greenhouse" | "lever" | "ashby";

export interface JobFeed {
  id: string;
  personaId: string;
  source: FeedSource;
  identifier: string;
  label: string;
  keywords: string;
  enabled: boolean;
  createdAt?: string;
  lastPolledAt?: string;
  lastStatus: string;
}

export interface FeedItem {
  id: string;
  feedId: string;
  personaId: string;
  title: string;
  company: string;
  url: string;
  sourceLabel: string;
  firstSeenAt?: string;
  status: "new" | "imported" | "dismissed";
}

export interface FeedPollStatus {
  enabled: boolean;
  intervalSeconds: number;
  running: boolean;
  lastRunAt?: string;
  lastError?: string;
  feedsTotal: number;
  feedsEnabled: number;
  itemsNew: number;
}

export type JobSource = "pasted" | "discovered";

export interface BackendSettings {
  mode: OllamaMode;
  base_url: string;
  api_key: string | null;
  model: string;
  num_ctx: number;
  mock_llm: boolean;
}

export interface GapItem {
  id: string;
  label: string;
  severity: "blocker" | "minor";
}

export interface MatchItem {
  id: string;
  label: string;
}

export interface Job {
  id: string;
  personaId: string;
  title: string;
  company: string;
  source: JobSource;
  sourceLabel: string;
  score: number;
  tag: string;
  status: JobStatus;
  matches: MatchItem[];
  gaps: GapItem[];
  bulletBefore: string;
  bulletAfter: string;
  outreachDraft: string;
  appliedAt?: string;
}

export type JobStatus = "inbox" | "reviewing" | "applied" | "archived";

export type BattleRoomTab = "tailoring" | "outreach";
