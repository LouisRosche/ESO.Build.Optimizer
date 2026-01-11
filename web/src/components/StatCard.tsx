import clsx from 'clsx';
import type { LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: LucideIcon;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  className?: string;
}

export default function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  className,
}: StatCardProps) {
  return (
    <div className={clsx('card', className)}>
      <div className="flex items-start justify-between">
        <div>
          <p className="stat-label">{title}</p>
          <p className="stat-value mt-1">{value}</p>
          {subtitle && (
            <p className="text-sm text-gray-500 mt-1">{subtitle}</p>
          )}
          {trend && (
            <div
              className={clsx(
                'flex items-center gap-1 mt-2 text-sm font-medium',
                trend.isPositive ? 'text-eso-green-400' : 'text-eso-red-400'
              )}
            >
              <span>{trend.isPositive ? '+' : ''}{trend.value}%</span>
              <span className="text-gray-500">vs last week</span>
            </div>
          )}
        </div>
        {Icon && (
          <div className="p-3 bg-eso-gold-500/10 rounded-lg">
            <Icon className="w-6 h-6 text-eso-gold-400" />
          </div>
        )}
      </div>
    </div>
  );
}
