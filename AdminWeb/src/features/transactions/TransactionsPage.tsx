/**
 * PURPOSE:
 * Transaction log page for staff to search, filter, sort, paginate, and
 * delete transaction records.
 *
 * API ENDPOINTS USED:
 * - GET /transactions
 * - DELETE /transactions/{transaction_id}
 */
import React, { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ChevronDown, Trash2, ArrowUp, ArrowDown, ArrowUpDown, Loader2, ChevronLeft, ChevronRight } from 'lucide-react';
import clsx from 'clsx';
import { api } from '../../lib/axios';

interface Transaction {
  transaction_id: number;
  user_id: number | null;
  user_name?: string;
  tool_id: number | null;
  tool_name?: string;
  checkout_timestamp: string;
  desired_return_date: string | null;
  return_timestamp: string | null;
  quantity: number;
  purpose: string | null;
  image_path: string | null;
  classification_correct: boolean | null;
  weight: number;
}

interface TransactionsResponse {
  items: Transaction[];
  total: number;
  page: number;
  size: number;
  pages: number;
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

export const TransactionsPage = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const queryClient = useQueryClient();

  // Sorting State
  const [sortConfig, setSortConfig] = useState<{ key: 'dateOut' | 'dateDue'; direction: 'asc' | 'desc' }>({
    key: 'dateOut',
    direction: 'desc',
  });

  // Filtering State
  const [isStatusDropdownOpen, setIsStatusDropdownOpen] = useState(false);
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>([]);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const uniqueStatuses = ['Borrowed', 'Returned', 'Consumed', 'Overdue'];

  const { data, isLoading, isError, error } = useQuery<TransactionsResponse>({
    queryKey: ['transactions', page, searchTerm, sortConfig, selectedStatuses],
    queryFn: async () => {
      const { data } = await api.get('/transactions', {
        params: { 
          page, 
          limit: 50,
          search_term: searchTerm,
          sort_by: sortConfig.key,
          sort_order: sortConfig.direction,
          status: selectedStatuses.length > 0 ? selectedStatuses.join(',') : undefined
        }
      });
      return data;
    },
    placeholderData: (previousData) => previousData, // Keep previous data while fetching new sorted data
  });

  const transactions = data?.items || [];
  const totalPages = data?.pages || 1;

  const deleteMutation = useMutation({
    mutationFn: async (transactionId: number) => {
      await api.delete(`/transactions/${transactionId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
    },
  });

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsStatusDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const toggleStatusFilter = (status: string) => {
    setSelectedStatuses((prev) =>
      prev.includes(status)
        ? prev.filter((s) => s !== status)
        : [...prev, status]
    );
  };

  const handleSort = (key: 'dateOut' | 'dateDue') => {
    setSortConfig((current) => ({
      key,
      direction:
        current.key === key && current.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  function deriveStatus(tx: Transaction) {
    if (tx.return_timestamp) return 'Returned';
    if (tx.desired_return_date) {
      const due = new Date(tx.desired_return_date);
      if (!isNaN(due.getTime()) && Date.now() > due.getTime()) return 'Overdue';
    }
    return 'Borrowed';
  }

  // Handle Search Input Change with Debounce or Page Reset
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
    setPage(1); // Reset to page 1 on new search
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-black">Transaction Log</h2>
      </div>

      {/* Search Bar */}
      <div className="relative">
        <input
          type="text"
          placeholder="Search by user ID, tool ID, or purpose"
          value={searchTerm}
          onChange={handleSearchChange}
          className="w-full pl-4 pr-4 py-3 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
        />
      </div>

      {/* Transactions Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-gray-100">
              <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Transaction ID
              </th>
              <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                UCID
              </th>
              <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Tool
              </th>
              <th 
                className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-50 transition-colors"
                onClick={() => handleSort('dateOut')}
              >
                <div className="flex items-center">
                  Date Out
                  {sortConfig.key === 'dateOut' ? (
                    sortConfig.direction === 'asc' ? <ArrowUp className="w-3 h-3 ml-1" /> : <ArrowDown className="w-3 h-3 ml-1" />
                  ) : (
                    <ArrowUpDown className="w-3 h-3 ml-1 text-gray-300" />
                  )}
                </div>
              </th>
              <th 
                className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-50 transition-colors"
                onClick={() => handleSort('dateDue')}
              >
                <div className="flex items-center">
                  Date Due
                  {sortConfig.key === 'dateDue' ? (
                    sortConfig.direction === 'asc' ? <ArrowUp className="w-3 h-3 ml-1" /> : <ArrowDown className="w-3 h-3 ml-1" />
                  ) : (
                    <ArrowUpDown className="w-3 h-3 ml-1 text-gray-300" />
                  )}
                </div>
              </th>
              <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Date Returned
              </th>
              <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider min-w-[260px]">
                Purpose
              </th>
              <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider relative">
                <div ref={dropdownRef} className="relative inline-block">
                  <div 
                    className="flex items-center cursor-pointer hover:text-gray-700"
                    onClick={() => setIsStatusDropdownOpen(!isStatusDropdownOpen)}
                  >
                    Status
                    <ChevronDown className="w-3 h-3 ml-1" />
                  </div>

                  {/* Status Filter Dropdown */}
                  {isStatusDropdownOpen && (
                    <div className="absolute top-full right-0 mt-2 w-48 bg-white rounded-md shadow-lg border border-gray-100 z-10 p-2">
                      {uniqueStatuses.map((status) => (
                        <label key={status} className="flex items-center px-2 py-2 hover:bg-gray-50 rounded cursor-pointer">
                          <input
                            type="checkbox"
                            checked={selectedStatuses.includes(status)}
                            onChange={() => toggleStatusFilter(status)}
                            className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                          />
                          <span className="ml-2 text-sm text-gray-700">{status}</span>
                        </label>
                      ))}
                    </div>
                  )}
                </div>
              </th>
              <th className="py-4 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider w-[120px]">
                Classified
              </th>
              <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                {/* Actions column */}
              </th>
            </tr>
          </thead>
          <tbody className="">
            {isLoading ? (
              <tr>
                <td colSpan={10} className="py-10 text-center text-sm text-gray-500">
                  Loading transactions...
                </td>
              </tr>
            ) : isError ? (
              <tr>
                <td colSpan={10} className="py-10 text-center text-sm text-red-500">
                  Failed to load transactions.
                  {error instanceof Error ? ` ${error.message}` : ''}
                </td>
              </tr>
            ) : transactions.length === 0 ? (
              <tr>
                <td colSpan={10} className="py-10 text-center text-sm text-gray-500">
                  No transactions found.
                </td>
              </tr>
            ) : (
              transactions.map((tx) => (
              <tr key={tx.transaction_id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                <td className="py-4 px-6 text-sm text-gray-900">
                  #{tx.transaction_id}
                </td>
                <td className="py-4 px-6 text-sm font-medium text-gray-900">
                   <div className="flex flex-col">
                      <span>{tx.user_name || 'Unknown'}</span>
                      <span className="text-[10px] text-gray-400">ID: {tx.user_id}</span>
                   </div>
                </td>
                <td className="py-4 px-6 text-sm text-gray-500">
                   <div className="flex flex-col">
                      <span>{tx.tool_name || 'Unknown'}</span>
                      <span className="text-[10px] text-gray-400">ID: {tx.tool_id}</span>
                   </div>
                </td>
                <td className="py-4 px-6 text-sm text-gray-500">
                  {new Date(tx.checkout_timestamp).toLocaleDateString()}
                  <span className="text-xs text-gray-400 block">
                    {new Date(tx.checkout_timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </td>
                <td className="py-4 px-6 text-sm text-gray-500">
                   {tx.desired_return_date ? new Date(tx.desired_return_date).toLocaleDateString() : 'N/A'}
                </td>
                <td className="py-4 px-6 text-sm text-gray-500">
                  {tx.return_timestamp ? (
                    <>
                      {new Date(tx.return_timestamp).toLocaleDateString()}
                      <span className="text-xs text-gray-400 block">
                        {new Date(tx.return_timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </td>
                 <td className="py-4 px-6 text-sm text-gray-500 max-w-[340px] whitespace-normal break-words" title={tx.purpose || ''}>
                   {tx.purpose || '-'}
                </td>
                <td className="py-4 px-6 text-sm">
                  <StatusBadge status={deriveStatus(tx)} />
                </td>
                <td className="py-4 px-4 text-sm">
                  {tx.classification_correct === true ? (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                      Yes
                    </span>
                  ) : tx.classification_correct === false ? (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                      No
                    </span>
                  ) : (
                    <span className="text-gray-400 text-xs">-</span>
                  )}
                </td>
                <td className="py-4 px-6 text-sm text-right">
                  <button
                    className="text-gray-400 hover:text-red-500 transition-colors"
                    onClick={() => {
                        if(window.confirm('Are you sure you want to delete this transaction record?')) {
                            deleteMutation.mutate(tx.transaction_id);
                        }
                    }}
                    disabled={deleteMutation.isPending}
                  >
                    {deleteMutation.isPending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                  </button>
                </td>
              </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      <div className="flex items-center justify-between border-t border-gray-200 bg-white px-4 py-3 sm:px-6 rounded-lg shadow-sm">
        <div className="flex flex-1 justify-between sm:hidden">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="relative inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            Previous
          </button>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="relative ml-3 inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            Next
          </button>
        </div>
        <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
          <div>
            <p className="text-sm text-gray-700">
              Showing page <span className="font-medium">{page}</span> of{' '}
              <span className="font-medium">{totalPages}</span> ({data?.total || 0} results)
            </p>
          </div>
          <div>
            <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm" aria-label="Pagination">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="relative inline-flex items-center rounded-l-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50"
              >
                <span className="sr-only">Previous</span>
                <ChevronLeft className="h-5 w-5" aria-hidden="true" />
              </button>
              {Array.from({ length: totalPages }, (_, i) => i + 1)
                .filter(p => p === 1 || p === totalPages || Math.abs(page - p) <= 1)
                .map((p, index, array) => {
                   // Add ellipsis logic if needed, simplify for now
                   const showEllipsis = index > 0 && p - array[index - 1] > 1;

                   return (
                    <React.Fragment key={p}>
                      {showEllipsis && <span className="relative inline-flex items-center px-4 py-2 text-sm font-semibold text-gray-700 ring-1 ring-inset ring-gray-300 focus:outline-offset-0">...</span>}
                      <button
                        onClick={() => setPage(p)}
                        className={clsx(
                          p === page
                            ? 'relative z-10 inline-flex items-center bg-blue-600 px-4 py-2 text-sm font-semibold text-white focus:z-20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600'
                            : 'relative inline-flex items-center px-4 py-2 text-sm font-semibold text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0'
                        )}
                      >
                        {p}
                      </button>
                    </React.Fragment>
                   );
                })}
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="relative inline-flex items-center rounded-r-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50"
              >
                <span className="sr-only">Next</span>
                <ChevronRight className="h-5 w-5" aria-hidden="true" />
              </button>
            </nav>
          </div>
        </div>
      </div>
    </div>
  );
};
