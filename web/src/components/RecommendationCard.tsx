import { ArrowRight, TrendingUp, AlertCircle, CheckCircle2 } from 'lucide-react';
import clsx from 'clsx';
import type { Recommendation } from '../types';

interface RecommendationCardProps {
  recommendation: Recommendation;
  showDetails?: boolean;
}

export default function RecommendationCard({
  recommendation,
  showDetails = true,
}: RecommendationCardProps) {
  const categoryConfig = {
    gear: {
      label: 'Gear Change',
      color: 'text-eso-purple-400',
      bg: 'bg-eso-purple-500/10',
    },
    skill: {
      label: 'Skill Optimization',
      color: 'text-eso-blue-400',
      bg: 'bg-eso-blue-500/10',
    },
    execution: {
      label: 'Execution Improvement',
      color: 'text-eso-gold-400',
      bg: 'bg-eso-gold-500/10',
    },
    build: {
      label: 'Build Adjustment',
      color: 'text-eso-green-400',
      bg: 'bg-eso-green-500/10',
    },
  };

  const config = categoryConfig[recommendation.category];
  const confidencePercent = Math.round(recommendation.confidence * 100);

  return (
    <div className="card">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <span
            className={clsx(
              'inline-flex items-center justify-center w-8 h-8 rounded-lg text-sm font-bold',
              config.bg,
              config.color
            )}
          >
            {recommendation.priority}
          </span>
          <div>
            <span className={clsx('text-sm font-medium', config.color)}>
              {config.label}
            </span>
            <div className="flex items-center gap-2 mt-1">
              <div className="flex items-center gap-1">
                {confidencePercent >= 80 ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-eso-green-400" />
                ) : confidencePercent >= 60 ? (
                  <TrendingUp className="w-3.5 h-3.5 text-eso-gold-400" />
                ) : (
                  <AlertCircle className="w-3.5 h-3.5 text-gray-400" />
                )}
                <span className="text-xs text-gray-500">
                  {confidencePercent}% confidence
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Current -> Recommended */}
      <div className="flex items-center gap-3 mb-4">
        <div className="flex-1 bg-eso-dark-800 rounded-lg p-3">
          <p className="text-xs text-gray-500 mb-1">Current</p>
          <p className="text-sm text-gray-300">{recommendation.current_state}</p>
        </div>
        <ArrowRight className="w-5 h-5 text-eso-gold-400 flex-shrink-0" />
        <div className="flex-1 bg-eso-gold-500/10 border border-eso-gold-500/20 rounded-lg p-3">
          <p className="text-xs text-eso-gold-400 mb-1">Recommended</p>
          <p className="text-sm text-gray-100">{recommendation.recommended_change}</p>
        </div>
      </div>

      {/* Expected Improvement */}
      <div className="flex items-center gap-2 mb-4 p-3 bg-eso-green-500/10 border border-eso-green-500/20 rounded-lg">
        <TrendingUp className="w-5 h-5 text-eso-green-400" />
        <span className="text-sm font-medium text-eso-green-400">
          {recommendation.expected_improvement}
        </span>
      </div>

      {/* Reasoning */}
      {showDetails && (
        <div className="pt-4 border-t border-eso-dark-700">
          <p className="text-xs text-gray-500 mb-1">Analysis</p>
          <p className="text-sm text-gray-400">{recommendation.reasoning}</p>
        </div>
      )}
    </div>
  );
}
