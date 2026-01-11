import { useState } from 'react';
import { Filter, Lightbulb, TrendingUp, AlertCircle, CheckCircle2, RefreshCw } from 'lucide-react';
import clsx from 'clsx';
import RecommendationCard from '../components/RecommendationCard';
import { mockRecommendations, mockRuns, formatDPS, getRelativeTime } from '../data/mockData';
import type { RecommendationCategory } from '../types';

export default function Recommendations() {
  const [selectedCategory, setSelectedCategory] = useState<RecommendationCategory | 'all'>('all');
  const [selectedRunId, setSelectedRunId] = useState<string | null>(mockRuns[0]?.run_id || null);

  const categories: { value: RecommendationCategory | 'all'; label: string; icon: typeof Lightbulb }[] = [
    { value: 'all', label: 'All', icon: Lightbulb },
    { value: 'gear', label: 'Gear', icon: Lightbulb },
    { value: 'skill', label: 'Skills', icon: Lightbulb },
    { value: 'execution', label: 'Execution', icon: Lightbulb },
    { value: 'build', label: 'Build', icon: Lightbulb },
  ];

  const filteredRecommendations = mockRecommendations.filter((rec) => {
    if (selectedCategory !== 'all' && rec.category !== selectedCategory) return false;
    if (selectedRunId && rec.run_id !== selectedRunId) return false;
    return true;
  });

  // Summary stats
  const totalRecommendations = mockRecommendations.length;
  const highConfidenceCount = mockRecommendations.filter((r) => r.confidence >= 0.8).length;
  const gearRecommendations = mockRecommendations.filter((r) => r.category === 'gear').length;
  const executionRecommendations = mockRecommendations.filter((r) => r.category === 'execution').length;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Recommendations</h1>
          <p className="text-gray-500 mt-1">
            AI-generated suggestions to improve your performance.
          </p>
        </div>
        <button className="btn-primary">
          <RefreshCw className="w-4 h-4" />
          Regenerate
        </button>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-eso-gold-500/10 rounded-lg">
              <Lightbulb className="w-5 h-5 text-eso-gold-400" />
            </div>
            <div>
              <p className="stat-label">Total</p>
              <p className="text-xl font-bold text-gray-100">{totalRecommendations}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-eso-green-500/10 rounded-lg">
              <CheckCircle2 className="w-5 h-5 text-eso-green-400" />
            </div>
            <div>
              <p className="stat-label">High Confidence</p>
              <p className="text-xl font-bold text-eso-green-400">{highConfidenceCount}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-eso-purple-500/10 rounded-lg">
              <TrendingUp className="w-5 h-5 text-eso-purple-400" />
            </div>
            <div>
              <p className="stat-label">Gear Changes</p>
              <p className="text-xl font-bold text-gray-100">{gearRecommendations}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-eso-blue-500/10 rounded-lg">
              <AlertCircle className="w-5 h-5 text-eso-blue-400" />
            </div>
            <div>
              <p className="stat-label">Execution Tips</p>
              <p className="text-xl font-bold text-gray-100">{executionRecommendations}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Filters Sidebar */}
        <div className="lg:col-span-1 space-y-6">
          {/* Category Filter */}
          <div className="card">
            <div className="flex items-center gap-2 mb-4">
              <Filter className="w-4 h-4 text-gray-400" />
              <h2 className="font-semibold text-gray-100">Category</h2>
            </div>
            <div className="space-y-1">
              {categories.map((cat) => (
                <button
                  key={cat.value}
                  onClick={() => setSelectedCategory(cat.value)}
                  className={clsx(
                    'w-full text-left px-3 py-2 rounded-lg text-sm transition-colors',
                    selectedCategory === cat.value
                      ? 'bg-eso-gold-500/10 text-eso-gold-400'
                      : 'text-gray-400 hover:text-gray-100 hover:bg-eso-dark-800'
                  )}
                >
                  {cat.label}
                </button>
              ))}
            </div>
          </div>

          {/* Run Filter */}
          <div className="card">
            <h2 className="font-semibold text-gray-100 mb-4">Select Run</h2>
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {mockRuns.map((run) => (
                <button
                  key={run.run_id}
                  onClick={() => setSelectedRunId(run.run_id)}
                  className={clsx(
                    'w-full text-left p-3 rounded-lg transition-colors',
                    selectedRunId === run.run_id
                      ? 'bg-eso-gold-500/10 border border-eso-gold-500/30'
                      : 'bg-eso-dark-800 hover:bg-eso-dark-700'
                  )}
                >
                  <p className="text-sm font-medium text-gray-100 truncate">
                    {run.content_name}
                  </p>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-xs text-gray-500">{run.character_name}</span>
                    <span className="text-xs text-gray-500">
                      {formatDPS(run.dps)}
                    </span>
                  </div>
                  <p className="text-xs text-gray-600 mt-1">
                    {getRelativeTime(run.timestamp)}
                  </p>
                </button>
              ))}
            </div>
          </div>

          {/* Confidence Legend */}
          <div className="card">
            <h2 className="font-semibold text-gray-100 mb-4">Confidence Levels</h2>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-4 h-4 text-eso-green-400" />
                <div>
                  <p className="text-sm text-gray-100">High (80%+)</p>
                  <p className="text-xs text-gray-500">Strong recommendation</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <TrendingUp className="w-4 h-4 text-eso-gold-400" />
                <div>
                  <p className="text-sm text-gray-100">Medium (60-79%)</p>
                  <p className="text-xs text-gray-500">Worth considering</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <AlertCircle className="w-4 h-4 text-gray-400" />
                <div>
                  <p className="text-sm text-gray-100">Low (&lt;60%)</p>
                  <p className="text-xs text-gray-500">Limited data</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Recommendations List */}
        <div className="lg:col-span-3">
          {filteredRecommendations.length > 0 ? (
            <div className="space-y-4">
              {filteredRecommendations.map((rec) => (
                <RecommendationCard key={rec.recommendation_id} recommendation={rec} />
              ))}
            </div>
          ) : (
            <div className="card flex flex-col items-center justify-center h-64">
              <Lightbulb className="w-12 h-12 text-gray-600 mb-4" />
              <h3 className="text-lg font-medium text-gray-100 mb-2">
                No Recommendations Found
              </h3>
              <p className="text-gray-500 text-center max-w-sm">
                {selectedCategory !== 'all'
                  ? `No ${selectedCategory} recommendations for the selected run.`
                  : 'Select a run to see its recommendations.'}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Improvement Summary */}
      {filteredRecommendations.length > 0 && (
        <div className="card bg-gradient-to-r from-eso-gold-500/10 to-eso-dark-900 border-eso-gold-500/30">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-100 mb-1">
                Potential Improvement Summary
              </h3>
              <p className="text-gray-400">
                Implementing all high-confidence recommendations could yield:
              </p>
            </div>
            <div className="text-right">
              <p className="text-3xl font-bold text-eso-green-400">+12-18%</p>
              <p className="text-sm text-gray-500">Estimated DPS increase</p>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-eso-dark-700">
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-2xl font-bold text-gray-100">+8%</p>
                <p className="text-xs text-gray-500">Gear optimization</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-100">+5%</p>
                <p className="text-xs text-gray-500">Buff uptime</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-100">+4%</p>
                <p className="text-xs text-gray-500">Build synergy</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
