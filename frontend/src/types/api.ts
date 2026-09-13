export type CatalogErrorOption = { code: string; label: string; error_type?: string | null };
export type CatalogModelOut = { model: string; model_aliases: string[]; error_options: CatalogErrorOption[] };
export type CatalogManufacturerOut = { manufacturer: string; models: CatalogModelOut[] };
export type CatalogCategoryOut = { equipment_category: string; manufacturers: CatalogManufacturerOut[] };
export type CatalogResponse = { categories: CatalogCategoryOut[]; total_supported_models: number };

export type TroubleshootRequest = {
  equipment_category: string;
  manufacturer: string;
  model: string;
  code?: string | null;
  symptom?: string | null;
  source?: string;
};
export type SourceCitationOut = { manual_title: string; manual_document_number?: string | null; page?: string | null; official_url?: string | null };
export type EvidenceOut = { equipment_category: string; manufacturer: string; model: string; code: string; issue_title: string; meaning: string; possible_causes: string[]; troubleshooting_steps: string[]; safe_user_checks: string[]; technician_only_checks: string[]; source: SourceCitationOut; retrieval_method?: string | null; detailed_note?: string | null };
export type GroundedAnswerOut = { issue_summary: string; meaning_explanation: string; cause_explanations: string[]; safe_check_guidance: string[]; technician_only_guidance: string[]; next_action: string };
export type SafetyOut = { escalate: boolean; technician_only: boolean; warning_text?: string | null; reason_category?: string | null };
export type TroubleshootStatus = 'verified_result' | 'issue_not_verified' | 'equipment_not_supported' | 'error';
export type TroubleshootResponse = { status: TroubleshootStatus; message: string; evidence?: EvidenceOut | null; grounded_answer?: GroundedAnswerOut | null; safety?: SafetyOut | null };
export type VisionCandidateOut = { equipment_category?: string | null; manufacturer?: string | null; model?: string | null; code?: string | null; confidence: number; raw_model_text?: string | null };
export type VisionExtractStatus = 'image_unclear' | 'candidates_found' | 'no_candidates' | 'error';
export type VisionExtractResponse = { status: VisionExtractStatus; reason?: string | null; candidates: VisionCandidateOut[]; message: string };
