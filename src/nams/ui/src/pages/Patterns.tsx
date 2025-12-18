import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { patternsApi } from '../api/client';
import { Plus, Edit2, Trash2, TestTube, GripVertical } from 'lucide-react';
import type { Pattern, PatternTestResult } from '../types';

function PatternTester({ pattern }: { pattern: Pattern }) {
  const [filename, setFilename] = useState('');
  const [result, setResult] = useState<PatternTestResult | null>(null);

  const testMutation = useMutation({
    mutationFn: () => patternsApi.test(pattern.id, filename),
    onSuccess: (data) => setResult(data),
  });

  return (
    <div className="mt-4 p-4 bg-gray-50 rounded">
      <h4 className="text-sm font-medium mb-2">Test Pattern</h4>
      <div className="flex gap-2">
        <input
          type="text"
          value={filename}
          onChange={(e) => setFilename(e.target.value)}
          placeholder="Enter filename to test..."
          className="flex-1 px-3 py-2 border rounded text-sm"
        />
        <button
          onClick={() => testMutation.mutate()}
          disabled={!filename}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
        >
          <TestTube className="w-4 h-4" />
        </button>
      </div>
      {result && (
        <div className="mt-2 p-2 bg-white rounded border text-sm">
          {result.matched ? (
            <div className="text-green-600">
              <p>Matched! Extracted:</p>
              <ul className="list-disc list-inside">
                {result.extracted_year && <li>Year: {result.extracted_year}</li>}
                {result.extracted_region && <li>Region: {result.extracted_region}</li>}
                {result.extracted_type && <li>Type: {result.extracted_type}</li>}
                {result.extracted_episode && <li>Episode: {result.extracted_episode}</li>}
              </ul>
            </div>
          ) : (
            <p className="text-red-600">No match</p>
          )}
        </div>
      )}
    </div>
  );
}

export function Patterns() {
  const queryClient = useQueryClient();
  const [selectedPattern, setSelectedPattern] = useState<Pattern | null>(null);

  const { data: patterns, isLoading } = useQuery({
    queryKey: ['patterns'],
    queryFn: () => patternsApi.list(),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => patternsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patterns'] });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Patterns</h1>
        <button className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
          <Plus className="w-4 h-4" />
          Add Pattern
        </button>
      </div>

      <p className="text-sm text-gray-500">
        Patterns are applied in priority order (lower number = higher priority).
        Each pattern extracts metadata (year, region, type, episode) from filenames.
      </p>

      {/* Pattern List */}
      <div className="bg-white rounded-lg shadow divide-y">
        {isLoading ? (
          <div className="flex justify-center py-12">Loading...</div>
        ) : (
          patterns?.map((pattern) => (
            <div key={pattern.id} className="p-4">
              <div className="flex items-start gap-4">
                <div className="flex items-center gap-2 text-gray-400 cursor-grab">
                  <GripVertical className="w-4 h-4" />
                  <span className="text-sm font-mono w-6">{pattern.priority}</span>
                </div>

                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="font-medium text-gray-900">{pattern.name}</h3>
                    {!pattern.is_active && (
                      <span className="px-2 py-0.5 bg-gray-100 text-gray-500 text-xs rounded">Inactive</span>
                    )}
                    {pattern.extract_region && (
                      <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">
                        {pattern.extract_region}
                      </span>
                    )}
                    {pattern.extract_type && (
                      <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded">
                        {pattern.extract_type}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-500 mt-1">{pattern.description}</p>
                  <code className="text-xs bg-gray-100 px-2 py-1 rounded mt-2 inline-block text-gray-600">
                    {pattern.regex}
                  </code>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setSelectedPattern(selectedPattern?.id === pattern.id ? null : pattern)}
                    className="p-2 text-gray-400 hover:text-blue-500"
                  >
                    <TestTube className="w-4 h-4" />
                  </button>
                  <button className="p-2 text-gray-400 hover:text-blue-500">
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => {
                      if (confirm(`Delete pattern "${pattern.name}"?`)) {
                        deleteMutation.mutate(pattern.id);
                      }
                    }}
                    className="p-2 text-gray-400 hover:text-red-500"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {selectedPattern?.id === pattern.id && (
                <PatternTester pattern={pattern} />
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
