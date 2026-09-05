import axios, { AxiosInstance } from 'axios';
import { RTOOrderResponse, OrderPayload, PincodeCluster, AbuseRing } from '../types';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

class RTOGuardAPI {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: BACKEND_URL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        console.log(`API Response: ${response.status} ${response.config.url}`);
        return response;
      },
      (error) => {
        console.error(`API Error: ${error.message}`);
        return Promise.reject(error);
      }
    );
  }

  // ============================================================================
  // RETURN-RISK SCORER
  // ============================================================================

  async scoreRTO(payload: OrderPayload): Promise<RTOOrderResponse> {
    const response = await this.client.post<RTOOrderResponse>(
      '/v1/score/rto',
      payload
    );
    return response.data;
  }

  async getThresholdSweep(): Promise<any[]> {
    const response = await this.client.get('/v1/threshold-sweep');
    return response.data;
  }

  // ============================================================================
  // FRAUD-SPIKE DETECTOR
  // ============================================================================

  async getActiveSpikeCluster(): Promise<PincodeCluster> {
    const response = await this.client.get('/v1/spike/active-cluster');
    return response.data;
  }

  async getSpikeMetrics(pincodeId: string): Promise<any> {
    const response = await this.client.get(`/v1/spike/metrics/${pincodeId}`);
    return response.data;
  }

  // ============================================================================
  // ABUSE-RING SENTINEL
  // ============================================================================

  async getActiveRings(): Promise<AbuseRing[]> {
    const response = await this.client.get('/v1/rings/active');
    return response.data;
  }

  async getRingDetails(ringId: string): Promise<AbuseRing> {
    const response = await this.client.get(`/v1/rings/${ringId}`);
    return response.data;
  }

  async blockRing(ringId: string): Promise<any> {
    const response = await this.client.post(`/v1/rings/${ringId}/block`);
    return response.data;
  }

  // ============================================================================
  // CHARGEBACK RESPONDER
  // ============================================================================

  async getDisputeCases(): Promise<any[]> {
    const response = await this.client.get('/v1/disputes/cases');
    return response.data;
  }

  async getDisputeDetails(caseId: string): Promise<any> {
    const response = await this.client.get(`/v1/disputes/cases/${caseId}`);
    return response.data;
  }

  async submitEvidence(caseId: string, evidenceData: any): Promise<any> {
    const response = await this.client.post(
      `/v1/disputes/cases/${caseId}/submit`,
      evidenceData
    );
    return response.data;
  }

  // ============================================================================
  // HEALTH CHECK
  // ============================================================================

  async healthCheck(): Promise<any> {
    const response = await this.client.get('/health');
    return response.data;
  }
}

export const rtoAPI = new RTOGuardAPI();
