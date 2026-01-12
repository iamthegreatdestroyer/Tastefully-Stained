/**
 * Verify Page Component
 * 
 * Watermark verification interface for content authenticity checking.
 * 
 * @copyright 2024-2026 Tastefully Stained
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import VerificationDashboard from '../components/VerificationDashboard';

/**
 * Verify page component.
 * 
 * Provides the interface for verifying watermarks and content provenance.
 */
function Verify(): JSX.Element {
  const [verificationResult, setVerificationResult] = useState<object | null>(null);

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
        <h1 className="text-4xl font-bold text-white mb-4">Verify Content</h1>
        <p className="text-gray-300 max-w-xl mx-auto">
          Upload an image to verify its watermark, check C2PA credentials,
          and validate blockchain anchoring.
        </p>
      </header>

      {/* Verification Dashboard */}
      <div className="max-w-4xl mx-auto">
        <VerificationDashboard
          onVerificationComplete={(result) => setVerificationResult(result)}
        />
      </div>
    </div>
  );
}

export default Verify;
