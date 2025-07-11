import React from 'react'

const Footer: React.FC = () => {
  return (
    <footer className="bg-gray-800 text-white py-8">
      <div className="container mx-auto px-4 text-center">
        <p className="text-sm">
          © 2024 Genomic Analysis LLM. Built with advanced AI for personalized genomic insights.
        </p>
        <p className="text-xs text-gray-400 mt-2">
          Please consult with healthcare professionals for medical decisions.
        </p>
      </div>
    </footer>
  )
}

export default Footer 