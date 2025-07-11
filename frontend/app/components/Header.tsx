'use client'

import { motion } from 'framer-motion'
import { FlaskConical, Github, Globe } from 'lucide-react'

export default function Header() {
  return (
    <motion.header
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-50"
    >
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-primary-600 rounded-lg">
              <FlaskConical className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Genomic-LLM</h1>
              <p className="text-xs text-gray-500">Análise Genômica com IA</p>
            </div>
          </div>

          {/* Navigation */}
          <nav className="hidden md:flex items-center space-x-6">
            <a
              href="#features"
              className="text-gray-600 hover:text-primary-600 transition-colors duration-200"
            >
              Recursos
            </a>
            <a
              href="#how-it-works"
              className="text-gray-600 hover:text-primary-600 transition-colors duration-200"
            >
              Como Funciona
            </a>
            <a
              href="#about"
              className="text-gray-600 hover:text-primary-600 transition-colors duration-200"
            >
              Sobre
            </a>
          </nav>

          {/* Actions */}
          <div className="flex items-center space-x-4">
            <a
              href="/docs"
              className="hidden sm:flex items-center space-x-2 text-gray-600 hover:text-primary-600 transition-colors duration-200"
            >
              <Globe className="w-4 h-4" />
              <span>Docs</span>
            </a>
            
            <a
              href="https://github.com/genomic-llm"
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 text-gray-600 hover:text-primary-600 transition-colors duration-200"
            >
              <Github className="w-5 h-5" />
            </a>
          </div>
        </div>
      </div>
    </motion.header>
  )
} 