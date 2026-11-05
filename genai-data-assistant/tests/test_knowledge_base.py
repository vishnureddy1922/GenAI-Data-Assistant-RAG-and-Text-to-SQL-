from pathlib import Path

from app.knowledge_base import DocsQA, chunk_id, load_markdown_chunks
from tests.conftest import FakeRetriever, fake_llm

KB = Path(__file__).resolve().parents[1] / "knowledge_base"


def test_chunks_keep_source_and_section():
    chunks = load_markdown_chunks(KB)
    assert len(chunks) > 10
    sources = {c.metadata["source"] for c in chunks}
    assert {"metric_definitions.md", "data_dictionary.md", "data_policies.md", "faq.md"} <= sources
    revenue = [c for c in chunks if c.metadata["section"].endswith("Revenue")]
    assert revenue and "completed" in revenue[0].page_content


def test_chunk_ids_are_stable_and_unique():
    a = load_markdown_chunks(KB)
    b = load_markdown_chunks(KB)
    assert [chunk_id(d) for d in a] == [chunk_id(d) for d in b]
    assert len({chunk_id(d) for d in a}) == len(a)


def test_docs_qa_returns_answer_with_sources():
    retriever = FakeRetriever()
    qa = DocsQA(fake_llm("Revenue counts completed orders only [1]."), retriever, k=2)
    result = qa.run("How is revenue defined?")

    assert "[1]" in result.answer
    assert result.sources[0] == {"ref": 1, "source": "metric_definitions.md", "section": "Metric definitions > Revenue"}
    assert len(result.contexts) == 2
    assert retriever.queries == [("How is revenue defined?", 2)]


def test_docs_qa_with_no_results():
    result = DocsQA(fake_llm("unused"), FakeRetriever(docs=[])).run("Unknown topic?")
    assert "couldn't find" in result.answer
    assert result.sources == []
