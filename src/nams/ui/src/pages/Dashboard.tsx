import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { statsApi, processApi } from '../api/client';
import {
  Files, FolderTree, HardDrive, Link2,
  RefreshCw, Download, FileSpreadsheet, Upload,
  CheckCircle, AlertTriangle, XCircle, Database
} from 'lucide-react';

function StatCard({ title, value, subtitle, icon: Icon, color }: {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ElementType;
  color: string;
}) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
        </div>
        <div className={`p-3 rounded-full ${color}`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
      </div>
    </div>
  );
}

// Scan Modal Component
function ScanModal({ isOpen, onClose, onScan }: {
  isOpen: boolean;
  onClose: () => void;
  onScan: (mode: 'incremental' | 'full', folderType: 'origin' | 'archive' | 'both', originPath: string, archivePath: string) => void;
}) {
  const [mode, setMode] = useState<'incremental' | 'full'>('incremental');
  const [folderType, setFolderType] = useState<'origin' | 'archive' | 'both'>('both');
  const [originPath, setOriginPath] = useState('Y:/WSOP Backup');
  const [archivePath, setArchivePath] = useState('Z:/archive');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-lg">
        <h2 className="text-xl font-bold text-gray-900 mb-4">NAS Scan</h2>

        {/* Paths */}
        <div className="mb-4 space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Origin Path</label>
            <input
              type="text"
              value={originPath}
              onChange={(e) => setOriginPath(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Y:/WSOP Backup"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Archive Path</label>
            <input
              type="text"
              value={archivePath}
              onChange={(e) => setArchivePath(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Z:/archive"
            />
          </div>
        </div>

        {/* Scan Mode */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">Scan Mode</label>
          <div className="flex space-x-4">
            <label className="flex items-center">
              <input
                type="radio"
                name="mode"
                value="incremental"
                checked={mode === 'incremental'}
                onChange={() => setMode('incremental')}
                className="mr-2"
              />
              <span className="text-sm">Incremental (추가분만)</span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                name="mode"
                value="full"
                checked={mode === 'full'}
                onChange={() => setMode('full')}
                className="mr-2"
              />
              <span className="text-sm">Full (전체 재스캔)</span>
            </label>
          </div>
        </div>

        {/* Folder Type */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">Folder</label>
          <div className="flex space-x-4">
            <label className="flex items-center">
              <input
                type="radio"
                name="folder"
                value="both"
                checked={folderType === 'both'}
                onChange={() => setFolderType('both')}
                className="mr-2"
              />
              <span className="text-sm">Both</span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                name="folder"
                value="origin"
                checked={folderType === 'origin'}
                onChange={() => setFolderType('origin')}
                className="mr-2"
              />
              <span className="text-sm">Origin Only</span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                name="folder"
                value="archive"
                checked={folderType === 'archive'}
                onChange={() => setFolderType('archive')}
                className="mr-2"
              />
              <span className="text-sm">Archive Only</span>
            </label>
          </div>
        </div>

        {/* Buttons */}
        <div className="flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 hover:text-gray-800"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              onScan(mode, folderType, originPath, archivePath);
              onClose();
            }}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Start Scan
          </button>
        </div>
      </div>
    </div>
  );
}

// Export Modal Component
function ExportModal({ isOpen, onClose, onExport, googleSheetsAvailable }: {
  isOpen: boolean;
  onClose: () => void;
  onExport: (format: 'csv' | 'json' | 'google_sheets') => void;
  googleSheetsAvailable: boolean;
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Export Data</h2>

        <div className="space-y-3">
          <button
            onClick={() => {
              onExport('csv');
              onClose();
            }}
            className="w-full flex items-center p-4 border rounded-lg hover:bg-gray-50"
          >
            <Download className="w-6 h-6 text-green-600 mr-3" />
            <div className="text-left">
              <p className="font-medium">CSV File</p>
              <p className="text-sm text-gray-500">Download as CSV file</p>
            </div>
          </button>

          <button
            onClick={() => {
              onExport('json');
              onClose();
            }}
            className="w-full flex items-center p-4 border rounded-lg hover:bg-gray-50"
          >
            <FileSpreadsheet className="w-6 h-6 text-blue-600 mr-3" />
            <div className="text-left">
              <p className="font-medium">JSON File</p>
              <p className="text-sm text-gray-500">Download as JSON file</p>
            </div>
          </button>

          <button
            onClick={() => {
              onExport('google_sheets');
              onClose();
            }}
            disabled={!googleSheetsAvailable}
            className={`w-full flex items-center p-4 border rounded-lg ${
              googleSheetsAvailable ? 'hover:bg-gray-50' : 'opacity-50 cursor-not-allowed'
            }`}
          >
            <FileSpreadsheet className="w-6 h-6 text-green-500 mr-3" />
            <div className="text-left">
              <p className="font-medium">Google Sheets</p>
              <p className="text-sm text-gray-500">
                {googleSheetsAvailable
                  ? 'Export to Google Sheets'
                  : 'API not configured'}
              </p>
            </div>
          </button>
        </div>

        <div className="flex justify-end mt-4">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 hover:text-gray-800"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

export function Dashboard() {
  const queryClient = useQueryClient();
  const [showScanModal, setShowScanModal] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const { data: stats, isLoading } = useQuery({
    queryKey: ['stats', 'overview'],
    queryFn: statsApi.getOverview,
  });

  const { data: yearStats } = useQuery({
    queryKey: ['stats', 'byYear'],
    queryFn: statsApi.getByYear,
  });

  const { data: regionStats } = useQuery({
    queryKey: ['stats', 'byRegion'],
    queryFn: statsApi.getByRegion,
  });

  const { data: unclassified } = useQuery({
    queryKey: ['stats', 'unclassified'],
    queryFn: statsApi.getUnclassified,
  });

  const { data: googleSheetsStatus } = useQuery({
    queryKey: ['googleSheetsStatus'],
    queryFn: processApi.getGoogleSheetsStatus,
  });

  const { data: matchingSummary } = useQuery({
    queryKey: ['stats', 'matchingSummary'],
    queryFn: statsApi.getMatchingSummary,
  });

  const { data: syncStatus } = useQuery({
    queryKey: ['stats', 'syncStatus'],
    queryFn: statsApi.getSyncStatus,
  });

  // Scan mutation
  const scanMutation = useMutation({
    mutationFn: (params: { mode: 'incremental' | 'full'; folderType: 'origin' | 'archive' | 'both'; originPath: string; archivePath: string }) =>
      processApi.scan({ mode: params.mode, folder_type: params.folderType, origin_path: params.originPath, archive_path: params.archivePath }),
    onSuccess: (data) => {
      if (data.success) {
        setMessage({ type: 'success', text: data.message });
        queryClient.invalidateQueries({ queryKey: ['stats'] });
      } else {
        setMessage({ type: 'error', text: data.message });
      }
    },
    onError: (error: Error) => {
      setMessage({ type: 'error', text: error.message });
    },
  });

  // Export mutation
  const exportMutation = useMutation({
    mutationFn: (format: 'csv' | 'json' | 'google_sheets') =>
      processApi.export({ format }),
    onSuccess: (data) => {
      if (data.success) {
        setMessage({ type: 'success', text: data.message });
        if (data.url) {
          window.open(data.url, '_blank');
        }
      } else {
        setMessage({ type: 'error', text: data.message });
      }
    },
    onError: (error: Error) => {
      setMessage({ type: 'error', text: error.message });
    },
  });

  // Migration mutation
  const migrateMutation = useMutation({
    mutationFn: () => processApi.migrate(true),
    onSuccess: (data) => {
      if (data.success) {
        setMessage({ type: 'success', text: data.message });
        queryClient.invalidateQueries({ queryKey: ['stats'] });
      } else {
        setMessage({ type: 'error', text: data.message });
      }
    },
    onError: (error: Error) => {
      setMessage({ type: 'error', text: error.message });
    },
  });

  if (isLoading) {
    return <div className="flex justify-center py-12">Loading...</div>;
  }

  const isProcessing = scanMutation.isPending || exportMutation.isPending || migrateMutation.isPending;

  return (
    <div className="space-y-8">
      {/* Header with Actions */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <div className="flex space-x-3">
          <button
            onClick={() => setShowScanModal(true)}
            disabled={isProcessing}
            className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${scanMutation.isPending ? 'animate-spin' : ''}`} />
            NAS Scan
          </button>
          <button
            onClick={() => setShowExportModal(true)}
            disabled={isProcessing}
            className="flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
          >
            <Download className={`w-4 h-4 mr-2 ${exportMutation.isPending ? 'animate-pulse' : ''}`} />
            Export
          </button>
          <button
            onClick={() => migrateMutation.mutate()}
            disabled={isProcessing}
            className="flex items-center px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
          >
            <Upload className={`w-4 h-4 mr-2 ${migrateMutation.isPending ? 'animate-pulse' : ''}`} />
            Import JSON
          </button>
        </div>
      </div>

      {/* Message */}
      {message && (
        <div className={`p-4 rounded-lg ${
          message.type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'
        }`}>
          {message.text}
          <button
            onClick={() => setMessage(null)}
            className="float-right text-gray-500 hover:text-gray-700"
          >
            &times;
          </button>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Files"
          value={stats?.total_files.toLocaleString() || 0}
          subtitle={stats?.total_size_formatted}
          icon={Files}
          color="bg-blue-500"
        />
        <StatCard
          title="Total Groups"
          value={stats?.total_groups.toLocaleString() || 0}
          subtitle={`${stats?.match_rate.toFixed(1)}% grouped`}
          icon={FolderTree}
          color="bg-green-500"
        />
        <StatCard
          title="PokerGO Matched"
          value={stats?.pokergo_matched_groups || 0}
          subtitle={`${stats?.pokergo_match_rate.toFixed(1)}% match rate`}
          icon={Link2}
          color="bg-purple-500"
        />
        <StatCard
          title="Unmatched"
          value={stats?.unmatched_files || 0}
          subtitle="files without group"
          icon={HardDrive}
          color="bg-orange-500"
        />
      </div>

      {/* 4-Category Matching Summary */}
      {matchingSummary && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">4-Category Matching Status</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-green-800">MATCHED</p>
                  <p className="text-2xl font-bold text-green-900">{matchingSummary.MATCHED}</p>
                  <p className="text-xs text-green-600">NAS + PokerGO</p>
                </div>
                <CheckCircle className="w-8 h-8 text-green-500" />
              </div>
            </div>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-800">NAS_ONLY_HISTORIC</p>
                  <p className="text-2xl font-bold text-gray-900">{matchingSummary.NAS_ONLY_HISTORIC}</p>
                  <p className="text-xs text-gray-600">Pre-2011 (No PokerGO)</p>
                </div>
                <Database className="w-8 h-8 text-gray-500" />
              </div>
            </div>
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-yellow-800">NAS_ONLY_MODERN</p>
                  <p className="text-2xl font-bold text-yellow-900">{matchingSummary.NAS_ONLY_MODERN}</p>
                  <p className="text-xs text-yellow-600">2011+ (Needs Review)</p>
                </div>
                <AlertTriangle className="w-8 h-8 text-yellow-500" />
              </div>
            </div>
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-red-800">POKERGO_ONLY</p>
                  <p className="text-2xl font-bold text-red-900">{matchingSummary.POKERGO_ONLY}</p>
                  <p className="text-xs text-red-600">No NAS File</p>
                </div>
                <XCircle className="w-8 h-8 text-red-500" />
              </div>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-gray-200 flex justify-between text-sm text-gray-500">
            <span>Total NAS Groups: {matchingSummary.total_nas_groups}</span>
            <span>Total PokerGO Episodes: {matchingSummary.total_pokergo_episodes}</span>
          </div>
        </div>
      )}

      {/* Origin/Archive Sync Status */}
      {syncStatus && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Origin/Archive Sync Status</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm font-medium text-blue-800">Origin Files</p>
              <p className="text-2xl font-bold text-blue-900">{syncStatus.origin_files}</p>
              <p className="text-xs text-blue-600">Primary: {syncStatus.origin_primary}</p>
            </div>
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
              <p className="text-sm font-medium text-purple-800">Archive Files</p>
              <p className="text-2xl font-bold text-purple-900">{syncStatus.archive_files}</p>
              <p className="text-xs text-purple-600">
                {syncStatus.has_role_conflict ? (
                  <span className="text-red-600">Primary: {syncStatus.archive_primary} (Conflict!)</span>
                ) : (
                  <span>Primary: {syncStatus.archive_primary}</span>
                )}
              </p>
            </div>
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <p className="text-sm font-medium text-green-800">Shared Groups</p>
              <p className="text-2xl font-bold text-green-900">{syncStatus.shared_groups}</p>
              <p className="text-xs text-green-600">Origin + Archive</p>
            </div>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <p className="text-sm font-medium text-gray-800">Exclusive Groups</p>
              <p className="text-lg font-bold text-gray-900">
                O: {syncStatus.origin_only_groups} / A: {syncStatus.archive_only_groups}
              </p>
              <p className="text-xs text-gray-600">Origin Only / Archive Only</p>
            </div>
          </div>
        </div>
      )}

      {/* Year Distribution */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Year Distribution</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {yearStats?.slice(0, 12).map((year) => (
            <div key={year.year} className="bg-gray-50 rounded p-3">
              <p className="text-lg font-bold text-gray-900">{year.year}</p>
              <p className="text-sm text-gray-500">{year.file_count} files</p>
              <p className="text-sm text-gray-500">{year.group_count} groups</p>
            </div>
          ))}
        </div>
      </div>

      {/* Region Distribution */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Region Distribution</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {regionStats?.map((region) => (
            <div key={region.region_code} className="bg-gray-50 rounded p-3">
              <p className="text-lg font-bold text-gray-900">{region.region_code}</p>
              <p className="text-xs text-gray-400">{region.region_name}</p>
              <p className="text-sm text-gray-500 mt-1">{region.file_count} files</p>
            </div>
          ))}
        </div>
      </div>

      {/* Unclassified Alert */}
      {unclassified && (unclassified.no_group > 0 || unclassified.unknown_type > 0) && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-yellow-800 mb-2">Attention Needed</h3>
          <ul className="list-disc list-inside text-sm text-yellow-700 space-y-1">
            {unclassified.no_group > 0 && (
              <li>{unclassified.no_group} files without group</li>
            )}
            {unclassified.unknown_type > 0 && (
              <li>{unclassified.unknown_type} files with unknown type</li>
            )}
            {unclassified.no_year > 0 && (
              <li>{unclassified.no_year} files without year</li>
            )}
          </ul>
        </div>
      )}

      {/* Modals */}
      <ScanModal
        isOpen={showScanModal}
        onClose={() => setShowScanModal(false)}
        onScan={(mode, folderType, originPath, archivePath) => scanMutation.mutate({ mode, folderType, originPath, archivePath })}
      />
      <ExportModal
        isOpen={showExportModal}
        onClose={() => setShowExportModal(false)}
        onExport={(format) => exportMutation.mutate(format)}
        googleSheetsAvailable={googleSheetsStatus?.available || false}
      />
    </div>
  );
}
