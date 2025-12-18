import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ChevronRight, ChevronDown, CheckCircle, FileVideo,
  HardDrive, Calendar, Layers, Film, FolderOpen, Copy, Cloud, Check
} from 'lucide-react';
import {
  contentTreeApi, entriesApi,
} from '../api/client';
import type {
  TreeYear, TreeCategory, TreeEventType, TreeEntry,
} from '../api/client';
import type { CategoryEntryDetail } from '../types';

// KPI Bar Component
function KPIBar({ summary }: { summary: {
  total_entries: number;
  exact_count: number;
  none_count: number;
  pokergo_only_count?: number;
  exact_rate: number;
  total_size_gb: number;
  year_count: number;
}}) {
  const formatSize = (gb: number) => {
    if (gb >= 1000) return `${(gb / 1000).toFixed(1)} TB`;
    return `${gb.toFixed(0)} GB`;
  };

  return (
    <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-6 py-4 rounded-lg shadow-lg">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-6 flex-wrap">
          <div className="flex items-center gap-2">
            <Film className="w-5 h-5" />
            <span className="text-2xl font-bold">{summary.total_entries}</span>
            <span className="text-blue-100">Entries</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-green-300" />
            <span className="text-xl font-semibold">{summary.exact_count}</span>
            <span className="text-blue-100">EXACT</span>
          </div>
          <div className="flex items-center gap-2">
            <HardDrive className="w-5 h-5 text-gray-300" />
            <span className="text-xl font-semibold">{summary.none_count}</span>
            <span className="text-blue-100">NAS Only</span>
          </div>
          <div className="flex items-center gap-2">
            <Cloud className="w-5 h-5 text-purple-300" />
            <span className="text-xl font-semibold">{summary.pokergo_only_count || 0}</span>
            <span className="text-blue-100">PokerGO Only</span>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <HardDrive className="w-5 h-5" />
            <span className="font-semibold">{formatSize(summary.total_size_gb)}</span>
          </div>
          <div className="flex items-center gap-2">
            <Calendar className="w-5 h-5" />
            <span className="font-semibold">{summary.year_count} Years</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// Match Badge Component
function MatchBadge({ matchType }: { matchType: string | null }) {
  if (matchType === 'EXACT') {
    return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">EXACT</span>;
  }
  if (matchType === 'NONE') {
    return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">NAS Only</span>;
  }
  if (matchType === 'POKERGO_ONLY') {
    return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800">PokerGO Only</span>;
  }
  return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">{matchType || 'N/A'}</span>;
}

// File Card Component with Copy functionality
function FileCard({ file, formatSize }: {
  file: {
    id: number;
    filename: string;
    drive?: string;
    folder?: string;
    size_bytes: number;
    role?: string;
  };
  formatSize: (bytes: number) => string;
}) {
  const [copied, setCopied] = useState(false);

  const folderPath = file.drive && file.folder
    ? `${file.drive}\\${file.folder}`
    : file.drive || '';
  const fullPath = folderPath ? `${folderPath}\\${file.filename}` : file.filename;

  const handleCopyPath = async () => {
    try {
      await navigator.clipboard.writeText(fullPath);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = fullPath;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div
      className={`p-3 rounded-lg border ${
        file.role === 'PRIMARY' ? 'bg-green-50 border-green-200' : 'bg-gray-50 border-gray-200'
      }`}
    >
      <div className="flex items-center gap-3">
        <span className={`text-xs font-medium px-2 py-1 rounded ${
          file.role === 'PRIMARY' ? 'bg-green-200 text-green-800' : 'bg-gray-200 text-gray-600'
        }`}>
          {file.role || 'BACKUP'}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">{file.filename}</p>
          <p className="text-xs text-gray-500">{formatSize(file.size_bytes)}</p>
        </div>
      </div>
      <div className="mt-2 flex items-center gap-2">
        <div
          onClick={handleCopyPath}
          className="flex-1 flex items-center gap-2 bg-white rounded px-2 py-1.5 border cursor-pointer hover:bg-blue-50 hover:border-blue-300 transition-colors group"
          title="Click to copy path"
        >
          <FolderOpen className="w-4 h-4 text-gray-400 flex-shrink-0 group-hover:text-blue-500" />
          <span className="text-xs text-gray-600 truncate font-mono group-hover:text-blue-700">{fullPath}</span>
        </div>
        <button
          onClick={handleCopyPath}
          className={`p-1.5 rounded transition-colors ${
            copied
              ? 'bg-green-100 text-green-600'
              : 'hover:bg-blue-100 text-gray-500 hover:text-blue-600'
          }`}
          title={copied ? 'Copied!' : 'Copy Path'}
        >
          {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
        </button>
      </div>
    </div>
  );
}

// Tree Node Components
function EntryNode({ entry, isSelected, onClick }: {
  entry: TreeEntry;
  isSelected: boolean;
  onClick: () => void;
}) {
  const getIcon = () => {
    if (entry.match_type === 'EXACT') {
      return <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0" />;
    }
    if (entry.match_type === 'POKERGO_ONLY') {
      return <Cloud className="w-4 h-4 text-purple-500 flex-shrink-0" />;
    }
    return <HardDrive className="w-4 h-4 text-gray-400 flex-shrink-0" />;
  };

  return (
    <div
      onClick={onClick}
      className={`flex items-center gap-2 px-3 py-1.5 cursor-pointer rounded text-sm ${
        isSelected ? 'bg-blue-100 text-blue-900' : 'hover:bg-gray-100'
      }`}
    >
      {getIcon()}
      <span className="truncate flex-1">{entry.display_title || entry.entry_code}</span>
      {entry.file_count > 0 && (
        <span className="text-xs text-gray-500">{entry.file_count}</span>
      )}
    </div>
  );
}

function EventTypeNode({ eventType, selectedEntryId, onSelectEntry }: {
  eventType: TreeEventType;
  selectedEntryId: number | null;
  onSelectEntry: (id: number) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const exactRate = eventType.entry_count > 0
    ? Math.round(eventType.exact_count / eventType.entry_count * 100)
    : 0;

  return (
    <div className="ml-4">
      <div
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 px-2 py-1.5 cursor-pointer hover:bg-gray-100 rounded text-sm font-medium"
      >
        {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        <span>{eventType.name}</span>
        <span className="text-xs text-gray-500">({eventType.entry_count})</span>
        <div className={`ml-auto text-xs px-1.5 py-0.5 rounded ${
          exactRate >= 70 ? 'bg-green-100 text-green-700' :
          exactRate >= 30 ? 'bg-yellow-100 text-yellow-700' :
          'bg-red-100 text-red-700'
        }`}>
          {exactRate}%
        </div>
      </div>
      {expanded && (
        <div className="ml-2 border-l border-gray-200">
          {eventType.entries.map(entry => (
            <EntryNode
              key={entry.id}
              entry={entry}
              isSelected={selectedEntryId === entry.id}
              onClick={() => onSelectEntry(entry.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function CategoryNode({ category, selectedEntryId, onSelectEntry }: {
  category: TreeCategory;
  selectedEntryId: number | null;
  onSelectEntry: (id: number) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const exactRate = category.entry_count > 0
    ? Math.round(category.exact_count / category.entry_count * 100)
    : 0;

  return (
    <div className="ml-2">
      <div
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 px-2 py-2 cursor-pointer hover:bg-gray-50 rounded"
      >
        {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        <Layers className="w-4 h-4 text-purple-500" />
        <span className="font-medium">{category.name}</span>
        {category.region && (
          <span className="text-xs px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded">{category.region}</span>
        )}
        <span className="text-sm text-gray-500">({category.entry_count})</span>
        <div className={`ml-auto text-xs font-medium px-2 py-0.5 rounded ${
          exactRate >= 70 ? 'bg-green-100 text-green-700' :
          exactRate >= 30 ? 'bg-yellow-100 text-yellow-700' :
          'bg-red-100 text-red-700'
        }`}>
          {exactRate}% EXACT
        </div>
      </div>
      {expanded && (
        <div className="border-l border-gray-200 ml-3">
          {category.event_types.map(et => (
            <EventTypeNode
              key={et.code}
              eventType={et}
              selectedEntryId={selectedEntryId}
              onSelectEntry={onSelectEntry}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function YearNode({ year, selectedEntryId, onSelectEntry }: {
  year: TreeYear;
  selectedEntryId: number | null;
  onSelectEntry: (id: number) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const exactRate = year.entry_count > 0
    ? Math.round(year.exact_count / year.entry_count * 100)
    : 0;

  return (
    <div className="border-b border-gray-100">
      <div
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-gray-50"
      >
        {expanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
        <Calendar className="w-5 h-5 text-blue-500" />
        <span className="text-lg font-bold">{year.year}</span>
        <span className="text-sm text-gray-500">({year.entry_count} entries)</span>
        <div className="ml-auto flex items-center gap-3">
          <span className="text-sm text-gray-500">{year.total_size_gb.toFixed(1)} GB</span>
          <div className={`text-sm font-medium px-2 py-1 rounded ${
            exactRate >= 70 ? 'bg-green-100 text-green-700' :
            exactRate >= 30 ? 'bg-yellow-100 text-yellow-700' :
            'bg-red-100 text-red-700'
          }`}>
            {exactRate}%
          </div>
        </div>
      </div>
      {expanded && (
        <div className="bg-gray-50 pb-2">
          {year.categories.map(cat => (
            <CategoryNode
              key={cat.code}
              category={cat}
              selectedEntryId={selectedEntryId}
              onSelectEntry={onSelectEntry}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Entry Detail Panel
function EntryDetailPanel({ entryId }: { entryId: number }) {
  const { data: entry, isLoading } = useQuery({
    queryKey: ['entry', entryId],
    queryFn: () => entriesApi.get(entryId),
    enabled: !!entryId,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        Loading...
      </div>
    );
  }

  if (!entry) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        Select an entry to view details
      </div>
    );
  }

  const formatSize = (bytes: number) => {
    const gb = bytes / (1024 ** 3);
    return gb >= 1 ? `${gb.toFixed(2)} GB` : `${(bytes / (1024 ** 2)).toFixed(0)} MB`;
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="border-b pb-4">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-xl font-bold text-gray-900">{entry.entry_code}</h2>
          <MatchBadge matchType={entry.match_type} />
        </div>
        {entry.display_title && (
          <p className="text-gray-600">{entry.display_title}</p>
        )}
      </div>

      {/* PokerGO Match Info */}
      {entry.pokergo_title && (
        <div className="bg-purple-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-purple-800 mb-2">PokerGO Match</h3>
          <p className="text-purple-900">{entry.pokergo_title}</p>
          {entry.match_score && (
            <p className="text-sm text-purple-600 mt-1">
              Score: {(entry.match_score * 100).toFixed(0)}%
            </p>
          )}
        </div>
      )}

      {/* Metadata */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs text-gray-500 uppercase mb-1">Year</p>
          <p className="text-lg font-semibold">{entry.year}</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs text-gray-500 uppercase mb-1">Event Type</p>
          <p className="text-lg font-semibold">{entry.event_type || 'N/A'}</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs text-gray-500 uppercase mb-1">Files</p>
          <p className="text-lg font-semibold">{entry.file_count || 0}</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs text-gray-500 uppercase mb-1">Total Size</p>
          <p className="text-lg font-semibold">{formatSize(entry.total_size_bytes || 0)}</p>
        </div>
      </div>

      {/* Files */}
      {entry.files && entry.files.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-2">
            <FileVideo className="w-4 h-4" />
            Files ({entry.files.length})
          </h3>
          <div className="space-y-2">
            {entry.files.map((file) => (
              <FileCard key={file.id} file={file} formatSize={formatSize} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Main Component
export function ContentExplorer() {
  const [selectedEntryId, setSelectedEntryId] = useState<number | null>(null);

  const { data: treeData, isLoading, error } = useQuery({
    queryKey: ['content-tree'],
    queryFn: () => contentTreeApi.getTree(),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen text-red-500">
        Error loading content tree
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      {/* KPI Bar */}
      <div className="p-4">
        {treeData?.summary && <KPIBar summary={treeData.summary} />}
      </div>

      {/* Main Content */}
      <div className="flex-1 flex gap-4 px-4 pb-4 min-h-0">
        {/* Tree Panel */}
        <div className="w-1/2 bg-white rounded-lg shadow overflow-hidden flex flex-col">
          <div className="px-4 py-3 border-b bg-gray-50">
            <h2 className="font-semibold text-gray-800 flex items-center gap-2">
              <Layers className="w-5 h-5 text-purple-500" />
              Content Tree
            </h2>
            <p className="text-xs text-gray-500 mt-1">Year &rarr; Category &rarr; Event Type &rarr; Entry</p>
          </div>
          <div className="flex-1 overflow-y-auto">
            {treeData?.years.map(year => (
              <YearNode
                key={year.year}
                year={year}
                selectedEntryId={selectedEntryId}
                onSelectEntry={setSelectedEntryId}
              />
            ))}
          </div>
        </div>

        {/* Detail Panel */}
        <div className="w-1/2 bg-white rounded-lg shadow overflow-y-auto">
          {selectedEntryId ? (
            <EntryDetailPanel entryId={selectedEntryId} />
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-400">
              <Film className="w-16 h-16 mb-4" />
              <p className="text-lg">Select an entry from the tree</p>
              <p className="text-sm">to view details and files</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
