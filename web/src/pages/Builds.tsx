import { useState, useMemo, useCallback } from 'react';
import { ArrowLeftRight, TrendingUp, AlertCircle, Search, Loader2 } from 'lucide-react';
import clsx from 'clsx';
import GearSetCard from '../components/GearSetCard';
import { useGearSets, useCharacters } from '../hooks/useApi';
import { mockGearSets, mockCharacters, formatDPS } from '../data/mockData';
import type { GearSet, Character } from '../types';

export default function Builds() {
  const { data: apiGearSets, isLoading: setsLoading } = useGearSets();
  const { data: apiCharacters, isLoading: charsLoading } = useCharacters();

  // Fall back to mock data when API is unreachable
  const gearSets = apiGearSets ?? mockGearSets;
  const characters = apiCharacters ?? mockCharacters;

  const isLoading = setsLoading && charsLoading;
  const usingMockData = !apiGearSets && !setsLoading;

  const [selectedCharacter, setSelectedCharacter] = useState<Character | null>(null);
  const [selectedSets, setSelectedSets] = useState<GearSet[]>([]);
  const [searchQuery, setSearchQuery] = useState('');

  // Auto-select first character when data loads
  const activeCharacter = selectedCharacter ?? characters[0] ?? null;

  const filteredSets = useMemo(() => gearSets.filter((set) =>
    set.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    set.set_type.toLowerCase().includes(searchQuery.toLowerCase())
  ), [searchQuery, gearSets]);

  // Memoized toggle function to prevent unnecessary re-renders in child components
  const toggleSetSelection = useCallback((set: GearSet) => {
    setSelectedSets((prev) =>
      prev.find((s) => s.set_id === set.set_id)
        ? prev.filter((s) => s.set_id !== set.set_id)
        : prev.length < 3
        ? [...prev, set]
        : prev
    );
  }, []);

  // Calculate expected DPS difference
  const calculateExpectedDPS = () => {
    if (!activeCharacter || selectedSets.length === 0) return null;

    // Mock calculation based on set tiers
    const tierMultipliers: Record<string, number> = { S: 1.12, A: 1.08, B: 1.04, C: 1.0, F: 0.95 };
    const currentAvgTier = 'A'; // Assume current build is A-tier
    const tiers = ['S', 'A', 'B', 'C', 'F'];
    const newAvgTier = selectedSets.reduce<string>((best, set) => {
      if (!set.pve_tier) return best;
      return tiers.indexOf(set.pve_tier) < tiers.indexOf(best) ? set.pve_tier : best;
    }, 'C');

    const currentMultiplier = tierMultipliers[currentAvgTier] ?? 1.0;
    const newMultiplier = tierMultipliers[newAvgTier] ?? 1.0;
    const baseDPS = activeCharacter.average_dps;
    const expectedDPS = Math.round((baseDPS / currentMultiplier) * newMultiplier);
    const difference = expectedDPS - baseDPS;
    const percentChange = ((difference / baseDPS) * 100).toFixed(1);

    return {
      current: baseDPS,
      expected: expectedDPS,
      difference,
      percentChange,
      isPositive: difference > 0,
    };
  };

  const dpsCalculation = calculateExpectedDPS();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-eso-gold-400 animate-spin" />
          <p className="text-gray-400">Loading builds...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-100">Build Comparison</h1>
        <p className="text-gray-500 mt-1">
          Compare your build against top performers and optimize gear selection.
        </p>
        {usingMockData && (
          <div className="flex items-center gap-2 mt-2 text-sm text-eso-gold-400">
            <AlertCircle className="w-4 h-4" />
            <span>API unavailable - showing sample data</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Current Build */}
        <div className="space-y-6">
          <div className="card">
            <h2 className="text-lg font-semibold text-gray-100 mb-4">Select Character</h2>
            {charsLoading ? (
              <div className="flex justify-center py-4">
                <Loader2 className="w-5 h-5 text-gray-500 animate-spin" />
              </div>
            ) : (
              <div className="space-y-2">
                {characters.map((char) => (
                  <button
                    key={char.id}
                    onClick={() => setSelectedCharacter(char)}
                    className={clsx(
                      'w-full text-left p-3 rounded-lg transition-colors',
                      activeCharacter?.id === char.id
                        ? 'bg-eso-gold-500/10 border border-eso-gold-500/30'
                        : 'bg-eso-dark-800 hover:bg-eso-dark-700'
                    )}
                  >
                    <p className="font-medium text-gray-100">{char.name}</p>
                    <p className="text-sm text-gray-500">
                      {char.class} - {formatDPS(char.average_dps)} avg DPS
                    </p>
                  </button>
                ))}
              </div>
            )}
          </div>

          {activeCharacter && (
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-100 mb-4">Current Build</h2>
              <div className="space-y-3">
                <div>
                  <p className="text-xs text-gray-500 mb-1">Class</p>
                  <p className="text-gray-100">
                    {activeCharacter.class}
                    {activeCharacter.subclass && ` / ${activeCharacter.subclass}`}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 mb-1">Race</p>
                  <p className="text-gray-100">{activeCharacter.race}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 mb-1">Current Sets</p>
                  <div className="flex flex-wrap gap-1">
                    {activeCharacter.current_sets.map((set) => (
                      <span
                        key={set}
                        className="text-xs px-2 py-1 bg-eso-dark-800 rounded text-gray-300"
                      >
                        {set}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="pt-3 border-t border-eso-dark-700">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Average DPS</span>
                    <span className="font-medium text-gray-100">
                      {formatDPS(activeCharacter.average_dps)}
                    </span>
                  </div>
                  <div className="flex justify-between mt-1">
                    <span className="text-gray-500">Best DPS</span>
                    <span className="font-medium text-eso-gold-400">
                      {formatDPS(activeCharacter.best_dps)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Middle Column: Comparison */}
        <div className="space-y-6">
          <div className="card">
            <div className="flex items-center gap-3 mb-4">
              <ArrowLeftRight className="w-5 h-5 text-eso-gold-400" />
              <h2 className="text-lg font-semibold text-gray-100">DPS Calculator</h2>
            </div>

            {dpsCalculation ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-eso-dark-800 rounded-lg p-4 text-center">
                    <p className="text-xs text-gray-500 mb-1">Current</p>
                    <p className="text-2xl font-bold text-gray-100">
                      {formatDPS(dpsCalculation.current)}
                    </p>
                  </div>
                  <div
                    className={clsx(
                      'rounded-lg p-4 text-center',
                      dpsCalculation.isPositive
                        ? 'bg-eso-green-500/10 border border-eso-green-500/30'
                        : 'bg-eso-red-500/10 border border-eso-red-500/30'
                    )}
                  >
                    <p className="text-xs text-gray-500 mb-1">Expected</p>
                    <p
                      className={clsx(
                        'text-2xl font-bold',
                        dpsCalculation.isPositive ? 'text-eso-green-400' : 'text-eso-red-400'
                      )}
                    >
                      {formatDPS(dpsCalculation.expected)}
                    </p>
                  </div>
                </div>

                <div
                  className={clsx(
                    'flex items-center justify-center gap-2 p-3 rounded-lg',
                    dpsCalculation.isPositive
                      ? 'bg-eso-green-500/10 text-eso-green-400'
                      : 'bg-eso-red-500/10 text-eso-red-400'
                  )}
                >
                  <TrendingUp className="w-5 h-5" />
                  <span className="font-medium">
                    {dpsCalculation.isPositive ? '+' : ''}
                    {formatDPS(dpsCalculation.difference)} ({dpsCalculation.percentChange}%)
                  </span>
                </div>

                <div className="text-center">
                  <p className="text-xs text-gray-500">
                    Estimate based on set tier and role affinity
                  </p>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-gray-500">
                <AlertCircle className="w-8 h-8 mb-2" />
                <p>Select sets to compare</p>
              </div>
            )}
          </div>

          {/* Selected Sets */}
          <div className="card">
            <h2 className="text-lg font-semibold text-gray-100 mb-4">
              Selected Sets ({selectedSets.length}/3)
            </h2>
            {selectedSets.length > 0 ? (
              <div className="space-y-3">
                {selectedSets.map((set) => (
                  <div
                    key={set.set_id}
                    className="flex items-center justify-between bg-eso-dark-800 rounded-lg p-3"
                  >
                    <div>
                      <p className="font-medium text-gray-100">{set.name}</p>
                      <p className="text-sm text-gray-500">{set.set_type}</p>
                    </div>
                    <button
                      onClick={() => toggleSetSelection(set)}
                      className="text-sm text-eso-red-400 hover:text-eso-red-300"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-4">
                Click on sets to add them for comparison
              </p>
            )}
          </div>
        </div>

        {/* Right Column: Gear Sets */}
        <div className="space-y-6">
          <div className="card">
            <h2 className="text-lg font-semibold text-gray-100 mb-4">Gear Sets Database</h2>
            <div className="relative mb-4">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                placeholder="Search sets..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input pl-10"
              />
            </div>
            {setsLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="w-5 h-5 text-gray-500 animate-spin" />
              </div>
            ) : (
              <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2">
                {filteredSets.map((set) => (
                  <GearSetCard
                    key={set.set_id}
                    set={set}
                    onClick={() => toggleSetSelection(set)}
                    isSelected={selectedSets.some((s) => s.set_id === set.set_id)}
                    showBonuses={false}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
