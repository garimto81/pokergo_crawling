// Filter bar component

import { useMatchStore } from '../../stores/matchStore';

const statusOptions: { value: string; label: string }[] = [
  { value: '', label: 'All Status' },
  { value: 'MATCHED', label: 'Matched' },
  { value: 'LIKELY', label: 'Likely' },
  { value: 'POSSIBLE', label: 'Possible' },
  { value: 'NOT_UPLOADED', label: 'Not Uploaded' },
  { value: 'VERIFIED', label: 'Verified' }
];

const scoreRanges = [
  { value: '', label: 'All Scores' },
  { value: '80-100', label: '80-100 (High)' },
  { value: '60-79', label: '60-79 (Medium)' },
  { value: '40-59', label: '40-59 (Low)' },
  { value: '0-39', label: '0-39 (Not Match)' }
];

export function FilterBar() {
  const { filters, setFilters, resetFilters } = useMatchStore();

  const handleStatusChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setFilters({ status: e.target.value || undefined });
  };

  const handleScoreChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    if (!value) {
      setFilters({ score_min: undefined, score_max: undefined });
    } else {
      const [min, max] = value.split('-').map(Number);
      setFilters({ score_min: min, score_max: max });
    }
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilters({ search: e.target.value || undefined });
  };

  return (
    <div className="bg-white rounded-lg shadow p-4 mb-6">
      <div className="flex flex-wrap gap-4 items-center">
        {/* Search */}
        <div className="flex-1 min-w-[200px]">
          <input
            type="text"
            placeholder="Search filename or title..."
            value={filters.search || ''}
            onChange={handleSearchChange}
            className="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Status filter */}
        <select
          value={filters.status || ''}
          onChange={handleStatusChange}
          className="px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500"
        >
          {statusOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        {/* Score filter */}
        <select
          value={
            filters.score_min !== undefined
              ? `${filters.score_min}-${filters.score_max}`
              : ''
          }
          onChange={handleScoreChange}
          className="px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500"
        >
          {scoreRanges.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        {/* Reset */}
        <button
          onClick={resetFilters}
          className="px-3 py-2 text-sm text-gray-600 hover:text-gray-900 transition"
        >
          Reset
        </button>
      </div>
    </div>
  );
}
