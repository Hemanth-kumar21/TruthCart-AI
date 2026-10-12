import React from "react";
import { ShieldCheck, Database, Cpu, RotateCcw, BarChart3, AlertCircle } from "lucide-react";
import type { HealthResponse, CatalogueStatusResponse } from "../types";

interface HeaderProps {
  health: HealthResponse | null;
  catalogueStatus: CatalogueStatusResponse | null;
  onResetChat: () => void;
  onOpenEvaluation: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  health,
  catalogueStatus,
  onResetChat,
  onOpenEvaluation,
}) => {
  const isOfficial = catalogueStatus?.is_official ?? false;
  const isSynthetic = catalogueStatus?.is_synthetic_fixture ?? false;

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-18 flex items-center justify-between">
        {/* Brand identity */}
        <div className="flex items-center space-x-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-blue-700 via-indigo-600 to-violet-600 flex items-center justify-center text-white shadow-sm ring-2 ring-indigo-50">
            <ShieldCheck className="h-6 w-6 stroke-[2.2]" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xl font-bold tracking-tight text-slate-900">
                TruthCart <span className="text-indigo-600">AI</span>
              </span>
              <span className="text-[11px] font-semibold uppercase px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                Team TalentX
              </span>
            </div>
            <p className="text-xs text-slate-500 font-medium">
              Shop Smarter. Trust Every Answer.
            </p>
          </div>
        </div>

        {/* Status Pills and Quick Actions */}
        <div className="flex items-center space-x-3">
          {/* Catalogue status */}
          <div className="hidden sm:flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium bg-slate-50 border-slate-200">
            <Database className="h-3.5 w-3.5 text-slate-500" />
            <span className="text-slate-600">Catalogue:</span>
            {isOfficial ? (
              <span className="text-emerald-700 font-semibold flex items-center">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 mr-1.5 animate-pulse" />
                Official Active ({catalogueStatus?.total_active_products})
              </span>
            ) : isSynthetic ? (
              <span className="text-indigo-700 font-semibold flex items-center">
                <span className="h-1.5 w-1.5 rounded-full bg-indigo-500 mr-1.5" />
                Dev Fixtures ({catalogueStatus?.total_active_products})
              </span>
            ) : (
              <span className="text-amber-700 font-semibold flex items-center">
                <AlertCircle className="h-3 w-3 mr-1 text-amber-500" />
                Awaiting Organiser
              </span>
            )}
          </div>

          {/* Model Status */}
          <div className="hidden md:flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium bg-slate-50 border-slate-200">
            <Cpu className="h-3.5 w-3.5 text-slate-500" />
            <span className="text-slate-600">Inference:</span>
            <span className="text-blue-700 font-semibold">
              {health?.model_readiness?.instruction_model_ready
                ? "Local Model Loaded"
                : "Deterministic Verifier (Active)"}
            </span>
          </div>

          {/* Evaluation Suite Button */}
          <button
            onClick={onOpenEvaluation}
            id="evaluation-suite-btn"
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 transition-colors cursor-pointer"
            title="Open 150-Question Benchmark & Evaluation Suite"
          >
            <BarChart3 className="h-3.5 w-3.5" />
            <span>Evaluation Suite</span>
          </button>

          {/* Reset Conversation */}
          <button
            onClick={onResetChat}
            id="reset-chat-btn"
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-slate-200 transition-colors cursor-pointer"
            title="Reset active dialogue constraints and start new conversation"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Reset</span>
          </button>
        </div>
      </div>
    </header>
  );
};
