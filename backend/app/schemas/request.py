from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="The shopper's query message.")
    conversation_id: Optional[str] = Field(None, description="Optional conversation session ID for multi-turn tracking.")

class EvaluationRequest(BaseModel):
    dataset_name: Optional[str] = Field("sample_eval_questions.json", description="File name of evaluation questions dataset.")
    max_questions: Optional[int] = Field(None, ge=1, le=1000, description="Max questions to evaluate.")
    dry_run: bool = Field(False, description="Dry run mode without updating persisted evaluation reports.")

class CatalogueIngestRequest(BaseModel):
    file_path: Optional[str] = Field(None, description="Explicit path to product catalogue.")
    column_mapping: Optional[Dict[str, str]] = Field(None, description="Custom column name mapping dictionary.")
    use_synthetic: bool = Field(False, description="Whether to explicitly load development fixtures for testing.")
