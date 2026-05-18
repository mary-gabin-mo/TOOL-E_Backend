/**
 * PURPOSE:
 * Inventory management page for browsing tools, sorting/filtering, and
 * uploading or replacing stock reference images.
 *
 * API ENDPOINTS USED:
 * - GET /tools
 * - PUT /tools/{tool_id}/stock-image
 */
import { useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, ArrowUp, ArrowDown, ArrowUpDown, Loader2, Search, X, ImagePlus, ChevronRight } from 'lucide-react';
import { AddToolModal } from './AddToolModal';
import { api } from '../../lib/axios';

// API Response type
interface Tool {
  id: number;
  name: string;
  size: string | null;
  type: string;
  status: string;
  total_quantity: number;
  available_quantity: number;
  consumed_quantity: number;
  trained: boolean;
  stock_image_b64?: string | null;
}

type SortKey = 'id' | 'name' | 'available_quantity';
type SortDirection = 'asc' | 'desc';

export const InventoryPage = () => {
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState('all');
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const queryClient = useQueryClient();
  
  // Fetch Tools
  const { data: tools = [], isLoading, isError } = useQuery<Tool[]>({
    queryKey: ['tools'],
    queryFn: async () => {
      const { data } = await api.get('/tools');
      return data;
    },
  });

  const uploadStockImageMutation = useMutation({
    mutationFn: async (file: File) => {
      if (!selectedTool) throw new Error('No tool selected');
      const formData = new FormData();
      formData.append('file', file);
      await api.put(`/tools/${selectedTool.id}/stock-image`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['tools'] });
    },
  });

  // Sorting State
  const [sortConfig, setSortConfig] = useState<{ key: SortKey; direction: SortDirection }>({
    key: 'id',
    direction: 'asc',
  });

  const uniqueTypes = useMemo(() => {
    return Array.from(new Set(tools.map((item) => item.type).filter(Boolean))).sort((a, b) => a.localeCompare(b));
  }, [tools]);

  // Derived Data
  const filteredAndSortedData = useMemo(() => {
    let data = [...tools];

    // 1. Filter by Search Query
    if (searchQuery) {
      const lowerQuery = searchQuery.toLowerCase();
      data = data.filter((item) => 
        item.name.toLowerCase().includes(lowerQuery)
      );
    }

    // 2. Filter by Type
    if (selectedType !== 'all') {
      data = data.filter((item) => item.type === selectedType);
    }

    // 3. Sort
    data.sort((a, b) => {
      if (sortConfig.key === 'id') {
        return sortConfig.direction === 'asc'
          ? a.id - b.id
          : b.id - a.id;
      } else if (sortConfig.key === 'name') {
        return sortConfig.direction === 'asc'
          ? a.name.localeCompare(b.name)
          : b.name.localeCompare(a.name);
      } else if (sortConfig.key === 'available_quantity') {
        return sortConfig.direction === 'asc'
          ? a.available_quantity - b.available_quantity
          : b.available_quantity - a.available_quantity;
      }
      return 0;
    });

    return data;
  }, [tools, sortConfig, searchQuery, selectedType]);

  const handleSort = (key: SortKey) => {
    setSortConfig((current) => ({
      key,
      direction:
        current.key === key && current.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  /*
  const toggleTypeFilter = (type: string) => {
    setSelectedTypes((prev) =>
      prev.includes(type)
        ? prev.filter((t) => t !== type)
        : [...prev, type]
    );
  };
  */

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="text-red-600 p-4 bg-red-50 rounded-lg">
        Error loading tools. Please try again later.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header & Actions */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h2 className="text-2xl font-bold text-black">Tool Inventory</h2>
        
        <div className="flex flex-col sm:flex-row gap-4 w-full sm:w-auto">
          {/* Search Bar */}
          <div className="relative w-full sm:w-96">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-4 w-4 text-gray-400" />
            </div>
            <input
              type="text"
              className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm transition duration-150 ease-in-out"
              placeholder="Search by name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="w-full sm:w-56">
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="block w-full px-3 py-2 border border-gray-300 rounded-md bg-white text-sm text-gray-700 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="all">All Tool Types</option>
              {uniqueTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => setIsAddModalOpen(true)}
            className="flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors font-medium whitespace-nowrap"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add New Tool
          </button>
        </div>
      </div>

      {/* Inventory Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-visible">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-gray-100">
              {/* ID Column - Sortable */}
              <th 
                className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-50 transition-colors"
                onClick={() => handleSort('id')}
              >
                <div className="flex items-center">
                  ID
                  {sortConfig.key === 'id' ? (
                    sortConfig.direction === 'asc' ? <ArrowUp className="w-3 h-3 ml-1" /> : <ArrowDown className="w-3 h-3 ml-1" />
                  ) : (
                    <ArrowUpDown className="w-3 h-3 ml-1 text-gray-300" />
                  )}
                </div>
              </th>

              {/* Name Column - Sortable */}
              <th 
                className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-50 transition-colors"
                onClick={() => handleSort('name')}
              >
                <div className="flex items-center">
                  Tool Name
                  {sortConfig.key === 'name' ? (
                    sortConfig.direction === 'asc' ? <ArrowUp className="w-3 h-3 ml-1" /> : <ArrowDown className="w-3 h-3 ml-1" />
                  ) : (
                    <ArrowUpDown className="w-3 h-3 ml-1 text-gray-300" />
                  )}
                </div>
              </th>

              {/* Tool Type Column */}
              <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Tool Type
              </th>

              {/* Size Column */}
              <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Size
              </th>

              {/* Total Column - Static */}
              <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Total
              </th>

              {/* Available Column - Sortable */}
              <th 
                className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-50 transition-colors"
                onClick={() => handleSort('available_quantity')}
              >
                <div className="flex items-center">
                  Available
                  {sortConfig.key === 'available_quantity' ? (
                    sortConfig.direction === 'asc' ? <ArrowUp className="w-3 h-3 ml-1" /> : <ArrowDown className="w-3 h-3 ml-1" />
                  ) : (
                    <ArrowUpDown className="w-3 h-3 ml-1 text-gray-300" />
                  )}
                </div>
              </th>

              {/* Status Column */}
              <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Status
              </th>

              <th className="py-4 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider text-right">
                
              </th>
            </tr>
          </thead>
          <tbody className="">
            {filteredAndSortedData.map((item, index) => (
              <tr
                key={`${item.id}-${index}`}
                className="group border-b border-gray-100 hover:bg-gray-50 transition-colors cursor-pointer"
                onClick={() => setSelectedTool(item)}
              >
                <td className="py-4 px-6 text-sm text-gray-500">
                  #{item.id}
                </td>
                <td className="py-4 px-6 text-sm font-medium text-gray-900">
                  <div className="flex flex-col items-start gap-1">
                    <span>{item.name}</span>
                    {!item.trained && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800">
                        ML Training Required
                      </span>
                    )}
                  </div>
                </td>
                <td className="py-4 px-6 text-sm text-gray-500">
                  {item.type || '-'}
                </td>
                <td className="py-4 px-6 text-sm text-gray-500">
                  {item.size || '-'}
                </td>
                <td className="py-4 px-6 text-sm text-gray-500">
                  {item.total_quantity}
                </td>
                <td className="py-4 px-6 text-sm text-gray-500">
                  {item.available_quantity}
                </td>
                <td className="py-4 px-6 text-sm">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    item.status === 'Available' ? 'bg-green-100 text-green-700' :
                    item.status === 'Low Stock' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-red-100 text-red-700'
                  }`}>
                    {item.status}
                  </span>
                </td>
                <td className="py-4 px-4 text-right">
                  <span className="inline-flex items-center text-gray-300 group-hover:text-gray-500 transition-colors">
                    <ChevronRight className="w-4 h-4" />
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Add Tool Modal */}
      <AddToolModal 
        isOpen={isAddModalOpen} 
        onClose={() => setIsAddModalOpen(false)} 
      />

      {selectedTool && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
          onClick={() => setSelectedTool(null)}
        >
          <div
            className="bg-white rounded-lg shadow-xl w-full max-w-2xl overflow-hidden"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{selectedTool.name}</h3>
                <p className="text-sm text-gray-500">Tool #{selectedTool.id} • {selectedTool.type}</p>
              </div>
              <button
                onClick={() => setSelectedTool(null)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div className="border border-gray-200 rounded-lg bg-gray-50 min-h-[280px] flex items-center justify-center overflow-hidden">
                {selectedTool.stock_image_b64 ? (
                  <img
                    src={`data:image/jpeg;base64,${selectedTool.stock_image_b64}`}
                    alt={`${selectedTool.name} stock`}
                    className="max-h-[420px] w-auto object-contain"
                  />
                ) : (
                  <div className="text-sm text-gray-500">No stock image uploaded yet.</div>
                )}
              </div>

              <div className="flex items-center justify-end gap-3">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (!file) return;
                    uploadStockImageMutation.mutate(file, {
                      onSuccess: () => {
                        const refreshed = queryClient
                          .getQueryData<Tool[]>(['tools'])
                          ?.find((tool) => tool.id === selectedTool.id);
                        if (refreshed) {
                          setSelectedTool(refreshed);
                        }
                      },
                    });
                    e.currentTarget.value = '';
                  }}
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploadStockImageMutation.isPending}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:bg-blue-400 inline-flex items-center gap-2"
                >
                  {uploadStockImageMutation.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <ImagePlus className="w-4 h-4" />
                      {selectedTool.stock_image_b64 ? 'Replace Stock Image' : 'Add Stock Image'}
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
