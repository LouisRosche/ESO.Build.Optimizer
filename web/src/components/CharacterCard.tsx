import { Swords, Trophy, Calendar, Shield } from 'lucide-react';
import clsx from 'clsx';
import type { Character, BuildSnapshot } from '../types';
import { formatDPS, getRelativeTime } from '../data/mockData';
import { classColors } from '../utils/classColors';
import type { KeyboardEvent } from 'react';

interface CharacterCardProps {
  character: Character;
  onClick?: () => void;
  isSelected?: boolean;
}

export default function CharacterCard({
  character,
  onClick,
  isSelected = false,
}: CharacterCardProps) {
  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick?.();
    }
  };

  // Extract build fields safely (build may be empty object from API)
  const build = (character.build && 'class' in character.build)
    ? character.build as BuildSnapshot
    : null;

  const charClass = build?.class ?? 'Dragonknight';

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`${character.character_name}, ${charClass}, CP ${character.cp_level ?? 0}, ${formatDPS(character.avg_dps)} average DPS`}
      className={clsx(
        'card-hover cursor-pointer',
        isSelected && 'border-eso-gold-500 ring-1 ring-eso-gold-500/20'
      )}
      onClick={onClick}
      onKeyDown={handleKeyDown}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-lg bg-eso-dark-800 flex items-center justify-center">
            <Shield className={clsx('w-6 h-6', classColors[charClass])} />
          </div>
          <div>
            <h3 className="font-medium text-gray-100">{character.character_name}</h3>
            <p className={clsx('text-sm', classColors[charClass])}>
              {charClass}
              {build?.subclass && (
                <span className="text-gray-500"> / {build.subclass}</span>
              )}
            </p>
          </div>
        </div>
        <span className="badge-info">
          CP {character.cp_level ?? 0}
        </span>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="flex items-center gap-2">
          <Swords className="w-4 h-4 text-gray-400" />
          <div>
            <p className="text-sm font-medium text-gray-100">{formatDPS(character.avg_dps)}</p>
            <p className="text-xs text-gray-500">Avg DPS</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Trophy className="w-4 h-4 text-eso-gold-400" />
          <div>
            <p className="text-sm font-medium text-gray-100">{formatDPS(character.best_dps)}</p>
            <p className="text-xs text-gray-500">Best DPS</p>
          </div>
        </div>
      </div>

      {/* Current Sets */}
      {build?.sets && build.sets.length > 0 && (
        <div className="mb-4">
          <p className="text-xs text-gray-500 mb-2">Current Sets</p>
          <div className="flex flex-wrap gap-1">
            {build.sets.map((set) => (
              <span
                key={set}
                className="text-xs px-2 py-1 bg-eso-dark-800 rounded text-gray-400"
              >
                {set}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-3 border-t border-eso-dark-700">
        <div className="flex items-center gap-1 text-xs text-gray-500">
          <Calendar className="w-3.5 h-3.5" />
          {character.last_played ? getRelativeTime(character.last_played) : 'Never'}
        </div>
        <span className="text-xs text-gray-500">
          {character.total_runs} runs
        </span>
      </div>
    </div>
  );
}
