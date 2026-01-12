/**
 * Blockchain Explorer Component
 * 
 * Displays blockchain anchor information and transaction details.
 * 
 * @copyright 2024-2026 Tastefully Stained
 */

import { ExternalLink, Clock, Hash, Layers } from 'lucide-react';

interface BlockchainAnchor {
  txHash: string;
  blockNumber: number;
  timestamp: string;
  network: string;
  confirmations: number;
}

interface BlockchainExplorerProps {
  anchor: BlockchainAnchor | null;
}

/**
 * Blockchain explorer component.
 * 
 * Displays blockchain anchor information with links to block explorers.
 */
function BlockchainExplorer({ anchor }: BlockchainExplorerProps): JSX.Element {
  if (!anchor) {
    return (
      <div className="bg-white/10 backdrop-blur-lg rounded-xl p-6 text-center text-gray-400">
        No blockchain anchor found
      </div>
    );
  }

  const explorerUrl = getExplorerUrl(anchor.network, anchor.txHash);

  return (
    <div className="bg-white/10 backdrop-blur-lg rounded-xl p-6 space-y-4">
      <h3 className="text-xl font-semibold text-white mb-4">Blockchain Anchor</h3>

      {/* Transaction Hash */}
      <div className="flex items-start gap-3">
        <Hash className="text-purple-400 mt-1" size={20} />
        <div className="flex-1 min-w-0">
          <div className="text-gray-400 text-sm">Transaction Hash</div>
          <div className="text-white font-mono text-sm truncate">{anchor.txHash}</div>
        </div>
        <a
          href={explorerUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-purple-400 hover:text-purple-300"
        >
          <ExternalLink size={20} />
        </a>
      </div>

      {/* Block Number */}
      <div className="flex items-start gap-3">
        <Layers className="text-purple-400 mt-1" size={20} />
        <div>
          <div className="text-gray-400 text-sm">Block Number</div>
          <div className="text-white">{anchor.blockNumber.toLocaleString()}</div>
        </div>
      </div>

      {/* Timestamp */}
      <div className="flex items-start gap-3">
        <Clock className="text-purple-400 mt-1" size={20} />
        <div>
          <div className="text-gray-400 text-sm">Timestamp</div>
          <div className="text-white">{new Date(anchor.timestamp).toLocaleString()}</div>
        </div>
      </div>

      {/* Network & Confirmations */}
      <div className="flex justify-between pt-4 border-t border-white/10">
        <div>
          <div className="text-gray-400 text-sm">Network</div>
          <div className="text-white capitalize">{anchor.network.replace('_', ' ')}</div>
        </div>
        <div className="text-right">
          <div className="text-gray-400 text-sm">Confirmations</div>
          <div className="text-green-400">{anchor.confirmations}</div>
        </div>
      </div>
    </div>
  );
}

/**
 * Get block explorer URL for a transaction.
 */
function getExplorerUrl(network: string, txHash: string): string {
  const explorers: Record<string, string> = {
    ethereum_mainnet: 'https://etherscan.io/tx/',
    ethereum_sepolia: 'https://sepolia.etherscan.io/tx/',
    polygon_mainnet: 'https://polygonscan.com/tx/',
    polygon_mumbai: 'https://mumbai.polygonscan.com/tx/',
    arbitrum_one: 'https://arbiscan.io/tx/',
  };

  const baseUrl = explorers[network] || 'https://etherscan.io/tx/';
  return `${baseUrl}${txHash}`;
}

export default BlockchainExplorer;
