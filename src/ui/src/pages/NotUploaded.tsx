// Not uploaded content page

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useMemo } from 'react';
import { fetchMatches, bulkUpdateMatches, getExportUrl } from '../api/matchApi';
import { StatusBadge } from '../components/common/StatusBadge';
import { ScoreIndicator } from '../components/common/ScoreIndicator';

export function NotUploaded() {
  const queryClient = useQueryClient();
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [scoreFilter, setScoreFilter] = useState<string>('all');  // 'all', 'high', 'medium', 'low'
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const { data, isLoading } = useQuery({
    queryKey: ['not-uploaded'],
    queryFn: () => fetchMatches({ status: 'NOT_UPLOADED', limit: 500 })  // 전체 데이터 로드
  });

  // 필터링된 데이터
  const filteredItems = useMemo(() => {
    if (!data?.items) return [];

    return data.items.filter(item => {
      // 검색어 필터
      if (searchTerm) {
        const search = searchTerm.toLowerCase();
        const matchesSearch =
          item.nas_filename?.toLowerCase().includes(search) ||
          item.nas_directory?.toLowerCase().includes(search);
        if (!matchesSearch) return false;
      }

      // 점수 필터
      if (scoreFilter !== 'all') {
        const score = item.match_score || 0;
        if (scoreFilter === 'high' && score < 30) return false;
        if (scoreFilter === 'medium' && (score < 15 || score >= 30)) return false;
        if (scoreFilter === 'low' && score >= 15) return false;
      }

      return true;
    });
  }, [data?.items, searchTerm, scoreFilter]);

  // 페이지네이션
  const paginatedItems = useMemo(() => {
    const start = (page - 1) * pageSize;
    return filteredItems.slice(start, start + pageSize);
  }, [filteredItems, page]);

  const totalPages = Math.ceil(filteredItems.length / pageSize);

  const bulkMutation = useMutation({
    mutationFn: ({ ids, status }: { ids: number[]; status: string }) =>
      bulkUpdateMatches(ids, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['not-uploaded'] });
      setSelectedIds([]);
    }
  });

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const selectAll = () => {
    if (data) {
      setSelectedIds(data.items.map((m) => m.id));
    }
  };

  const clearSelection = () => setSelectedIds([]);

  const handleBulkAction = (status: string) => {
    if (selectedIds.length > 0) {
      bulkMutation.mutate({ ids: selectedIds, status });
    }
  };

  // Group by directory (사용 paginated items)
  const groupedData = paginatedItems.reduce((acc, item) => {
    const dir = item.nas_directory?.split('\\').slice(-2).join(' / ') || 'Unknown';
    if (!acc[dir]) acc[dir] = [];
    acc[dir].push(item);
    return acc;
  }, {} as Record<string, typeof paginatedItems>);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Not Uploaded Content</h1>
          <p className="text-sm text-gray-500 mt-1">
            총 {data?.total || 0}개 / 필터 적용: {filteredItems.length}개
          </p>
        </div>
        <a
          href={getExportUrl('not-uploaded', 'csv')}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
        >
          Export CSV
        </a>
      </div>

      {/* Filter Bar */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex flex-wrap gap-4 items-center">
          {/* 검색 */}
          <div className="flex-1 min-w-[200px]">
            <input
              type="text"
              placeholder="파일명 또는 디렉토리 검색..."
              value={searchTerm}
              onChange={(e) => { setSearchTerm(e.target.value); setPage(1); }}
              className="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* 점수 필터 */}
          <select
            value={scoreFilter}
            onChange={(e) => { setScoreFilter(e.target.value); setPage(1); }}
            className="px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">전체 점수</option>
            <option value="high">30+ (매칭 가능성 높음)</option>
            <option value="medium">15-29 (중간)</option>
            <option value="low">0-14 (매칭 없음)</option>
          </select>

          {/* 초기화 */}
          <button
            onClick={() => { setSearchTerm(''); setScoreFilter('all'); setPage(1); }}
            className="px-3 py-2 text-sm text-gray-600 hover:text-gray-900"
          >
            초기화
          </button>
        </div>
      </div>

      {/* Bulk Actions */}
      {selectedIds.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-center justify-between">
          <span className="text-sm font-medium text-blue-800">
            {selectedIds.length} items selected
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => handleBulkAction('UPLOAD_PLANNED')}
              className="px-3 py-1.5 text-sm font-medium text-cyan-700 bg-cyan-100 rounded hover:bg-cyan-200"
            >
              Mark as Planned
            </button>
            <button
              onClick={() => handleBulkAction('EXCLUDED')}
              className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-100 rounded hover:bg-gray-200"
            >
              Exclude
            </button>
            <button
              onClick={clearSelection}
              className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800"
            >
              Clear
            </button>
          </div>
        </div>
      )}

      {/* Selection controls */}
      <div className="flex items-center gap-4">
        <button
          onClick={selectAll}
          className="text-sm text-blue-600 hover:text-blue-800"
        >
          Select All
        </button>
        <button
          onClick={clearSelection}
          className="text-sm text-gray-600 hover:text-gray-800"
        >
          Clear Selection
        </button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-500">Loading...</div>
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <p className="text-gray-500">검색 결과가 없습니다</p>
        </div>
      ) : (
        <>
          <div className="space-y-6">
            {Object.entries(groupedData || {}).map(([dir, items]) => (
              <div key={dir} className="bg-white rounded-lg shadow overflow-hidden">
                <div className="px-4 py-3 bg-gray-50 border-b">
                  <h3 className="font-medium text-gray-900">{dir}</h3>
                  <span className="text-sm text-gray-500">{items.length} files</span>
                </div>
                <div className="divide-y">
                  {items.map((item) => (
                    <div
                      key={item.id}
                      className={`px-4 py-3 flex items-center gap-4 hover:bg-gray-50 ${
                        selectedIds.includes(item.id) ? 'bg-blue-50' : ''
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(item.id)}
                        onChange={() => toggleSelect(item.id)}
                        className="h-4 w-4 text-blue-600 rounded"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {item.nas_filename}
                        </p>
                        {item.nas_size_bytes && (
                          <p className="text-xs text-gray-500">
                            {(item.nas_size_bytes / (1024 * 1024 * 1024)).toFixed(2)} GB
                          </p>
                        )}
                      </div>
                      <ScoreIndicator score={item.match_score} showBar={false} />
                      <StatusBadge status={item.match_status} size="sm" />
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between bg-white rounded-lg shadow px-4 py-3">
              <div className="text-sm text-gray-500">
                {filteredItems.length}개 중 {(page - 1) * pageSize + 1}-{Math.min(page * pageSize, filteredItems.length)}개 표시
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(1)}
                  disabled={page === 1}
                  className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50"
                >
                  처음
                </button>
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50"
                >
                  이전
                </button>
                <span className="px-3 py-1 text-sm">
                  {page} / {totalPages}
                </span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50"
                >
                  다음
                </button>
                <button
                  onClick={() => setPage(totalPages)}
                  disabled={page === totalPages}
                  className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50"
                >
                  마지막
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
