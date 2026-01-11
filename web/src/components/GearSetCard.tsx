import clsx from 'clsx';
import type { GearSet } from '../types';

interface GearSetCardProps {
  set: GearSet;
  onClick?: () => void;
  isSelected?: boolean;
  showBonuses?: boolean;
}

export default function GearSetCard({
  set,
  onClick,
  isSelected = false,
  showBonuses = true,
}: GearSetCardProps) {
  const tierColors = {
    S: 'text-eso-gold-400 bg-eso-gold-500/10 border-eso-gold-500/30',
    A: 'text-eso-green-400 bg-eso-green-500/10 border-eso-green-500/30',
    B: 'text-eso-blue-400 bg-eso-blue-500/10 border-eso-blue-500/30',
    C: 'text-gray-400 bg-gray-500/10 border-gray-500/30',
    F: 'text-eso-red-400 bg-eso-red-500/10 border-eso-red-500/30',
  };

  const setTypeColors: Record<string, string> = {
    Trial: 'badge-warning',
    Dungeon: 'badge-info',
    Overland: 'badge-success',
    Monster: 'badge-danger',
    Craftable: 'text-gray-400 bg-gray-500/20',
    Mythic: 'text-eso-purple-400 bg-eso-purple-500/20',
    Arena: 'text-orange-400 bg-orange-500/20',
    PvP: 'text-red-400 bg-red-500/20',
  };

  return (
    <div
      className={clsx(
        'card-hover cursor-pointer',
        isSelected && 'border-eso-gold-500 ring-1 ring-eso-gold-500/20'
      )}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-medium text-gray-100">{set.name}</h3>
          <p className="text-sm text-gray-500">{set.location}</p>
        </div>
        <div className="flex items-center gap-2">
          {set.pve_tier && (
            <span
              className={clsx(
                'inline-flex items-center justify-center w-7 h-7 rounded border text-sm font-bold',
                tierColors[set.pve_tier]
              )}
            >
              {set.pve_tier}
            </span>
          )}
        </div>
      </div>

      {/* Type and Weight */}
      <div className="flex items-center gap-2 mb-3">
        <span className={clsx('badge', setTypeColors[set.set_type])}>
          {set.set_type}
        </span>
        <span className="text-xs text-gray-500">{set.weight}</span>
        {set.dlc_required && (
          <span className="text-xs text-gray-500">
            ({set.dlc_required})
          </span>
        )}
      </div>

      {/* Bonuses */}
      {showBonuses && (
        <div className="space-y-2">
          {Object.entries(set.bonuses).map(([pieces, bonus]) => (
            <div
              key={pieces}
              className="flex items-start gap-2 text-sm"
            >
              <span className="flex-shrink-0 w-5 h-5 flex items-center justify-center rounded bg-eso-dark-800 text-xs text-gray-400">
                {pieces}
              </span>
              <span className="text-gray-400">
                {bonus.stat && bonus.value
                  ? `${bonus.stat}: +${bonus.value}`
                  : bonus.stat && bonus.uptime
                  ? `${bonus.stat} (${bonus.uptime})`
                  : bonus.effect}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Role Affinity */}
      {set.role_affinity && (
        <div className="mt-3 pt-3 border-t border-eso-dark-700">
          <p className="text-xs text-gray-500 mb-2">Role Affinity</p>
          <div className="flex gap-4">
            <div className="flex-1">
              <div className="h-1.5 bg-eso-dark-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-eso-red-400 rounded-full"
                  style={{ width: `${set.role_affinity.damage_dealt * 100}%` }}
                />
              </div>
              <p className="text-xs text-gray-500 mt-1">DPS</p>
            </div>
            <div className="flex-1">
              <div className="h-1.5 bg-eso-dark-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-eso-green-400 rounded-full"
                  style={{ width: `${set.role_affinity.healing_done * 100}%` }}
                />
              </div>
              <p className="text-xs text-gray-500 mt-1">Heal</p>
            </div>
            <div className="flex-1">
              <div className="h-1.5 bg-eso-dark-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-eso-blue-400 rounded-full"
                  style={{ width: `${set.role_affinity.buff_uptime * 100}%` }}
                />
              </div>
              <p className="text-xs text-gray-500 mt-1">Support</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
