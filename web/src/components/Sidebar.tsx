import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  GitCompare,
  BarChart3,
  Users,
  Lightbulb,
  Settings,
  LogOut,
} from 'lucide-react';
import clsx from 'clsx';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Build Comparison', href: '/builds', icon: GitCompare },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Characters', href: '/characters', icon: Users },
  { name: 'Recommendations', href: '/recommendations', icon: Lightbulb },
];

export default function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-eso-dark-900 border-r border-eso-dark-700 flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-eso-dark-700">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-eso-gold-400 to-eso-gold-600 flex items-center justify-center">
            <span className="text-eso-dark-950 font-bold text-lg">E</span>
          </div>
          <div>
            <h1 className="font-bold text-gray-100">ESO Optimizer</h1>
            <p className="text-xs text-gray-500">Build Analytics</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-eso-gold-500/10 text-eso-gold-400 border border-eso-gold-500/20'
                  : 'text-gray-400 hover:text-gray-100 hover:bg-eso-dark-800'
              )
            }
          >
            <item.icon className="w-5 h-5" />
            {item.name}
          </NavLink>
        ))}
      </nav>

      {/* Bottom section */}
      <div className="p-4 border-t border-eso-dark-700 space-y-1">
        <button className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium text-gray-400 hover:text-gray-100 hover:bg-eso-dark-800 transition-colors">
          <Settings className="w-5 h-5" />
          Settings
        </button>
        <button className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium text-gray-400 hover:text-gray-100 hover:bg-eso-dark-800 transition-colors">
          <LogOut className="w-5 h-5" />
          Sign Out
        </button>
      </div>

      {/* User info */}
      <div className="p-4 border-t border-eso-dark-700">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-eso-dark-700 flex items-center justify-center">
            <span className="text-gray-300 font-medium">DK</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-100 truncate">Drakonis</p>
            <p className="text-xs text-gray-500">CP 2100</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
