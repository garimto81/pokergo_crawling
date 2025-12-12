// Score indicator component

interface ScoreIndicatorProps {
  score: number;
  showBar?: boolean;
}

function getScoreColor(score: number) {
  if (score >= 80) return { bg: 'bg-green-500', text: 'text-green-700' };
  if (score >= 60) return { bg: 'bg-yellow-500', text: 'text-yellow-700' };
  if (score >= 40) return { bg: 'bg-orange-500', text: 'text-orange-700' };
  return { bg: 'bg-red-500', text: 'text-red-700' };
}

export function ScoreIndicator({ score, showBar = true }: ScoreIndicatorProps) {
  const { bg, text } = getScoreColor(score);

  return (
    <div className="flex items-center gap-2">
      <span className={`font-bold text-lg ${text}`}>{score}</span>
      {showBar && (
        <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full ${bg} transition-all`}
            style={{ width: `${score}%` }}
          />
        </div>
      )}
    </div>
  );
}
