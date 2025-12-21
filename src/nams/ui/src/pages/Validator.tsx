import { useState, useEffect, useCallback, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Play,
  ChevronLeft,
  Check,
  SkipForward,
  RefreshCw,
  Search,
  Filter,
  Clock,
  CheckCircle,
  FileVideo,
  HardDrive
} from 'lucide-react';

// Types
interface ValidatorEntry {
  id: number;
  entry_code: string;
  display_title: string | null;
  pokergo_title: string | null;
  year: number;
  event_type: string | null;
  category_id: number | null;
  category_name: string | null;
  match_type: string | null;
  match_score: number | null;
  verified: boolean;
  verified_at: string | null;
  verified_by: string | null;
  file_count: number;
  total_size_gb: number;
}

interface EntryFile {
  id: number;
  filename: string;
  full_path: string;
  size_bytes: number;
  size_gb: number;
  drive: string | null;
  role: string | null;
  extension: string;
}

interface ValidatorStats {
  total_entries: number;
  verified_entries: number;
  pending_entries: number;
  verification_rate: number;
  entries_by_year: Record<string, { total: number; verified: number }>;
  recent_verifications: number;
}

interface EntryChange {
  id: number;
  action: string;
  changed_by: string;
  changed_at: string;
}

// API functions
const validatorApi = {
  getPending: async (params: { page?: number; page_size?: number; year?: number; search?: string }) => {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set('page', String(params.page));
    if (params.page_size) searchParams.set('page_size', String(params.page_size));
    if (params.year) searchParams.set('year', String(params.year));
    if (params.search) searchParams.set('search', params.search);

    const res = await fetch(`http://localhost:8001/api/validator/pending?${searchParams}`);
    return res.json();
  },

  getEntry: async (id: number) => {
    const res = await fetch(`http://localhost:8001/api/validator/entry/${id}`);
    return res.json();
  },

  updateEntry: async (id: number, data: { display_title?: string; category_id?: number }) => {
    const res = await fetch(`http://localhost:8001/api/validator/entry/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return res.json();
  },

  verifyEntry: async (id: number, data: { verified_by?: string; notes?: string } = {}) => {
    const res = await fetch(`http://localhost:8001/api/validator/entry/${id}/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return res.json();
  },

  playVideo: async (entryId: number, fileId: number) => {
    const res = await fetch(`http://localhost:8001/api/validator/entry/${entryId}/play`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_id: fileId }),
    });
    return res.json();
  },

  getStats: async (): Promise<ValidatorStats> => {
    const res = await fetch('http://localhost:8001/api/validator/stats');
    return res.json();
  },
};

// Utility functions
const formatBytes = (bytes: number) => {
  const gb = bytes / (1024 ** 3);
  if (gb >= 1) return `${gb.toFixed(2)} GB`;
  const mb = bytes / (1024 ** 2);
  return `${mb.toFixed(1)} MB`;
};

const matchTypeBadge = (type?: string | null) => {
  switch (type) {
    case 'EXACT': return 'bg-green-100 text-green-800';
    case 'PARTIAL': return 'bg-yellow-100 text-yellow-800';
    case 'MANUAL': return 'bg-blue-100 text-blue-800';
    default: return 'bg-gray-100 text-gray-500';
  }
};

export function Validator() {
  const queryClient = useQueryClient();

  // State
  const [currentIndex, setCurrentIndex] = useState(0);
  const [editedTitle, setEditedTitle] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [yearFilter, setYearFilter] = useState<number | undefined>();
  const [page, setPage] = useState(1);

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['validator-stats'],
    queryFn: validatorApi.getStats,
  });

  // Fetch pending entries
  const { data: pendingData, isLoading, refetch } = useQuery({
    queryKey: ['validator-pending', page, yearFilter, searchTerm],
    queryFn: () => validatorApi.getPending({
      page,
      page_size: 50,
      year: yearFilter,
      search: searchTerm || undefined,
    }),
  });

  const entries: ValidatorEntry[] = pendingData?.items || [];
  const totalEntries = pendingData?.total || 0;
  const currentEntry = entries[currentIndex];

  // Fetch entry details
  const { data: entryDetail } = useQuery({
    queryKey: ['validator-entry', currentEntry?.id],
    queryFn: () => validatorApi.getEntry(currentEntry!.id),
    enabled: !!currentEntry,
  });

  const files: EntryFile[] = entryDetail?.files || [];

  // Sync edited title when entry changes using ref to track previous ID
  const prevEntryIdRef = useRef<number | undefined>(undefined);
  const currentEntryId = currentEntry?.id;
  if (currentEntryId !== prevEntryIdRef.current) {
    prevEntryIdRef.current = currentEntryId;
    if (currentEntry) {
      setEditedTitle(currentEntry.display_title || '');
    }
  }

  // Mutations
  const updateMutation = useMutation({
    mutationFn: (data: { display_title?: string }) =>
      validatorApi.updateEntry(currentEntry!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['validator-pending'] });
      queryClient.invalidateQueries({ queryKey: ['validator-entry', currentEntry?.id] });
    },
  });

  const verifyMutation = useMutation({
    mutationFn: () => validatorApi.verifyEntry(currentEntry!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['validator-pending'] });
      queryClient.invalidateQueries({ queryKey: ['validator-stats'] });
      // Move to next entry
      if (currentIndex < entries.length - 1) {
        setCurrentIndex(prev => prev + 1);
      } else if (page < (pendingData?.total_pages || 1)) {
        setPage(prev => prev + 1);
        setCurrentIndex(0);
      }
    },
  });

  const playMutation = useMutation({
    mutationFn: (fileId: number) => validatorApi.playVideo(currentEntry!.id, fileId),
  });

  // Navigation handlers
  const goNext = useCallback(() => {
    if (currentIndex < entries.length - 1) {
      setCurrentIndex(prev => prev + 1);
    } else if (page < (pendingData?.total_pages || 1)) {
      setPage(prev => prev + 1);
      setCurrentIndex(0);
    }
  }, [currentIndex, entries.length, page, pendingData?.total_pages]);

  const goPrev = useCallback(() => {
    if (currentIndex > 0) {
      setCurrentIndex(prev => prev - 1);
    } else if (page > 1) {
      setPage(prev => prev - 1);
      setCurrentIndex(49); // Last item of previous page
    }
  }, [currentIndex, page]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement) return;

      switch (e.key) {
        case 'n':
        case 'N':
          goNext();
          break;
        case 'p':
        case 'P':
          goPrev();
          break;
        case 'Enter':
          if (!verifyMutation.isPending) {
            verifyMutation.mutate();
          }
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [goNext, goPrev, verifyMutation]);

  // Save handler
  const handleSave = () => {
    if (editedTitle !== currentEntry?.display_title) {
      updateMutation.mutate({ display_title: editedTitle });
    }
  };

  // Verify and next
  const handleVerifyAndNext = () => {
    if (editedTitle !== currentEntry?.display_title) {
      updateMutation.mutate({ display_title: editedTitle });
    }
    verifyMutation.mutate();
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with Stats */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Catalog Validator</h1>
          <p className="text-sm text-gray-500 mt-1">
            영상을 재생하여 제목과 카테고리를 검증합니다
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-sm">
            <CheckCircle className="w-4 h-4 text-green-500" />
            <span>{stats?.verified_entries || 0} 검증됨</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Clock className="w-4 h-4 text-yellow-500" />
            <span>{stats?.pending_entries || 0} 대기중</span>
          </div>
          <div className="text-sm font-medium">
            {((stats?.verification_rate || 0) * 100).toFixed(1)}% 완료
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 bg-white p-4 rounded-lg shadow-sm">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-400" />
          <select
            className="border rounded px-3 py-1.5 text-sm"
            value={yearFilter || ''}
            onChange={(e) => {
              setYearFilter(e.target.value ? Number(e.target.value) : undefined);
              setCurrentIndex(0);
              setPage(1);
            }}
          >
            <option value="">All Years</option>
            {[2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017].map(y => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2 flex-1">
          <Search className="w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search entries..."
            className="border rounded px-3 py-1.5 text-sm flex-1"
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentIndex(0);
              setPage(1);
            }}
          />
        </div>

        <button
          onClick={() => refetch()}
          className="flex items-center gap-2 px-3 py-1.5 text-sm border rounded hover:bg-gray-50"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Main Content */}
      {currentEntry ? (
        <div className="bg-white rounded-lg shadow-sm overflow-hidden">
          {/* Entry Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b bg-gray-50">
            <div className="flex items-center gap-3">
              <span className="text-sm font-mono text-gray-600">
                {currentEntry.entry_code}
              </span>
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${matchTypeBadge(currentEntry.match_type)}`}>
                {currentEntry.match_type || 'NONE'}
              </span>
              {currentEntry.match_score && (
                <span className="text-xs text-gray-500">
                  {(currentEntry.match_score * 100).toFixed(0)}% match
                </span>
              )}
            </div>
            <div className="text-sm text-gray-500">
              [{currentIndex + 1 + (page - 1) * 50}/{totalEntries}]
            </div>
          </div>

          {/* Entry Content */}
          <div className="p-6 space-y-6">
            {/* Title Editor */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">
                Display Title
              </label>
              <input
                type="text"
                className="w-full border rounded-lg px-4 py-2 text-lg"
                value={editedTitle}
                onChange={(e) => setEditedTitle(e.target.value)}
                placeholder="Enter display title..."
              />
            </div>

            {/* PokerGO Title Reference */}
            {currentEntry.pokergo_title && (
              <div className="space-y-1">
                <label className="block text-sm font-medium text-gray-500">
                  PokerGO Title (Reference)
                </label>
                <p className="text-gray-600 bg-gray-50 px-4 py-2 rounded">
                  {currentEntry.pokergo_title}
                </p>
              </div>
            )}

            {/* Category */}
            <div className="flex items-center gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-500 mb-1">
                  Category
                </label>
                <span className="text-gray-800">
                  {currentEntry.category_name || 'Uncategorized'}
                </span>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-500 mb-1">
                  Year
                </label>
                <span className="text-gray-800">{currentEntry.year}</span>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-500 mb-1">
                  Event Type
                </label>
                <span className="text-gray-800">{currentEntry.event_type || '-'}</span>
              </div>
            </div>

            {/* Files */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">
                Files ({files.length})
              </label>
              <div className="space-y-2">
                {files.map((file) => (
                  <div
                    key={file.id}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <FileVideo className="w-5 h-5 text-blue-500" />
                      <div>
                        <p className="text-sm font-medium">{file.filename}</p>
                        <p className="text-xs text-gray-500 flex items-center gap-2">
                          <HardDrive className="w-3 h-3" />
                          {file.drive} | {formatBytes(file.size_bytes)} | {file.role || 'PRIMARY'}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => playMutation.mutate(file.id)}
                      disabled={playMutation.isPending}
                      className="flex items-center gap-2 px-3 py-1.5 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
                    >
                      <Play className="w-4 h-4" />
                      재생
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between px-6 py-4 border-t bg-gray-50">
            <div className="flex items-center gap-2">
              <button
                onClick={goPrev}
                disabled={currentIndex === 0 && page === 1}
                className="flex items-center gap-1 px-3 py-2 border rounded hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-4 h-4" />
                Prev (P)
              </button>
              <button
                onClick={goNext}
                className="flex items-center gap-1 px-3 py-2 border rounded hover:bg-white"
              >
                Skip (N)
                <SkipForward className="w-4 h-4" />
              </button>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleSave}
                disabled={updateMutation.isPending || editedTitle === currentEntry.display_title}
                className="px-4 py-2 border rounded hover:bg-white disabled:opacity-50"
              >
                Save
              </button>
              <button
                onClick={handleVerifyAndNext}
                disabled={verifyMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
              >
                <Check className="w-4 h-4" />
                Verify & Next (Enter)
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm p-12 text-center">
          <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            All entries verified!
          </h2>
          <p className="text-gray-500">
            No pending entries to validate.
          </p>
        </div>
      )}

      {/* Change History */}
      {entryDetail?.changes && entryDetail.changes.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Recent Changes</h3>
          <div className="space-y-2">
            {entryDetail.changes.slice(0, 5).map((change: EntryChange) => (
              <div key={change.id} className="text-sm text-gray-600 flex items-center gap-2">
                <Clock className="w-4 h-4 text-gray-400" />
                <span>
                  {change.action} by {change.changed_by} - {change.changed_at}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Keyboard Shortcuts Help */}
      <div className="text-center text-xs text-gray-400">
        Shortcuts: N = Next | P = Previous | Enter = Verify & Next
      </div>
    </div>
  );
}

export default Validator;
