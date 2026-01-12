/**
 * Home Page Component
 * 
 * Landing page for Tastefully Stained service.
 * 
 * @copyright 2024-2026 Tastefully Stained
 */

import { Link } from 'react-router-dom';
import { Shield, Upload, Search, Lock } from 'lucide-react';

/**
 * Feature card component for the home page.
 */
interface FeatureCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
}

function FeatureCard({ icon, title, description }: FeatureCardProps): JSX.Element {
  return (
    <div className="bg-white/10 backdrop-blur-lg rounded-xl p-6 hover:bg-white/20 transition-colors">
      <div className="text-purple-400 mb-4">{icon}</div>
      <h3 className="text-xl font-semibold text-white mb-2">{title}</h3>
      <p className="text-gray-300">{description}</p>
    </div>
  );
}

/**
 * Home page component.
 * 
 * Displays service overview, features, and navigation to main functions.
 */
function Home(): JSX.Element {
  return (
    <div className="container mx-auto px-4 py-16">
      {/* Header */}
      <header className="text-center mb-16">
        <h1 className="text-5xl font-bold text-white mb-4">
          Tastefully <span className="text-purple-400">Stained</span>
        </h1>
        <p className="text-xl text-gray-300 max-w-2xl mx-auto">
          AI Content Provenance & Watermarking Service. Protect your content with
          C2PA-compliant watermarking and blockchain verification.
        </p>
      </header>

      {/* CTA Buttons */}
      <div className="flex justify-center gap-4 mb-16">
        <Link
          to="/upload"
          className="bg-purple-600 hover:bg-purple-700 text-white px-8 py-3 rounded-lg font-semibold flex items-center gap-2 transition-colors"
        >
          <Upload size={20} />
          Watermark Content
        </Link>
        <Link
          to="/verify"
          className="bg-white/10 hover:bg-white/20 text-white px-8 py-3 rounded-lg font-semibold flex items-center gap-2 transition-colors"
        >
          <Search size={20} />
          Verify Content
        </Link>
      </div>

      {/* Features */}
      <div className="grid md:grid-cols-3 gap-8 mb-16">
        <FeatureCard
          icon={<Shield size={40} />}
          title="C2PA Compliant"
          description="Full compliance with Content Authenticity Initiative standards for trusted provenance."
        />
        <FeatureCard
          icon={<Lock size={40} />}
          title="Blockchain Anchored"
          description="Immutable proof of authenticity with Ethereum blockchain anchoring."
        />
        <FeatureCard
          icon={<Upload size={40} />}
          title="Invisible Watermarks"
          description="Advanced DCT/DWT algorithms for imperceptible yet robust watermarks."
        />
      </div>

      {/* Footer */}
      <footer className="text-center text-gray-400">
        <p>© 2024-2026 Tastefully Stained. All rights reserved.</p>
      </footer>
    </div>
  );
}

export default Home;
