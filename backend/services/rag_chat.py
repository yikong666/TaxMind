"""FAQ/RAG/风险门禁与 LLM 流式生成主链路。"""

import logging

from backend.models.conversation import MessageStatus

logger = logging.getLogger("taxmind.rag_chat")
ANSWER_PROMPT = """你是 TaxMind 财税助手。只能依据给定上下文回答，不得伪造文号。
按结论、适用条件、政策依据、政策文号、适用地区、适用期间、操作步骤、注意事项组织回答。
若依据不足必须明确说明。引用编号必须来自上下文。"""


# 编排器以事件字典输出，HTTP 层只负责转换为 SSE 文本。
class RagChatService:
    def __init__(self, conversations, understanding, faq, retrieval, llm):
        self.conversations = conversations
        self.understanding = understanding
        self.faq = faq
        self.retrieval = retrieval
        self.llm = llm

    def stream(self, conversation, owner_id, request):
        # 在写入本轮消息前截取历史，避免把当前空白回答带入模型上下文。
        history = self.conversations.repository.history(conversation.id, request.history_rounds)
        self.conversations.add_user(conversation.id, request.query)
        assistant = self.conversations.add_assistant(
            conversation.id, request.model, request.history_rounds
        )
        yield {
            "event": "session",
            "data": {"conversation_id": conversation.id, "message_id": assistant.id},
        }
        try:
            understood = self.understanding.understand(request.query)
            assistant.risk_level = understood.risk_level.value
            if understood.safety_message:
                yield from self._complete(assistant, understood.safety_message, "guardrail", [])
                return
            if understood.needs_clarification:
                yield from self._complete(
                    assistant, understood.clarification_question, "clarification", []
                )
                return
            faq_result = self.faq.route(owner_id, request.query, request.region, request.query_date)
            if faq_result["matched"]:
                item = faq_result["faq"]
                citation = {
                    k: item.get(k)
                    for k in (
                        "id",
                        "question",
                        "doc_no",
                        "region",
                        "effective_start",
                        "effective_end",
                    )
                }
                yield from self._complete(assistant, item["answer"], "faq", [citation])
                return
            hits = []
            if request.knowledge_base_ids:
                hits = self.retrieval.search(
                    owner_id=owner_id,
                    query=request.query,
                    knowledge_base_ids=request.knowledge_base_ids,
                    region=request.region,
                    query_date=request.query_date,
                    tax_type=understood.tax_type,
                    taxpayer_type=understood.taxpayer_type,
                    top_k=5,
                )
            if not hits:
                yield from self._complete(
                    assistant,
                    "当前知识库中没有找到足够可靠的依据，请补充信息或转人工确认。",
                    "no_context",
                    [],
                )
                return
            citations = [
                {
                    "document_id": h.document_id,
                    "doc_no": h.metadata.get("doc_no"),
                    "region": h.metadata.get("region"),
                    "source_url": h.metadata.get("source_url"),
                    "content": h.text,
                }
                for h in hits
            ]
            context = "\n\n".join(f"[{i + 1}] {h.parent_content}" for i, h in enumerate(hits))
            history_messages = [
                {"role": message.role.value, "content": message.content}
                for message in history
                if message.status == MessageStatus.COMPLETED
            ]
            messages = [
                {"role": "system", "content": ANSWER_PROMPT},
                *history_messages,
                {"role": "user", "content": f"上下文：\n{context}\n\n问题：{request.query}"},
            ]
            full = ""
            yield {"event": "status", "data": {"stage": "generating"}}
            for token in self.llm.stream_answer(
                messages,
                model=request.model,
                temperature=request.temperature,
                top_p=request.top_p,
                max_tokens=request.max_tokens,
            ):
                full += token
                yield {"event": "token", "data": {"text": token}}
            yield from self._complete(assistant, full, "rag", citations, emit_token=False)
        except Exception as exc:
            assistant.status = MessageStatus.FAILED
            assistant.error_message = str(exc)
            self.conversations.repository.save(assistant)
            logger.exception("RAG 流式回答失败 conversation_id=%s", conversation.id)
            yield {"event": "error", "data": {"message": "回答生成失败，请稍后重试"}}

    def _complete(self, message, content, source, citations, emit_token=True):
        if emit_token:
            yield {"event": "token", "data": {"text": content}}
        message.content = content
        message.route_source = source
        message.citations = citations
        message.status = MessageStatus.COMPLETED
        self.conversations.repository.save(message)
        for citation in citations:
            yield {"event": "citation", "data": citation}
        yield {"event": "done", "data": {"message_id": message.id, "route_source": source}}
