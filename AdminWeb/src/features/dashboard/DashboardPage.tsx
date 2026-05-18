/**
 * PURPOSE:
 * Admin dashboard page showing live stats, period analytics, and term
 * configuration used by reporting/analytics filters.
 *
 * API ENDPOINTS USED:
 * - GET /terms
 * - PUT /terms
 * - GET /analytics/dashboard
 */
import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { api } from '../../lib/axios';
import { Loader2, Calendar, Settings, X } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { queryClient } from '../../lib/react-query';

type TermItem = {
  id: string;
  name: string;
  start: string;
  end: string;
};

type TermConfigModalProps = {
  isOpen: boolean;
  isSaving: boolean;
  initialTerms: TermItem[];
  onClose: () => void;
  onSave: (terms: TermItem[]) => void;
};

const TermConfigModal = ({ isOpen, isSaving, initialTerms, onClose, onSave }: TermConfigModalProps) => {
  const [terms, setTerms] = useState<TermItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setTerms(initialTerms);
      setError(null);
    }
  }, [isOpen, initialTerms]);

  if (!isOpen) return null;

  const updateTerm = (index: number, key: keyof TermItem, value: string) => {
    setTerms((prev) => prev.map((term, i) => (i === index ? { ...term, [key]: value } : term)));
  };

  const addTerm = () => {
    setTerms((prev) => [
      ...prev,
      {
        id: '',
        name: '',
        start: '',
        end: '',
      },
    ]);
  };

  const removeTerm = (index: number) => {
    setTerms((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSave = () => {
    const seenIds = new Set<string>();

    for (const term of terms) {
      if (!term.id.trim() || !term.name.trim() || !term.start.trim() || !term.end.trim()) {
        setError('All fields are required for every term.');
        return;
      }

      if (term.end < term.start) {
        setError(`End date cannot be before start date for ${term.id}.`);
        return;
      }

      if (seenIds.has(term.id.trim())) {
        setError(`Duplicate term code found: ${term.id}.`);
        return;
      }
      seenIds.add(term.id.trim());
    }

    setError(null);
    onSave(terms);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-500/30 backdrop-blur-sm">
      <div className="bg-white rounded-lg shadow-lg w-full max-w-4xl p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-bold text-gray-900">Configure Terms</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <p className="text-sm text-gray-500 mb-6">Set the start and end dates for academic terms. These dates are used for analytics filtering.</p>

        <div className="space-y-4">
          <div className="grid grid-cols-[1.2fr_1.8fr_1fr_1fr_auto] gap-4 font-semibold text-sm text-gray-600 px-2">
            <div>Code</div>
            <div>Term Name</div>
            <div>Start Date</div>
            <div>End Date</div>
            <div></div>
          </div>
          
          <div className="max-h-102 overflow-y-auto space-y-2">
            {terms.map((term, index) => (
              <div key={index} className="grid grid-cols-[1.2fr_1.8fr_1fr_1fr_auto] gap-4 items-center bg-gray-50 p-2 rounded border border-gray-100">
                <input 
                  type="text" 
                  value={term.id}
                  onChange={(e) => updateTerm(index, 'id', e.target.value)}
                  placeholder="winter_2027"
                  className="border border-gray-300 rounded px-2 py-1 text-sm w-full outline-none focus:border-blue-500"
                />
                <input 
                  type="text" 
                  value={term.name}
                  onChange={(e) => updateTerm(index, 'name', e.target.value)}
                  className="border border-gray-300 rounded px-2 py-1 text-sm w-full outline-none focus:border-blue-500"
                />
                <input 
                  type="date" 
                  value={term.start}
                  onChange={(e) => updateTerm(index, 'start', e.target.value)}
                  className="border border-gray-300 rounded px-2 py-1 text-sm w-full outline-none focus:border-blue-500" 
                />
                <input 
                  type="date" 
                  value={term.end}
                  onChange={(e) => updateTerm(index, 'end', e.target.value)}
                  className="border border-gray-300 rounded px-2 py-1 text-sm w-full outline-none focus:border-blue-500" 
                />
                <button onClick={() => removeTerm(index)} className="text-red-500 hover:text-red-700 text-sm px-2">Remove</button>
              </div>
            ))}
          </div>
          
          <button onClick={addTerm} className="text-blue-600 hover:text-blue-700 text-sm font-medium flex items-center gap-1 mt-2">
            + Add New Term
          </button>

          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>

        <div className="mt-8 flex justify-end gap-3">
          <button 
            onClick={onClose} 
            disabled={isSaving}
            className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button 
            onClick={handleSave}
            disabled={isSaving}
            className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:bg-gray-400"
          >
            {isSaving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
};

export const DashboardPage = () => {
  const [period, setPeriod] = useState('1_month');
  const [showConfigModal, setShowConfigModal] = useState(false);

  const termsQuery = useQuery({
    queryKey: ['terms'],
    queryFn: async () => {
      const response = await api.get('/terms');
      return (response.data.terms ?? []) as TermItem[];
    }
  });

  const saveTermsMutation = useMutation({
    mutationFn: async (terms: TermItem[]) => {
      const response = await api.put('/terms', { terms });
      return response.data;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['terms'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
      ]);
      setShowConfigModal(false);
    },
  });

  const periods = useMemo(() => {
    const termOptions = (termsQuery.data ?? []).map((term) => ({ value: term.id, label: term.name }));
    return [{ value: '1_month', label: 'Recent 1 Month' }, ...termOptions];
  }, [termsQuery.data]);

  useEffect(() => {
    if (!periods.some((p) => p.value === period)) {
      setPeriod('1_month');
    }
  }, [period, periods]);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['dashboard', period],
    queryFn: async () => {
      const { data } = await api.get('/analytics/dashboard', {
        params: { period }
      });
      return data;
    }
  });

  if (isLoading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (isError) {
    return <div className="p-4 text-red-600">Failed to load dashboard data.</div>;
  }

  const { live_stats, period_stats } = data || {};
  const selectedPeriodLabel = periods.find((p) => p.value === period)?.label ?? period;
  const rangeStartLabel = period_stats?.start_date ? new Date(period_stats.start_date).toLocaleDateString() : '-';
  const rangeEndLabel = period_stats?.end_date ? new Date(period_stats.end_date).toLocaleDateString() : '-';

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-black">Dashboard</h2>
        
        {/* Period Selector */}
        <div className="flex items-center gap-2">
            <Calendar className="w-5 h-5 text-gray-500" />
            <select 
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
                className="bg-white border border-gray-300 text-gray-700 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block p-2.5 outline-none"
            >
                {periods.map(p => (
                    <option key={p.value} value={p.value}>{p.label}</option>
                ))}
            </select>
            <button 
              onClick={() => setShowConfigModal(true)}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors text-gray-500 hover:text-gray-700 ml-1"
              title="Configure Term Dates"
            >
              <Settings className="w-5 h-5" />
            </button>
        </div>
      </div>

      {/* Live Stats Grid (Always Current) */}
      <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Current Status</h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Total Inventory</p>
          <p className="text-3xl font-bold text-gray-900">{live_stats?.total_tools ?? '-'}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Currently Borrowed</p>
          <p className="text-3xl font-bold text-blue-600">{live_stats?.current_borrowed ?? '-'}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Currently Overdue</p>
          <p className="text-3xl font-bold text-red-600">{live_stats?.current_overdue ?? '-'}</p>
        </div>
      </div>

      {/* Period Stats */}
      <div className="pt-4">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
            Analytics ({selectedPeriodLabel})
        </h3>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Activity Summary */}
            <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Total Checkouts in Period</p>
                <p className="text-3xl font-bold text-gray-900 mb-2">{period_stats?.checkouts ?? 0}</p>
                <p className="text-sm text-gray-500">
                  From {rangeStartLabel} to {rangeEndLabel}
                </p>
            </div>

            {/* Top 10 Borrowed Tools (Chart) */}
            <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100 min-h-[400px]">
              <h3 className="text-lg font-bold text-gray-900 mb-4">Top Used Tools</h3>
              {period_stats?.top_tools && period_stats.top_tools.length > 0 ? (
                <div className="h-[300px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={period_stats.top_tools}
                      layout="vertical"
                      margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
                      <XAxis type="number" hide />
                      <YAxis 
                        dataKey="name" 
                        type="category" 
                        width={150} 
                        tick={{ fontSize: 12 }} 
                      />
                      <Tooltip 
                        contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                        cursor={{ fill: '#f3f4f6' }}
                      />
                      <Bar 
                        dataKey="uses" 
                        fill="#3b82f6" 
                        radius={[0, 4, 4, 0]} 
                        barSize={20}
                        name="Usage Count"
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-full flex items-center justify-center text-gray-500 text-sm">
                  No usage data for this period.
                </div>
              )}
            </div>
        </div>
      </div>
      
      <TermConfigModal 
        isOpen={showConfigModal} 
        isSaving={saveTermsMutation.isPending}
        initialTerms={termsQuery.data ?? []}
        onClose={() => setShowConfigModal(false)} 
        onSave={(terms) => saveTermsMutation.mutate(terms)}
      />
    </div>
  );
};
