import time
from fastapi import APIRouter, HTTPException
from app.schemas.request import ChatRequest
from app.schemas.response import ChatResponse
from app.llm.query_understanding import query_understanding
from app.retrieval.hybrid_retriever import hybrid_retriever
from app.evidence_engine.decision_engine import decision_engine
from app.llm.response_generator import response_generator
from app.conversation.context_manager import context_manager
from app.core.logging_config import SafeLogger

router = APIRouter(tags=["Chat"])

@router.post("/chat", response_model=ChatResponse)
def handle_chat(req: ChatRequest) -> ChatResponse:
    start_time = time.perf_counter()
    msg = req.message.strip()

    if not msg:
        raise HTTPException(status_code=400, detail="Query message cannot be empty.")

    # 1. Multi-turn Session Management
    session = context_manager.get_or_create_session(req.conversation_id)

    # 2. Query Understanding
    parsed = query_understanding.parse(msg)

    # 3. Constraint Tracking: Combine current parsed query with conversation context
    # Only inherit prior constraints if current query is not a completely new standalone query
    combined_params = dict(parsed)
    if not parsed.get("product_id") and not parsed.get("is_policy_query"):
        prior = session.constraints.to_dict()
        for k in ("category", "max_price", "min_price", "brand", "color", "material", "stock_required"):
            if combined_params.get(k) is None and prior.get(k) is not None:
                combined_params[k] = prior[k]

        # Update session with newly extracted parameters
        session.constraints.update(parsed)

    # 4. Hybrid Retrieval
    product_cands, policy_cand = hybrid_retriever.retrieve(
        query=msg,
        structured_params=combined_params
    )

    # 5. Deterministic Evidence Engine
    evidence_obj = decision_engine.evaluate(
        query=msg,
        parsed_query=combined_params,
        product_candidates=product_cands,
        policy_candidate=policy_cand
    )

    # 6. Evidence-Grounded Response Generation
    matched_prods = [c.data for c in product_cands]
    response_text, products, citations, model_status = response_generator.generate_response(
        evidence_obj=evidence_obj,
        matched_products=matched_prods
    )

    latency_ms = (time.perf_counter() - start_time) * 1000.0

    retrieval_summary = f"{len(product_cands)} products retrieved"
    if policy_cand:
        retrieval_summary += f", policy [{policy_cand.source_id}] matched"

    chat_resp = ChatResponse(
        decision=evidence_obj.decision,
        response_text=response_text,
        products=products,
        citations=citations,
        evidence=evidence_obj,
        clarification_question=evidence_obj.clarification_question,
        refusal_reason=evidence_obj.refusal_reason,
        retrieval_status=retrieval_summary,
        model_status=model_status,
        latency_ms=round(latency_ms, 2),
        conversation_id=session.conversation_id
    )

    # Record turn in session
    session.add_turn(msg, chat_resp.model_dump())

    return chat_resp
