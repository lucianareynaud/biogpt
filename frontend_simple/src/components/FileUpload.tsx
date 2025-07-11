import React, { useState, useRef } from 'react'
import axios from 'axios'
import { AnalysisResult } from '../App'

interface FileUploadProps {
  onUploadSuccess: (result: AnalysisResult) => void
}

const FileUpload: React.FC<FileUploadProps> = ({ onUploadSuccess }) => {
  const [uploading, setUploading] = useState(false)
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0])
    }
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0])
    }
  }

  const handleFile = async (file: File) => {
    setUploading(true)
    
    try {
      const formData = new FormData()
      formData.append('file', file)
      
      const response = await axios.post('/api/upload-genome', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
      
      const result: AnalysisResult = {
        id: response.data.analysis_id,
        status: 'processing',
        filename: file.name,
        uploadedAt: new Date().toISOString(),
      }
      
      onUploadSuccess(result)
    } catch (error) {
      console.error('Upload failed:', error)
      const result: AnalysisResult = {
        id: Date.now().toString(),
        status: 'error',
        filename: file.name,
        uploadedAt: new Date().toISOString(),
        message: 'Upload failed'
      }
      onUploadSuccess(result)
    } finally {
      setUploading(false)
    }
  }

  const openFileSelector = () => {
    fileInputRef.current?.click()
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold mb-4">Upload Genetic Data</h2>
      
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          dragActive
            ? 'border-blue-400 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400'
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <div className="space-y-4">
          <div className="text-4xl">📁</div>
          {uploading ? (
            <div>
              <div className="animate-spin text-2xl">⟳</div>
              <p className="text-gray-600">Uploading and processing...</p>
            </div>
          ) : (
            <div>
              <p className="text-lg text-gray-700">
                Drag and drop your genetic data file here
              </p>
              <p className="text-sm text-gray-500">
                Supports 23andMe, AncestryDNA, MyHeritage, and VCF formats
              </p>
              <button
                onClick={openFileSelector}
                className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                Choose File
              </button>
            </div>
          )}
        </div>
      </div>
      
      <input
        ref={fileInputRef}
        type="file"
        accept=".txt,.csv,.vcf,.tsv"
        onChange={handleFileInput}
        className="hidden"
      />
    </div>
  )
}

export default FileUpload 