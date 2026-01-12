/**
 * API Service
 * 
 * HTTP client for communicating with the Tastefully Stained backend.
 * 
 * @copyright 2024-2026 Tastefully Stained
 */

import axios, { AxiosError } from 'axios';

// Configure base URL from environment or default
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

// Create axios instance with defaults
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60 seconds for image processing
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for adding auth headers
api.interceptors.request.use((config) => {
  const apiKey = localStorage.getItem('tastefully_stained_api_key');
  if (apiKey) {
    config.headers['X-API-Key'] = apiKey;
  }
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

/**
 * Embed watermark request parameters.
 */
export interface EmbedWatermarkParams {
  file: File;
  watermarkData: string;
  strategy: 'auto' | 'dct' | 'dwt' | 'hybrid';
  includeC2PA: boolean;
  anchorBlockchain: boolean;
}

/**
 * Embed watermark response.
 */
export interface EmbedWatermarkResponse {
  success: boolean;
  message: string;
  watermarkedImageUrl: string | null;
  watermarkId: string | null;
  c2paManifestUrl: string | null;
  blockchainTxHash: string | null;
  qualityMetrics: Record<string, number>;
  processingTimeMs: number;
}

/**
 * Verification response.
 */
export interface VerificationResponse {
  isValid: boolean;
  isAuthentic: boolean;
  confidence: number;
  c2paVerified: boolean;
  blockchainVerified: boolean;
  tamperingDetected: boolean;
  details: Record<string, unknown>;
}

/**
 * Embed watermark in an image.
 * 
 * @param params - Embedding parameters
 * @returns Embedding result
 */
export async function embedWatermark(params: EmbedWatermarkParams): Promise<EmbedWatermarkResponse> {
  const formData = new FormData();
  formData.append('image', params.file);
  formData.append('watermark_data', params.watermarkData);
  formData.append('strategy', params.strategy);

  const response = await api.post<EmbedWatermarkResponse>('/watermark/embed', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
}

/**
 * Verify watermark in an image.
 * 
 * @param file - Image file to verify
 * @returns Verification result
 */
export async function verifyWatermark(file: File): Promise<VerificationResponse> {
  const formData = new FormData();
  formData.append('image', file);

  const response = await api.post<VerificationResponse>('/watermark/verify', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
}

/**
 * Extract watermark from an image.
 * 
 * @param file - Image file to extract from
 * @returns Extracted watermark data
 */
export async function extractWatermark(file: File): Promise<{ data: string; confidence: number }> {
  const formData = new FormData();
  formData.append('image', file);

  const response = await api.post('/watermark/extract', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
}

/**
 * Get health status of the API.
 */
export async function getHealth(): Promise<{ status: string; version: string }> {
  const response = await api.get('/health');
  return response.data;
}

export default api;
