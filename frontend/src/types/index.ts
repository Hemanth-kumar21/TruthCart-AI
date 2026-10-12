export type DecisionType = "ANSWER" | "CLARIFY" | "REFUSE";

export interface EvidenceItem {
  source_type: "product" | "policy";
  source_id: string;
  field: string;
  value: any;
  confidence: number;
}

export interface EvidenceObject {
  decision: DecisionType;
  query: string;
  evidence: EvidenceItem[];
  unsupported_fields: string[];
  clarification_question?: string | null;
  refusal_reason?: string | null;
}

export interface ProductResult {
  product_id: string;
  title: string;
  description: string;
  category: string;
  price: number;
  stock_status: string;
  rating?: number | null;
  attributes: Record<string, any>;
  citation: string;
}

export interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  timestamp: string;
  text: string;
  decision?: DecisionType;
  products?: ProductResult[];
  citations?: string[];
  evidence?: EvidenceObject;
  clarification_question?: string | null;
  refusal_reason?: string | null;
  retrieval_status?: string;
  model_status?: string;
  latency_ms?: number;
}

export interface ReadinessStatus {
  catalogue_ready: boolean;
  policy_ready: boolean;
  embedding_model_ready: boolean;
  instruction_model_ready: boolean;
  is_using_synthetic_fixtures: boolean;
  message: string;
}

export interface HealthResponse {
  status: string;
  project_name: string;
  team_name: string;
  version: string;
  data_readiness: {
    catalogue_ready: boolean;
    policy_ready: boolean;
    embedding_model_ready: boolean;
    instruction_model_ready: boolean;
    is_using_synthetic_fixtures: boolean;
    message: string;
  };
  model_readiness: {
    embedding_model_ready: boolean;
    instruction_model_ready: boolean;
    embedding_model_type: string;
    instruction_model_type: string;
    execution_mode: string;
    external_api_calls_enabled: boolean;
  };
}

export interface CatalogueStatusResponse {
  status: string;
  is_ready?: boolean;
  is_official: boolean;
  is_synthetic_fixture: boolean;
  records_loaded: number;
  records_rejected: number;
  duplicate_records: number;
  missing_fields_count: number;
  categories: string[];
  total_active_products: number;
  data_source_path?: string | null;
}

export interface QuestionEvaluationResult {
  question_id: string;
  query: string;
  expected_decision?: string | null;
  actual_decision: string;
  decision_match?: boolean | null;
  citations: string[];
  citations_valid: boolean;
  has_unsupported_claims: boolean;
  latency_ms: number;
  notes?: string | null;
}

export interface EvaluationReportResponse {
  report_id: string;
  timestamp: string;
  dataset_name: string;
  total_questions_tested: number;
  successfully_evaluated: number;
  groundedness_score: number;
  answer_helpfulness_score: number;
  refusal_accuracy: number;
  clarification_accuracy: number;
  unsupported_claim_rate: number;
  citation_validity_rate: number;
  avg_latency_ms: number;
  compute_info: Record<string, any>;
  details: QuestionEvaluationResult[];
}
