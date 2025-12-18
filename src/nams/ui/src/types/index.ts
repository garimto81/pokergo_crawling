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

export interface PatternTestResult {
  matched: boolean;
  pattern_name?: string;
  extracted_year?: string;
  extracted_region?: string;
  extracted_type?: string;
  extracted_episode?: number;
  confidence: number;
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
  catalog_title?: string;
  catalog_title_manual?: boolean;
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
  catalog_title_manual?: boolean;
}

// Exclusion Rule types
export type RuleType = 'size' | 'duration' | 'keyword';
export type Operator = 'lt' | 'gt' | 'eq' | 'contains';

export interface ExclusionRule {
  id: number;
  rule_type: RuleType;
  operator: Operator;
  value: string;
  description?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ExclusionRuleCreate {
  rule_type: RuleType;
  operator: Operator;
  value: string;
  description?: string;
  is_active?: boolean;
}

export interface ExclusionRuleUpdate {
  rule_type?: RuleType;
  operator?: Operator;
  value?: string;
  description?: string;
  is_active?: boolean;
}

export interface ExclusionRuleListResponse {
  items: ExclusionRule[];
  total: number;
}

// Category types
export interface Category {
  id: number;
  code: string;
  name: string;
  year: number;
  region?: string;
  source?: string;
  pokergo_category?: string;
  description?: string;
  entry_count?: number;
  file_count?: number;
  total_size_gb?: number;
  created_at?: string;
}

export interface CategoryEntry {
  id: number;
  entry_code: string;
  display_title?: string;
  year: number;
  event_type?: string;
  event_name?: string;
  sequence?: number;
  sequence_type?: string;
  category_id?: number;
  source?: string;
  pokergo_ep_id?: string;
  pokergo_title?: string;
  match_type?: 'EXACT' | 'PARTIAL' | 'MANUAL' | 'NONE';
  match_score?: number;
  verified: boolean;
  verified_at?: string;
  verified_by?: string;
  notes?: string;
  file_count?: number;
  total_size_bytes?: number;
  created_at?: string;
  updated_at?: string;
}

export interface CategoryEntryDetail extends CategoryEntry {
  category_name?: string;
  files: EntryFile[];
}

export interface EntryFile {
  id: number;
  file_id?: string;
  filename: string;
  drive?: string;
  folder?: string;
  size_bytes: number;
  role?: string;
  is_excluded: boolean;
}

export interface KPIStats {
  total_entries: number;
  total_files: number;
  active_files: number;
  category_coverage: number;
  title_completeness: number;
  pokergo_utilization: number;
  verification_rate: number;
  match_type_stats: {
    exact: number;
    partial: number;
    manual: number;
    none: number;
  };
  source_stats: {
    pokergo: number;
    nas_only: number;
  };
  verification_needed: number;
}
