'use client'

import React, { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { Send, MessageCircle, Bot, User, Loader } from 'lucide-react'
import toast from 'react-hot-toast'
import axios from 'axios'

interface ChatProps {
  analysisId: string
}

interface Message {
  id: string
  content: string
  isUser: boolean
  timestamp: Date
}

export default function Chat({ analysisId }: ChatProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    initializeChat()
  }, [analysisId])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const initializeChat = async () => {
    try {
      const response = await axios.post('/api/v1/chat/session', {
        analysis_id: analysisId
      })
      setSessionId(response.data.session_id)
      
      // Add welcome message
      setMessages([{
        id: '1',
        content: 'Olá! Sou uma IA especializada em genômica. Posso ajudar a interpretar os resultados da sua análise genética. O que gostaria de saber?',
        isUser: false,
        timestamp: new Date()
      }])
    } catch (error) {
      console.error('Error initializing chat:', error)
      toast.error('Erro ao inicializar chat')
    }
  }

  const sendMessage = async () => {
    if (!input.trim() || !sessionId || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: input.trim(),
      isUser: true,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const response = await axios.post('/api/v1/chat/message', {
        session_id: sessionId,
        message: userMessage.content
      })

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: response.data.response,
        isUser: false,
        timestamp: new Date()
      }

      setMessages(prev => [...prev, aiMessage])
    } catch (error) {
      console.error('Error sending message:', error)
      toast.error('Erro ao enviar mensagem')
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: 'Desculpe, ocorreu um erro. Tente novamente.',
        isUser: false,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="card">
        <div className="card-header">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-primary-100 rounded-full">
              <MessageCircle className="w-5 h-5 text-primary-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold">Chat com IA Especializada</h3>
              <p className="text-sm text-gray-500">
                Converse sobre seus resultados genéticos com nossa IA treinada em literatura biomédica
              </p>
            </div>
          </div>
        </div>
        
        <div className="h-96 overflow-y-auto p-6 space-y-4">
          {messages.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className={`flex ${message.isUser ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`flex items-start space-x-3 max-w-xs lg:max-w-md ${
                message.isUser ? 'flex-row-reverse space-x-reverse' : ''
              }`}>
                <div className={`p-2 rounded-full ${
                  message.isUser ? 'bg-primary-100' : 'bg-gray-100'
                }`}>
                  {message.isUser ? (
                    <User className="w-4 h-4 text-primary-600" />
                  ) : (
                    <Bot className="w-4 h-4 text-gray-600" />
                  )}
                </div>
                
                <div className={`rounded-lg px-4 py-2 ${
                  message.isUser
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}>
                  <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  <p className={`text-xs mt-1 ${
                    message.isUser ? 'text-primary-200' : 'text-gray-500'
                  }`}>
                    {message.timestamp.toLocaleTimeString('pt-BR', { 
                      hour: '2-digit', 
                      minute: '2-digit' 
                    })}
                  </p>
                </div>
              </div>
            </motion.div>
          ))}
          
          {isLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-start"
            >
              <div className="flex items-start space-x-3">
                <div className="p-2 bg-gray-100 rounded-full">
                  <Bot className="w-4 h-4 text-gray-600" />
                </div>
                <div className="bg-gray-100 rounded-lg px-4 py-2">
                  <div className="flex items-center space-x-2">
                    <Loader className="w-4 h-4 animate-spin" />
                    <span className="text-sm text-gray-600">Analisando...</span>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
        
        <div className="border-t border-gray-200 p-4">
          <div className="flex space-x-3">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Digite sua pergunta sobre os resultados genéticos..."
              className="flex-1 resize-none border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              rows={2}
              disabled={isLoading}
            />
            <button
              onClick={sendMessage}
              disabled={!input.trim() || isLoading}
              className="btn-primary p-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
          
          <div className="mt-3 text-xs text-gray-500">
            💡 Sugestões: Pergunte sobre variantes específicas, riscos genéticos, ou como interpretar os resultados
          </div>
        </div>
      </div>
    </div>
  )
} 