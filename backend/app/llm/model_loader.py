import os
from pathlib import Path
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.logging_config import SafeLogger

class ModelLoader:
    """Detects, inspects, and manages organiser-supplied local model checkpoints."""

    def __init__(self):
        self.embedding_model_loaded: bool = False
        self.instruction_model_loaded: bool = False
        self.embedding_model_path: Optional[Path] = None
        self.instruction_model_path: Optional[Path] = None
        self.embedding_model_type: Optional[str] = None
        self.instruction_model_type: Optional[str] = None
        self._check_models()

    def _check_models(self) -> None:
        emb_dir = settings.get_embedding_model_path()
        inst_dir = settings.get_instruction_model_path()

        # Check embedding model dir
        if emb_dir.exists():
            files = [f for f in emb_dir.iterdir() if f.is_file() and not f.name.startswith('.')]
            if files:
                self.embedding_model_loaded = True
                self.embedding_model_path = emb_dir
                self.embedding_model_type = "Local Files Checkpoint"
                SafeLogger.info(f"Organiser embedding model detected at: {emb_dir.name}")
            else:
                self.embedding_model_loaded = False
                SafeLogger.info("No embedding model files detected. Running in lightweight vector fallback mode.")
        else:
            self.embedding_model_loaded = False

        # Check instruction model dir
        if inst_dir.exists():
            files = [f for f in inst_dir.iterdir() if f.is_file() and not f.name.startswith('.')]
            if files:
                self.instruction_model_loaded = True
                self.instruction_model_path = inst_dir
                self.instruction_model_type = "Local Files Checkpoint"
                SafeLogger.info(f"Organiser instruction model detected at: {inst_dir.name}")
            else:
                self.instruction_model_loaded = False
                SafeLogger.info("No instruction model files detected. Running with deterministic evidence response generator.")
        else:
            self.instruction_model_loaded = False

    def get_status(self) -> Dict[str, Any]:
        self._check_models()
        return {
            "embedding_model_ready": self.embedding_model_loaded,
            "instruction_model_ready": self.instruction_model_loaded,
            "embedding_model_type": self.embedding_model_type or "Deterministic Local Vector Index (Active)",
            "instruction_model_type": self.instruction_model_type or "Grounded Rule Generator (Active)",
            "execution_mode": "Offline Local / CPU",
            "external_api_calls_enabled": False
        }

model_loader = ModelLoader()
