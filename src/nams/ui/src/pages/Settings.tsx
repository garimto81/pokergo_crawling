import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { settingsApi, exclusionsApi } from '../api/client';
import { MapPin, Tag, Filter, Plus, Trash2, ToggleLeft, ToggleRight } from 'lucide-react';
import type { ExclusionRule, ExclusionRuleCreate, RuleType, Operator } from '../types';

// Helper functions for exclusion rules
const getRuleTypeLabel = (type: RuleType) => {
  switch (type) {
    case 'size': return 'Size';
    case 'duration': return 'Duration';
    case 'keyword': return 'Keyword';
    default: return type;
  }
};

const getOperatorLabel = (op: Operator) => {
  switch (op) {
    case 'lt': return '<';
    case 'gt': return '>';
    case 'eq': return '=';
    case 'contains': return 'contains';
    default: return op;
  }
};

const formatValue = (rule: ExclusionRule) => {
  if (rule.rule_type === 'size') {
    const bytes = parseInt(rule.value);
    if (bytes >= 1073741824) return `${(bytes / 1073741824).toFixed(1)} GB`;
    if (bytes >= 1048576) return `${(bytes / 1048576).toFixed(1)} MB`;
    return `${bytes} B`;
  }
  if (rule.rule_type === 'duration') {
    const secs = parseInt(rule.value);
    if (secs >= 3600) return `${(secs / 3600).toFixed(1)} hr`;
    if (secs >= 60) return `${(secs / 60).toFixed(0)} min`;
    return `${secs} sec`;
  }
  return rule.value;
};

// Add Rule Modal Component
function AddRuleModal({ onClose, onAdd }: { onClose: () => void; onAdd: (rule: ExclusionRuleCreate) => void }) {
  const [ruleType, setRuleType] = useState<RuleType>('keyword');
  const [operator, setOperator] = useState<Operator>('contains');
  const [value, setValue] = useState('');
  const [description, setDescription] = useState('');

  const getAvailableOperators = (): Operator[] => {
    if (ruleType === 'keyword') return ['contains', 'eq'];
    return ['lt', 'gt', 'eq'];
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    let finalValue = value;

    // Convert size to bytes if needed
    if (ruleType === 'size') {
      const match = value.match(/^(\d+(?:\.\d+)?)\s*(GB|MB|KB|B)?$/i);
      if (match) {
        const num = parseFloat(match[1]);
        const unit = (match[2] || 'B').toUpperCase();
        switch (unit) {
          case 'GB': finalValue = Math.round(num * 1073741824).toString(); break;
          case 'MB': finalValue = Math.round(num * 1048576).toString(); break;
          case 'KB': finalValue = Math.round(num * 1024).toString(); break;
          default: finalValue = Math.round(num).toString();
        }
      }
    }

    // Convert duration to seconds if needed
    if (ruleType === 'duration') {
      const match = value.match(/^(\d+(?:\.\d+)?)\s*(hr|hour|h|min|m|sec|s)?$/i);
      if (match) {
        const num = parseFloat(match[1]);
        const unit = (match[2] || 's').toLowerCase();
        if (unit.startsWith('h')) finalValue = Math.round(num * 3600).toString();
        else if (unit.startsWith('m')) finalValue = Math.round(num * 60).toString();
        else finalValue = Math.round(num).toString();
      }
    }

    onAdd({
      rule_type: ruleType,
      operator,
      value: finalValue,
      description: description || undefined,
      is_active: true,
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
        <h3 className="text-lg font-semibold mb-4">Add Exclusion Rule</h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Rule Type</label>
            <select
              value={ruleType}
              onChange={(e) => {
                setRuleType(e.target.value as RuleType);
                setOperator(e.target.value === 'keyword' ? 'contains' : 'lt');
              }}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="size">Size</option>
              <option value="duration">Duration</option>
              <option value="keyword">Keyword</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Operator</label>
            <select
              value={operator}
              onChange={(e) => setOperator(e.target.value as Operator)}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              {getAvailableOperators().map(op => (
                <option key={op} value={op}>{getOperatorLabel(op)}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Value
              {ruleType === 'size' && <span className="text-gray-400 ml-1">(e.g., 1GB, 500MB)</span>}
              {ruleType === 'duration' && <span className="text-gray-400 ml-1">(e.g., 1hr, 30min)</span>}
            </label>
            <input
              type="text"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder={ruleType === 'size' ? '1GB' : ruleType === 'duration' ? '1hr' : 'keyword'}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description (optional)</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Why exclude these files?"
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:text-gray-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              Add Rule
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function Settings() {
  const queryClient = useQueryClient();
  const [showAddModal, setShowAddModal] = useState(false);

  // Existing queries
  const { data: regions, isLoading: regionsLoading } = useQuery({
    queryKey: ['regions'],
    queryFn: settingsApi.getRegions,
  });

  const { data: eventTypes, isLoading: typesLoading } = useQuery({
    queryKey: ['eventTypes'],
    queryFn: settingsApi.getEventTypes,
  });

  // Exclusion Rules
  const { data: exclusionRules, isLoading: rulesLoading } = useQuery({
    queryKey: ['exclusionRules'],
    queryFn: () => exclusionsApi.list(),
  });

  const createRuleMutation = useMutation({
    mutationFn: exclusionsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exclusionRules'] });
      setShowAddModal(false);
    },
  });

  const toggleRuleMutation = useMutation({
    mutationFn: exclusionsApi.toggle,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exclusionRules'] });
    },
  });

  const deleteRuleMutation = useMutation({
    mutationFn: exclusionsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exclusionRules'] });
    },
  });

  const handleAddRule = (rule: ExclusionRuleCreate) => {
    createRuleMutation.mutate(rule);
  };

  const handleToggleRule = (id: number) => {
    toggleRuleMutation.mutate(id);
  };

  const handleDeleteRule = (id: number) => {
    if (confirm('Are you sure you want to delete this rule?')) {
      deleteRuleMutation.mutate(id);
    }
  };

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">Settings</h1>

      {/* Exclusion Rules */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Filter className="w-5 h-5 text-gray-400" />
            <h2 className="text-lg font-semibold text-gray-900">Exclusion Rules</h2>
            <span className="text-sm text-gray-500">
              ({exclusionRules?.items.filter(r => r.is_active).length || 0} active)
            </span>
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 flex items-center gap-1"
          >
            <Plus className="w-4 h-4" />
            Add Rule
          </button>
        </div>
        <div className="p-6">
          {rulesLoading ? (
            <div>Loading...</div>
          ) : exclusionRules?.items.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              No exclusion rules configured. Add rules to filter files during NAS scan.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead>
                  <tr className="text-left text-sm text-gray-500 border-b">
                    <th className="pb-2 font-medium">Type</th>
                    <th className="pb-2 font-medium">Condition</th>
                    <th className="pb-2 font-medium">Description</th>
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {exclusionRules?.items.map((rule) => (
                    <tr key={rule.id} className={!rule.is_active ? 'opacity-50' : ''}>
                      <td className="py-3">
                        <span className={`px-2 py-1 text-xs rounded ${
                          rule.rule_type === 'size' ? 'bg-purple-100 text-purple-700' :
                          rule.rule_type === 'duration' ? 'bg-orange-100 text-orange-700' :
                          'bg-blue-100 text-blue-700'
                        }`}>
                          {getRuleTypeLabel(rule.rule_type)}
                        </span>
                      </td>
                      <td className="py-3 font-mono text-sm">
                        {getOperatorLabel(rule.operator)} {formatValue(rule)}
                      </td>
                      <td className="py-3 text-sm text-gray-600">
                        {rule.description || '-'}
                      </td>
                      <td className="py-3">
                        <button
                          onClick={() => handleToggleRule(rule.id)}
                          className="p-1 hover:bg-gray-100 rounded"
                          title={rule.is_active ? 'Click to deactivate' : 'Click to activate'}
                        >
                          {rule.is_active ? (
                            <ToggleRight className="w-6 h-6 text-green-500" />
                          ) : (
                            <ToggleLeft className="w-6 h-6 text-gray-400" />
                          )}
                        </button>
                      </td>
                      <td className="py-3">
                        <button
                          onClick={() => handleDeleteRule(rule.id)}
                          className="p-1 text-red-500 hover:bg-red-50 rounded"
                          title="Delete rule"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="mt-4 p-3 bg-gray-50 rounded text-sm text-gray-600">
            <strong>How it works:</strong> Files matching any active exclusion rule will be skipped during NAS scan.
            <ul className="mt-2 list-disc list-inside space-y-1">
              <li><strong>Size:</strong> Exclude files smaller/larger than specified size</li>
              <li><strong>Duration:</strong> Exclude videos shorter/longer than specified duration</li>
              <li><strong>Keyword:</strong> Exclude files containing specific keywords in filename or path</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Regions */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MapPin className="w-5 h-5 text-gray-400" />
            <h2 className="text-lg font-semibold text-gray-900">Regions</h2>
          </div>
          <button className="px-4 py-2 text-sm bg-blue-500 text-white rounded hover:bg-blue-600">
            Add Region
          </button>
        </div>
        <div className="p-6">
          {regionsLoading ? (
            <div>Loading...</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {regions?.map((region) => (
                <div key={region.id} className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-lg text-gray-900">{region.code}</span>
                    {!region.is_active && (
                      <span className="text-xs text-gray-400">Inactive</span>
                    )}
                  </div>
                  <p className="text-sm text-gray-600">{region.name}</p>
                  {region.description && (
                    <p className="text-xs text-gray-400 mt-1">{region.description}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Event Types */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Tag className="w-5 h-5 text-gray-400" />
            <h2 className="text-lg font-semibold text-gray-900">Event Types</h2>
          </div>
          <button className="px-4 py-2 text-sm bg-blue-500 text-white rounded hover:bg-blue-600">
            Add Type
          </button>
        </div>
        <div className="p-6">
          {typesLoading ? (
            <div>Loading...</div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {eventTypes?.map((type) => (
                <div key={type.id} className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-gray-900">{type.code}</span>
                    {!type.is_active && (
                      <span className="text-xs text-gray-400">Inactive</span>
                    )}
                  </div>
                  <p className="text-sm text-gray-600">{type.name}</p>
                  {type.description && (
                    <p className="text-xs text-gray-400 mt-1">{type.description}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* API Info */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">API Information</h2>
        <div className="space-y-2 text-sm">
          <p><span className="text-gray-500">API URL:</span> http://localhost:8001</p>
          <p><span className="text-gray-500">Docs:</span> <a href="http://localhost:8001/docs" target="_blank" className="text-blue-500 hover:underline">http://localhost:8001/docs</a></p>
        </div>
      </div>

      {/* Add Rule Modal */}
      {showAddModal && (
        <AddRuleModal
          onClose={() => setShowAddModal(false)}
          onAdd={handleAddRule}
        />
      )}
    </div>
  );
}
