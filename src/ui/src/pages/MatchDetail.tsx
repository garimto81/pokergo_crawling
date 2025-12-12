// Match detail page - Full Side-by-Side comparison

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, Link } from 'react-router-dom';
import { fetchMatch, updateMatch } from '../api/matchApi';
import { StatusBadge } from '../components/common/StatusBadge';
import { ScoreIndicator } from '../components/common/ScoreIndicator';

export function MatchDetail() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const { data: match, isLoading, error } = useQuery({
    queryKey: ['match', id],
    queryFn: () => fetchMatch(Number(id)),
    enabled: !!id
  });

  const updateMutation = useMutation({
    mutationFn: (status: string) => updateMatch(Number(id), { match_status: status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['match', id] });
      queryClient.invalidateQueries({ queryKey: ['matches'] });
    }
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  if (error || !match) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500">Match not found</p>
        <Link to="/matches" className="text-blue-600 hover:underline mt-2 inline-block">
          Back to matches
        </Link>
      </div>
    );
  }

  const details = match.match_details
    ? match.match_details.split(',').map((d) => {
        const [name, score] = d.trim().split(':');
        return { name: name?.trim(), score: score?.trim() };
      })
    : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            to="/matches"
            className="text-gray-500 hover:text-gray-700"
          >
            &larr; Back
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">Match Detail #{id}</h1>
        </div>
        <div className="flex items-center gap-3">
          <ScoreIndicator score={match.match_score} />
          <StatusBadge status={match.match_status} />
        </div>
      </div>

      {/* Side-by-Side Comparison */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="grid grid-cols-1 lg:grid-cols-2">
          {/* NAS File Panel */}
          <div className="p-6 border-b lg:border-b-0 lg:border-r">
            <div className="flex items-center gap-2 mb-4">
              <span className="text-2xl">📁</span>
              <h2 className="text-lg font-semibold text-gray-900">NAS File</h2>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-gray-500 uppercase">Filename</label>
                <p className="text-sm font-medium text-gray-900 mt-1">{match.nas_filename}</p>
              </div>

              <div>
                <label className="text-xs font-medium text-gray-500 uppercase">Directory</label>
                <p className="text-sm text-gray-700 mt-1 break-all">{match.nas_directory}</p>
              </div>

              {match.nas_size_bytes && (
                <div>
                  <label className="text-xs font-medium text-gray-500 uppercase">Size</label>
                  <p className="text-sm text-gray-700 mt-1">
                    {(match.nas_size_bytes / (1024 * 1024 * 1024)).toFixed(2)} GB
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* YouTube Panel */}
          <div className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <span className="text-2xl">🎬</span>
              <h2 className="text-lg font-semibold text-gray-900">YouTube Match</h2>
            </div>

            {match.youtube_title ? (
              <div className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-gray-500 uppercase">Title</label>
                  <p className="text-sm font-medium text-gray-900 mt-1">{match.youtube_title}</p>
                </div>

                {match.youtube_video_id && (
                  <>
                    <div>
                      <label className="text-xs font-medium text-gray-500 uppercase">Video ID</label>
                      <p className="text-sm text-gray-700 mt-1">{match.youtube_video_id}</p>
                    </div>

                    <a
                      href={`https://www.youtube.com/watch?v=${match.youtube_video_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700"
                    >
                      ▶ Watch on YouTube
                    </a>
                  </>
                )}
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-gray-400 italic">No YouTube match found</p>
                <p className="text-sm text-gray-500 mt-2">
                  This file may not be uploaded yet
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Score Breakdown */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Match Score Breakdown</h3>

        <div className="flex items-center justify-center mb-6">
          <div className="text-center">
            <div className="text-5xl font-bold text-gray-900">{match.match_score}</div>
            <div className="text-sm text-gray-500 mt-1">/ 100</div>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {details.map((detail, i) => {
            const scoreValue = parseInt(detail.score?.replace(/[^0-9-]/g, '') || '0');
            const isPositive = scoreValue > 0;

            return (
              <div
                key={i}
                className={`p-4 rounded-lg text-center ${
                  isPositive ? 'bg-green-50' : 'bg-gray-50'
                }`}
              >
                <div className="text-sm font-medium text-gray-600 capitalize">
                  {detail.name?.replace('_', ' ')}
                </div>
                <div
                  className={`text-2xl font-bold mt-1 ${
                    isPositive ? 'text-green-600' : 'text-gray-400'
                  }`}
                >
                  {detail.score}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Actions */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Actions</h3>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => updateMutation.mutate('VERIFIED')}
            disabled={match.match_status === 'VERIFIED'}
            className="px-4 py-2 text-sm font-medium text-green-700 bg-green-100 rounded-md hover:bg-green-200 disabled:opacity-50"
          >
            ✓ Verify Match
          </button>
          <button
            onClick={() => updateMutation.mutate('WRONG_MATCH')}
            disabled={match.match_status === 'WRONG_MATCH'}
            className="px-4 py-2 text-sm font-medium text-red-700 bg-red-100 rounded-md hover:bg-red-200 disabled:opacity-50"
          >
            ✗ Mark as Wrong
          </button>
          <button
            onClick={() => updateMutation.mutate('NOT_UPLOADED')}
            className="px-4 py-2 text-sm font-medium text-orange-700 bg-orange-100 rounded-md hover:bg-orange-200"
          >
            Mark as Not Uploaded
          </button>
        </div>
      </div>
    </div>
  );
}
