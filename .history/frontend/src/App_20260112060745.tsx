/**
 * Tastefully Stained - Main App Component
 * 
 * Root application component with routing configuration.
 * 
 * @copyright 2024-2026 Tastefully Stained
 */

import { Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import Upload from './pages/Upload';
import Verify from './pages/Verify';

/**
 * Main application component.
 * 
 * Defines the routing structure for the application:
 * - / - Home page with service overview
 * - /upload - Watermark embedding interface
 * - /verify - Watermark verification interface
 */
function App(): JSX.Element {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/upload" element={<Upload />} />
        <Route path="/verify" element={<Verify />} />
      </Routes>
    </div>
  );
}

export default App;
