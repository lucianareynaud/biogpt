'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import FileUpload from './components/FileUpload'
import AnalysisResults from './components/AnalysisResults'
import Header from './components/Header'
import Footer from './components/Footer'
import { FlaskConical, TrendingUp, FileText, MessageCircle } from 'lucide-react'

export default function Home() {
  const [analysisId, setAnalysisId] = useState<string | null>(null)
  const [uploadProgress, setUploadProgress] = useState<number>(0)

  const features = [
    {
      icon: FlaskConical,
      title: 'Análise ACMG',
      description: 'Classificação de variantes seguindo diretrizes ACMG-AMP 2015',
      color: 'text-primary-600'
    },
    {
      icon: TrendingUp,
      title: 'Dados Populacionais',
      description: 'Integração com bases ClinVar e gnomAD para contexto clínico',
      color: 'text-success-600'
    },
    {
      icon: FileText,
      title: 'Relatórios Detalhados',
      description: 'Laudos profissionais em PDF nos idiomas PT-BR e EN',
      color: 'text-warning-600'
    },
    {
      icon: MessageCircle,
      title: 'Chat com IA',
      description: 'Interpretação inteligente usando PubMedBERT',
      color: 'text-purple-600'
    }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      <Header />
      
      <main className="container mx-auto px-4 py-8">
        {!analysisId ? (
          <>
            {/* Hero Section */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="text-center mb-12"
            >
              <div className="flex justify-center mb-6">
                <div className="p-4 bg-primary-100 rounded-full">
                  <FlaskConical className="w-12 h-12 text-primary-600" />
                </div>
              </div>
              
              <h1 className="text-4xl md:text-6xl font-bold text-gray-900 mb-6 text-balance">
                Análise Genômica
                <span className="text-primary-600 block">com Inteligência Artificial</span>
              </h1>
              
              <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto text-balance">
                Carregue seus dados do 23andMe e obtenha uma análise detalhada de variantes genéticas 
                com classificação ACMG e interpretação por IA especializada em biomedicina.
              </p>
              
              <div className="flex flex-wrap justify-center gap-4 mb-12">
                <div className="badge badge-info">
                  <FlaskConical className="w-4 h-4 mr-1" />
                  ACMG-2015
                </div>
                <div className="badge badge-success">
                  <TrendingUp className="w-4 h-4 mr-1" />
                  ClinVar + gnomAD
                </div>
                <div className="badge badge-warning">
                  <MessageCircle className="w-4 h-4 mr-1" />
                  PubMedBERT
                </div>
              </div>
            </motion.div>

            {/* Upload Section */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="max-w-4xl mx-auto mb-16"
            >
              <FileUpload
                onUploadComplete={setAnalysisId}
                onProgress={setUploadProgress}
              />
            </motion.div>

            {/* Features Section */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.4 }}
              className="mb-16"
            >
              <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
                Tecnologia de Ponta para Análise Genômica
              </h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
                {features.map((feature, index) => {
                  const Icon = feature.icon
                  return (
                    <motion.div
                      key={feature.title}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.6, delay: 0.6 + (index * 0.1) }}
                      className="card hover:shadow-lg transition-shadow duration-300"
                    >
                      <div className="card-body text-center">
                        <div className="flex justify-center mb-4">
                          <div className="p-3 bg-gray-100 rounded-full">
                            <Icon className={`w-8 h-8 ${feature.color}`} />
                          </div>
                        </div>
                        
                        <h3 className="text-lg font-semibold text-gray-900 mb-2">
                          {feature.title}
                        </h3>
                        
                        <p className="text-gray-600 text-sm">
                          {feature.description}
                        </p>
                      </div>
                    </motion.div>
                  )
                })}
              </div>
            </motion.div>

            {/* How it works */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.8 }}
              className="bg-white rounded-2xl shadow-lg p-8 mb-16"
            >
              <h2 className="text-3xl font-bold text-center text-gray-900 mb-8">
                Como Funciona
              </h2>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                <div className="text-center">
                  <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <span className="text-2xl font-bold text-primary-600">1</span>
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">Upload do Arquivo</h3>
                  <p className="text-gray-600">
                    Carregue seu arquivo .txt do 23andMe de forma segura
                  </p>
                </div>
                
                <div className="text-center">
                  <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <span className="text-2xl font-bold text-primary-600">2</span>
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">Análise com IA</h3>
                  <p className="text-gray-600">
                    Processamento automático com classificação ACMG e consulta às bases de dados
                  </p>
                </div>
                
                <div className="text-center">
                  <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <span className="text-2xl font-bold text-primary-600">3</span>
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">Relatório & Chat</h3>
                  <p className="text-gray-600">
                    Receba relatório detalhado e converse com IA sobre os resultados
                  </p>
                </div>
              </div>
            </motion.div>
          </>
        ) : (
          <AnalysisResults analysisId={analysisId} onBack={() => setAnalysisId(null)} />
        )}
      </main>
      
      <Footer />
    </div>
  )
} 