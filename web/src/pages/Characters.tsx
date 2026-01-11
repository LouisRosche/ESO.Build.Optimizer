import { useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Trophy, Swords, Clock, Calendar, TrendingUp, History } from 'lucide-react';
import clsx from 'clsx';
import CharacterCard from '../components/CharacterCard';
import RunCard from '../components/RunCard';
import { mockCharacters, mockRuns, formatDPS, mockDPSTrend } from '../data/mockData';
import type { Character } from '../types';

export default function Characters() {
  const [selectedCharacter, setSelectedCharacter] = useState<Character | null>(null);

  // Get runs for selected character
  const characterRuns = selectedCharacter
    ? mockRuns.filter((run) => run.character_name === selectedCharacter.name)
    : [];

  // Mock DPS history for selected character
  const characterDPSHistory = mockDPSTrend.map((point, index) => ({
    date: new Date(point.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    dps: point.dps + (selectedCharacter ? (selectedCharacter.id === 'char-001' ? 0 : -5000 - index * 500) : 0),
  }));

  const classIcons: Record<string, string> = {
    Dragonknight: 'text-orange-400',
    Nightblade: 'text-purple-400',
    Sorcerer: 'text-blue-400',
    Templar: 'text-yellow-400',
    Warden: 'text-green-400',
    Necromancer: 'text-emerald-400',
    Arcanist: 'text-cyan-400',
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-100">Characters</h1>
        <p className="text-gray-500 mt-1">
          View and manage your character roster and their performance stats.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Character List */}
        <div className="lg:col-span-1 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-100">Your Characters</h2>
            <span className="text-sm text-gray-500">{mockCharacters.length} total</span>
          </div>
          <div className="space-y-4">
            {mockCharacters.map((character) => (
              <CharacterCard
                key={character.id}
                character={character}
                onClick={() => setSelectedCharacter(character)}
                isSelected={selectedCharacter?.id === character.id}
              />
            ))}
          </div>
        </div>

        {/* Character Details */}
        <div className="lg:col-span-2">
          {selectedCharacter ? (
            <div className="space-y-6">
              {/* Character Header */}
              <div className="card">
                <div className="flex items-start justify-between mb-6">
                  <div className="flex items-center gap-4">
                    <div className="w-16 h-16 rounded-xl bg-eso-dark-800 flex items-center justify-center">
                      <span className={clsx('text-3xl', classIcons[selectedCharacter.class])}>
                        {selectedCharacter.class.charAt(0)}
                      </span>
                    </div>
                    <div>
                      <h2 className="text-xl font-bold text-gray-100">
                        {selectedCharacter.name}
                      </h2>
                      <p className={clsx('text-sm', classIcons[selectedCharacter.class])}>
                        {selectedCharacter.class}
                        {selectedCharacter.subclass && ` / ${selectedCharacter.subclass}`}
                      </p>
                      <p className="text-sm text-gray-500">
                        {selectedCharacter.race} - CP {selectedCharacter.cp_level}
                      </p>
                    </div>
                  </div>
                  <span className="badge-info text-lg px-4 py-2">
                    CP {selectedCharacter.cp_level}
                  </span>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-eso-dark-800 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-1">
                      <Swords className="w-4 h-4 text-gray-400" />
                      <span className="text-xs text-gray-500">Avg DPS</span>
                    </div>
                    <p className="text-xl font-bold text-gray-100">
                      {formatDPS(selectedCharacter.average_dps)}
                    </p>
                  </div>
                  <div className="bg-eso-dark-800 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-1">
                      <Trophy className="w-4 h-4 text-eso-gold-400" />
                      <span className="text-xs text-gray-500">Best DPS</span>
                    </div>
                    <p className="text-xl font-bold text-eso-gold-400">
                      {formatDPS(selectedCharacter.best_dps)}
                    </p>
                  </div>
                  <div className="bg-eso-dark-800 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-1">
                      <History className="w-4 h-4 text-gray-400" />
                      <span className="text-xs text-gray-500">Total Runs</span>
                    </div>
                    <p className="text-xl font-bold text-gray-100">
                      {selectedCharacter.total_runs}
                    </p>
                  </div>
                  <div className="bg-eso-dark-800 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-1">
                      <Calendar className="w-4 h-4 text-gray-400" />
                      <span className="text-xs text-gray-500">Favorite</span>
                    </div>
                    <p className="text-sm font-bold text-gray-100 truncate">
                      {selectedCharacter.favorite_content}
                    </p>
                  </div>
                </div>
              </div>

              {/* Current Build */}
              <div className="card">
                <h3 className="text-lg font-semibold text-gray-100 mb-4">Current Build</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <p className="text-xs text-gray-500 mb-2">Equipped Sets</p>
                    <div className="space-y-2">
                      {selectedCharacter.current_sets.map((set) => (
                        <div
                          key={set}
                          className="flex items-center justify-between bg-eso-dark-800 rounded-lg px-4 py-3"
                        >
                          <span className="text-gray-100">{set}</span>
                          <span className="badge-warning">5pc</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-2">Class Skills</p>
                    <div className="bg-eso-dark-800 rounded-lg p-4">
                      <div className="grid grid-cols-3 gap-2">
                        {['Molten Whip', 'Burning Embers', 'Venomous Claw', 'Flames of Oblivion', 'Bull Netch', 'Standard of Might'].map((skill) => (
                          <div
                            key={skill}
                            className="text-center p-2 bg-eso-dark-700 rounded"
                          >
                            <p className="text-xs text-gray-400 truncate">{skill}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* DPS History Chart */}
              <div className="card">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-semibold text-gray-100">DPS History</h3>
                  <div className="flex items-center gap-2 text-eso-green-400">
                    <TrendingUp className="w-4 h-4" />
                    <span className="text-sm font-medium">Improving</span>
                  </div>
                </div>
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={characterDPSHistory}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#393941" />
                      <XAxis
                        dataKey="date"
                        stroke="#737383"
                        fontSize={12}
                        tickLine={false}
                      />
                      <YAxis
                        stroke="#737383"
                        fontSize={12}
                        tickLine={false}
                        tickFormatter={(value) => formatDPS(value)}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#41414b',
                          border: '1px solid #4c4c58',
                          borderRadius: '8px',
                        }}
                        labelStyle={{ color: '#eeeef0' }}
                        formatter={(value: number) => [formatDPS(value), 'DPS']}
                      />
                      <Line
                        type="monotone"
                        dataKey="dps"
                        stroke="#d4a012"
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Recent Runs */}
              <div>
                <h3 className="text-lg font-semibold text-gray-100 mb-4">
                  Recent Runs
                </h3>
                {characterRuns.length > 0 ? (
                  <div className="space-y-3">
                    {characterRuns.map((run) => (
                      <RunCard key={run.run_id} run={run} />
                    ))}
                  </div>
                ) : (
                  <div className="card text-center py-8">
                    <p className="text-gray-500">No runs found for this character</p>
                    <p className="text-sm text-gray-600 mt-1">
                      Complete some content to see run history
                    </p>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="card flex flex-col items-center justify-center h-96">
              <div className="w-16 h-16 bg-eso-dark-800 rounded-full flex items-center justify-center mb-4">
                <Clock className="w-8 h-8 text-gray-500" />
              </div>
              <h3 className="text-lg font-medium text-gray-100 mb-2">
                Select a Character
              </h3>
              <p className="text-gray-500 text-center max-w-sm">
                Choose a character from the list to view their detailed stats,
                build information, and run history.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
