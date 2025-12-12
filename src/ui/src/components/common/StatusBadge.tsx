// Status badge component

import type { MatchStatus } from '../../types/match';

interface StatusBadgeProps {
  status: MatchStatus;
  size?: 'sm' | 'md';
}

const statusConfig: Record<MatchStatus, { bg: string; text: string; label: string }> = {
  MATCHED: { bg: 'bg-green-100', text: 'text-green-800', label: 'Matched' },
  LIKELY: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Likely' },
  POSSIBLE: { bg: 'bg-orange-100', text: 'text-orange-800', label: 'Possible' },
  NOT_UPLOADED: { bg: 'bg-red-100', text: 'text-red-800', label: 'Not Uploaded' },
  VERIFIED: { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Verified' },
  WRONG_MATCH: { bg: 'bg-gray-100', text: 'text-gray-800', label: 'Wrong' },
  MANUAL_MATCH: { bg: 'bg-purple-100', text: 'text-purple-800', label: 'Manual' },
  UPLOAD_PLANNED: { bg: 'bg-cyan-100', text: 'text-cyan-800', label: 'Planned' },
  EXCLUDED: { bg: 'bg-gray-100', text: 'text-gray-500', label: 'Excluded' }
};

export function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const config = statusConfig[status] || statusConfig.POSSIBLE;
  const sizeClass = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm';

  return (
    <span className={`inline-flex items-center rounded-full font-medium ${config.bg} ${config.text} ${sizeClass}`}>
      {config.label}
    </span>
  );
}
