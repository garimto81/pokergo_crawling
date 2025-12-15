import { useQuery } from '@tanstack/react-query';
import { settingsApi } from '../api/client';
import { MapPin, Tag } from 'lucide-react';

export function Settings() {
  const { data: regions, isLoading: regionsLoading } = useQuery({
    queryKey: ['regions'],
    queryFn: settingsApi.getRegions,
  });

  const { data: eventTypes, isLoading: typesLoading } = useQuery({
    queryKey: ['eventTypes'],
    queryFn: settingsApi.getEventTypes,
  });

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">Settings</h1>

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
          <p><span className="text-gray-500">API URL:</span> http://localhost:8002</p>
          <p><span className="text-gray-500">Docs:</span> <a href="http://localhost:8002/docs" target="_blank" className="text-blue-500 hover:underline">http://localhost:8002/docs</a></p>
        </div>
      </div>
    </div>
  );
}
