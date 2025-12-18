import axios from 'axios';
import type {
  OverviewStats,
  YearStats,
  RegionStats,
  Pattern,
  PatternTestResult,
  Region,
  EventType,
  NasFile,
  AssetGroup,
  AssetGroupDetail,
  PaginatedResponse,
  ExclusionRule,
  ExclusionRuleCreate,
  ExclusionRuleUpdate,
  ExclusionRuleListResponse,
  Category,
  CategoryEntry,
  CategoryEntryDetail,
  KPIStats,
} from '../types';

const api = axios.create({
  baseURL: '/api',
});

// Stats API
export interface MatchingSummary {
  total_nas_groups: number;
  total_pokergo_episodes: number;
  MATCHED: number;
  NAS_ONLY_HISTORIC: number;
  NAS_ONLY_MODERN: number;
  POKERGO_ONLY: number;
}

export interface SyncStatus {
  origin_files: number;
  archive_files: number;
  origin_primary: number;
  archive_primary: number;
  shared_groups: number;
  origin_only_groups: number;
  archive_only_groups: number;
  has_role_conflict: boolean;
}

export const statsApi = {
  getOverview: () => api.get<OverviewStats>('/stats/overview').then(r => r.data),
  getByYear: () => api.get<YearStats[]>('/stats/by-year').then(r => r.data),
  getByRegion: () => api.get<RegionStats[]>('/stats/by-region').then(r => r.data),
  getUnclassified: () => api.get<Record<string, number>>('/stats/unclassified').then(r => r.data),
  getMatchingSummary: () => api.get<MatchingSummary>('/stats/matching-summary').then(r => r.data),
  getSyncStatus: () => api.get<SyncStatus>('/stats/sync-status').then(r => r.data),
};

// Patterns API
export const patternsApi = {
  list: (activeOnly = false) =>
    api.get<Pattern[]>('/patterns', { params: { active_only: activeOnly } }).then(r => r.data),
  get: (id: number) => api.get<Pattern>(`/patterns/${id}`).then(r => r.data),
  create: (data: Partial<Pattern>) => api.post<Pattern>('/patterns', data).then(r => r.data),
  update: (id: number, data: Partial<Pattern>) =>
    api.put<Pattern>(`/patterns/${id}`, data).then(r => r.data),
  delete: (id: number) => api.delete(`/patterns/${id}`).then(r => r.data),
  test: (id: number, filename: string) =>
    api.post<PatternTestResult>(`/patterns/${id}/test`, { filename }).then(r => r.data),
};

// Settings API (Regions, EventTypes)
export const settingsApi = {
  getRegions: () => api.get<Region[]>('/regions').then(r => r.data),
  getEventTypes: () => api.get<EventType[]>('/event-types').then(r => r.data),
  createRegion: (data: Partial<Region>) => api.post<Region>('/regions', data).then(r => r.data),
  createEventType: (data: Partial<EventType>) =>
    api.post<EventType>('/event-types', data).then(r => r.data),
};

// Files API
export interface FileFilters {
  page?: number;
  page_size?: number;
  year?: number;
  region_id?: number;
  event_type_id?: number;
  has_group?: boolean;
  search?: string;
}

export const filesApi = {
  list: (filters: FileFilters = {}) =>
    api.get<PaginatedResponse<NasFile>>('/files', { params: filters }).then(r => r.data),
  get: (id: number) => api.get<NasFile>(`/files/${id}`).then(r => r.data),
  update: (id: number, data: Partial<NasFile>) =>
    api.put<NasFile>(`/files/${id}`, data).then(r => r.data),
  override: (id: number, data: { year?: number; region_id?: number; event_type_id?: number; episode?: number; reason: string }) =>
    api.post<NasFile>(`/files/${id}/override`, data).then(r => r.data),
  move: (id: number, targetGroupId: number, role = 'backup') =>
    api.post(`/files/${id}/move`, { target_group_id: targetGroupId, role }).then(r => r.data),
};

// Groups API
export interface GroupFilters {
  page?: number;
  page_size?: number;
  year?: number;
  region_id?: number;
  event_type_id?: number;
  has_pokergo_match?: boolean;
  search?: string;
}

export const groupsApi = {
  list: (filters: GroupFilters = {}) =>
    api.get<PaginatedResponse<AssetGroup>>('/groups', { params: filters }).then(r => r.data),
  get: (id: number) => api.get<AssetGroupDetail>(`/groups/${id}`).then(r => r.data),
  create: (data: Partial<AssetGroup>) => api.post<AssetGroup>('/groups', data).then(r => r.data),
  update: (id: number, data: Partial<AssetGroup>) =>
    api.put<AssetGroup>(`/groups/${id}`, data).then(r => r.data),
  delete: (id: number) => api.delete(`/groups/${id}`).then(r => r.data),
  setPrimary: (groupId: number, fileId: number) =>
    api.post(`/groups/${groupId}/set-primary`, { file_id: fileId }).then(r => r.data),
  merge: (sourceIds: number[], targetId: number) =>
    api.post('/groups/merge', { source_group_ids: sourceIds, target_group_id: targetId }).then(r => r.data),
};

// Process API (Scan, Export, Migration)
export interface ScanRequest {
  mode: 'incremental' | 'full';
  folder_type: 'origin' | 'archive' | 'both';
  origin_path?: string;
  archive_path?: string;
}

export interface ExportRequest {
  format: 'csv' | 'json' | 'google_sheets';
  sheet_name?: string;
}

export interface ProcessResponse {
  success: boolean;
  message: string;
  stats?: Record<string, unknown>;
  file_path?: string;
  url?: string;
}

export const processApi = {
  // NAS Scan
  scan: (request: ScanRequest) =>
    api.post<ProcessResponse>('/process/scan', request).then(r => r.data),

  // Export
  export: (request: ExportRequest) =>
    api.post<ProcessResponse>('/process/export', request).then(r => r.data),
  downloadCsv: () => api.get('/process/export/csv', { responseType: 'blob' }).then(r => r.data),
  getGoogleSheetsStatus: () =>
    api.get<{ available: boolean; message: string }>('/process/export/google-sheets/status').then(r => r.data),

  // Migration
  migrate: (clearExisting = false) =>
    api.post<ProcessResponse>('/process/migrate', { clear_existing: clearExisting }).then(r => r.data),

  // Status
  getStatus: () => api.get('/process/status').then(r => r.data),
};

// Exclusion Rules API
export const exclusionsApi = {
  list: (activeOnly = false, ruleType?: string) =>
    api.get<ExclusionRuleListResponse>('/exclusions', {
      params: { active_only: activeOnly, rule_type: ruleType }
    }).then(r => r.data),
  get: (id: number) => api.get<ExclusionRule>(`/exclusions/${id}`).then(r => r.data),
  create: (data: ExclusionRuleCreate) =>
    api.post<ExclusionRule>('/exclusions', data).then(r => r.data),
  update: (id: number, data: ExclusionRuleUpdate) =>
    api.put<ExclusionRule>(`/exclusions/${id}`, data).then(r => r.data),
  delete: (id: number) => api.delete(`/exclusions/${id}`).then(r => r.data),
  toggle: (id: number) => api.put<ExclusionRule>(`/exclusions/${id}/toggle`).then(r => r.data),
  test: (data: { rule_type: string; operator: string; value: string; sample_filename?: string; sample_size_bytes?: number; sample_duration_sec?: number }) =>
    api.post<{ would_exclude: boolean; reason: string }>('/exclusions/test', data).then(r => r.data),
};

// Categories API
export interface CategoryFilters {
  page?: number;
  page_size?: number;
  year?: number;
  region?: string;
  source?: string;
}

export const categoriesApi = {
  list: (filters: CategoryFilters = {}) =>
    api.get<PaginatedResponse<Category>>('/categories', { params: filters }).then(r => r.data),
  get: (id: number) => api.get<Category>(`/categories/${id}`).then(r => r.data),
  getEntries: (id: number, page = 1, pageSize = 50) =>
    api.get<PaginatedResponse<CategoryEntry>>(`/categories/${id}/entries`, {
      params: { page, page_size: pageSize }
    }).then(r => r.data),
};

// Entries API
export interface EntryFilters {
  page?: number;
  page_size?: number;
  match_type?: string;
  source?: string;
  verified?: boolean;
  year?: number;
  event_type?: string;
  search?: string;
}

export const entriesApi = {
  list: (filters: EntryFilters = {}) =>
    api.get<PaginatedResponse<CategoryEntry>>('/entries', { params: filters }).then(r => r.data),
  get: (id: number) => api.get<CategoryEntryDetail>(`/entries/${id}`).then(r => r.data),
  update: (id: number, data: Partial<CategoryEntry>) =>
    api.patch<CategoryEntry>(`/entries/${id}`, data).then(r => r.data),
  verify: (id: number, verifiedBy = 'user', notes?: string) =>
    api.post<CategoryEntry>(`/entries/${id}/verify`, { verified_by: verifiedBy, notes }).then(r => r.data),
  verifyBatch: (entryIds: number[], verifiedBy = 'user') =>
    api.post<{ verified_count: number; total_requested: number }>('/entries/verify-batch', {
      entry_ids: entryIds,
      verified_by: verifiedBy
    }).then(r => r.data),
  generateTitles: (useAi = false, dryRun = false) =>
    api.post<{ total: number; improved: number; ai_generated: number; pattern_generated: number; unchanged: number; samples: Array<{ entry_code: string; old: string; new: string }> }>(
      '/entries/generate-titles',
      null,
      { params: { use_ai: useAi, dry_run: dryRun } }
    ).then(r => r.data),
  improveTitles: (dryRun = false) =>
    api.post<{ total: number; improved: number; samples: Array<{ entry_code: string; old: string; new: string }> }>(
      '/entries/improve-titles',
      null,
      { params: { dry_run: dryRun } }
    ).then(r => r.data),
};

// KPI Stats API
export const kpiApi = {
  getStats: () => api.get<KPIStats>('/stats/kpi').then(r => r.data),
};

// Content Tree API (for Content Explorer)
export interface TreeEntry {
  id: number;
  entry_code: string;
  display_title: string | null;
  pokergo_title: string | null;
  match_type: string | null;
  match_score: number | null;
  file_count: number;
  total_size_gb: number;
}

export interface TreeEventType {
  code: string;
  name: string;
  entry_count: number;
  exact_count: number;
  none_count: number;
  entries: TreeEntry[];
}

export interface TreeCategory {
  id: number;
  code: string;
  name: string;
  region: string | null;
  entry_count: number;
  exact_count: number;
  none_count: number;
  event_types: TreeEventType[];
}

export interface TreeYear {
  year: number;
  entry_count: number;
  exact_count: number;
  none_count: number;
  total_size_gb: number;
  categories: TreeCategory[];
}

export interface ContentTreeResponse {
  years: TreeYear[];
  summary: {
    total_entries: number;
    exact_count: number;
    none_count: number;
    exact_rate: number;
    total_size_gb: number;
    year_count: number;
  };
}

export const contentTreeApi = {
  getTree: (year?: number) =>
    api.get<ContentTreeResponse>('/content-tree', { params: year ? { year } : {} }).then(r => r.data),
};

export default api;
