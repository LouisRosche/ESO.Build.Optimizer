import { Swords, Trophy, Clock, Target, TrendingUp } from 'lucide-react';
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
import {
  mockRuns,
  mockStatistics,
  mockDPSTrend,
  mockPercentileTrend,
  formatDPS,
} from '../data/mockData';

export default function Dashboard() {
  const successRate = Math.round(
    (mockStatistics.successful_runs / mockStatistics.total_runs) * 100
  );

  const totalPlayTimeHours = Math.round(mockStatistics.total_play_time_sec / 3600);

  // Format trend data for charts
  const dpsTrendData = mockDPSTrend.map((point) => ({
    ...point,
    date: new Date(point.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
  }));

  const percentileTrendData = mockPercentileTrend.map((point) => ({
    ...point,
    date: new Date(point.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
  }));

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-100">Dashboard</h1>
        <p className="text-gray-500 mt-1">
          Welcome back, Drakonis. Here's your performance overview.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Runs"
          value={mockStatistics.total_runs}
          subtitle={`${successRate}% success rate`}
          icon={Target}
        />
        <StatCard
          title="Average DPS"
          value={formatDPS(mockStatistics.average_dps)}
          trend={{ value: 12, isPositive: true }}
          icon={Swords}
        />
        <StatCard
          title="Best DPS"
          value={formatDPS(mockStatistics.best_dps)}
          subtitle={mockStatistics.favorite_content || 'N/A'}
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
            <div className="flex items-center gap-2 text-eso-green-400">
              <TrendingUp className="w-4 h-4" />
              <span className="text-sm font-medium">+31.7%</span>
            </div>
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
            <span className="text-2xl font-bold text-eso-gold-400">
              85th
            </span>
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
          <button className="btn-ghost text-sm">View All</button>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {mockRuns.slice(0, 6).map((run) => (
            <RunCard key={run.run_id} run={run} />
          ))}
        </div>
      </div>
    </div>
  );
}
