// Match card component - Side-by-Side comparison

import { Link } from 'react-router-dom';
import type { Match } from '../../types/match';
import { StatusBadge } from '../common/StatusBadge';
import { ScoreIndicator } from '../common/ScoreIndicator';

interface MatchCardProps {
  match: Match;
  onVerify?: (id: number) => void;
  onReject?: (id: number) => void;
}

export function MatchCard({ match, onVerify, onReject }: MatchCardProps) {
  const details = match.match_details ? match.match_details.split(',').map(d => d.trim()) : [];

  return (
    <div className="bg-white rounded-lg shadow hover:shadow-md transition-shadow">
      {/* Header with score */}
      <div className="flex items-center justify-between px-4 py-3 border-b bg-gray-50">
        <div className="flex items-center gap-3">
          <ScoreIndicator score={match.match_score} />
          <StatusBadge status={match.match_status} />
        </div>
        <Link
          to={`/matches/${match.id}`}
          className="text-sm text-blue-600 hover:text-blue-800"
        >
          Details &rarr;
        </Link>
      </div>

      {/* Side-by-side comparison */}
      <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x">
        {/* NAS File (Left) */}
        <div className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg">📁</span>
            <span className="text-sm font-semibold text-gray-700">NAS File</span>
          </div>
          <p className="text-sm font-medium text-gray-900 truncate" title={match.nas_filename}>
            {match.nas_filename}
          </p>
          <p className="text-xs text-gray-500 truncate mt-1" title={match.nas_directory || ''}>
            {match.nas_directory?.split('\\').slice(-3).join(' / ')}
          </p>
          {match.nas_size_bytes && (
            <p className="text-xs text-gray-400 mt-1">
              {(match.nas_size_bytes / (1024 * 1024 * 1024)).toFixed(2)} GB
            </p>
          )}
        </div>

        {/* YouTube Match (Right) */}
        <div className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg">🎬</span>
            <span className="text-sm font-semibold text-gray-700">YouTube</span>
          </div>
          {match.youtube_title ? (
            <>
              <p className="text-sm font-medium text-gray-900 truncate" title={match.youtube_title}>
                {match.youtube_title}
              </p>
              {match.youtube_video_id && (
                <a
                  href={`https://www.youtube.com/watch?v=${match.youtube_video_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-blue-600 hover:underline mt-1 inline-block"
                >
                  Watch on YouTube &rarr;
                </a>
              )}
            </>
          ) : (
            <p className="text-sm text-gray-400 italic">No match found</p>
          )}
        </div>
      </div>

      {/* Match details */}
      {details.length > 0 && (
        <div className="px-4 py-2 bg-gray-50 border-t">
          <div className="flex flex-wrap gap-2">
            {details.slice(0, 4).map((detail, i) => (
              <span
                key={i}
                className={`text-xs px-2 py-0.5 rounded ${
                  detail.includes('+') && !detail.includes('+0')
                    ? 'bg-green-100 text-green-700'
                    : 'bg-gray-100 text-gray-600'
                }`}
              >
                {detail}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 px-4 py-3 border-t">
        {onVerify && (
          <button
            onClick={() => onVerify(match.id)}
            className="px-3 py-1.5 text-sm font-medium text-green-700 bg-green-100 rounded hover:bg-green-200 transition"
          >
            ✓ Verify
          </button>
        )}
        {onReject && (
          <button
            onClick={() => onReject(match.id)}
            className="px-3 py-1.5 text-sm font-medium text-red-700 bg-red-100 rounded hover:bg-red-200 transition"
          >
            ✗ Wrong
          </button>
        )}
      </div>
    </div>
  );
}
