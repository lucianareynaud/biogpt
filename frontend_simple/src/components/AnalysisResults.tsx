import React from 'react'
import { AnalysisResult } from '../App'

interface AnalysisResultsProps {
  results: AnalysisResult[]
  onAnalysisSelect: (analysisId: string) => void
  selectedAnalysis: string | null
}

const AnalysisResults: React.FC<AnalysisResultsProps> = ({
  results,
  onAnalysisSelect,
  selectedAnalysis
}) => {
  const getStatusIcon = (status: AnalysisResult['status']) => {
    switch (status) {
      case 'pending':
        return '⏳'
      case 'processing':
        return '⚙️'
      case 'completed':
        return '✅'
      case 'error':
        return '❌'
      default:
        return '❓'
    }
  }

  const getStatusText = (status: AnalysisResult['status']) => {
    switch (status) {
      case 'pending':
        return 'Pending'
      case 'processing':
        return 'Processing'
      case 'completed':
        return 'Completed'
      case 'error':
        return 'Error'
      default:
        return 'Unknown'
    }
  }

  if (results.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4">Analysis Results</h2>
        <p className="text-gray-500 text-center py-8">
          No analyses yet. Upload a file to get started.
        </p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold mb-4">Analysis Results</h2>
      
      <div className="space-y-3">
        {results.map((result) => (
          <div
            key={result.id}
            className={`p-4 border rounded-lg cursor-pointer transition-colors ${
              selectedAnalysis === result.id
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
            onClick={() => onAnalysisSelect(result.id)}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <span className="text-xl">{getStatusIcon(result.status)}</span>
                <div>
                  <p className="font-medium text-gray-900">{result.filename}</p>
                  <p className="text-sm text-gray-500">
                    {new Date(result.uploadedAt).toLocaleString()}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <span
                  className={`px-2 py-1 text-xs rounded-full ${
                    result.status === 'completed'
                      ? 'bg-green-100 text-green-800'
                      : result.status === 'error'
                      ? 'bg-red-100 text-red-800'
                      : result.status === 'processing'
                      ? 'bg-yellow-100 text-yellow-800'
                      : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {getStatusText(result.status)}
                </span>
              </div>
            </div>
            {result.message && (
              <p className="mt-2 text-sm text-gray-600">{result.message}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export default AnalysisResults 