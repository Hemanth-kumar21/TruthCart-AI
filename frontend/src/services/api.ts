import type {
  HealthResponse,
  CatalogueStatusResponse,
  EvaluationReportResponse,
} from "../types";

const API_BASE = "/api";

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchCatalogueStatus(): Promise<CatalogueStatusResponse> {
  const res = await fetch(`${API_BASE}/catalogue/status`);
  if (!res.ok) {
    throw new Error(`Catalogue status fetch failed: ${res.statusText}`);
  }
  return res.json();
}

export async function reloadCatalogue(useSynthetic: boolean = false): Promise<CatalogueStatusResponse> {
  const res = await fetch(`${API_BASE}/catalogue/reload`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ use_synthetic: useSynthetic }),
  });
  if (!res.ok) {
    throw new Error(`Catalogue reload failed: ${res.statusText}`);
  }
  return res.json();
}

export async function sendChatMessage(
  message: string,
  conversationId?: string
): Promise<any> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
    }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Chat request failed: ${res.statusText}`);
  }
  return res.json();
}

export async function runEvaluationSuite(
  datasetName: string = "sample_eval_questions.json",
  maxQuestions?: number,
  dryRun: boolean = false
): Promise<EvaluationReportResponse> {
  const res = await fetch(`${API_BASE}/evaluation/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      dataset_name: datasetName,
      max_questions: maxQuestions,
      dry_run: dryRun,
    }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Evaluation run failed: ${res.statusText}`);
  }
  return res.json();
}
