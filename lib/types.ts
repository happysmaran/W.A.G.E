export type OllamaMode = "cloud-free" | "cloud-pro" | "local";

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

export type JobSource = "greenhouse" | "lever" | "ashby" | "company-site" | "board";

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
