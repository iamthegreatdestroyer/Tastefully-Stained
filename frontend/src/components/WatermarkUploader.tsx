/**
 * Watermark Uploader Component
 * 
 * Drag-and-drop file uploader for watermark embedding.
 * 
 * @copyright 2024-2026 Tastefully Stained
 */

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, X, CheckCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import { embedWatermark } from '../services/api';

interface WatermarkUploaderProps {
  onProcessingStart: () => void;
  onProcessingEnd: () => void;
}

/**
 * Watermark uploader component with drag-and-drop support.
 * 
 * @param onProcessingStart - Callback when processing starts
 * @param onProcessingEnd - Callback when processing ends
 */
function WatermarkUploader({
  onProcessingStart,
  onProcessingEnd,
}: WatermarkUploaderProps): JSX.Element {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [watermarkData, setWatermarkData] = useState('');
  const [strategy, setStrategy] = useState<'auto' | 'dct' | 'dwt' | 'hybrid'>('auto');
  const [includeC2PA, setIncludeC2PA] = useState(true);
  const [anchorBlockchain, setAnchorBlockchain] = useState(false);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setSelectedFile(acceptedFiles[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png', '.webp', '.avif'],
    },
    maxFiles: 1,
    maxSize: 50 * 1024 * 1024, // 50MB
  });

  const handleSubmit = async (): Promise<void> => {
    if (!selectedFile) {
      toast.error('Please select an image');
      return;
    }

    if (!watermarkData.trim()) {
      toast.error('Please enter watermark data');
      return;
    }

    onProcessingStart();

    try {
      const result = await embedWatermark({
        file: selectedFile,
        watermarkData,
        strategy,
        includeC2PA,
        anchorBlockchain,
      });

      toast.success('Watermark embedded successfully!');
      console.log('Result:', result);
    } catch (error) {
      toast.error('Failed to embed watermark');
      console.error(error);
    } finally {
      onProcessingEnd();
    }
  };

  return (
    <div className="space-y-6">
      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
          isDragActive
            ? 'border-purple-400 bg-purple-500/10'
            : 'border-gray-500 hover:border-purple-400'
        }`}
      >
        <input {...getInputProps()} />
        {selectedFile ? (
          <div className="flex items-center justify-center gap-4">
            <CheckCircle className="text-green-400" size={24} />
            <span className="text-white">{selectedFile.name}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setSelectedFile(null);
              }}
              className="text-gray-400 hover:text-red-400"
            >
              <X size={20} />
            </button>
          </div>
        ) : (
          <>
            <Upload className="mx-auto text-gray-400 mb-4" size={48} />
            <p className="text-white mb-2">
              {isDragActive
                ? 'Drop the image here...'
                : 'Drag & drop an image, or click to select'}
            </p>
            <p className="text-gray-400 text-sm">
              Supports JPEG, PNG, WebP, AVIF (max 50MB)
            </p>
          </>
        )}
      </div>

      {/* Watermark Data Input */}
      <div>
        <label className="block text-white mb-2">Watermark Data</label>
        <textarea
          value={watermarkData}
          onChange={(e) => setWatermarkData(e.target.value)}
          placeholder="Enter data to embed as watermark..."
          className="w-full bg-white/10 text-white rounded-lg px-4 py-3 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
          rows={3}
        />
      </div>

      {/* Strategy Selection */}
      <div>
        <label className="block text-white mb-2">Algorithm Strategy</label>
        <select
          value={strategy}
          onChange={(e) => setStrategy(e.target.value as any)}
          className="w-full bg-white/10 text-white rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-purple-500"
        >
          <option value="auto">Auto (Recommended)</option>
          <option value="dct">DCT (JPEG Optimized)</option>
          <option value="dwt">DWT (Geometric Resistant)</option>
          <option value="hybrid">Hybrid (Maximum Robustness)</option>
        </select>
      </div>

      {/* Options */}
      <div className="flex gap-6">
        <label className="flex items-center gap-2 text-white cursor-pointer">
          <input
            type="checkbox"
            checked={includeC2PA}
            onChange={(e) => setIncludeC2PA(e.target.checked)}
            className="rounded"
          />
          Include C2PA Manifest
        </label>
        <label className="flex items-center gap-2 text-white cursor-pointer">
          <input
            type="checkbox"
            checked={anchorBlockchain}
            onChange={(e) => setAnchorBlockchain(e.target.checked)}
            className="rounded"
          />
          Anchor to Blockchain
        </label>
      </div>

      {/* Submit Button */}
      <button
        onClick={handleSubmit}
        disabled={!selectedFile || !watermarkData.trim()}
        className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white py-4 rounded-lg font-semibold transition-colors"
      >
        Embed Watermark
      </button>
    </div>
  );
}

export default WatermarkUploader;
