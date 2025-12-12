// Match types

export type MatchStatus =
  | 'MATCHED'
  | 'LIKELY'
  | 'POSSIBLE'
  | 'NOT_UPLOADED'
  | 'VERIFIED'
  | 'WRONG_MATCH'
  | 'MANUAL_MATCH'
  | 'UPLOAD_PLANNED'
  | 'EXCLUDED';

export interface Match {
  id: number;
  nas_filename: string;
  nas_directory: string | null;
  nas_size_bytes: number | null;
  youtube_video_id: string | null;
  youtube_title: string | null;
  match_score: number;
  match_status: MatchStatus;
  match_details: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface MatchListResponse {
  items: Match[];
  total: number;
  page: number;
  pages: number;
  limit: number;
}

export interface StatsSummary {
  total: number;
  by_status: Record<string, number>;
  match_rate: number;
  avg_score: number;
}

export interface CategoryCount {
  directory: string;
  count: number;
  files: Array<{ filename: string; score: number }>;
}

export interface NotUploadedCategories {
  total: number;
  categories: CategoryCount[];
}

export interface ScoreDistribution {
  bins: number[];
  counts: number[];
}
