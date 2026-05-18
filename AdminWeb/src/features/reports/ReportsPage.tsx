/**
 * PURPOSE:
 * Reporting page that filters transactions by term/date range and exports
 * the resulting dataset to CSV.
 *
 * API ENDPOINTS USED:
 * - GET /terms
 * - GET /transactions
 */
import { useEffect, useMemo, useState } from 'react';
import { Download, Loader2, Calendar } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import clsx from 'clsx';
import { api } from '../../lib/axios';

interface TermItem {
  id: string;
  name: string;
  start: string;
  end: string;
}

interface Transaction {
  transaction_id: string;
  user_id?: number | null;
  user_name?: string | null;
  tool_id?: number | null;
  tool_name?: string | null;
  checkout_timestamp: string;
  desired_return_date: string | null;
  return_timestamp: string | null;
  purpose?: string | null;
  classification_correct?: boolean | null;
  status: string;
  quantity: number;
}

const StatusBadge = ({ status }: { status: string }) => {
  const styles = {
    Borrowed: 'bg-blue-100 text-blue-700',
    Consumed: 'bg-gray-100 text-gray-700',
    Returned: 'bg-green-100 text-green-700',
    Overdue: 'bg-red-100 text-red-700',
  };

  return (
    <span
      className={clsx(
        'px-3 py-1 rounded-full text-xs font-semibold',
        styles[status as keyof typeof styles] || 'bg-gray-100 text-gray-700'
      )}
    >
      {status}
    </span>
  );
};

export const ReportsPage = () => {
  const [selectedTermId, setSelectedTermId] = useState('custom');

  // Date state
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  
  // Trigger for refetching
  const [enabled, setEnabled] = useState(false);

  const termsQuery = useQuery({
    queryKey: ['terms'],
    queryFn: async () => {
      const response = await api.get('/terms');
      return (response.data.terms ?? []) as TermItem[];
    }
  });

  const termOptions = useMemo(() => termsQuery.data ?? [], [termsQuery.data]);

  useEffect(() => {
    if (selectedTermId === 'custom') return;
    const selectedTerm = termOptions.find((term) => term.id === selectedTermId);
    if (!selectedTerm) {
      setSelectedTermId('custom');
      return;
    }

    setStartDate(selectedTerm.start);
    setEndDate(selectedTerm.end);
  }, [selectedTermId, termOptions]);

  // Fetch Data
  const { data, isLoading, isError } = useQuery({
    queryKey: ['reports', startDate, endDate],
    queryFn: async () => {
      const params: any = { limit: 1000 }; // Fetch up to 1000 records for the report
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      
      const response = await api.get<{ items: Transaction[] }>('/transactions', { params });
      return response.data.items;
    },
    enabled: enabled, // Only run when enabled (after clicking Generate)
  });

  const handleGenerate = () => {
    if (!startDate || !endDate) return;
    setEnabled(true);
  };

  const handleDownload = () => {
    if (!data || data.length === 0) return;

    const headers = ['Transaction ID', 'User', 'Tool', 'Date Out', 'Due Date', 'Returned Date', 'Purpose', 'Status', 'Classified', 'Quantity'];

    const escapeCsv = (value: any) => {
      if (value === null || value === undefined) return '""';
      const str = typeof value === 'string' ? value : String(value);
      return '"' + str.replace(/"/g, '""') + '"';
    };

    const formatDateTime = (iso: string | null) => {
      if (!iso) return '';
      const d = new Date(iso);
      if (isNaN(d.getTime())) return '';
      const date = d.toLocaleDateString();
      const time = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      return `${date} ${time}`;
    };

    const rows = data.map(item => [
      item.transaction_id,
      item.user_name || 'Unknown',
      item.tool_name || 'Unknown',
      formatDateTime(item.checkout_timestamp),
      item.desired_return_date ? new Date(item.desired_return_date).toLocaleDateString() : 'N/A',
      item.return_timestamp ? formatDateTime(item.return_timestamp) : 'N/A',
      item.purpose || '',
      item.status,
      item.classification_correct === true ? 'Yes' : item.classification_correct === false ? 'No' : '',
      item.quantity,
    ]);

    const csvLines = [
      headers.map(escapeCsv).join(','),
      ...rows.map((r) => r.map(escapeCsv).join(',')),
    ];

    const csvContent = "data:text/csv;charset=utf-8," + csvLines.join('\n');

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    const rangeTag = selectedTermId !== 'custom'
      ? selectedTermId
      : `${startDate || 'all'}_to_${endDate || 'all'}`;
    link.setAttribute('download', `report_${rangeTag}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-black">Generate Reports</h2>
      </div>

      {/* Filter Card */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex flex-col gap-6">
          <div className="w-full">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Term
            </label>
            <div className="relative">
              <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <select
                value={selectedTermId}
                onChange={(e) => setSelectedTermId(e.target.value)}
                className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-600 bg-white"
              >
                <option value="custom">Custom Date Range</option>
                {termOptions.map((term) => (
                  <option key={term.id} value={term.id}>
                    {term.name}
                  </option>
                ))}
              </select>
            </div>
            {termsQuery.isError && (
              <p className="text-xs text-red-500 mt-1">Failed to load terms. You can still use custom dates.</p>
            )}
          </div>

          <div className="flex flex-col sm:flex-row items-end gap-6">
          <div className="flex-1 w-full">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Start Date
            </label>
            <div className="relative">
              <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="date"
                value={startDate}
                onChange={(e) => {
                  setStartDate(e.target.value);
                  setSelectedTermId('custom');
                }}
                className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-600"
              />
            </div>
          </div>
          <div className="flex-1 w-full">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              End Date
            </label>
            <div className="relative">
              <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="date"
                value={endDate}
                onChange={(e) => {
                  setEndDate(e.target.value);
                  setSelectedTermId('custom');
                }}
                className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-600"
              />
            </div>
          </div>
          <div className="flex gap-3">
            <button
              onClick={handleGenerate}
              disabled={!startDate || !endDate}
              className={`px-6 py-2 rounded-md transition-colors font-medium ${
                !startDate || !endDate
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              }`}
            >
              Generate Report
            </button>
            {data && data.length > 0 && (
              <button
                onClick={handleDownload}
                className="px-6 py-2 border border-green-600 text-green-600 bg-green-50 rounded-md hover:bg-green-100 transition-colors font-medium flex items-center gap-2"
              >
                <Download className="w-4 h-4" />
                Export CSV
              </button>
            )}
          </div>
          </div>
        </div>
      </div>

      {/* Results Table */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      ) : isError ? (
        <div className="text-red-500 bg-red-50 p-4 rounded-md">
          Failed to load report data. Please try again.
        </div>
      ) : data ? (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          {data.length === 0 ? (
            <div className="p-12 text-center text-gray-500">
              No transactions found for the selected period.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-100">
                    <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">Transaction ID</th>
                    <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">UCID</th>
                    <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">Tool</th>
                    <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">Date Out</th>
                    <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">Due Date</th>
                    <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">Date Returned</th>
                    <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider min-w-[260px]">Purpose</th>
                    <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
                    <th className="py-4 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider w-[120px]">Classified</th>
                    <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">Quantity</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {data.map((item) => (
                    <tr key={item.transaction_id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                      <td className="py-4 px-6 text-sm text-gray-900 font-medium">#{item.transaction_id}</td>
                      <td className="py-4 px-6 text-sm font-medium text-gray-900">
                        <div className="flex flex-col">
                          <span>{item.user_name || 'Unknown'}</span>
                          <span className="text-[10px] text-gray-400">ID: {item.user_id ?? '-'}</span>
                        </div>
                      </td>
                      <td className="py-4 px-6 text-sm text-gray-500">
                        <div className="flex flex-col">
                          <span>{item.tool_name || 'Unknown'}</span>
                          <span className="text-[10px] text-gray-400">ID: {item.tool_id ?? '-'}</span>
                        </div>
                      </td>
                      <td className="py-4 px-6 text-sm text-gray-500">
                        {new Date(item.checkout_timestamp).toLocaleDateString()}
                        <span className="text-xs text-gray-400 block">
                          {new Date(item.checkout_timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </td>
                      <td className="py-4 px-6 text-sm text-gray-500">
                        {item.desired_return_date ? new Date(item.desired_return_date).toLocaleDateString() : 'N/A'}
                      </td>
                      <td className="py-4 px-6 text-sm text-gray-500">
                        {item.return_timestamp ? (
                          <>
                            {new Date(item.return_timestamp).toLocaleDateString()}
                            <span className="text-xs text-gray-400 block">
                              {new Date(item.return_timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                          </>
                        ) : (
                          <span className="text-gray-400">N/A</span>
                        )}
                      </td>
                      <td className="py-4 px-6 text-sm text-gray-500 max-w-[340px] whitespace-normal break-words" title={item.purpose || ''}>
                        {item.purpose || '-'}
                      </td>
                      <td className="py-4 px-6 text-sm">
                        <StatusBadge status={item.status} />
                      </td>
                      <td className="py-4 px-4 text-sm">
                        {item.classification_correct === true ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">Yes</span>
                        ) : item.classification_correct === false ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">No</span>
                        ) : (
                          <span className="text-gray-400 text-xs">-</span>
                        )}
                      </td>
                      <td className="py-4 px-6 text-sm text-gray-500">{item.quantity}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        <div className="text-center py-12 bg-gray-50 rounded-lg border border-dashed border-gray-300">
          <div className="text-gray-500">Select dates and click "Generate Report" to view transactions.</div>
        </div>
      )}
    </div>
  );
};
