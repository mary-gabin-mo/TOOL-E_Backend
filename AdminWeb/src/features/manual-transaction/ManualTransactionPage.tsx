/**
 * PURPOSE:
 * Staff fallback page to manually create checkout transactions or process
 * returns when kiosk flow is unavailable.
 *
 * API ENDPOINTS USED:
 * - GET /tools
 * - POST /transactions
 * - GET /transactions
 * - PUT /transactions/{transaction_id}
 */
import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/axios';

const deriveStatus = (tx: any) => {
  if (tx.return_timestamp) return 'Returned';
  if (tx.desired_return_date) {
    const due = new Date(tx.desired_return_date);
    if (!isNaN(due.getTime()) && Date.now() > due.getTime()) return 'Overdue';
  }
  return 'Borrowed';
};

const StatusBadge = ({ status }: { status: string }) => {
  const styles: Record<string, string> = {
    Borrowed: 'bg-blue-100 text-blue-700',
    Consumed: 'bg-gray-100 text-gray-700',
    Returned: 'bg-green-100 text-green-700',
    Overdue: 'bg-red-100 text-red-700',
  };

  return (
    <span
      className={`px-3 py-1 rounded-full text-xs font-semibold ${
        styles[status] || 'bg-gray-100 text-gray-700'
      }`}
    >
      {status}
    </span>
  );
};

export const ManualTransactionPage = () => {
  const [activeTab, setActiveTab] = useState<'checkout' | 'return'>('checkout');
  const [userId, setUserId] = useState('');
  const [selectedToolId, setSelectedToolId] = useState('');
  const [manualToolName, setManualToolName] = useState('');
  const [purpose, setPurpose] = useState('');
  const [courseCode, setCourseCode] = useState('');
  const [teamName, setTeamName] = useState('');
  const [desiredReturnDate, setDesiredReturnDate] = useState('');
  const [formError, setFormError] = useState<string | null>(null);

  const [returnUserId, setReturnUserId] = useState('');
  const [lookupUserId, setLookupUserId] = useState('');
  const [selectedTransactionId, setSelectedTransactionId] = useState<number | null>(null);

  const queryClient = useQueryClient();
  const isOtherTool = selectedToolId === 'other';

  const buildPurposePayload = () => {
    const basePurpose = (() => {
      if (purpose === 'Academic Course') {
        return `Academic Course: ${courseCode}`;
      }
      if (purpose === 'Team') {
        return `Team: ${teamName.trim()}`;
      }
      return purpose || null;
    })();

    if (isOtherTool && manualToolName.trim()) {
      return `${basePurpose} | Tool: ${manualToolName.trim()}`;
    }

    return basePurpose;
  };

  const { data: tools = [] } = useQuery<{ id: number; name: string }[]>({
    queryKey: ['tools'],
    queryFn: async () => {
      const { data } = await api.get('/tools');
      return data;
    },
  });

  const checkoutMutation = useMutation({
    mutationFn: async () => {
      await api.post('/transactions', {
        user_id: userId ? Number(userId) : null,
        tool_id: selectedToolId && !isOtherTool ? Number(selectedToolId) : null,
        desired_return_date: desiredReturnDate || null,
        purpose: buildPurposePayload(),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      setUserId('');
      setSelectedToolId('');
      setManualToolName('');
      setPurpose('');
      setCourseCode('');
      setTeamName('');
      setDesiredReturnDate('');
      setFormError(null);
    },
    onError: (err: any) => {
       setFormError(err.response?.data?.message || "Failed to create transaction.");
    }
  });

  const { data: userTransactions = [], isFetching: isFetchingReturns, isError, error } = useQuery<any[]>({
    queryKey: ['transactions', lookupUserId],
    queryFn: async () => {
      const parsedId = parseInt(lookupUserId, 10);
      if (isNaN(parsedId)) throw new Error('Invalid UCID');
      
      const { data } = await api.get('/transactions', {
        params: { user_id: parsedId, limit: 50 },
      });
      return data.items || [];
    },
    enabled: Boolean(lookupUserId),
    retry: false
  });

  const selectedTransaction = useMemo(() => {
    return userTransactions.find((tx) => tx.transaction_id === selectedTransactionId) || null;
  }, [userTransactions, selectedTransactionId]);

  const returnMutation = useMutation({
    mutationFn: async () => {
      if (!selectedTransactionId) return;
      await api.put(`/transactions/${selectedTransactionId}`, {
        return_timestamp: new Date().toISOString(),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions', lookupUserId] });
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      setSelectedTransactionId(null);
    },
  });

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-black">Manual Transaction (Staff Fallback)</h2>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 max-w-6xl mx-auto">
        <div className="flex gap-4 mb-6">
          <button
            className={`px-4 py-2 rounded-md text-sm font-medium ${
              activeTab === 'checkout' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'
            }`}
            onClick={() => setActiveTab('checkout')}
          >
            Checkout
          </button>
          <button
            className={`px-4 py-2 rounded-md text-sm font-medium ${
              activeTab === 'return' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'
            }`}
            onClick={() => setActiveTab('return')}
          >
            Return
          </button>
        </div>

        {activeTab === 'checkout' ? (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setFormError(null);

              if (!userId) {
                setFormError("Please enter a UCID.");
                return;
              }

              if (!/^\d+$/.test(userId)) {
                setFormError("UCID must contain only numbers.");
                return;
              }

              if (!selectedToolId) {
                setFormError("Please select a tool.");
                return;
              }

              if (isOtherTool && !manualToolName.trim()) {
                setFormError("Please enter the manual tool name for 'Other'.");
                return;
              }

              if (!desiredReturnDate) {
                 setFormError("Please select a desired return date.");
                 return;
              }

              if (!purpose) {
                setFormError("Please select a purpose.");
                return;
              }

              if (purpose === 'Academic Course') {
                const normalizedCode = courseCode.trim().toUpperCase();
                if (!/^[A-Z]{4}\d{3}$/.test(normalizedCode)) {
                  setFormError("Course code must be 4 letters followed by 3 numbers (e.g., ENGG123).");
                  return;
                }
              }

              if (purpose === 'Team' && !teamName.trim()) {
                setFormError("Please enter a team name.");
                return;
              }

              const [y, m, d] = desiredReturnDate.split('-').map(Number);
              const returnDate = new Date(y, m - 1, d);
              const today = new Date();
              today.setHours(0, 0, 0, 0);
              
              if (returnDate < today) {
                setFormError("Return date cannot be in the past.");
                return;
              }

              checkoutMutation.mutate();
            }}
            className="space-y-4"
          >
            {formError && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative text-sm">
                <span className="block sm:inline">{formError}</span>
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">UCID</label>
              <input
                type="text"
                placeholder="e.g., 12345678"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tool</label>
              <select
                value={selectedToolId}
                onChange={(e) => {
                  const value = e.target.value;
                  setSelectedToolId(value);
                  if (value !== 'other') {
                    setManualToolName('');
                  }
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white"
              >
                <option value="">Select a tool...</option>
                {tools.map((tool) => (
                  <option key={tool.id} value={tool.id}>
                    {tool.name} (#{tool.id})
                  </option>
                ))}
                <option value="other">Other (Manual Entry)</option>
              </select>
            </div>

            {isOtherTool && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Manual Tool Name</label>
                <input
                  type="text"
                  placeholder="Enter tool name"
                  value={manualToolName}
                  onChange={(e) => setManualToolName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
            )}


            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Desired Return Date</label>
              <input
                type="date"
                value={desiredReturnDate}
                onChange={(e) => setDesiredReturnDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Purpose</label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {['Academic Course', 'Personal Project', 'Team', 'Research'].map((option) => (
                  <button
                    key={option}
                    type="button"
                    onClick={() => {
                      setPurpose(option);
                      if (option !== 'Academic Course') {
                        setCourseCode('');
                      }
                      if (option !== 'Team') {
                        setTeamName('');
                      }
                    }}
                    className={`px-4 py-2 rounded-md text-sm font-medium border transition-colors ${
                      purpose === option
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                    }`}
                  >
                    {option}
                  </button>
                ))}
              </div>
            </div>

            {purpose === 'Academic Course' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Course Code</label>
                <input
                  type="text"
                  placeholder="e.g., ENGG123"
                  value={courseCode}
                  onChange={(e) => setCourseCode(e.target.value.toUpperCase())}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  maxLength={7}
                />
              </div>
            )}

            {purpose === 'Team' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Team Name</label>
                <input
                  type="text"
                  placeholder="Enter team name"
                  value={teamName}
                  onChange={(e) => setTeamName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
            )}

            <div className="pt-2 flex justify-end">
              <button
                type="submit"
                disabled={checkoutMutation.isPending}
                className="px-6 py-2 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 disabled:bg-gray-400"
              >
                {checkoutMutation.isPending ? 'Saving...' : 'Create Transaction'}
              </button>
            </div>
          </form>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">UCID</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Search UCID"
                  value={returnUserId}
                  onChange={(e) => setReturnUserId(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      setLookupUserId(returnUserId);
                    }
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
                <button
                  type="button"
                  onClick={() => setLookupUserId(returnUserId)}
                  className="px-4 py-2 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700"
                >
                  Lookup
                </button>
              </div>
            </div>

            <div className="border rounded-md overflow-hidden bg-white shadow-sm min-h-[400px]">
              <div className="px-4 py-3 text-sm font-medium bg-gray-50 border-b border-gray-200 flex justify-between items-center">
                <span>Select a Transaction to Return</span>
                {lookupUserId && <span className="text-xs text-gray-500 font-normal">Showing results for UCID: {lookupUserId}</span>}
              </div>
              
              {isFetchingReturns ? (
                <div className="p-10 text-center text-sm text-gray-500">Loading transactions...</div>
              ) : isError ? (
                 <div className="p-10 text-center text-sm text-red-500">
                  {error instanceof Error && error.message === 'Invalid UCID' 
                    ? 'Please enter a valid numeric UCID.' 
                    : 'Failed to load transactions. Check connection or UCID.'}
                 </div>
              ) : userTransactions.length === 0 ? (
                <div className="p-10 text-center text-sm text-gray-500">
                  {lookupUserId ? 'No transactions found for this user.' : 'Use the lookup box to search for a user.'}
                </div>
              ) : (
                <div className="overflow-x-auto max-h-[600px]">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-gray-50 text-gray-500 font-medium border-b border-gray-100 sticky top-0 z-10 shadow-sm">
                      <tr>
                        <th className="px-4 py-3 whitespace-nowrap">ID</th>
                        <th className="px-4 py-3 whitespace-nowrap">UCID</th>
                        <th className="px-4 py-3 whitespace-nowrap">Tool</th>
                        <th className="px-4 py-3 whitespace-nowrap">Date Out</th>
                        <th className="px-4 py-3 whitespace-nowrap">Purpose</th>
                        <th className="px-4 py-3 whitespace-nowrap">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {userTransactions.map((tx) => {
                        const toolName = tools.find((t) => t.id === tx.tool_id)?.name || 'Unknown';
                        const status = deriveStatus(tx);
                        const isSelected = selectedTransactionId === tx.transaction_id;
                        
                        return (
                          <tr 
                            key={tx.transaction_id}
                            onClick={() => {
                              setSelectedTransactionId(tx.transaction_id);
                            }}
                            className={`cursor-pointer transition-colors ${
                              isSelected 
                                ? 'bg-blue-50 hover:bg-blue-100 ring-1 ring-inset ring-blue-200' 
                                : 'hover:bg-gray-50'
                            }`}
                          >
                            <td className="px-4 py-3 font-medium text-gray-900">#{tx.transaction_id}</td>
                            <td className="px-4 py-3 text-gray-900">{tx.user_id}</td>
                            <td className="px-4 py-3 text-gray-600">
                                <div className="font-medium text-gray-900">{toolName}</div>
                                <div className="text-xs text-gray-400">ID: {tx.tool_id}</div>
                            </td>
                            <td className="px-4 py-3 text-gray-600">
                              {new Date(tx.checkout_timestamp).toLocaleDateString()}
                              <div className="text-xs text-gray-400">
                                {new Date(tx.checkout_timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                              </div>
                            </td>
                             <td className="px-4 py-3 text-gray-600 max-w-[150px] truncate" title={tx.purpose || ''}>
                              {tx.purpose || '-'}
                            </td>
                            <td className="px-4 py-3">
                              <StatusBadge status={status} />
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {selectedTransaction && (
              <div className="space-y-4 pt-4 border-t border-gray-100">
                <div className="flex items-center justify-between bg-blue-50 p-4 rounded-lg border border-blue-100">
                  <div>
                    <h3 className="font-semibold text-blue-900">Return Action</h3>
                    <p className="text-sm text-blue-700">
                      Mark Transaction #{selectedTransaction.transaction_id} as returned at {new Date().toLocaleTimeString()}?
                    </p>
                  </div>
                  <button
                    onClick={() => returnMutation.mutate()}
                    disabled={returnMutation.isPending}
                    className="px-6 py-2 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 disabled:bg-gray-400 shadow-sm flex items-center gap-2"
                  >
                    {returnMutation.isPending ? (
                      <>Processing...</> 
                    ) : (
                      <>Confirm Return (Now)</>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
