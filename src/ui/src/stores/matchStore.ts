// Zustand store for match state

import { create } from 'zustand';
import type { MatchFilters } from '../api/matchApi';

interface MatchStore {
  // Filters
  filters: MatchFilters;
  setFilters: (filters: Partial<MatchFilters>) => void;
  resetFilters: () => void;

  // Selection
  selectedIds: number[];
  toggleSelection: (id: number) => void;
  selectAll: (ids: number[]) => void;
  clearSelection: () => void;

  // UI state
  currentView: 'list' | 'grid';
  setCurrentView: (view: 'list' | 'grid') => void;
}

const defaultFilters: MatchFilters = {
  page: 1,
  limit: 20,
  status: undefined,
  score_min: undefined,
  score_max: undefined,
  search: undefined
};

export const useMatchStore = create<MatchStore>((set) => ({
  // Filters
  filters: defaultFilters,
  setFilters: (newFilters) =>
    set((state) => ({
      filters: { ...state.filters, ...newFilters, page: newFilters.page ?? 1 }
    })),
  resetFilters: () => set({ filters: defaultFilters }),

  // Selection
  selectedIds: [],
  toggleSelection: (id) =>
    set((state) => ({
      selectedIds: state.selectedIds.includes(id)
        ? state.selectedIds.filter((i) => i !== id)
        : [...state.selectedIds, id]
    })),
  selectAll: (ids) => set({ selectedIds: ids }),
  clearSelection: () => set({ selectedIds: [] }),

  // UI
  currentView: 'list',
  setCurrentView: (view) => set({ currentView: view })
}));
