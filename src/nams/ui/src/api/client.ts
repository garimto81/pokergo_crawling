import axios from 'axios';
import type {
  OverviewStats,
  YearStats,
  RegionStats,
  Pattern,
  Region,
  EventType,
  NasFile,
  AssetGroup,
  AssetGroupDetail,
  PaginatedResponse
} from '../types';

const api = axios.create({
  baseURL: '/api',
});

// Stats API
export const statsApi = {
  getOverview: () => api.get<OverviewStats>('/stats/overview').then(r => r.data),
  getByYear: () => api.get<YearStats[]>('/stats/by-year').then(r => r.data),
  getByRegion: () => api.get<RegionStats[]>('/stats/by-region').then(r => r.data),
  getUnclassified: () => api.get<Record<string, number>>('/stats/unclassified').then(r => r.data),
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
    api.post(`/patterns/${id}/test`, { filename }).then(r => r.data),
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

export default api;
