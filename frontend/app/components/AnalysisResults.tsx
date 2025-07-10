'use client'

import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  ArrowLeft, Download, MessageCircle, FileText, 
  DNA, TrendingUp, AlertTriangle, CheckCircle,
  BarChart3, PieChart, Globe
} from 'lucide-react'
import toast from 'react-hot-toast'
import axios from 'axios'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import Chat from './Chat'

interface AnalysisResultsProps {
  analysisId: string
  onBack: () => void
}

interface Analysis {
  id: string
  status: string
  created_at: string
  completed_at: string
  total_variants: number
  pathogenic_variants: number
  likely_pathogenic_variants: number
  uncertain_variants: number
  likely_benign_variants: number
  benign_variants: number
  filename: string
}

interface Variant {
  id: string
  rsid: string
  chromosome: string
  position: number
  genotype: string
  acmg_classification: string
  gene_symbol: string
  clinical_significance: string
  gnomad_frequency: number
  interpretation: string
}

export default function AnalysisResults({ analysisId, onBack }: AnalysisResultsProps) {
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [variants, setVariants] = useState<Variant[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'overview' | 'variants' | 'chat' | 'reports'>('overview')

  useEffect(() => {
    fetchAnalysisData()
  }, [analysisId])

  const fetchAnalysisData = async () => {
    try {
      setLoading(true)
      
      // Fetch analysis details
      const analysisResponse = await axios.get(`/api/v1/genome-upload/${analysisId}`)
      setAnalysis(analysisResponse.data)

      // Fetch significant variants
      const variantsResponse = await axios.get(`/api/v1/genome-upload/${analysisId}/variants?significant_only=true`)
      setVariants(variantsResponse.data)

    } catch (error) {
      console.error('Error fetching analysis data:', error)
      toast.error('Erro ao carregar dados da análise')
    } finally {
      setLoading(false)
    }
  }

  const downloadReport = async (language: 'pt-BR' | 'en') => {
    try {
      const response = await axios.post(`/api/v1/reports/generate`, {
        analysis_id: analysisId,
        language,
        report_type: 'detailed'
      })

      const { report_id } = response.data
      
      // Download the PDF
      const downloadResponse = await axios.get(`/api/v1/reports/${report_id}/download`, {
        responseType: 'blob'
      })

      // Create download link
      const url = window.URL.createObjectURL(new Blob([downloadResponse.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `genomic_report_${analysisId}_${language}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)

      toast.success('Relatório baixado com sucesso!')
    } catch (error) {
      console.error('Error downloading report:', error)
      toast.error('Erro ao baixar relatório')
    }
  }

  const getClassificationColor = (classification: string) => {
    switch (classification.toLowerCase()) {
      case 'pathogenic':
        return 'text-red-600 bg-red-100'
      case 'likely pathogenic':
        return 'text-orange-600 bg-orange-100'
      case 'uncertain significance':
      case 'vus':
        return 'text-yellow-600 bg-yellow-100'
      case 'likely benign':
        return 'text-green-600 bg-green-100'
      case 'benign':
        return 'text-green-700 bg-green-100'
      default:
        return 'text-gray-600 bg-gray-100'
    }
  }

  const renderOverview = () => {
    if (!analysis) return null

    const clinicallySignificant = (analysis.pathogenic_variants || 0) + (analysis.likely_pathogenic_variants || 0)
    const totalProcessed = analysis.total_variants || 0

    return (
      <div className="space-y-8">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="card">
            <div className="card-body text-center">
              <div className="flex justify-center mb-4">
                <DNA className="w-8 h-8 text-primary-600" />
              </div>
              <div className="text-3xl font-bold text-primary-600 mb-2">
                {totalProcessed.toLocaleString()}
              </div>
              <div className="text-sm text-gray-600">
                Variantes Analisadas
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-body text-center">
              <div className="flex justify-center mb-4">
                <AlertTriangle className="w-8 h-8 text-red-600" />
              </div>
              <div className="text-3xl font-bold text-red-600 mb-2">
                {clinicallySignificant}
              </div>
              <div className="text-sm text-gray-600">
                Clinicamente Relevantes
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-body text-center">
              <div className="flex justify-center mb-4">
                <TrendingUp className="w-8 h-8 text-yellow-600" />
              </div>
              <div className="text-3xl font-bold text-yellow-600 mb-2">
                {analysis.uncertain_variants || 0}
              </div>
              <div className="text-sm text-gray-600">
                Significado Incerto
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-body text-center">
              <div className="flex justify-center mb-4">
                <CheckCircle className="w-8 h-8 text-green-600" />
              </div>
              <div className="text-3xl font-bold text-green-600 mb-2">
                {((analysis.benign_variants || 0) + (analysis.likely_benign_variants || 0))}
              </div>
              <div className="text-sm text-gray-600">
                Benignas
              </div>
            </div>
          </div>
        </div>

        {/* Analysis Info */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-semibold">Informações da Análise</h3>
          </div>
          <div className="card-body">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <div className="space-y-3">
                  <div>
                    <span className="text-sm font-medium text-gray-500">ID da Análise:</span>
                    <p className="text-gray-900 font-mono">{analysis.id}</p>
                  </div>
                  <div>
                    <span className="text-sm font-medium text-gray-500">Arquivo Original:</span>
                    <p className="text-gray-900">{analysis.filename}</p>
                  </div>
                  <div>
                    <span className="text-sm font-medium text-gray-500">Status:</span>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      analysis.status === 'completed' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {analysis.status === 'completed' ? 'Concluída' : 'Processando'}
                    </span>
                  </div>
                </div>
              </div>
              <div>
                <div className="space-y-3">
                  <div>
                    <span className="text-sm font-medium text-gray-500">Data de Criação:</span>
                    <p className="text-gray-900">
                      {format(new Date(analysis.created_at), 'dd/MM/yyyy HH:mm', { locale: ptBR })}
                    </p>
                  </div>
                  <div>
                    <span className="text-sm font-medium text-gray-500">Data de Conclusão:</span>
                    <p className="text-gray-900">
                      {analysis.completed_at 
                        ? format(new Date(analysis.completed_at), 'dd/MM/yyyy HH:mm', { locale: ptBR })
                        : 'Em processamento...'
                      }
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Classification Distribution */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-semibold">Distribuição por Classificação ACMG</h3>
          </div>
          <div className="card-body">
            <div className="space-y-4">
              {[
                { label: 'Patogênica', count: analysis.pathogenic_variants || 0, color: 'bg-red-500' },
                { label: 'Provavelmente Patogênica', count: analysis.likely_pathogenic_variants || 0, color: 'bg-orange-500' },
                { label: 'Significado Incerto (VUS)', count: analysis.uncertain_variants || 0, color: 'bg-yellow-500' },
                { label: 'Provavelmente Benigna', count: analysis.likely_benign_variants || 0, color: 'bg-green-400' },
                { label: 'Benigna', count: analysis.benign_variants || 0, color: 'bg-green-600' }
              ].map((item) => {
                const percentage = totalProcessed > 0 ? (item.count / totalProcessed * 100) : 0
                return (
                  <div key={item.label} className="flex items-center space-x-4">
                    <div className="w-32 text-sm text-gray-600">{item.label}</div>
                    <div className="flex-1 bg-gray-200 rounded-full h-4 relative">
                      <div 
                        className={`${item.color} h-4 rounded-full transition-all duration-500`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                    <div className="w-20 text-sm text-gray-900 text-right">
                      {item.count} ({percentage.toFixed(1)}%)
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        {/* Clinical Alert */}
        {clinicallySignificant > 0 && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-red-50 border border-red-200 rounded-lg p-6"
          >
            <div className="flex items-start space-x-3">
              <AlertTriangle className="w-6 h-6 text-red-600 mt-1" />
              <div>
                <h4 className="font-semibold text-red-900 mb-2">
                  Variantes Clinicamente Significativas Identificadas
                </h4>
                <p className="text-red-800 text-sm mb-4">
                  Esta análise identificou {clinicallySignificant} variante(s) com possível significado clínico. 
                  É recomendado consultar um médico geneticista ou conselheiro genético para interpretação adequada destes resultados.
                </p>
                <div className="flex space-x-3">
                  <button
                    onClick={() => setActiveTab('variants')}
                    className="btn-primary text-sm"
                  >
                    Ver Variantes
                  </button>
                  <button
                    onClick={() => setActiveTab('chat')}
                    className="btn-secondary text-sm"
                  >
                    Conversar com IA
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    )
  }

  const renderVariants = () => {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-semibold">
            Variantes Clinicamente Significativas ({variants.length})
          </h3>
        </div>

        {variants.length === 0 ? (
          <div className="card">
            <div className="card-body text-center py-12">
              <CheckCircle className="w-16 h-16 text-green-600 mx-auto mb-4" />
              <h4 className="text-xl font-semibold text-gray-900 mb-2">
                Nenhuma Variante Significativa
              </h4>
              <p className="text-gray-600">
                Não foram identificadas variantes classificadas como patogênicas ou provavelmente patogênicas.
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {variants.map((variant) => (
              <motion.div
                key={variant.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="card"
              >
                <div className="card-body">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h4 className="text-lg font-semibold text-gray-900">
                        {variant.gene_symbol || variant.rsid}
                      </h4>
                      <p className="text-sm text-gray-500">
                        {variant.chromosome}:{variant.position} • {variant.genotype}
                      </p>
                    </div>
                    <span className={`badge ${getClassificationColor(variant.acmg_classification)}`}>
                      {variant.acmg_classification}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    <div>
                      <span className="text-sm font-medium text-gray-500">rsID:</span>
                      <p className="text-gray-900 font-mono">{variant.rsid}</p>
                    </div>
                    <div>
                      <span className="text-sm font-medium text-gray-500">Frequência Populacional:</span>
                      <p className="text-gray-900">
                        {variant.gnomad_frequency ? (variant.gnomad_frequency * 100).toFixed(4) + '%' : 'Não disponível'}
                      </p>
                    </div>
                    <div className="md:col-span-2">
                      <span className="text-sm font-medium text-gray-500">Significado Clínico:</span>
                      <p className="text-gray-900">{variant.clinical_significance || 'Não disponível'}</p>
                    </div>
                  </div>

                  {variant.interpretation && (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                      <span className="text-sm font-medium text-blue-900">Interpretação da IA:</span>
                      <p className="text-blue-800 text-sm mt-1">{variant.interpretation}</p>
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Carregando resultados da análise...</p>
        </div>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="max-w-6xl mx-auto"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center space-x-4">
          <button
            onClick={onBack}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors duration-200"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Resultados da Análise</h1>
            <p className="text-gray-600">
              {analysis && format(new Date(analysis.created_at), 'dd/MM/yyyy HH:mm', { locale: ptBR })}
            </p>
          </div>
        </div>

        <div className="flex space-x-3">
          <button
            onClick={() => downloadReport('pt-BR')}
            className="btn-secondary flex items-center space-x-2"
          >
            <Download className="w-4 h-4" />
            <span>PDF (PT-BR)</span>
          </button>
          <button
            onClick={() => downloadReport('en')}
            className="btn-secondary flex items-center space-x-2"
          >
            <Download className="w-4 h-4" />
            <span>PDF (EN)</span>
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-8">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'overview', label: 'Visão Geral', icon: BarChart3 },
            { id: 'variants', label: 'Variantes', icon: DNA },
            { id: 'chat', label: 'Chat com IA', icon: MessageCircle },
            { id: 'reports', label: 'Relatórios', icon: FileText }
          ].map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors duration-200 ${
                  activeTab === tab.id
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            )
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="mb-8">
        {activeTab === 'overview' && renderOverview()}
        {activeTab === 'variants' && renderVariants()}
        {activeTab === 'chat' && analysis && <Chat analysisId={analysis.id} />}
        {activeTab === 'reports' && (
          <div className="space-y-6">
            <h3 className="text-lg font-semibold">Relatórios Disponíveis</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="card">
                <div className="card-body">
                  <h4 className="font-semibold mb-2">Relatório em Português</h4>
                  <p className="text-gray-600 text-sm mb-4">
                    Relatório detalhado com interpretações em português brasileiro
                  </p>
                  <button
                    onClick={() => downloadReport('pt-BR')}
                    className="btn-primary w-full"
                  >
                    Download PDF (PT-BR)
                  </button>
                </div>
              </div>
              <div className="card">
                <div className="card-body">
                  <h4 className="font-semibold mb-2">English Report</h4>
                  <p className="text-gray-600 text-sm mb-4">
                    Detailed report with interpretations in English
                  </p>
                  <button
                    onClick={() => downloadReport('en')}
                    className="btn-primary w-full"
                  >
                    Download PDF (EN)
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  )
} 