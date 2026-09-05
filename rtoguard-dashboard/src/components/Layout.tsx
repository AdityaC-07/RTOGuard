import React, { ReactNode } from 'react';
import { Search, MapPin, Shield, FileText } from 'lucide-react';
import { useStore } from '../store/dashboardStore';

interface LayoutProps {
  children: ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { active_tab, setActiveTab } = useStore();

  const tabs = [
    { id: 'risk-scorer', label: 'Check an Order', icon: Search },
    { id: 'spike-detector', label: 'Area Alerts', icon: MapPin },
    { id: 'ring-sentinel', label: 'Fraud Groups', icon: Shield },
    { id: 'chargeback-responder', label: 'Disputes', icon: FileText },
  ];

  return (
    <div className="min-h-screen bg-beige flex flex-col md:flex-row">
      {/* Desktop Sidebar (>= 768px) */}
      <aside className="hidden md:flex w-[220px] bg-navy flex-col sticky top-0 h-screen shrink-0 border-r border-navy-light/30">
        
        {/* Header */}
        <div className="p-5 border-b border-navy-light/30">
          <h1 className="text-lg font-semibold text-beige">RTOGuard</h1>
          <p className="text-xs text-beige/70 mt-0.5">Fraud prevention for your store.</p>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex-1 py-4 space-y-1">
          {tabs.map(tab => {
            const Icon = tab.icon;
            const isActive = active_tab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`w-full flex items-center gap-3 px-5 py-3 text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-navy-light text-beige border-l-4 border-beige font-semibold'
                    : 'text-beige/80 hover:bg-navy-light/50 hover:text-beige border-l-4 border-transparent'
                }`}
              >
                <Icon size={16} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      {/* Mobile Bottom Navigation (< 768px) */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 bg-navy z-50 border-t border-navy-light/30 flex items-center justify-around h-16 px-2">
        {tabs.map(tab => {
          const Icon = tab.icon;
          const isActive = active_tab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex flex-col items-center justify-center gap-1 flex-1 py-1 text-xs transition-all ${
                isActive
                  ? 'text-beige font-semibold'
                  : 'text-beige/60 hover:text-beige'
              }`}
            >
              <Icon size={18} />
              <span className="text-[10px]">{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-h-screen overflow-x-hidden bg-beige text-ink">
        <main className="flex-1 p-4 md:p-6 pb-24 md:pb-6 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
};
