import React, { useState } from 'react'
import Header from './components/Header'
import FileUpload from './components/FileUpload'
import AnalysisResults from './components/AnalysisResults'
import Chat from './components/Chat'
import Footer from './components/Footer'

export interface AnalysisResult {
  id: string
  status: 'pending' | 'processing' | 'completed' | 'error'
  filename: string
  uploadedAt: string
  message?: string
}

const App: React.FC = () => {
  const [analysisResults, setAnalysisResults] = useState<AnalysisResult[]>([])
  const [selectedAnalysis, setSelectedAnalysis] = useState<string | null>(null)

  const handleUploadSuccess = (result: AnalysisResult) => {
    setAnalysisResults(prev => [...prev, result])
  }

  const handleAnalysisSelect = (analysisId: string) => {
    setSelectedAnalysis(analysisId)
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header />
      
      <main className="flex-1 container mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Left Column */}
          <div className="space-y-6">
            <FileUpload onUploadSuccess={handleUploadSuccess} />
            <AnalysisResults 
              results={analysisResults}
              onAnalysisSelect={handleAnalysisSelect}
              selectedAnalysis={selectedAnalysis}
            />
          </div>
          
          {/* Right Column */}
          <div>
            <Chat analysisId={selectedAnalysis} />
          </div>
        </div>
      </main>

      <Footer />
    </div>
  )
}

export default App 