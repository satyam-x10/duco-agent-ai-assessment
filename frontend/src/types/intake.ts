export type RequirementSlotId =
  | 'priya_pt_invoice'
  | 'aarav_mri_report'
  | 'surgeon_estimate'
  | 'user_query_transcript';

export interface RequirementSlot {
  id: RequirementSlotId;
  title: string;
  description: string;
  allowedFormats: string[];
}

export interface UploadedFile {
  name: string;
  size: number;
  type: string;
  status: 'ready' | 'uploading' | 'error';
  slotId: RequirementSlotId;
  errorMsg?: string;
}
