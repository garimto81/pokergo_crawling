// Match list page

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchMatches, updateMatch } from '../api/matchApi';
import { useMatchStore } from '../stores/matchStore';
import { FilterBar } from '../components/matches/FilterBar';
import { MatchCard } from '../components/matches/MatchCard';
import { Pagination } from '../components/matches/Pagination';

export function MatchList() {
  const queryClient = useQueryClient();
  const { filters, setFilters } = useMatchStore();

  const { data, isLoading, error } = useQuery({
    queryKey: ['matches', filters],
    queryFn: () => fetchMatches(filters)
  });

  const verifyMutation = useMutation({
    mutationFn: (id: number) => updateMatch(id, { match_status: 'VERIFIED' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['matches'] });
    }
  });

  const rejectMutation = useMutation({
    mutationFn: (id: number) => updateMatch(id, { match_status: 'WRONG_MATCH' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['matches'] });
    }
  });

  const handlePageChange = (page: number) => {
    setFilters({ page });
  };

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500">Error loading matches. Is the API running?</p>
        <p className="text-sm text-gray-500 mt-2">
          Start the API: uvicorn src.api.main:app --reload
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">All Matches</h1>
        <span className="text-sm text-gray-500">
          {data?.total || 0} total matches
        </span>
      </div>

      <FilterBar />

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-500">Loading matches...</div>
        </div>
      ) : (
        <>
          <div className="space-y-4">
            {data?.items.map((match) => (
              <MatchCard
                key={match.id}
                match={match}
                onVerify={(id) => verifyMutation.mutate(id)}
                onReject={(id) => rejectMutation.mutate(id)}
              />
            ))}
          </div>

          {data && data.pages > 1 && (
            <Pagination
              page={data.page}
              pages={data.pages}
              total={data.total}
              limit={data.limit}
              onPageChange={handlePageChange}
            />
          )}
        </>
      )}
    </div>
  );
}
