import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Swords, Trophy, Clock, Target, TrendingUp, Loader2, AlertCircle } from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts';
import StatCard from '../components/StatCard';
import RunCard from '../components/RunCard';
import { useRuns, useRunStatistics, useDPSTrend, usePercentileTrend } from '../hooks/useApi';
import {
  mockRuns,
  mockStatistics,
  mockDPSTrend,
  mockPercentileTrend,
  formatDPS,
} from '../data/mockData';

export default function Dashboard() {
  const { data: apiRuns, isLoading: runsLoading, error: runsError } = useRuns({ limit: 6 });
  const { data: apiStats, isLoading: statsLoading } = useRunStatistics();
  const { data: apiDPSTrend, isLoading: dpsTrendLoading } = useDPSTrend({ time_range: '30d' });
  const { data: apiPercentileTrend, isLoading: percentileTrendLoading } = usePercentileTrend({ time_range: '30d' });

  // Fall back to mock data when API is unreachable
  const runs = apiRuns ?? mockRuns;
  const statistics = apiStats ?? mockStatistics;
  const dpsTrend = apiDPSTrend ?? mockDPSTrend;
  const percentileTrend = apiPercentileTrend ?? mockPercentileTrend;

  const isLoading = runsLoading || statsLoading;
  const usingMockData = !apiRuns && !runsLoading;

  const successRate = statistics.total_runs > 0
    ? Math.round((statistics.successful_runs / statistics.total_runs) * 100)
    : 0;

  const totalPlayTimeHours = Math.round(statistics.total_play_time_sec / 3600);

  // Format trend data for charts - memoized to prevent unnecessary recalculations
  const dpsTrendData = useMemo(() => dpsTrend.map((point) => ({
    ...point,
    date: new Date(point.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
  })), [dpsTrend]);

  const percentileTrendData = useMemo(() => percentileTrend.map((point) => ({
    ...point,
    date: new Date(point.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
  })), [percentileTrend]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-eso-gold-400 animate-spin" />
          <p className="text-gray-400">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-100">Dashboard</h1>
        <p className="text-gray-500 mt-1">
          Welcome back, {statistics.favorite_character ?? 'Adventurer'}. Here's your performance overview.
        </p>
        {usingMockData && (
          <div className="flex items-center gap-2 mt-2 text-sm text-eso-gold-400">
            <AlertCircle className="w-4 h-4" />
            <span>API unavailable - showing sample data</span>
          </div>
        )}
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Runs"
          value={statistics.total_runs}
          subtitle={`${successRate}% success rate`}
          icon={Target}
        />
        <StatCard
          title="Average DPS"
          value={formatDPS(statistics.average_dps)}
          trend={{ value: 12, isPositive: true }}
          icon={Swords}
        />
        <StatCard
          title="Best DPS"
          value={formatDPS(statistics.best_dps)}
          subtitle={statistics.favorite_content || 'N/A'}
          icon={Trophy}
        />
        <StatCard
          title="Play Time"
          value={`${totalPlayTimeHours}h`}
          subtitle="Total tracked time"
          icon={Clock}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* DPS Trend Chart */}
        <div className="card">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold text-gray-100">DPS Trend</h2>
              <p className="text-sm text-gray-500">Last 30 days performance</p>
            </div>
            {dpsTrendLoading ? (
              <Loader2 className="w-4 h-4 text-gray-500 animate-spin" />
            ) : (
              <div className="flex items-center gap-2 text-eso-green-400">
                <TrendingUp className="w-4 h-4" />
                <span className="text-sm font-medium">+31.7%</span>
              </div>
            )}
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={dpsTrendData}>
                <defs>
                  <linearGradient id="dpsGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#d4a012" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#d4a012" stopOpacity={0} />
                  </linearGradient>
                </defs>
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
                <Area
                  type="monotone"
                  dataKey="dps"
                  stroke="#d4a012"
                  strokeWidth={2}
                  fill="url(#dpsGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Percentile Trend Chart */}
        <div className="card">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold text-gray-100">Percentile Ranking</h2>
              <p className="text-sm text-gray-500">Compared to similar players</p>
            </div>
            {percentileTrendLoading ? (
              <Loader2 className="w-4 h-4 text-gray-500 animate-spin" />
            ) : (
              <span className="text-2xl font-bold text-eso-gold-400">
                {percentileTrendData.length > 0
                  ? `${percentileTrendData[percentileTrendData.length - 1].percentile}th`
                  : '--'}
              </span>
            )}
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={percentileTrendData}>
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
                  formatter={(value: number) => [`${value}th percentile`, 'Rank']}
                />
                <Line
                  type="monotone"
                  dataKey="percentile"
                  stroke="#22c55e"
                  strokeWidth={2}
                  dot={{ fill: '#22c55e', r: 4 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Recent Runs */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-100">Recent Encounters</h2>
          <Link to="/analytics" className="btn-ghost text-sm">View All</Link>
        </div>
        {runsError && !apiRuns && (
          <div className="flex items-center gap-2 mb-4 text-sm text-gray-500">
            <AlertCircle className="w-4 h-4" />
            <span>Could not reach API - displaying sample runs</span>
          </div>
        )}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {runs.slice(0, 6).map((run) => (
            <RunCard key={run.run_id} run={run} />
          ))}
        </div>
      </div>
    </div>
  );
}
