import { Clock, Swords, CheckCircle2, XCircle } from 'lucide-react';
import clsx from 'clsx';
import type { CombatRunListItem } from '../types';
import { formatDuration, formatDPS, getRelativeTime } from '../data/mockData';

interface RunCardProps {
  run: CombatRunListItem;
  onClick?: () => void;
}

export default function RunCard({ run, onClick }: RunCardProps) {
  const difficultyColors = {
    normal: 'badge-info',
    veteran: 'badge-warning',
    hardmode: 'badge-danger',
  };

  const contentTypeLabels = {
    dungeon: 'Dungeon',
    trial: 'Trial',
    arena: 'Arena',
    overworld: 'Overworld',
    pvp: 'PvP',
  };

  return (
    <div
      className={clsx(
        'card-hover cursor-pointer',
        !run.success && 'border-eso-red-500/30'
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-medium text-gray-100">{run.content_name}</h3>
          <p className="text-sm text-gray-500">{run.character_name}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={clsx(difficultyColors[run.difficulty])}>
            {run.difficulty.charAt(0).toUpperCase() + run.difficulty.slice(1)}
          </span>
          <span className="badge-info">
            {contentTypeLabels[run.content_type]}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="flex items-center gap-2">
          <Swords className="w-4 h-4 text-eso-gold-400" />
          <div>
            <p className="text-sm font-medium text-gray-100">{formatDPS(run.dps)}</p>
            <p className="text-xs text-gray-500">DPS</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-gray-400" />
          <div>
            <p className="text-sm font-medium text-gray-100">{formatDuration(run.duration_sec)}</p>
            <p className="text-xs text-gray-500">Duration</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {run.success ? (
            <CheckCircle2 className="w-4 h-4 text-eso-green-400" />
          ) : (
            <XCircle className="w-4 h-4 text-eso-red-400" />
          )}
          <div>
            <p className={clsx(
              'text-sm font-medium',
              run.success ? 'text-eso-green-400' : 'text-eso-red-400'
            )}>
              {run.success ? 'Success' : 'Failed'}
            </p>
            <p className="text-xs text-gray-500">{getRelativeTime(run.timestamp)}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
