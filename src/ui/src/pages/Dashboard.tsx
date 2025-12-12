// Dashboard page

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { StatsSummary, NotUploadedCategories, ScoreDistribution } from '../types/match';

// 동적 API URL: 현재 호스트 기반으로 API 서버 주소 결정
const API_BASE = `http://${window.location.hostname}:8001/api`;

export function Dashboard() {
  const [stats, setStats] = useState<StatsSummary | null>(null);
  const [categories, setCategories] = useState<NotUploadedCategories | null>(null);
  const [distribution, setDistribution] = useState<ScoreDistribution | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);

        const [statsRes, catRes, distRes] = await Promise.all([
          fetch(`${API_BASE}/stats/summary`),
          fetch(`${API_BASE}/stats/not-uploaded-categories`),
          fetch(`${API_BASE}/stats/score-distribution?bins=10`)
        ]);

        if (!statsRes.ok) throw new Error('Failed to load stats');

        setStats(await statsRes.json());
        setCategories(await catRes.json());
        setDistribution(await distRes.json());
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data');
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-gray-500">Loading dashboard...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <p className="text-red-600 font-medium">Error: {error}</p>
        <p className="text-sm text-red-500 mt-2">
          Make sure the API server is running: uvicorn src.api.main:app --reload
        </p>
      </div>
    );
  }

  const chartData = distribution?.bins.map((bin, i) => ({
    range: `${bin}-${bin + 9}`,
    count: distribution.counts[i]
  })) || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <div className="flex gap-2">
          <a
            href={`${API_BASE}/export/report?format=csv`}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border rounded-md hover:bg-gray-50"
          >
            Export CSV
          </a>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="w-3 h-3 rounded-full bg-blue-500 mr-3" />
              <span className="text-sm font-medium text-gray-500">Total NAS Files</span>
            </div>
            <div className="mt-2">
              <span className="text-3xl font-bold text-gray-900">{stats.total}</span>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="w-3 h-3 rounded-full bg-green-500 mr-3" />
              <span className="text-sm font-medium text-gray-500">Matched</span>
            </div>
            <div className="mt-2 flex items-baseline">
              <span className="text-3xl font-bold text-gray-900">
                {stats.by_status.MATCHED + stats.by_status.LIKELY}
              </span>
              <span className="ml-2 text-sm text-gray-500">({stats.match_rate}%)</span>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="w-3 h-3 rounded-full bg-yellow-500 mr-3" />
              <span className="text-sm font-medium text-gray-500">Need Review</span>
            </div>
            <div className="mt-2 flex items-baseline">
              <span className="text-3xl font-bold text-gray-900">{stats.by_status.POSSIBLE}</span>
              <span className="ml-2 text-sm text-gray-500">
                ({((stats.by_status.POSSIBLE / stats.total) * 100).toFixed(1)}%)
              </span>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="w-3 h-3 rounded-full bg-red-500 mr-3" />
              <span className="text-sm font-medium text-gray-500">Not Uploaded</span>
            </div>
            <div className="mt-2 flex items-baseline">
              <span className="text-3xl font-bold text-gray-900">{stats.by_status.NOT_UPLOADED}</span>
              <span className="ml-2 text-sm text-gray-500">
                ({((stats.by_status.NOT_UPLOADED / stats.total) * 100).toFixed(1)}%)
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Score Distribution */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Score Distribution</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="range" fontSize={12} />
                <YAxis fontSize={12} />
                <Tooltip />
                <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Not Uploaded Categories */}
        {categories && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Not Uploaded by Category ({categories.total} files)
            </h3>
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {categories.categories.slice(0, 8).map((cat, i) => (
                <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {cat.directory.split('\\').slice(-2).join(' / ')}
                    </p>
                  </div>
                  <span className="ml-2 px-2 py-1 text-sm font-medium text-red-700 bg-red-100 rounded">
                    {cat.count}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          to="/matches"
          className="p-6 bg-white rounded-lg shadow hover:shadow-md transition-shadow"
        >
          <h3 className="text-lg font-semibold text-gray-900">View All Matches</h3>
          <p className="text-sm text-gray-500 mt-1">Browse all {stats?.total || 0} matches</p>
        </Link>

        <Link
          to="/not-uploaded"
          className="p-6 bg-white rounded-lg shadow hover:shadow-md transition-shadow"
        >
          <h3 className="text-lg font-semibold text-gray-900">Manage Not Uploaded</h3>
          <p className="text-sm text-gray-500 mt-1">
            {stats?.by_status.NOT_UPLOADED || 0} files not on YouTube
          </p>
        </Link>

        <Link
          to="/matches?status=POSSIBLE"
          className="p-6 bg-white rounded-lg shadow hover:shadow-md transition-shadow"
        >
          <h3 className="text-lg font-semibold text-gray-900">Review Possible</h3>
          <p className="text-sm text-gray-500 mt-1">
            {stats?.by_status.POSSIBLE || 0} matches need review
          </p>
        </Link>
      </div>
    </div>
  );
}
