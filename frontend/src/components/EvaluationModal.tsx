import React, { useState } from "react";
import {
  X,
  Play,
  BarChart3,
  AlertTriangle,
  RefreshCw,
  FileCheck2,
} from "lucide-react";
import { runEvaluationSuite } from "../services/api";
import type { EvaluationReportResponse } from "../types";

interface EvaluationModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const EvaluationModal: React.FC<EvaluationModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [report, setReport] = useState<EvaluationReportResponse | null>(null);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleRunEvaluation = async () => {
    setIsRunning(true);
    setError(null);
    try {
      const result = await runEvaluationSuite("sample_eval_questions.json");
      setReport(result);
    } catch (err: any) {
      setError(err.message || "Failed to execute evaluation suite.");
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6 animate-fade-in">
      <div className="bg-white rounded-2xl max-w-4xl w-full max-h-[90vh] shadow-2xl border border-slate-200 flex flex-col overflow-hidden">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-xl bg-indigo-600 text-white flex items-center justify-center">
              <BarChart3 className="h-5 w-5" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-lg">
                TruthCart AI Benchmark & Evaluation Suite
              </h3>
              <p className="text-xs text-slate-500">
                Rigorous RAG & Hallucination Resistance Verification (150-Question Benchmark Framework)
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-200/60 transition-colors cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Action Card */}
          <div className="bg-indigo-50/60 border border-indigo-100 rounded-xl p-5 flex flex-wrap items-center justify-between gap-4">
            <div>
              <h4 className="font-semibold text-indigo-950 text-sm">
                Run Automated Evaluation Pipeline
              </h4>
              <p className="text-xs text-indigo-800 mt-1 max-w-xl">
                Executes questions through Query Understanding, Hybrid Retrieval, Evidence Engine, Citation Validation, and Response Grounding. Measures zero-hallucination accuracy deterministically.
              </p>
            </div>

            <button
              onClick={handleRunEvaluation}
              disabled={isRunning}
              id="run-eval-suite-btn"
              className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white font-semibold text-xs shadow-sm flex items-center space-x-2 transition-all cursor-pointer"
            >
              {isRunning ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  <span>Evaluating Pipeline...</span>
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 fill-white" />
                  <span>Execute Benchmark</span>
                </>
              )}
            </button>
          </div>

          {error && (
            <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 text-xs text-rose-800 flex items-center space-x-2">
              <AlertTriangle className="h-4 w-4 text-rose-600 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Results Overview */}
          {report ? (
            <div className="space-y-6 animate-fade-in">
              {/* Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
                {/* Groundedness */}
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5">
                  <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                    Groundedness
                  </span>
                  <span className="text-2xl font-bold text-emerald-600 block mt-1">
                    {(report.groundedness_score * 100).toFixed(1)}%
                  </span>
                  <span className="text-[10px] text-slate-400">Zero-hallucination rate</span>
                </div>

                {/* Citation Validity */}
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5">
                  <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                    Citation Validity
                  </span>
                  <span className="text-2xl font-bold text-indigo-600 block mt-1">
                    {(report.citation_validity_rate * 100).toFixed(1)}%
                  </span>
                  <span className="text-[10px] text-slate-400">Server verified links</span>
                </div>

                {/* Refusal Accuracy */}
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5">
                  <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                    Refusal Accuracy
                  </span>
                  <span className="text-2xl font-bold text-blue-600 block mt-1">
                    {(report.refusal_accuracy * 100).toFixed(1)}%
                  </span>
                  <span className="text-[10px] text-slate-400">Out-of-catalogue accuracy</span>
                </div>

                {/* Latency */}
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5">
                  <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                    Avg Latency
                  </span>
                  <span className="text-2xl font-bold text-slate-800 block mt-1">
                    {report.avg_latency_ms.toFixed(1)} ms
                  </span>
                  <span className="text-[10px] text-slate-400">Local CPU execution</span>
                </div>
              </div>

              {/* Additional metric badges */}
              <div className="flex flex-wrap gap-2 text-xs">
                <span className="px-3 py-1 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200 font-medium">
                  Unsupported Claim Rate: {(report.unsupported_claim_rate * 100).toFixed(1)}%
                </span>
                <span className="px-3 py-1 rounded-lg bg-indigo-50 text-indigo-800 border border-indigo-200 font-medium">
                  Clarification Accuracy: {(report.clarification_accuracy * 100).toFixed(1)}%
                </span>
                <span className="px-3 py-1 rounded-lg bg-slate-100 text-slate-700 border border-slate-200 font-medium">
                  Questions Evaluated: {report.successfully_evaluated} / {report.total_questions_tested}
                </span>
              </div>

              {/* Per-Question Trace Table */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600 mb-3">
                  Per-Query Benchmark Traces
                </h4>
                <div className="border border-slate-200 rounded-xl overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 uppercase text-[10px] tracking-wider">
                        <tr>
                          <th className="px-4 py-2.5 font-bold">QID</th>
                          <th className="px-4 py-2.5 font-bold">Query</th>
                          <th className="px-4 py-2.5 font-bold">Expected</th>
                          <th className="px-4 py-2.5 font-bold">Actual</th>
                          <th className="px-4 py-2.5 font-bold">Citations</th>
                          <th className="px-4 py-2.5 font-bold">Latency</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 font-medium">
                        {report.details.map((q) => (
                          <tr key={q.question_id} className="hover:bg-slate-50/60">
                            <td className="px-4 py-2.5 font-mono text-slate-500">
                              {q.question_id}
                            </td>
                            <td className="px-4 py-2.5 text-slate-900 max-w-xs truncate">
                              {q.query}
                            </td>
                            <td className="px-4 py-2.5 text-slate-600">
                              {q.expected_decision || "N/A"}
                            </td>
                            <td className="px-4 py-2.5">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                  q.actual_decision === "ANSWER"
                                    ? "bg-emerald-100 text-emerald-800"
                                    : q.actual_decision === "CLARIFY"
                                    ? "bg-amber-100 text-amber-800"
                                    : "bg-rose-100 text-rose-800"
                                }`}
                              >
                                {q.actual_decision}
                              </span>
                            </td>
                            <td className="px-4 py-2.5 font-mono text-indigo-700">
                              {q.citations.length > 0 ? q.citations.join(", ") : "None"}
                            </td>
                            <td className="px-4 py-2.5 text-slate-500">
                              {q.latency_ms.toFixed(1)}ms
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-slate-400 text-xs">
              <FileCheck2 className="h-10 w-10 mx-auto text-slate-300 mb-2 stroke-[1.5]" />
              <p>Click "Execute Benchmark" to run the evaluation pipeline against test questions.</p>
              <p className="text-[11px] text-slate-400 mt-1">
                Metrics are calculated dynamically and recorded directly to <code>artifacts/evaluation_reports/</code>.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
