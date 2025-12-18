import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { entriesApi, kpiApi, type EntryFilters } from '../api/client';
import type { CategoryEntry } from '../types';

// Match type badge colors
const matchTypeBadge = (type?: string) => {
  switch (type) {
    case 'EXACT':
      return 'bg-green-100 text-green-800';
    case 'PARTIAL':
      return 'bg-yellow-100 text-yellow-800';
    case 'MANUAL':
      return 'bg-blue-100 text-blue-800';
    case 'NONE':
      return 'bg-gray-100 text-gray-800';
    default:
      return 'bg-gray-100 text-gray-500';
  }
};

// Format bytes to human readable
const formatBytes = (bytes?: number) => {
  if (!bytes) return '-';
  const gb = bytes / (1024 ** 3);
  if (gb >= 1) return `${gb.toFixed(2)} GB`;
  const mb = bytes / (1024 ** 2);
  return `${mb.toFixed(1)} MB`;
};

export function Entries() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<EntryFilters>({
    page: 1,
    page_size: 20,
  });
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [detailEntry, setDetailEntry] = useState<CategoryEntry | null>(null);

  // Fetch KPI stats
  const { data: kpiStats } = useQuery({
    queryKey: ['kpi-stats'],
    queryFn: kpiApi.getStats,
  });

  // Fetch entries
  const { data: entriesData, isLoading } = useQuery({
    queryKey: ['entries', filters],
    queryFn: () => entriesApi.list(filters),
  });

  // Verify single entry
  const verifyMutation = useMutation({
    mutationFn: (id: number) => entriesApi.verify(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['entries'] });
      queryClient.invalidateQueries({ queryKey: ['kpi-stats'] });
    },
  });

  // Verify batch
  const verifyBatchMutation = useMutation({
    mutationFn: (ids: number[]) => entriesApi.verifyBatch(ids),
    onSuccess: () => {
      setSelectedIds([]);
      queryClient.invalidateQueries({ queryKey: ['entries'] });
      queryClient.invalidateQueries({ queryKey: ['kpi-stats'] });
    },
  });

  // Toggle selection
  const toggleSelect = (id: number) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  // Select all visible
  const selectAllVisible = () => {
    const visibleIds = entriesData?.items.map(e => e.id) || [];
    setSelectedIds(prev => {
      const allSelected = visibleIds.every(id => prev.includes(id));
      if (allSelected) {
        return prev.filter(id => !visibleIds.includes(id));
      }
      return [...new Set([...prev, ...visibleIds])];
    });
  };

  // Pagination
  const totalPages = Math.ceil((entriesData?.total || 0) / (filters.page_size || 20));

  return (
    <div className="space-y-6">
      {/* Header with KPI */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Entry Verification</h1>
          <p className="text-gray-600">검증이 필요한 항목을 확인하고 승인합니다</p>
        </div>
        {kpiStats && (
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-white rounded-lg p-3 shadow-sm border">
              <div className="text-2xl font-bold text-blue-600">{kpiStats.total_entries}</div>
              <div className="text-xs text-gray-500">Total Entries</div>
            </div>
            <div className="bg-white rounded-lg p-3 shadow-sm border">
              <div className="text-2xl font-bold text-green-600">{kpiStats.verification_rate}%</div>
              <div className="text-xs text-gray-500">Verified</div>
            </div>
            <div className="bg-white rounded-lg p-3 shadow-sm border">
              <div className="text-2xl font-bold text-yellow-600">{kpiStats.verification_needed}</div>
              <div className="text-xs text-gray-500">Needs Review</div>
            </div>
            <div className="bg-white rounded-lg p-3 shadow-sm border">
              <div className="text-2xl font-bold text-purple-600">{kpiStats.pokergo_utilization}%</div>
              <div className="text-xs text-gray-500">PokerGO Match</div>
            </div>
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border p-4">
        <div className="flex flex-wrap gap-4 items-center">
          <select
            className="border rounded-md px-3 py-2 text-sm"
            value={filters.match_type || ''}
            onChange={e => setFilters(f => ({ ...f, match_type: e.target.value || undefined, page: 1 }))}
          >
            <option value="">All Match Types</option>
            <option value="EXACT">EXACT</option>
            <option value="PARTIAL">PARTIAL</option>
            <option value="MANUAL">MANUAL</option>
            <option value="NONE">NONE</option>
          </select>

          <select
            className="border rounded-md px-3 py-2 text-sm"
            value={filters.verified === undefined ? '' : filters.verified ? 'true' : 'false'}
            onChange={e => setFilters(f => ({
              ...f,
              verified: e.target.value === '' ? undefined : e.target.value === 'true',
              page: 1
            }))}
          >
            <option value="">All Status</option>
            <option value="false">Unverified</option>
            <option value="true">Verified</option>
          </select>

          <select
            className="border rounded-md px-3 py-2 text-sm"
            value={filters.source || ''}
            onChange={e => setFilters(f => ({ ...f, source: e.target.value || undefined, page: 1 }))}
          >
            <option value="">All Sources</option>
            <option value="POKERGO">PokerGO</option>
            <option value="NAS_ONLY">NAS Only</option>
          </select>

          <input
            type="text"
            placeholder="Search title..."
            className="border rounded-md px-3 py-2 text-sm flex-1 min-w-[200px]"
            value={filters.search || ''}
            onChange={e => setFilters(f => ({ ...f, search: e.target.value || undefined, page: 1 }))}
          />

          {selectedIds.length > 0 && (
            <button
              onClick={() => verifyBatchMutation.mutate(selectedIds)}
              disabled={verifyBatchMutation.isPending}
              className="bg-green-600 text-white px-4 py-2 rounded-md text-sm hover:bg-green-700 disabled:opacity-50"
            >
              {verifyBatchMutation.isPending ? 'Verifying...' : `Verify ${selectedIds.length} Selected`}
            </button>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left">
                <input
                  type="checkbox"
                  checked={entriesData?.items.every(e => selectedIds.includes(e.id)) && entriesData.items.length > 0}
                  onChange={selectAllVisible}
                  className="rounded"
                />
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Entry Code</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Display Title</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">PokerGO Title</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Match</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Score</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Files</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {isLoading ? (
              <tr>
                <td colSpan={9} className="px-4 py-8 text-center text-gray-500">Loading...</td>
              </tr>
            ) : entriesData?.items.length === 0 ? (
              <tr>
                <td colSpan={9} className="px-4 py-8 text-center text-gray-500">No entries found</td>
              </tr>
            ) : (
              entriesData?.items.map(entry => (
                <tr key={entry.id} className={`hover:bg-gray-50 ${selectedIds.includes(entry.id) ? 'bg-blue-50' : ''}`}>
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(entry.id)}
                      onChange={() => toggleSelect(entry.id)}
                      className="rounded"
                    />
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-mono text-sm text-gray-900">{entry.entry_code}</span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="max-w-[200px] truncate text-sm" title={entry.display_title}>
                      {entry.display_title || '-'}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="max-w-[200px] truncate text-sm text-gray-600" title={entry.pokergo_title}>
                      {entry.pokergo_title || '-'}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${matchTypeBadge(entry.match_type)}`}>
                      {entry.match_type || '-'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {entry.match_score ? `${(entry.match_score * 100).toFixed(0)}%` : '-'}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {entry.file_count || 0}
                    <span className="text-gray-400 ml-1">({formatBytes(entry.total_size_bytes)})</span>
                  </td>
                  <td className="px-4 py-3">
                    {entry.verified ? (
                      <span className="inline-flex px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        Verified
                      </span>
                    ) : (
                      <span className="inline-flex px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                        Pending
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button
                        onClick={() => setDetailEntry(entry)}
                        className="text-blue-600 hover:text-blue-800 text-sm"
                      >
                        Detail
                      </button>
                      {!entry.verified && (
                        <button
                          onClick={() => verifyMutation.mutate(entry.id)}
                          disabled={verifyMutation.isPending}
                          className="text-green-600 hover:text-green-800 text-sm disabled:opacity-50"
                        >
                          Verify
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {/* Pagination */}
        <div className="px-4 py-3 bg-gray-50 border-t flex justify-between items-center">
          <div className="text-sm text-gray-500">
            Showing {((filters.page || 1) - 1) * (filters.page_size || 20) + 1} to{' '}
            {Math.min((filters.page || 1) * (filters.page_size || 20), entriesData?.total || 0)} of{' '}
            {entriesData?.total || 0} entries
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setFilters(f => ({ ...f, page: Math.max(1, (f.page || 1) - 1) }))}
              disabled={(filters.page || 1) <= 1}
              className="px-3 py-1 border rounded text-sm disabled:opacity-50"
            >
              Previous
            </button>
            <span className="px-3 py-1 text-sm">
              Page {filters.page || 1} of {totalPages}
            </span>
            <button
              onClick={() => setFilters(f => ({ ...f, page: Math.min(totalPages, (f.page || 1) + 1) }))}
              disabled={(filters.page || 1) >= totalPages}
              className="px-3 py-1 border rounded text-sm disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      </div>

      {/* Detail Modal */}
      {detailEntry && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-start mb-4">
                <h2 className="text-xl font-bold">{detailEntry.entry_code}</h2>
                <button onClick={() => setDetailEntry(null)} className="text-gray-400 hover:text-gray-600">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs text-gray-500">Display Title</label>
                    <div className="font-medium">{detailEntry.display_title || '-'}</div>
                  </div>
                  <div>
                    <label className="text-xs text-gray-500">PokerGO Title</label>
                    <div className="font-medium text-gray-600">{detailEntry.pokergo_title || '-'}</div>
                  </div>
                  <div>
                    <label className="text-xs text-gray-500">Match Type</label>
                    <div>
                      <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${matchTypeBadge(detailEntry.match_type)}`}>
                        {detailEntry.match_type || '-'}
                      </span>
                    </div>
                  </div>
                  <div>
                    <label className="text-xs text-gray-500">Match Score</label>
                    <div className="font-medium">
                      {detailEntry.match_score ? `${(detailEntry.match_score * 100).toFixed(1)}%` : '-'}
                    </div>
                  </div>
                  <div>
                    <label className="text-xs text-gray-500">Year</label>
                    <div className="font-medium">{detailEntry.year}</div>
                  </div>
                  <div>
                    <label className="text-xs text-gray-500">Event Type</label>
                    <div className="font-medium">{detailEntry.event_type || '-'}</div>
                  </div>
                  <div>
                    <label className="text-xs text-gray-500">Source</label>
                    <div className="font-medium">{detailEntry.source || '-'}</div>
                  </div>
                  <div>
                    <label className="text-xs text-gray-500">Files</label>
                    <div className="font-medium">{detailEntry.file_count || 0}</div>
                  </div>
                </div>

                <div className="flex gap-2 pt-4 border-t">
                  {!detailEntry.verified && (
                    <button
                      onClick={() => {
                        verifyMutation.mutate(detailEntry.id);
                        setDetailEntry(null);
                      }}
                      className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700"
                    >
                      Verify Entry
                    </button>
                  )}
                  <button
                    onClick={() => setDetailEntry(null)}
                    className="border px-4 py-2 rounded-md hover:bg-gray-50"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
