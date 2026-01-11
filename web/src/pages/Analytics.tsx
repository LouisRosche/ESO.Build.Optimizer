import { useState, useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
} from 'recharts';
import { Calendar, Skull, Zap, Target, TrendingUp, AlertTriangle } from 'lucide-react';
import clsx from 'clsx';
import {
  mockDPSTrend,
  mockBuffAnalysis,
  mockRuns,
  formatDPS,
  mockDetailedRun,
} from '../data/mockData';

export default function Analytics() {
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d');

  // Format data for charts - memoized to prevent unnecessary recalculations
  const dpsTrendData = useMemo(() => mockDPSTrend.map((point) => ({
    ...point,
    date: new Date(point.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
  })), []);

  // Crit rate data from mock runs - memoized to prevent Math.random() UI flickering
  const critRateData = useMemo(() => mockRuns.slice(0, 8).map((_, index) => ({
    run: `Run ${index + 1}`,
    critRate: (0.55 + Math.random() * 0.15) * 100, // Mock crit rates 55-70%
  })), []);

  // Buff uptime data for radar chart
  const buffRadarData = useMemo(() => mockBuffAnalysis.map((buff) => ({
    buff: buff.name.replace('Major ', '').replace('Minor ', ''),
    current: buff.average_uptime * 100,
    target: buff.target_uptime * 100,
  })), []);

  // Deaths per content type
  const deathsData = useMemo(() => [
    { content: 'Trials', deaths: 12 },
    { content: 'Dungeons', deaths: 5 },
    { content: 'Arenas', deaths: 3 },
    { content: 'Overworld', deaths: 1 },
  ], []);

  // Contribution breakdown from detailed run
  const contributionData = useMemo(() => mockDetailedRun.contribution_scores
    ? Object.entries(mockDetailedRun.contribution_scores).map(([key, value]) => ({
        category: key
          .replace(/_/g, ' ')
          .replace(/\b\w/g, (l) => l.toUpperCase()),
        value: Math.round(value * 100),
      }))
    : [], []);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Analytics</h1>
          <p className="text-gray-500 mt-1">
            Deep dive into your performance metrics and trends.
          </p>
        </div>
        <div className="flex items-center gap-2 bg-eso-dark-900 p-1 rounded-lg">
          {(['7d', '30d', '90d'] as const).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={clsx(
                'px-4 py-2 text-sm font-medium rounded-md transition-colors',
                timeRange === range
                  ? 'bg-eso-gold-500/20 text-eso-gold-400'
                  : 'text-gray-400 hover:text-gray-100'
              )}
            >
              {range === '7d' ? '7 Days' : range === '30d' ? '30 Days' : '90 Days'}
            </button>
          ))}
        </div>
      </div>

      {/* Performance Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-eso-gold-500/10 rounded-lg">
              <TrendingUp className="w-5 h-5 text-eso-gold-400" />
            </div>
            <div>
              <p className="stat-label">DPS Growth</p>
              <p className="text-xl font-bold text-eso-green-400">+31.7%</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-eso-blue-500/10 rounded-lg">
              <Zap className="w-5 h-5 text-eso-blue-400" />
            </div>
            <div>
              <p className="stat-label">Avg Crit Rate</p>
              <p className="text-xl font-bold text-gray-100">62.4%</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-eso-green-500/10 rounded-lg">
              <Target className="w-5 h-5 text-eso-green-400" />
            </div>
            <div>
              <p className="stat-label">Buff Uptime</p>
              <p className="text-xl font-bold text-gray-100">73.8%</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-eso-red-500/10 rounded-lg">
              <Skull className="w-5 h-5 text-eso-red-400" />
            </div>
            <div>
              <p className="stat-label">Deaths (30d)</p>
              <p className="text-xl font-bold text-gray-100">21</p>
            </div>
          </div>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* DPS Over Time */}
        <div className="card">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-gray-100">DPS Over Time</h2>
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-gray-500" />
              <span className="text-sm text-gray-500">Last {timeRange}</span>
            </div>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={dpsTrendData}>
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
                  dot={{ fill: '#d4a012', r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Buff Uptime Radar */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-100 mb-6">Buff Uptime Analysis</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={buffRadarData}>
                <PolarGrid stroke="#393941" />
                <PolarAngleAxis
                  dataKey="buff"
                  tick={{ fill: '#737383', fontSize: 11 }}
                />
                <PolarRadiusAxis
                  angle={30}
                  domain={[0, 100]}
                  tick={{ fill: '#737383', fontSize: 10 }}
                />
                <Radar
                  name="Current"
                  dataKey="current"
                  stroke="#d4a012"
                  fill="#d4a012"
                  fillOpacity={0.3}
                />
                <Radar
                  name="Target"
                  dataKey="target"
                  stroke="#22c55e"
                  fill="#22c55e"
                  fillOpacity={0.1}
                  strokeDasharray="5 5"
                />
                <Legend />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Crit Rate Per Run */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-100 mb-6">Crit Rate by Run</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={critRateData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#393941" />
                <XAxis
                  dataKey="run"
                  stroke="#737383"
                  fontSize={12}
                  tickLine={false}
                />
                <YAxis
                  stroke="#737383"
                  fontSize={12}
                  tickLine={false}
                  domain={[0, 100]}
                  tickFormatter={(value) => `${value}%`}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#41414b',
                    border: '1px solid #4c4c58',
                    borderRadius: '8px',
                  }}
                  labelStyle={{ color: '#eeeef0' }}
                  formatter={(value: number) => [`${value.toFixed(1)}%`, 'Crit Rate']}
                />
                <Bar dataKey="critRate" radius={[4, 4, 0, 0]}>
                  {critRateData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.critRate >= 65 ? '#22c55e' : entry.critRate >= 60 ? '#d4a012' : '#ef4444'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Deaths by Content */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-100 mb-6">Deaths by Content Type</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={deathsData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#393941" horizontal={false} />
                <XAxis type="number" stroke="#737383" fontSize={12} tickLine={false} />
                <YAxis
                  type="category"
                  dataKey="content"
                  stroke="#737383"
                  fontSize={12}
                  tickLine={false}
                  width={80}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#41414b',
                    border: '1px solid #4c4c58',
                    borderRadius: '8px',
                  }}
                  labelStyle={{ color: '#eeeef0' }}
                />
                <Bar dataKey="deaths" fill="#ef4444" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Buff Uptime Details */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-100 mb-6">Buff Uptime Details</h2>
        <div className="space-y-4">
          {mockBuffAnalysis.map((buff) => {
            const uptimePercent = Math.round(buff.average_uptime * 100);
            const targetPercent = Math.round(buff.target_uptime * 100);
            const gap = targetPercent - uptimePercent;

            return (
              <div key={buff.name} className="flex items-center gap-4">
                <div className="w-36 flex-shrink-0">
                  <p className="text-sm font-medium text-gray-100">{buff.name}</p>
                  <div className="flex items-center gap-1">
                    {buff.importance === 'critical' && (
                      <AlertTriangle className="w-3 h-3 text-eso-red-400" />
                    )}
                    <span
                      className={clsx(
                        'text-xs',
                        buff.importance === 'critical'
                          ? 'text-eso-red-400'
                          : buff.importance === 'high'
                          ? 'text-eso-gold-400'
                          : 'text-gray-500'
                      )}
                    >
                      {buff.importance.charAt(0).toUpperCase() + buff.importance.slice(1)}
                    </span>
                  </div>
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-gray-400">
                      {uptimePercent}% / {targetPercent}%
                    </span>
                    {gap > 10 && (
                      <span className="text-xs text-eso-red-400">-{gap}% below target</span>
                    )}
                  </div>
                  <div className="h-2 bg-eso-dark-800 rounded-full overflow-hidden">
                    <div
                      className={clsx(
                        'h-full rounded-full transition-all',
                        uptimePercent >= targetPercent - 5
                          ? 'bg-eso-green-500'
                          : uptimePercent >= targetPercent - 15
                          ? 'bg-eso-gold-500'
                          : 'bg-eso-red-500'
                      )}
                      style={{ width: `${uptimePercent}%` }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Contribution Scores */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-100 mb-6">Contribution Breakdown</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
          {contributionData.map((item) => (
            <div key={item.category} className="text-center">
              <div
                className="w-20 h-20 mx-auto rounded-full flex items-center justify-center text-lg font-bold"
                style={{
                  background: `conic-gradient(
                    ${item.value >= 80 ? '#22c55e' : item.value >= 60 ? '#d4a012' : '#ef4444'} ${item.value * 3.6}deg,
                    #393941 0deg
                  )`,
                }}
              >
                <div className="w-16 h-16 rounded-full bg-eso-dark-900 flex items-center justify-center">
                  <span className="text-gray-100">{item.value}%</span>
                </div>
              </div>
              <p className="mt-2 text-xs text-gray-400">{item.category}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
