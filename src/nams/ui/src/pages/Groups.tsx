import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { groupsApi } from '../api/client';
import { Search, ChevronLeft, ChevronRight, ChevronDown, ChevronUp } from 'lucide-react';
import type { AssetGroupDetail } from '../types';

function GroupDetail({ group }: { group: AssetGroupDetail }) {
  return (
    <div className="bg-gray-50 p-4 border-t">
      <h4 className="font-medium mb-2">Files in this group:</h4>
      <div className="space-y-2">
        {group.files.map((file) => (
          <div key={file.id} className="flex items-center justify-between text-sm">
            <span className={file.role === 'primary' ? 'font-medium text-green-700' : 'text-gray-600'}>
              {file.role === 'primary' && '[Primary] '}
              {file.filename}
            </span>
            <span className="text-gray-400">{file.size_formatted}</span>
          </div>
        ))}
      </div>
      {group.pokergo_title && (
        <div className="mt-4 pt-4 border-t">
          <p className="text-sm text-gray-500">PokerGO Match:</p>
          <p className="font-medium text-purple-700">{group.pokergo_title}</p>
          <p className="text-xs text-gray-400">Score: {((group.pokergo_match_score || 0) * 100).toFixed(0)}%</p>
        </div>
      )}
    </div>
  );
}

export function Groups() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [yearFilter, setYearFilter] = useState<number | undefined>();
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['groups', { page, search, year: yearFilter }],
    queryFn: () => groupsApi.list({ page, page_size: 30, search, year: yearFilter }),
  });

  const { data: groupDetail } = useQuery({
    queryKey: ['group', expandedId],
    queryFn: () => groupsApi.get(expandedId!),
    enabled: expandedId !== null,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Groups</h1>
        <span className="text-sm text-gray-500">
          {data?.total.toLocaleString()} groups total
        </span>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-64">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search group ID..."
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <select
            value={yearFilter || ''}
            onChange={(e) => { setYearFilter(e.target.value ? Number(e.target.value) : undefined); setPage(1); }}
            className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Years</option>
            {Array.from({ length: 55 }, (_, i) => 2025 - i).map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-12">Loading...</div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="w-10"></th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Group ID</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Year</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Region</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ep</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Files</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Size</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">PokerGO</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {data?.items.map((group) => (
                <>
                  <tr
                    key={group.id}
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => setExpandedId(expandedId === group.id ? null : group.id)}
                  >
                    <td className="pl-4">
                      {expandedId === group.id ? (
                        <ChevronUp className="w-4 h-4 text-gray-400" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-gray-400" />
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{group.group_id}</td>
                    <td className="px-6 py-4 text-sm text-gray-500">{group.year}</td>
                    <td className="px-6 py-4 text-sm text-gray-500">{group.region_code || '-'}</td>
                    <td className="px-6 py-4 text-sm text-gray-500">{group.event_type_code || '-'}</td>
                    <td className="px-6 py-4 text-sm text-gray-500">{group.episode || '-'}</td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {group.file_count}
                      {group.has_backup && (
                        <span className="ml-1 text-xs text-green-600">(+backup)</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">{group.total_size_formatted}</td>
                    <td className="px-6 py-4">
                      {group.has_pokergo_match ? (
                        <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs">Matched</span>
                      ) : (
                        <span className="text-gray-400 text-xs">-</span>
                      )}
                    </td>
                  </tr>
                  {expandedId === group.id && groupDetail && (
                    <tr key={`${group.id}-detail`}>
                      <td colSpan={9}>
                        <GroupDetail group={groupDetail} />
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        )}

        {/* Pagination */}
        {data && data.total_pages > 1 && (
          <div className="bg-gray-50 px-6 py-3 flex items-center justify-between border-t">
            <div className="text-sm text-gray-500">
              Page {data.page} of {data.total_pages}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-2 rounded border disabled:opacity-50 hover:bg-gray-100"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setPage(p => Math.min(data.total_pages, p + 1))}
                disabled={page === data.total_pages}
                className="p-2 rounded border disabled:opacity-50 hover:bg-gray-100"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
