// Stats cards component

import type { StatsSummary } from '../../types/match';

interface StatsCardsProps {
  stats: StatsSummary;
}

export function StatsCards({ stats }: StatsCardsProps) {
  const cards = [
    {
      label: 'Total NAS Files',
      value: stats.total,
      color: 'bg-blue-500'
    },
    {
      label: 'Matched',
      value: stats.by_status.MATCHED + stats.by_status.LIKELY,
      percent: stats.match_rate,
      color: 'bg-green-500'
    },
    {
      label: 'Need Review',
      value: stats.by_status.POSSIBLE,
      percent: (stats.by_status.POSSIBLE / stats.total) * 100,
      color: 'bg-yellow-500'
    },
    {
      label: 'Not Uploaded',
      value: stats.by_status.NOT_UPLOADED,
      percent: (stats.by_status.NOT_UPLOADED / stats.total) * 100,
      color: 'bg-red-500'
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card) => (
        <div key={card.label} className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className={`w-3 h-3 rounded-full ${card.color} mr-3`} />
            <span className="text-sm font-medium text-gray-500">{card.label}</span>
          </div>
          <div className="mt-2 flex items-baseline">
            <span className="text-3xl font-bold text-gray-900">{card.value}</span>
            {card.percent !== undefined && (
              <span className="ml-2 text-sm text-gray-500">
                ({card.percent.toFixed(1)}%)
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
