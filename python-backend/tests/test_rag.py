"""
Tests for RAG (Retrieval-Augmented Generation) knowledge base.

Tests cover: document loading, text splitting, retrieval with mocked embeddings,
source attribution, no-result fallback, and reindex flow.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from commerce.tools import rag_retrieve_tool
from rag.loader import load_documents
from rag.splitter import split_markdown
from rag.store import retrieve


# =============================================================================
#  1. Document Loading
# =============================================================================


class TestDocumentLoading:
    def test_loads_all_documents(self):
        docs = load_documents()
        assert len(docs) == 12, f"Expected 12 docs, got {len(docs)}"

    def test_documents_have_required_fields(self):
        docs = load_documents()
        for d in docs:
            assert "path" in d
            assert "content" in d
            assert "category" in d
            assert "title" in d
            assert len(d["content"]) > 50, f"{d['path']} content too short"

    def test_categories(self):
        docs = load_documents()
        categories = {d["category"] for d in docs}
        assert "products" in categories
        assert "policies" in categories
        assert "after_sales" in categories
        assert "faq" in categories


# =============================================================================
#  2. Text Splitting
# =============================================================================


class TestTextSplitting:
    def test_splits_long_content(self):
        # Create multiline content with paragraph breaks to trigger splitting
        lines = []
        for i in range(20):
            lines.append(f"Paragraph {i}: " + "content about e-commerce support. " * 15)
        content = "\n\n".join(lines)  # ~20 paragraphs with explicit breaks
        chunks = split_markdown(content, max_chars=500, overlap=50)
        assert len(chunks) >= 2

    def test_short_content_returns_single_chunk(self):
        content = "This is a short paragraph about warranty."
        chunks = split_markdown(content)
        assert len(chunks) == 1
        assert "warranty" in chunks[0]

    def test_preserves_markdown_headings(self):
        content = "## Section A\nContent A here.\n\n## Section B\nContent B here."
        chunks = split_markdown(content, max_chars=500)
        # Should preserve heading structure
        assert any("Section A" in c for c in chunks)
        assert any("Section B" in c for c in chunks)

    def test_all_knowledge_docs_split(self):
        docs = load_documents()
        for d in docs:
            chunks = split_markdown(d["content"])
            assert len(chunks) >= 1, f"{d['path']} produced 0 chunks"
            for c in chunks:
                assert len(c) > 0, f"{d['path']} has empty chunk"


# =============================================================================
#  3. Retrieval Tests (with mocked embeddings)
# =============================================================================


def _make_mock_results(query: str) -> list[dict]:
    """Simulate what store.retrieve would return."""
    return [
        {
            "content": "自用户签收商品之日起 7 天内，商品保持完好且不影响二次销售，可申请无理由退货。",
            "source": "policies/return_policy.md",
            "title": "7 天无理由退货政策",
            "category": "policies",
            "score": 0.85,
        },
        {
            "content": "退货签收后1-3个工作日退款到原支付账户。",
            "source": "after_sales/refund_timeline.md",
            "title": "退款时效说明",
            "category": "after_sales",
            "score": 0.72,
        },
    ]


class TestRetrievalWithMock:
    @patch("rag.store.retrieve")
    @pytest.mark.asyncio
    async def test_warranty_retrieval(self, mock_retrieve):
        """Warranty question should retrieve warranty document."""
        mock_retrieve.return_value = [
            {
                "content": "数码配件保修6-12个月，智能穿戴保修24个月。",
                "source": "policies/warranty.md",
                "title": "商品保修政策",
                "category": "policies",
                "score": 0.88,
            }
        ]
        ctx = MagicMock()
        ctx.tool_name = "rag_retrieve"
        ctx.tool_call_id = "test"
        ctx.tool_arguments = '{"question": "蓝牙耳机保修多久"}'
        # Also set necessary fields for error handling
        ctx.run_config = None

        result = await rag_retrieve_tool.on_invoke_tool(
            ctx, '{"question": "蓝牙耳机保修多久"}'
        )
        assert "保修" in result
        assert "policies/warranty.md" in result

    @patch("rag.store.retrieve")
    @pytest.mark.asyncio
    async def test_refund_policy_retrieval(self, mock_retrieve):
        """Refund question should retrieve refund policy."""
        mock_retrieve.return_value = [
            {
                "content": "自用户签收商品之日起 7 天内可申请无理由退货。",
                "source": "policies/return_policy.md",
                "title": "7 天无理由退货政策",
                "category": "policies",
                "score": 0.91,
            }
        ]
        ctx = MagicMock()
        ctx.tool_name = "rag_retrieve"
        ctx.tool_call_id = "test"
        ctx.tool_arguments = '{"question": "退货政策是什么"}'
        ctx.run_config = None

        result = await rag_retrieve_tool.on_invoke_tool(
            ctx, '{"question": "退货政策是什么"}'
        )
        assert "7 天" in result or "无理由" in result
        assert "policies/return_policy.md" in result

    @patch("rag.store.retrieve")
    @pytest.mark.asyncio
    async def test_irrelevant_question_triggers_fallback(self, mock_retrieve):
        """Completely irrelevant question should return fallback guidance."""
        mock_retrieve.return_value = []  # No results
        ctx = MagicMock()
        ctx.tool_name = "rag_retrieve"
        ctx.tool_call_id = "test"
        ctx.tool_arguments = '{"question": "今天天气怎么样"}'
        ctx.run_config = None

        result = await rag_retrieve_tool.on_invoke_tool(
            ctx, '{"question": "今天天气怎么样"}'
        )
        assert "未在知识库中找到" in result or "未找到" in result
        assert "400-888-6666" in result

    @patch("rag.store.retrieve")
    @pytest.mark.asyncio
    async def test_source_attribution_returned(self, mock_retrieve):
        """Results must include source file paths."""
        mock_retrieve.return_value = [
            {
                "content": "电池保修12个月，但自然衰减不在保修范围内。",
                "source": "products/power_bank.md",
                "title": "快充移动电源 20000mAh 商品说明",
                "category": "products",
                "score": 0.79,
            }
        ]
        ctx = MagicMock()
        ctx.tool_name = "rag_retrieve"
        ctx.tool_call_id = "test"
        ctx.tool_arguments = '{"question": "充电宝保修多久"}'
        ctx.run_config = None

        result = await rag_retrieve_tool.on_invoke_tool(
            ctx, '{"question": "充电宝保修多久"}'
        )
        assert "products/power_bank.md" in result
        assert "移动电源" in result or "保修" in result


# =============================================================================
#  4. Reindex / Reload Tests
# =============================================================================


class TestReindex:
    def test_reload_documents_consistent(self):
        """Loading documents twice should return the same count."""
        docs1 = load_documents()
        docs2 = load_documents()
        assert len(docs1) == len(docs2)

    def test_chunks_reproducible(self):
        """Same content should always produce same chunk count."""
        docs = load_documents()
        for d in docs:
            chunks1 = split_markdown(d["content"])
            chunks2 = split_markdown(d["content"])
            assert len(chunks1) == len(chunks2), (
                f"{d['path']}: chunk count differs ({len(chunks1)} vs {len(chunks2)})"
            )


# =============================================================================
#  5. Knowledge Base Integrity
# =============================================================================


class TestKnowledgeBaseIntegrity:
    def test_policies_have_key_info(self):
        """Each policy document should contain key information."""
        docs = load_documents()

        warranty = next(d for d in docs if "warranty" in d["path"])
        assert "保修" in warranty["content"]

        return_policy = next(d for d in docs if "return_policy" in d["path"])
        assert "7 天" in return_policy["content"] or "7天" in return_policy["content"]

        shipping = next(d for d in docs if "shipping" in d["path"])
        assert "包邮" in shipping["content"] or "配送" in shipping["content"]

    def test_product_docs_have_specs(self):
        """Product documents should contain specifications."""
        docs = load_documents()

        earphone = next(d for d in docs if "earphone" in d["path"])
        assert "蓝牙" in earphone["content"] or "降噪" in earphone["content"]

        watch = next(d for d in docs if "watch" in d["path"])
        assert "AMOLED" in watch["content"] or "续航" in watch["content"]

    def test_faq_docs_have_contact_info(self):
        """FAQ documents should reference customer support."""
        docs = load_documents()
        handoff = next(d for d in docs if "handoff" in d["path"])
        assert "400-888-6666" in handoff["content"]
