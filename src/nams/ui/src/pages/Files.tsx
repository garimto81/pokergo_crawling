import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { filesApi } from '../api/client';
import { Search, ChevronLeft, ChevronRight } from 'lucide-react';

export function Files() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [yearFilter, setYearFilter] = useState<number | undefined>();
  const [hasGroup, setHasGroup] = useState<boolean | undefined>();

  const { data, isLoading } = useQuery({
    queryKey: ['files', { page, search, year: yearFilter, has_group: hasGroup }],
    queryFn: () => filesApi.list({ page, page_size: 50, search, year: yearFilter, has_group: hasGroup }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Files</h1>
        <span className="text-sm text-gray-500">
          {data?.total.toLocaleString()} files total
        </span>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex flex-wrap gap-4">
          {/* Search */}
          <div className="flex-1 min-w-64">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search filename..."
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          {/* Year filter */}
          <select
            value={yearFilter || ''}
            onChange={(e) => { setYearFilter(e.target.value ? Number(e.target.value) : undefined); setPage(1); }}
            className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Years</option>
            {Array.from({ length: 30 }, (_, i) => 2025 - i).map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>

          {/* Group filter */}
          <select
            value={hasGroup === undefined ? '' : hasGroup ? 'yes' : 'no'}
            onChange={(e) => {
              setHasGroup(e.target.value === '' ? undefined : e.target.value === 'yes');
              setPage(1);
            }}
            className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Files</option>
            <option value="yes">Has Group</option>
            <option value="no">No Group</option>
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
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Filename</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Size</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Year</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Region</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Group</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {data?.items.map((file) => (
                <tr key={file.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900 truncate max-w-md" title={file.filename}>
                      {file.filename}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">{file.size_formatted}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">{file.year || '-'}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">{file.region_code || '-'}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">{file.event_type_code || '-'}</td>
                  <td className="px-6 py-4 text-sm">
                    {file.group_id ? (
                      <span className="text-blue-600">{file.group_id}</span>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`px-2 py-1 rounded text-xs ${
                      file.role === 'primary' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                    }`}>
                      {file.role}
                    </span>
                  </td>
                </tr>
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
