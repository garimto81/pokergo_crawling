// Not uploaded categories breakdown

import type { NotUploadedCategories } from '../../types/match';

interface CategoryBreakdownProps {
  data: NotUploadedCategories;
}

export function CategoryBreakdown({ data }: CategoryBreakdownProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Not Uploaded by Category ({data.total} files)
      </h3>
      <div className="space-y-3 max-h-80 overflow-y-auto">
        {data.categories.slice(0, 10).map((cat, i) => (
          <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {cat.directory.split('\\').slice(-2).join(' / ')}
              </p>
              <p className="text-xs text-gray-500">
                {cat.files.slice(0, 2).map(f => f.filename.slice(0, 30)).join(', ')}...
              </p>
            </div>
            <span className="ml-2 px-2 py-1 text-sm font-medium text-red-700 bg-red-100 rounded">
              {cat.count}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
