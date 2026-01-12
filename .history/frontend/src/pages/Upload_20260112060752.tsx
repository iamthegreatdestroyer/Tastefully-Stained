/**
 * Upload Page Component
 * 
 * Watermark embedding interface for content creators.
 * 
 * @copyright 2024-2026 Tastefully Stained
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import WatermarkUploader from '../components/WatermarkUploader';

/**
 * Upload page component.
 * 
 * Provides the interface for uploading images and embedding watermarks.
 */
function Upload(): JSX.Element {
  const [isProcessing, setIsProcessing] = useState(false);

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Navigation */}
      <Link
        to="/"
        className="inline-flex items-center gap-2 text-gray-300 hover:text-white mb-8"
      >
        <ArrowLeft size={20} />
        Back to Home
      </Link>

      {/* Header */}
      <header className="text-center mb-12">
        <h1 className="text-4xl font-bold text-white mb-4">Watermark Your Content</h1>
        <p className="text-gray-300 max-w-xl mx-auto">
          Upload your image to embed an invisible watermark with C2PA credentials
          and optional blockchain anchoring.
        </p>
      </header>

      {/* Uploader Component */}
      <div className="max-w-2xl mx-auto">
        <WatermarkUploader
          onProcessingStart={() => setIsProcessing(true)}
          onProcessingEnd={() => setIsProcessing(false)}
        />
      </div>

      {/* Processing Indicator */}
      {isProcessing && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center">
          <div className="bg-white/10 backdrop-blur-lg rounded-xl p-8 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-purple-500 border-t-transparent mx-auto mb-4" />
            <p className="text-white">Processing your content...</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default Upload;
