'use client'

import React, { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { motion } from 'framer-motion'
import { Upload, File, CheckCircle, AlertCircle, Loader } from 'lucide-react'
import toast from 'react-hot-toast'
import axios from 'axios'

interface FileUploadProps {
  onUploadComplete: (analysisId: string) => void
  onProgress: (progress: number) => void
}

interface UploadStatus {
  status: 'idle' | 'uploading' | 'processing' | 'completed' | 'error'
  progress: number
  message: string
  analysisId?: string
}

export default function FileUpload({ onUploadComplete, onProgress }: FileUploadProps) {
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>({
    status: 'idle',
    progress: 0,
    message: ''
  })

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    
    if (!file) return

    // Validate file type
    if (!file.name.toLowerCase().endsWith('.txt')) {
      toast.error('Por favor, selecione um arquivo .txt do 23andMe')
      return
    }

    // Validate file size (max 50MB)
    if (file.size > 50 * 1024 * 1024) {
      toast.error('Arquivo muito grande. Máximo 50MB permitido.')
      return
    }

    await uploadFile(file)
  }, [])

  const uploadFile = async (file: File) => {
    try {
      setUploadStatus({
        status: 'uploading',
        progress: 0,
        message: 'Iniciando upload...'
      })

      const formData = new FormData()
      formData.append('file', file)

      // Upload file
      const uploadResponse = await axios.post('/api/v1/genome-upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const progress = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 1))
          setUploadStatus(prev => ({
            ...prev,
            progress,
            message: `Uploading... ${progress}%`
          }))
          onProgress(progress)
        }
      })

      const { upload_id } = uploadResponse.data

      // Start processing
      setUploadStatus({
        status: 'processing',
        progress: 0,
        message: 'Processando arquivo...'
      })

      const processResponse = await axios.post(`/api/v1/genome-upload/${upload_id}/process`)
      const { analysis_id } = processResponse.data

      // Poll for completion
      await pollAnalysisStatus(analysis_id)

    } catch (error: any) {
      console.error('Upload error:', error)
      setUploadStatus({
        status: 'error',
        progress: 0,
        message: error.response?.data?.detail || 'Erro durante o upload'
      })
      toast.error('Erro durante o upload. Tente novamente.')
    }
  }

  const pollAnalysisStatus = async (analysisId: string) => {
    const maxAttempts = 120 // 10 minutes max
    let attempts = 0

    const poll = async () => {
      try {
        attempts++
        const response = await axios.get(`/api/v1/genome-upload/${analysisId}/status`)
        const { status, progress = 0, message = '' } = response.data

        setUploadStatus({
          status: 'processing',
          progress,
          message: message || `Analisando variantes... ${progress}%`
        })

        if (status === 'completed') {
          setUploadStatus({
            status: 'completed',
            progress: 100,
            message: 'Análise concluída!',
            analysisId
          })
          toast.success('Análise concluída com sucesso!')
          onUploadComplete(analysisId)
          return
        }

        if (status === 'error') {
          throw new Error(message || 'Erro durante o processamento')
        }

        if (attempts >= maxAttempts) {
          throw new Error('Timeout: Análise demorou mais que o esperado')
        }

        // Continue polling
        setTimeout(poll, 5000) // Poll every 5 seconds
      } catch (error: any) {
        setUploadStatus({
          status: 'error',
          progress: 0,
          message: error.message || 'Erro durante o processamento'
        })
        toast.error(error.message || 'Erro durante o processamento')
      }
    }

    poll()
  }

  const { getRootProps, getInputProps, isDragActive, isDragAccept, isDragReject } = useDropzone({
    onDrop,
    accept: {
      'text/plain': ['.txt']
    },
    maxFiles: 1,
    disabled: uploadStatus.status === 'uploading' || uploadStatus.status === 'processing'
  })

  const getDropzoneStyle = () => {
    if (isDragReject) return 'border-red-500 bg-red-50'
    if (isDragAccept) return 'border-green-500 bg-green-50'
    if (isDragActive) return 'border-primary-500 bg-primary-50'
    return 'border-gray-300'
  }

  const renderUploadContent = () => {
    if (uploadStatus.status === 'idle') {
      return (
        <>
          <div className="flex justify-center mb-6">
            <div className="p-6 bg-primary-100 rounded-full">
              <Upload className="w-12 h-12 text-primary-600" />
            </div>
          </div>
          
          <h3 className="text-2xl font-semibold text-gray-900 mb-4">
            Upload do arquivo 23andMe
          </h3>
          
          <p className="text-gray-600 mb-6 max-w-md mx-auto">
            Arraste e solte seu arquivo .txt do 23andMe aqui, ou clique para selecionar
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 items-center justify-center text-sm text-gray-500">
            <div className="flex items-center">
              <File className="w-4 h-4 mr-2" />
              Formato: .txt
            </div>
            <div className="flex items-center">
              <CheckCircle className="w-4 h-4 mr-2" />
              Máximo: 50MB
            </div>
          </div>
        </>
      )
    }

    if (uploadStatus.status === 'uploading' || uploadStatus.status === 'processing') {
      return (
        <>
          <div className="flex justify-center mb-6">
            <div className="p-6 bg-primary-100 rounded-full">
              <Loader className="w-12 h-12 text-primary-600 animate-spin" />
            </div>
          </div>
          
          <h3 className="text-2xl font-semibold text-gray-900 mb-4">
            {uploadStatus.status === 'uploading' ? 'Uploading...' : 'Processando...'}
          </h3>
          
          <p className="text-gray-600 mb-6">
            {uploadStatus.message}
          </p>
          
          <div className="w-full max-w-md mx-auto">
            <div className="progress-bar">
              <div 
                className="progress-fill"
                style={{ width: `${uploadStatus.progress}%` }}
              />
            </div>
            <p className="text-center text-sm text-gray-500 mt-2">
              {uploadStatus.progress}% concluído
            </p>
          </div>
        </>
      )
    }

    if (uploadStatus.status === 'error') {
      return (
        <>
          <div className="flex justify-center mb-6">
            <div className="p-6 bg-red-100 rounded-full">
              <AlertCircle className="w-12 h-12 text-red-600" />
            </div>
          </div>
          
          <h3 className="text-2xl font-semibold text-gray-900 mb-4">
            Erro no Upload
          </h3>
          
          <p className="text-red-600 mb-6">
            {uploadStatus.message}
          </p>
          
          <button
            onClick={() => setUploadStatus({ status: 'idle', progress: 0, message: '' })}
            className="btn-primary"
          >
            Tentar Novamente
          </button>
        </>
      )
    }

    return null
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="w-full"
    >
      <div className="card">
        <div
          {...getRootProps()}
          className={`
            card-body text-center cursor-pointer transition-all duration-300
            border-2 border-dashed rounded-lg p-12
            ${getDropzoneStyle()}
            ${uploadStatus.status === 'uploading' || uploadStatus.status === 'processing' 
              ? 'cursor-not-allowed opacity-50' 
              : 'hover:border-primary-400 hover:bg-primary-25'
            }
          `}
        >
          <input {...getInputProps()} />
          {renderUploadContent()}
        </div>
      </div>

      {/* Instructions */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.3 }}
        className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6"
      >
        <h4 className="font-semibold text-blue-900 mb-3">
          📋 Como obter seus dados do 23andMe:
        </h4>
        <ol className="list-decimal list-inside space-y-2 text-blue-800 text-sm">
          <li>Acesse sua conta no 23andMe</li>
          <li>Vá para "Browse Raw Data" ou "Dados Brutos"</li>
          <li>Clique em "Download" para baixar o arquivo .txt</li>
          <li>Use esse arquivo aqui para análise</li>
        </ol>
        
        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
          <p className="text-yellow-800 text-xs">
            ⚠️ <strong>Privacidade:</strong> Seus dados genéticos são processados localmente e não são compartilhados. 
            Este sistema é apenas para fins educacionais.
          </p>
        </div>
      </motion.div>
    </motion.div>
  )
} 