import { useState, useEffect, useRef } from "react";
import {
  Send,
  Sparkles,
  ShieldAlert,
  ArrowRight,
  RefreshCw,
} from "lucide-react";
import { Header } from "./components/Header";
import { ReadinessBanner } from "./components/ReadinessBanner";
import { ChatMessage } from "./components/ChatMessage";
import { EvidenceDrawer } from "./components/EvidenceDrawer";
import { EvaluationModal } from "./components/EvaluationModal";
import {
  fetchHealth,
  fetchCatalogueStatus,
  reloadCatalogue,
  sendChatMessage,
} from "./services/api";
import type {
  HealthResponse,
  CatalogueStatusResponse,
  ChatMessage as ChatMessageType,
  EvidenceObject,
} from "./types";

export function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [catalogueStatus, setCatalogueStatus] = useState<CatalogueStatusResponse | null>(null);
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [inputMessage, setInputMessage] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isDataLoading, setIsDataLoading] = useState<boolean>(false);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  // Evidence Drawer state
  const [selectedEvidence, setSelectedEvidence] = useState<{
    evidence: EvidenceObject;
    latencyMs?: number;
    retrievalStatus?: string;
    modelStatus?: string;
  } | null>(null);
  const [isEvidenceOpen, setIsEvidenceOpen] = useState<boolean>(false);

  // Evaluation Modal state
  const [isEvaluationOpen, setIsEvaluationOpen] = useState<boolean>(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of chat
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Initial load of health and catalogue status
  useEffect(() => {
    loadAppStatus();
  }, []);

  const loadAppStatus = async () => {
    try {
      const [h, c] = await Promise.all([fetchHealth(), fetchCatalogueStatus()]);
      setHealth(h);
      setCatalogueStatus(c);
    } catch (err: any) {
      console.warn("Could not fetch status:", err.message);
    }
  };

  const handleToggleFixtures = async (enable: boolean) => {
    setIsDataLoading(true);
    try {
      const updatedCat = await reloadCatalogue(enable);
      setCatalogueStatus(updatedCat);
      const updatedHealth = await fetchHealth();
      setHealth(updatedHealth);
    } catch (err: any) {
      setError(err.message || "Failed to toggle fixtures.");
    } finally {
      setIsDataLoading(false);
    }
  };

  const handleSendMessage = async (queryText?: string) => {
    const textToSend = (queryText || inputMessage).trim();
    if (!textToSend || isLoading) return;

    setError(null);
    setInputMessage("");

    const userMsg: ChatMessageType = {
      id: `user-${Date.now()}`,
      sender: "user",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      text: textToSend,
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const resp = await sendChatMessage(textToSend, conversationId);
      setConversationId(resp.conversation_id);

      const assistantMsg: ChatMessageType = {
        id: `assistant-${Date.now()}`,
        sender: "assistant",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        text: resp.response_text,
        decision: resp.decision,
        products: resp.products,
        citations: resp.citations,
        evidence: resp.evidence,
        clarification_question: resp.clarification_question,
        refusal_reason: resp.refusal_reason,
        retrieval_status: resp.retrieval_status,
        model_status: resp.model_status,
        latency_ms: resp.latency_ms,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      setError(err.message || "An error occurred while communicating with TruthCart AI.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetChat = () => {
    setMessages([]);
    setConversationId(undefined);
    setError(null);
  };

  const handleOpenEvidence = (msg: ChatMessageType) => {
    if (msg.evidence) {
      setSelectedEvidence({
        evidence: msg.evidence,
        latencyMs: msg.latency_ms,
        retrievalStatus: msg.retrieval_status,
        modelStatus: msg.model_status,
      });
      setIsEvidenceOpen(true);
    }
  };

  const samplePrompts = [
    { label: "Price Lookup", query: "What is the price of TC-DEV-101?" },
    { label: "Budget & Material", query: "Show me cotton shirts under 1500" },
    { label: "Store Policy", query: "What is your return policy window?" },
    { label: "Attribute Check", query: "Does the Apex 15 laptop have 16 GB RAM?" },
    { label: "Ambiguity Test", query: "Show me shirts" },
    { label: "Out of Catalogue", query: "Do you have iPhone 15 Pro Max?" },
  ];

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col text-slate-800">
      {/* Header */}
      <Header
        health={health}
        catalogueStatus={catalogueStatus}
        onResetChat={handleResetChat}
        onOpenEvaluation={() => setIsEvaluationOpen(true)}
      />

      {/* Readiness / Fixtures Banner */}
      <ReadinessBanner
        catalogueStatus={catalogueStatus}
        onToggleFixtures={handleToggleFixtures}
        isLoading={isDataLoading}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-4 sm:px-6 py-6 flex flex-col justify-between">
        {/* Messages or Welcome State */}
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center py-8 text-center max-w-2xl mx-auto space-y-8 animate-fade-in">
            {/* Hero Pill */}
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-200 text-xs font-semibold text-indigo-700 shadow-2xs">
              <Sparkles className="h-3.5 w-3.5" />
              <span>Talent AP Mega Hackathon 2026 • Retail Track (Problem Statement R3)</span>
            </div>

            {/* Title & Tagline */}
            <div>
              <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
                The Shopping Assistant That{" "}
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-700 via-indigo-600 to-violet-600">
                  Doesn't Lie
                </span>
              </h2>
              <p className="text-sm sm:text-base text-slate-600 mt-3 leading-relaxed">
                Traditional AI shopping assistants invent prices, stock, and policies.{" "}
                <strong>TruthCart AI</strong> answers only from verified catalogue records and store policies. If evidence is insufficient, it refuses or clarifies rather than guesses.
              </p>
            </div>

            {/* Core Pillars */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5 w-full text-left">
              <div className="p-4 rounded-xl bg-white border border-slate-200/90 shadow-2xs">
                <span className="text-xs font-bold text-indigo-700 block mb-1">
                  1. Catalogue As Truth
                </span>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Prices, availability, and specs come exclusively from verified ground-truth records.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-white border border-slate-200/90 shadow-2xs">
                <span className="text-xs font-bold text-indigo-700 block mb-1">
                  2. Citation Enforcement
                </span>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Every factual claim includes a server-validated citation link <code className="text-[10px] bg-slate-100 px-1 py-0.5 rounded">[PRODUCT:ID]</code>.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-white border border-slate-200/90 shadow-2xs">
                <span className="text-xs font-bold text-indigo-700 block mb-1">
                  3. Deterministic Engine
                </span>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Answers, clarifies, or refuses deterministically. The LLM cannot override evidence decisions.
                </p>
              </div>
            </div>

            {/* Suggested Example Queries */}
            <div className="w-full text-left space-y-2.5 pt-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400 block text-center">
                Try Example Queries (Clearly Labelled Synthetic Fixtures)
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {samplePrompts.map((p, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(p.query)}
                    className="p-3 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-left transition-all hover:border-indigo-300 shadow-2xs group flex items-center justify-between cursor-pointer"
                  >
                    <div>
                      <span className="text-[10px] font-semibold uppercase text-indigo-600 block">
                        {p.label}
                      </span>
                      <span className="text-xs font-medium text-slate-800">
                        "{p.query}"
                      </span>
                    </div>
                    <ArrowRight className="h-3.5 w-3.5 text-slate-400 group-hover:text-indigo-600 transition-colors shrink-0 ml-2" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto space-y-4 pb-4">
            {messages.map((msg) => (
              <ChatMessage
                key={msg.id}
                message={msg}
                onOpenEvidence={handleOpenEvidence}
                onSelectSuggestion={(sug) => handleSendMessage(sug)}
              />
            ))}

            {isLoading && (
              <div className="flex justify-start items-center space-x-3 py-2 animate-fade-in">
                <div className="h-8 w-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center shrink-0 animate-pulse">
                  <RefreshCw className="h-4 w-4 animate-spin" />
                </div>
                <div className="bg-white border border-slate-200 rounded-xl px-4 py-2.5 shadow-2xs text-xs text-slate-600 flex items-center space-x-2">
                  <span>Verifying ground truth evidence with Evidence Engine...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}

        {/* Error Alert if any */}
        {error && (
          <div className="mb-3 bg-rose-50 border border-rose-200 rounded-xl p-3 text-xs text-rose-800 flex items-center space-x-2">
            <ShieldAlert className="h-4 w-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Input Bar Form */}
        <div className="pt-3 sticky bottom-0 bg-slate-50 pb-2">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center space-x-2 bg-white rounded-2xl border border-slate-300 p-2 shadow-sm focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-100 transition-all"
          >
            <input
              type="text"
              id="shopping-query-input"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Ask about products, specifications, prices, or store policies..."
              disabled={isLoading}
              className="flex-1 px-3 py-1.5 text-sm bg-transparent outline-none text-slate-900 placeholder:text-slate-400"
            />
            <button
              type="submit"
              id="send-query-btn"
              disabled={!inputMessage.trim() || isLoading}
              className="h-10 w-10 rounded-xl bg-gradient-to-r from-blue-700 to-indigo-600 hover:from-blue-800 hover:to-indigo-700 disabled:from-slate-300 disabled:to-slate-300 text-white flex items-center justify-center transition-all shadow-xs cursor-pointer disabled:cursor-not-allowed shrink-0"
              title="Send shopping query"
            >
              {isLoading ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4 stroke-[2.2]" />
              )}
            </button>
          </form>
          <div className="text-center mt-2">
            <p className="text-[11px] text-slate-400">
              TruthCart AI operates offline on local CPU models. No external API calls are made.
            </p>
          </div>
        </div>
      </main>

      {/* Evidence Drawer */}
      <EvidenceDrawer
        evidence={selectedEvidence?.evidence || null}
        isOpen={isEvidenceOpen}
        onClose={() => setIsEvidenceOpen(false)}
        latencyMs={selectedEvidence?.latencyMs}
        retrievalStatus={selectedEvidence?.retrievalStatus}
        modelStatus={selectedEvidence?.modelStatus}
      />

      {/* Benchmark / Evaluation Suite Modal */}
      <EvaluationModal
        isOpen={isEvaluationOpen}
        onClose={() => setIsEvaluationOpen(false)}
      />
    </div>
  );
}

export default App;
