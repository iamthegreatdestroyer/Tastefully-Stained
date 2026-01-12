/**
 * Blockchain Service
 * 
 * Web3 integration for blockchain anchor verification.
 * 
 * @copyright 2024-2026 Tastefully Stained
 */

import { ethers } from 'ethers';

/**
 * Blockchain anchor information.
 */
export interface BlockchainAnchor {
  txHash: string;
  blockNumber: number;
  timestamp: string;
  network: string;
  confirmations: number;
  contentHash: string;
}

/**
 * Network configuration.
 */
const NETWORKS: Record<string, { rpcUrl: string; chainId: number }> = {
  ethereum_mainnet: {
    rpcUrl: 'https://mainnet.infura.io/v3/',
    chainId: 1,
  },
  ethereum_sepolia: {
    rpcUrl: 'https://sepolia.infura.io/v3/',
    chainId: 11155111,
  },
  polygon_mainnet: {
    rpcUrl: 'https://polygon-mainnet.infura.io/v3/',
    chainId: 137,
  },
};

/**
 * Get provider for a network.
 * 
 * @param network - Network name
 * @param infuraKey - Infura API key
 * @returns ethers provider
 */
export function getProvider(network: string, infuraKey: string): ethers.JsonRpcProvider {
  const config = NETWORKS[network];
  if (!config) {
    throw new Error(`Unsupported network: ${network}`);
  }

  return new ethers.JsonRpcProvider(`${config.rpcUrl}${infuraKey}`);
}

/**
 * Verify a blockchain anchor.
 * 
 * @param txHash - Transaction hash to verify
 * @param network - Network to check
 * @param infuraKey - Infura API key
 * @returns Anchor information or null if not found
 */
export async function verifyAnchor(
  txHash: string,
  network: string,
  infuraKey: string
): Promise<BlockchainAnchor | null> {
  try {
    const provider = getProvider(network, infuraKey);
    
    // Get transaction receipt
    const receipt = await provider.getTransactionReceipt(txHash);
    if (!receipt) {
      return null;
    }

    // Get block for timestamp
    const block = await provider.getBlock(receipt.blockNumber);
    if (!block) {
      return null;
    }

    // Get current block for confirmations
    const currentBlock = await provider.getBlockNumber();
    const confirmations = currentBlock - receipt.blockNumber;

    return {
      txHash,
      blockNumber: receipt.blockNumber,
      timestamp: new Date(block.timestamp * 1000).toISOString(),
      network,
      confirmations,
      contentHash: '', // Would be extracted from transaction data
    };
  } catch (error) {
    console.error('Failed to verify anchor:', error);
    return null;
  }
}

/**
 * Connect to user's wallet.
 * 
 * @returns Connected signer
 */
export async function connectWallet(): Promise<ethers.Signer> {
  if (typeof window.ethereum === 'undefined') {
    throw new Error('MetaMask is not installed');
  }

  const provider = new ethers.BrowserProvider(window.ethereum);
  await provider.send('eth_requestAccounts', []);
  
  return provider.getSigner();
}

/**
 * Get current network from wallet.
 * 
 * @returns Network name
 */
export async function getCurrentNetwork(): Promise<string> {
  if (typeof window.ethereum === 'undefined') {
    throw new Error('MetaMask is not installed');
  }

  const provider = new ethers.BrowserProvider(window.ethereum);
  const network = await provider.getNetwork();
  
  // Map chain ID to network name
  const chainIdMap: Record<number, string> = {
    1: 'ethereum_mainnet',
    11155111: 'ethereum_sepolia',
    137: 'polygon_mainnet',
    80001: 'polygon_mumbai',
    42161: 'arbitrum_one',
  };

  return chainIdMap[Number(network.chainId)] || 'unknown';
}
