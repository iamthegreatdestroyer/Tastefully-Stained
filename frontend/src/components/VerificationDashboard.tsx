/**
 * Verification Dashboard Component
 * 
 * Displays watermark verification results and provenance information.
 * 
 * @copyright 2024-2026 Tastefully Stained
 */

import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, CheckCircle, XCircle, AlertTriangle, Shield, Link } from 'lucide-react';
import toast from 'react-hot-toast';
import { verifyWatermark } from '../services/api';

interface VerificationDashboardProps {
  onVerificationComplete: (result: object) => void;
}

interface VerificationResult {
  isValid: boolean;
  isAuthentic: boolean;
  confidence: number;
  c2paVerified: boolean;
  blockchainVerified: boolean;
  tamperingDetected: boolean;
  details: Record<string, unknown>;
}

/**
 * Verification dashboard component.
 * 
 * Provides file upload and displays comprehensive verification results.
 */
function VerificationDashboard({
  onVerificationComplete,
}: VerificationDashboardProps): JSX.Element {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isVerifying, setIsVerifying] = useState(false);
  const [result, setResult] = useState<VerificationResult | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setSelectedFile(acceptedFiles[0]);
      setResult(null);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpeg', '.jpg', '.png', '.webp', '.avif'] },
    maxFiles: 1,
  });

  const handleVerify = async (): Promise<void> => {
    if (!selectedFile) return;

    setIsVerifying(true);
    try {
      const verificationResult = await verifyWatermark(selectedFile);
      setResult(verificationResult);
      onVerificationComplete(verificationResult);
      toast.success('Verification complete');
    } catch (error) {
      toast.error('Verification failed');
      console.error(error);
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* File Upload */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
          isDragActive ? 'border-purple-400 bg-purple-500/10' : 'border-gray-500 hover:border-purple-400'
        }`}
      >
        <input {...getInputProps()} />
        {selectedFile ? (
          <div className="text-white">{selectedFile.name}</div>
        ) : (
          <>
            <Upload className="mx-auto text-gray-400 mb-4" size={48} />
            <p className="text-white">Drop an image to verify</p>
          </>
        )}
      </div>

      {/* Verify Button */}
      {selectedFile && !result && (
        <button
          onClick={handleVerify}
          disabled={isVerifying}
          className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 text-white py-4 rounded-lg font-semibold"
        >
          {isVerifying ? 'Verifying...' : 'Verify Content'}
        </button>
      )}

      {/* Results Display */}
      {result && (
        <div className="bg-white/10 backdrop-blur-lg rounded-xl p-6 space-y-6">
          {/* Overall Status */}
          <div className="text-center">
            {result.isValid ? (
              <div className="text-green-400">
                <CheckCircle className="mx-auto mb-2" size={48} />
                <h3 className="text-xl font-semibold">Verified</h3>
              </div>
            ) : result.tamperingDetected ? (
              <div className="text-red-400">
                <XCircle className="mx-auto mb-2" size={48} />
                <h3 className="text-xl font-semibold">Tampering Detected</h3>
              </div>
            ) : (
              <div className="text-yellow-400">
                <AlertTriangle className="mx-auto mb-2" size={48} />
                <h3 className="text-xl font-semibold">No Watermark Found</h3>
              </div>
            )}
          </div>

          {/* Confidence */}
          <div className="text-center">
            <div className="text-gray-300 mb-2">Confidence</div>
            <div className="text-3xl font-bold text-white">
              {(result.confidence * 100).toFixed(1)}%
            </div>
          </div>

          {/* Verification Details */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white/5 rounded-lg p-4 flex items-center gap-3">
              <Shield className={result.c2paVerified ? 'text-green-400' : 'text-gray-500'} />
              <div>
                <div className="text-white font-medium">C2PA</div>
                <div className="text-sm text-gray-400">
                  {result.c2paVerified ? 'Verified' : 'Not Found'}
                </div>
              </div>
            </div>
            <div className="bg-white/5 rounded-lg p-4 flex items-center gap-3">
              <Link className={result.blockchainVerified ? 'text-green-400' : 'text-gray-500'} />
              <div>
                <div className="text-white font-medium">Blockchain</div>
                <div className="text-sm text-gray-400">
                  {result.blockchainVerified ? 'Anchored' : 'Not Anchored'}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default VerificationDashboard;
