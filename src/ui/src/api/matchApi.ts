// API client for match endpoints

import type {
  Match,
  MatchListResponse,
  StatsSummary,
  NotUploadedCategories,
  ScoreDistribution
} from '../types/match';

// 동적 API URL: 현재 호스트 기반으로 API 서버 주소 결정
const API_BASE = `http://${window.location.hostname}:8001/api`;

// Stats API
export async function fetchStatsSummary(): Promise<StatsSummary> {
  const res = await fetch(`${API_BASE}/stats/summary`);
  if (!res.ok) throw new Error('Failed to fetch stats');
  return res.json();
}

export async function fetchNotUploadedCategories(): Promise<NotUploadedCategories> {
  const res = await fetch(`${API_BASE}/stats/not-uploaded-categories`);
  if (!res.ok) throw new Error('Failed to fetch categories');
  return res.json();
}

export async function fetchScoreDistribution(bins = 10): Promise<ScoreDistribution> {
  const res = await fetch(`${API_BASE}/stats/score-distribution?bins=${bins}`);
  if (!res.ok) throw new Error('Failed to fetch distribution');
  return res.json();
}

// Matches API
export interface MatchFilters {
  page?: number;
  limit?: number;
  status?: string;
  score_min?: number;
  score_max?: number;
  search?: string;
}

export async function fetchMatches(filters: MatchFilters = {}): Promise<MatchListResponse> {
  const params = new URLSearchParams();
  if (filters.page) params.set('page', String(filters.page));
  if (filters.limit) params.set('limit', String(filters.limit));
  if (filters.status) params.set('status', filters.status);
  if (filters.score_min !== undefined) params.set('score_min', String(filters.score_min));
  if (filters.score_max !== undefined) params.set('score_max', String(filters.score_max));
  if (filters.search) params.set('search', filters.search);

  const res = await fetch(`${API_BASE}/matches?${params}`);
  if (!res.ok) throw new Error('Failed to fetch matches');
  return res.json();
}

export async function fetchMatch(id: number): Promise<Match> {
  const res = await fetch(`${API_BASE}/matches/${id}`);
  if (!res.ok) throw new Error('Failed to fetch match');
  return res.json();
}

export async function updateMatch(
  id: number,
  update: { match_status?: string; youtube_video_id?: string; youtube_title?: string }
): Promise<Match> {
  const res = await fetch(`${API_BASE}/matches/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(update)
  });
  if (!res.ok) throw new Error('Failed to update match');
  return res.json();
}

export async function bulkUpdateMatches(
  ids: number[],
  status: string,
  notes?: string
): Promise<{ updated: number; status: string }> {
  const res = await fetch(`${API_BASE}/matches/bulk-update`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids, status, notes })
  });
  if (!res.ok) throw new Error('Failed to bulk update');
  return res.json();
}

// Export API
export function getExportUrl(type: 'report' | 'not-uploaded', format: 'json' | 'csv' = 'json') {
  return `${API_BASE}/export/${type}?format=${format}`;
}
