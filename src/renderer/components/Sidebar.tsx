import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Bot, FlaskConical, ClipboardList, Eye, ScrollText, Settings, Menu } from 'lucide-react';
import { useTradingStore } from '../stores/trading-store';

const Sidebar: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const agentRunning = useTradingStore(state => state.agentState.running);
  const auth = useTradingStore(state => state.auth);
  const dashboard = useTradingStore(state => state.dashboard);

  const links = [
    { to: '/dashboard', icon: <LayoutDashboard size={20} />, label: 'Dashboard' },
    { to: '/agent', icon: <Bot size={20} />, label: 'Agent Control' },
    { to: '/paper-trade', icon: <FlaskConical size={20} />, label: 'Paper Trading' },
    { to: '/orders', icon: <ClipboardList size={20} />, label: 'Orders' },
    { to: '/watchlist', icon: <Eye size={20} />, label: 'Watchlist' },
    { to: '/activity', icon: <ScrollText size={20} />, label: 'Activity Log' },
    { to: '/settings', icon: <Settings size={20} />, label: 'Settings' }
  ];

  return (
    <div className={`bg-surface-900 border-r border-surface-800 flex flex-col transition-all duration-300 ${collapsed ? 'w-16' : 'w-60'}`}>
      <div className="flex items-center justify-between p-4 pt-10 border-b border-surface-800" style={{ WebkitAppRegion: 'drag' } as any}>
        {!collapsed && <span className="font-bold text-accent-light">SmartAPI Agent</span>}
        <button onClick={() => setCollapsed(!collapsed)} className="text-surface-400 hover:text-white transition-colors" style={{ WebkitAppRegion: 'no-drag' } as any}>
          <Menu size={20} />
        </button>
      </div>
      <nav className="flex-1 py-4">
        <ul className="space-y-1">
          {links.map(link => (
            <li key={link.to}>
              <NavLink
                to={link.to}
                className={({ isActive }) =>
                  `flex items-center px-4 py-3 transition-colors ${
                    isActive ? 'bg-surface-800 border-l-4 border-accent-light text-white' : 'text-surface-400 hover:bg-surface-800 hover:text-white border-l-4 border-transparent'
                  }`
                }
                title={collapsed ? link.label : undefined}
              >
                {link.icon}
                {!collapsed && <span className="ml-4">{link.label}</span>}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <div className="p-4 border-t border-surface-800 flex flex-col items-center">
        <div className="flex items-center w-full" title={agentRunning ? 'Agent Running' : 'Agent Stopped'}>
          <div className={`w-3 h-3 rounded-full ${agentRunning ? 'bg-profit-light animate-pulse-slow' : 'bg-surface-500'}`}></div>
          {!collapsed && <span className="ml-3 text-sm text-surface-300">{agentRunning ? 'Agent Active' : 'Agent Idle'}</span>}
        </div>
        {!collapsed && auth.isLoggedIn && (
          <div className="w-full mt-3 pt-3 border-t border-surface-800/80 flex flex-col gap-1 text-xs">
            <div className="text-surface-400 truncate">
              ID: <span className="text-white font-mono">{auth.credentials?.userId || 'Connected'}</span>
            </div>
            <div className="text-surface-400">
              Bal: <span className="text-profit-light font-mono font-bold">₹{(dashboard?.availableMargin || 0).toFixed(2)}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Sidebar;
