'use client'

import { motion } from 'framer-motion'
import { FlaskConical, Heart, Shield, Book } from 'lucide-react'

export default function Footer() {
  return (
    <motion.footer
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.6, delay: 1 }}
      className="bg-gray-900 text-white"
    >
      <div className="container mx-auto px-4 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="space-y-4">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-primary-600 rounded-lg">
                <DNA className="w-6 h-6 text-white" />
              </div>
              <div>
                <h2 className="text-lg font-bold">Genomic-LLM</h2>
                <p className="text-sm text-gray-400">v1.0.0</p>
              </div>
            </div>
            
            <p className="text-gray-400 text-sm">
              Plataforma avançada para análise genômica com inteligência artificial,
              oferecendo interpretações precisas e relatórios profissionais.
            </p>
          </div>

          {/* Resources */}
          <div>
            <h3 className="text-lg font-semibold mb-4">Recursos</h3>
            <ul className="space-y-2 text-gray-400">
              <li>
                <a href="/docs" className="hover:text-white transition-colors duration-200">
                  Documentação
                </a>
              </li>
              <li>
                <a href="/api-docs" className="hover:text-white transition-colors duration-200">
                  API Reference
                </a>
              </li>
              <li>
                <a href="/examples" className="hover:text-white transition-colors duration-200">
                  Exemplos
                </a>
              </li>
              <li>
                <a href="/support" className="hover:text-white transition-colors duration-200">
                  Suporte
                </a>
              </li>
            </ul>
          </div>

          {/* Company */}
          <div>
            <h3 className="text-lg font-semibold mb-4">Empresa</h3>
            <ul className="space-y-2 text-gray-400">
              <li>
                <a href="/about" className="hover:text-white transition-colors duration-200">
                  Sobre Nós
                </a>
              </li>
              <li>
                <a href="/privacy" className="hover:text-white transition-colors duration-200">
                  Privacidade
                </a>
              </li>
              <li>
                <a href="/terms" className="hover:text-white transition-colors duration-200">
                  Termos de Uso
                </a>
              </li>
              <li>
                <a href="/contact" className="hover:text-white transition-colors duration-200">
                  Contato
                </a>
              </li>
            </ul>
          </div>

          {/* Legal & Security */}
          <div>
            <h3 className="text-lg font-semibold mb-4">Segurança & Conformidade</h3>
            <div className="space-y-4">
              <div className="flex items-center space-x-2 text-gray-400">
                <Shield className="w-4 h-4" />
                <span className="text-sm">Dados Criptografados</span>
              </div>
              
              <div className="flex items-center space-x-2 text-gray-400">
                <Book className="w-4 h-4" />
                <span className="text-sm">Diretrizes ACMG</span>
              </div>
              
              <div className="flex items-center space-x-2 text-gray-400">
                <Heart className="w-4 h-4" />
                <span className="text-sm">Uso Educacional</span>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="border-t border-gray-800 mt-8 pt-8">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <p className="text-gray-400 text-sm">
              © 2024 Genomic-LLM. Todos os direitos reservados.
            </p>
            
            <div className="flex items-center space-x-4 mt-4 md:mt-0">
              <span className="text-gray-400 text-sm">
                Feito com
              </span>
              <Heart className="w-4 h-4 text-red-500" />
              <span className="text-gray-400 text-sm">
                para a ciência
              </span>
            </div>
          </div>
          
          <div className="mt-4 text-center">
            <p className="text-xs text-gray-500">
              ⚠️ Este sistema é destinado apenas para fins educacionais e informativos. 
              Não substitui avaliação médica profissional. Consulte sempre um médico geneticista 
              para interpretação clínica de resultados genéticos.
            </p>
          </div>
        </div>
      </div>
    </motion.footer>
  )
} 