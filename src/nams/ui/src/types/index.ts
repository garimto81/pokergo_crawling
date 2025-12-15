// Common types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Stats types
export interface OverviewStats {
  total_files: number;
  total_groups: number;
  total_size_bytes: number;
  total_size_formatted: string;
  matched_files: number;
  unmatched_files: number;
  match_rate: number;
  pokergo_matched_groups: number;
  pokergo_match_rate: number;
}

export interface YearStats {
  year: number;
  file_count: number;
  group_count: number;
  size_bytes: number;
  size_formatted: string;
}

export interface RegionStats {
  region_code: string;
  region_name: string;
  file_count: number;
  group_count: number;
  size_bytes: number;
}

// Region & EventType
export interface Region {
  id: number;
  code: string;
  name: string;
  description?: string;
  is_active: boolean;
}

export interface EventType {
  id: number;
  code: string;
  name: string;
  description?: string;
  is_active: boolean;
}

// Pattern types
export interface Pattern {
  id: number;
  name: string;
  priority: number;
  regex: string;
  extract_year: boolean;
  extract_region?: string;
  extract_type?: string;
  extract_episode: boolean;
  description?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// File types
export interface NasFile {
  id: number;
  filename: string;
  size_bytes: number;
  size_formatted: string;
  year?: number;
  region_code?: string;
  event_type_code?: string;
  episode?: number;
  group_id?: string;
  role: string;
  is_manual_override: boolean;
}

// Group types
export interface AssetGroup {
  id: number;
  group_id: string;
  year: number;
  region_code?: string;
  event_type_code?: string;
  episode?: number;
  file_count: number;
  total_size_formatted: string;
  has_backup: boolean;
  has_pokergo_match: boolean;
  pokergo_title?: string;
}

export interface AssetGroupDetail extends AssetGroup {
  files: NasFile[];
  pokergo_episode_id?: string;
  pokergo_match_score?: number;
}
