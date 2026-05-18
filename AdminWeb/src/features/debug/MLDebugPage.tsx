/**
 * PURPOSE:
 * Manual ML debugging page for admins to upload a tool image and inspect
 * raw prediction output from the backend classifier.
 *
 * API ENDPOINTS USED:
 * - POST /identify_tool (multipart/form-data, field: file)
 */
import React, { useState } from 'react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

export const MLDebugPage: React.FC = () => {
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [prediction, setPrediction] = useState<any | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            setSelectedFile(e.target.files[0]);
            setPrediction(null);
            setError(null);
        }
    };

    const handleUpload = async () => {
        if (!selectedFile) return;

        setLoading(true);
        setError(null);
        setPrediction(null);

        const formData = new FormData();
        formData.append('file', selectedFile);

        try {
            const response = await axios.post(`${API_BASE_URL}/identify_tool`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });
            setPrediction(response.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || err.message || 'An error occurred during prediction.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="p-8 max-w-2xl mx-auto">
            <h1 className="text-2xl font-bold mb-6">ML Debug: Identify Tool</h1>
            
            <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
                <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Select an image to classify
                    </label>
                    <input
                        type="file"
                        accept="image/*"
                        onChange={handleFileChange}
                        className="block w-full text-sm text-gray-500
                            file:mr-4 file:py-2 file:px-4
                            file:rounded-full file:border-0
                            file:text-sm file:font-semibold
                            file:bg-blue-50 file:text-blue-700
                            hover:file:bg-blue-100"
                    />
                </div>

                <div className="flex items-center space-x-4">
                    <button
                        onClick={handleUpload}
                        disabled={!selectedFile || loading}
                        className={`px-4 py-2 rounded text-white font-medium ${
                            !selectedFile || loading
                                ? 'bg-gray-400 cursor-not-allowed'
                                : 'bg-blue-600 hover:bg-blue-700'
                        }`}
                    >
                        {loading ? 'Analyzing...' : 'Identify Tool'}
                    </button>
                    
                    {selectedFile && (
                        <span className="text-sm text-gray-500">
                            Selected: {selectedFile.name}
                        </span>
                    )}
                </div>

                {error && (
                    <div className="mt-4 p-4 bg-red-50 text-red-700 rounded-md">
                        <strong>Error:</strong> {error}
                    </div>
                )}

                {prediction && (
                    <div className="mt-6">
                        <h2 className="text-lg font-semibold mb-2 text-green-700">Result:</h2>
                        <div className="bg-gray-900 text-green-400 p-4 rounded overflow-auto font-mono text-xs shadow-inner">
                            <pre>{JSON.stringify(prediction, null, 2)}</pre>
                        </div>
                        
                        {prediction.success && (
                            <div className="mt-4 p-4 bg-green-50 rounded border border-green-200">
                                <p className="text-lg">
                                    <strong>Detected:</strong> {prediction.prediction}
                                </p>
                                <p>
                                    <strong>Score:</strong> {(prediction.score * 100).toFixed(2)}%
                                </p>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};
