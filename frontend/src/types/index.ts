export interface TriageResult {
  post_type: 'reputational_rumour' | 'scam_phishing' | 'benign_feedback';
  requires_deep_verification: boolean;
  urgency_level: 'low' | 'medium' | 'high' | 'critical';
  reasoning: string;
}

export interface Claim {
  claim_id: string;
  claim_text: string;
  entity: string;
  topic: string;
}

export interface EvidenceCitation {
  chunk_id: string;
  source: string;
  tier: number;
  url: string;
  publish_date?: string;
  snippet: string;
  is_title_only: boolean;
  is_simulated: boolean;
  score: number;
}

export interface VerificationResult {
  verdict: 'supported' | 'contradicted' | 'unverifiable' | 'insufficient_evidence';
  confidence: number;
  reasoning: string;
  cited_passages: EvidenceCitation[];
  retrieval_rounds: number;
  is_grounded: boolean;
  abstention_reason?: string;
}

export interface ClassificationResult {
  category: 'misinformation' | 'scam_impersonation' | 'credible' | 'unverified';
  rationale: string;
}

export interface RiskScore {
  total_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  severity_score: number;
  velocity_score: number;
  reach_score: number;
  verdict_score: number;
  active_components: string[];
  renormalised_note: string;
}

export interface DraftedResponse {
  formal_response: string;
  pidgin_response?: string;
  cited_chunk_ids: string[];
  citation_validation_passed: boolean;
  validation_notes: string;
}

export interface PipelineTraceStep {
  step_number: number;
  agent_name: string;
  status: 'running' | 'completed' | 'bypassed' | 'failed';
  timestamp: string;
  output_summary: string;
  details?: Record<string, any>;
}

export interface FullAnalysisResult {
  post_id: string;
  raw_text: string;
  redacted_text: string;
  normalized_query: string;
  has_pidgin: boolean;
  triage: TriageResult;
  claims: Claim[];
  verification: VerificationResult;
  classification: ClassificationResult;
  risk: RiskScore;
  response_draft: DraftedResponse;
  approval_status: 'pending' | 'approved' | 'rejected' | 'edited';
  traces: PipelineTraceStep[];
  created_at: string;
  editor_notes?: string;
  rejection_reason?: string;
}

export interface SeedPost {
  id: string;
  text: string;
  language: string;
  category_type: string;
  gold_label: string;
  expected_verdict: string;
  linked_kb_docs: string[];
  rationale: string;
  metadata: {
    platform: string;
    timestamp?: string;
    likes?: number;
    shares?: number;
  };
}

export interface KBSource {
  id: string;
  name: string;
  base_url: string;
  tier: number;
  access_method: string;
  rate_limit_seconds?: number;
  crawl_delay_seconds?: number;
  robots_status: string;
  terms_of_use_note: string;
  is_active: boolean;
}
