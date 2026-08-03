import axios from 'axios';
import type { RequirementSlotId, UploadedFile } from '../types/intake';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface BackendDocumentMetadata {
  filename: string;
  original_filename?: string;
  size_bytes: number;
  content_type: string;
  upload_time: string;
  status: string;
}

export interface IntakeStatusResponse {
  status: Record<RequirementSlotId, BackendDocumentMetadata | null>;
}

export interface IntakeUploadResponse {
  status: string;
  message: string;
  document_type: RequirementSlotId;
  metadata: BackendDocumentMetadata;
}

export interface AnalysisStartResponse {
  job_id: string;
  status: string;
  created_at: string;
  message: string;
}

export interface AnalysisStatusResponse {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'awaiting_approval';
  progress_percent: number;
  message: string;
  created_at: string;
  completed_at?: string;
  error_details?: string;
  current_agent?: string | null;
  warnings?: string[];
}

// Convert backend metadata to frontend UI model
export const mapMetadataToUploadedFile = (
  meta: BackendDocumentMetadata,
  slotId: RequirementSlotId
): UploadedFile => {
  return {
    name: meta.original_filename || meta.filename,
    storedName: meta.filename,
    size: meta.size_bytes,
    type: meta.content_type,
    status: 'ready',
    slotId,
  };
};

export const ApiService = {
  /**
   * Fetch status of all intake slots from backend storage.
   */
  async fetchIntakeStatus(): Promise<Record<RequirementSlotId, UploadedFile | undefined>> {
    const response = await apiClient.get<IntakeStatusResponse>('/intake/status');
    const backendStatus = response.data.status;

    const result: Record<RequirementSlotId, UploadedFile | undefined> = {
      priya_pt_invoice: undefined,
      aarav_mri_report: undefined,
      surgeon_estimate: undefined,
      user_query_transcript: undefined,
    };

    Object.keys(result).forEach((key) => {
      const slotId = key as RequirementSlotId;
      const meta = backendStatus[slotId];
      if (meta) {
        result[slotId] = mapMetadataToUploadedFile(meta, slotId);
      }
    });

    return result;
  },

  /**
   * Upload a document to a specific intake slot.
   */
  async uploadDocument(file: File, slotId: RequirementSlotId): Promise<UploadedFile> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', slotId);

    const response = await apiClient.post<IntakeUploadResponse>('/intake/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return mapMetadataToUploadedFile(response.data.metadata, slotId);
  },

  /**
   * Delete document associated with a specific slot.
   */
  async deleteDocument(slotId: RequirementSlotId): Promise<void> {
    await apiClient.delete(`/intake/${slotId}`);
  },

  /**
   * Triggers the coordination assessment.
   */
  async startAnalysis(ocrEngine?: string, mockMode?: boolean): Promise<AnalysisStartResponse> {
    const response = await apiClient.post<AnalysisStartResponse>('/analysis/start', {
      ocr_engine: ocrEngine || 'library',
      mock_mode: mockMode || false,
    });
    return response.data;
  },

  /**
   * Polls the active analysis job status.
   */
  async getAnalysisStatus(jobId: string): Promise<AnalysisStatusResponse> {
    const response = await apiClient.get<AnalysisStatusResponse>(`/analysis/status/${jobId}`);
    return response.data;
  },

  /**
   * Fetches final assessment reports summary.
   */
  async getReportsSummary(jobId: string): Promise<any> {
    const response = await apiClient.get<any>(`/reports/summary`, {
      params: { job_id: jobId },
    });
    return response.data;
  },

  /**
   * Approves the analysis job manually.
   */
  async approveAnalysis(jobId: string): Promise<any> {
    const response = await apiClient.post<any>(`/analysis/approve`, null, {
      params: { job_id: jobId },
    });
    return response.data;
  },

  /**
   * Rejects the analysis job and triggers re-analysis.
   */
  async rejectAnalysis(jobId: string): Promise<any> {
    const response = await apiClient.post<any>(`/analysis/reject`, null, {
      params: { job_id: jobId },
    });
    return response.data;
  },

  /**
   * Fetches previous assessment job history.
   */
  async getAnalysisHistory(): Promise<AnalysisStatusResponse[]> {
    const response = await apiClient.get<AnalysisStatusResponse[]>('/analysis/history');
    return response.data;
  },

  /**
   * Clears the previous assessment job history.
   */
  async clearAnalysisHistory(): Promise<void> {
    await apiClient.post('/analysis/clear-history');
  },

  /**
   * Fetches TTS Audio Verdict Summary briefing for a job.
   */
  async fetchAudioBriefing(jobId: string): Promise<any> {
    const response = await apiClient.get(`/analysis/${jobId}/audio`);
    return response.data;
  },

  /**
   * Fetches HITL audit status for a job.
   */
  async fetchHitlStatus(jobId: string): Promise<any> {
    const response = await apiClient.get(`/analysis/${jobId}/hitl-status`);
    return response.data;
  },

  /**
   * Applies clinician override parameters and resumes the pipeline.
   */
  async overrideAndResume(jobId: string, overrideData: any): Promise<any> {
    const response = await apiClient.post(`/analysis/${jobId}/override`, overrideData);
    return response.data;
  },

  /**
   * Generates a synthetic scanned document with scan rotation and noise.
   */
  async generateScannedDocument(payload: any): Promise<any> {
    const response = await apiClient.post('/analysis/documents/generate-scanned', payload);
    return response.data;
  },

  /**
   * Queries CPT procedure rule details from the rules database.
   */
  async fetchCptRule(cptCode: string): Promise<any> {
    const response = await apiClient.get(`/rules/cpt/${cptCode}`);
    return response.data;
  },

  /**
   * Queries ICD-10 diagnosis rule details from the rules database.
   */
  async fetchIcdRule(icdCode: string): Promise<any> {
    const response = await apiClient.get(`/rules/icd/${icdCode}`);
    return response.data;
  },
};
