"""Offline evaluation of the assistant.

Three scores, tracked across prompt and model changes:

* routing accuracy:       did the question go to the right path?
* SQL execution accuracy: does the generated query return the same result set as the gold query?
                          (compares values, ignoring column names and row order)
* RAG quality (RAGAS):    faithfulness, answer relevancy and context recall on the docs questions

    python -m eval.run_eval                    # all
    python -m eval.run_eval --skip-ragas       # SQL + routing only (cheaper)

Writes eval/report.json and prints a summary table.
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine

from app.config import get_settings
from app.factory import build_assistant
from app.router import route_question
from app.text_to_sql import run_readonly

HERE = Path(__file__).parent


def normalize(rows: list[dict]) -> list[tuple]:
    def norm(v):
        if isinstance(v, float | Decimal):
            return round(float(v), 2)
        return v

    return sorted((tuple(norm(v) for v in r.values()) for r in rows), key=repr)


def eval_sql(assistant, items, engine, timeout_ms) -> list[dict]:
    results = []
    for item in items:
        resp = assistant.ask(item["question"], force_route="sql")
        _, gold_rows = run_readonly(engine, item["gold_sql"], timeout_ms)
        match = resp.error is None and normalize(resp.rows) == normalize(gold_rows)
        results.append({"id": item["id"], "match": match, "sql": resp.sql, "error": resp.error})
        print(f"  {item['id']}: {'PASS' if match else 'FAIL'}")
    return results


def eval_ragas(assistant, items) -> dict:
    from ragas import EvaluationDataset, evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import Faithfulness, LLMContextRecall, ResponseRelevancy

    from app.llm import get_chat_model, get_embeddings

    rows = []
    for item in items:
        resp = assistant.ask(item["question"], force_route="docs")
        rows.append(
            {
                "user_input": item["question"],
                "response": resp.answer,
                "retrieved_contexts": resp.contexts,
                "reference": item["reference"],
            }
        )
    dataset = EvaluationDataset.from_list(rows)
    result = evaluate(
        dataset,
        metrics=[Faithfulness(), ResponseRelevancy(), LLMContextRecall()],
        llm=LangchainLLMWrapper(get_chat_model()),
        embeddings=LangchainEmbeddingsWrapper(get_embeddings()),
    )
    df = result.to_pandas()
    return {col: round(float(df[col].mean()), 3) for col in df.columns if df[col].dtype.kind == "f"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-ragas", action="store_true")
    args = parser.parse_args()

    s = get_settings()
    items = [json.loads(line) for line in (HERE / "questions.jsonl").read_text().splitlines() if line.strip()]
    assistant = build_assistant(s)
    engine = create_engine(s.readonly_database_url)

    print("Routing")
    routing = [route_question(i["question"], assistant.llm) == i["route"] for i in items]

    print("SQL execution accuracy")
    sql_items = [i for i in items if i["route"] == "sql"]
    sql_results = eval_sql(assistant, sql_items, engine, s.sql_timeout_ms)

    report = {
        "model": s.openai_chat_model if s.llm_provider == "openai" else s.bedrock_chat_model,
        "routing_accuracy": round(sum(routing) / len(routing), 3),
        "sql_execution_accuracy": round(sum(r["match"] for r in sql_results) / len(sql_results), 3),
        "sql_details": sql_results,
    }

    if not args.skip_ragas:
        print("RAGAS")
        report["ragas"] = eval_ragas(assistant, [i for i in items if i["route"] == "docs"])

    (HERE / "report.json").write_text(json.dumps(report, indent=2, default=str))
    print("\nSummary")
    print(f"  routing accuracy        {report['routing_accuracy']:.0%}")
    print(f"  SQL execution accuracy  {report['sql_execution_accuracy']:.0%}")
    for k, v in report.get("ragas", {}).items():
        print(f"  {k:<24}{v}")


if __name__ == "__main__":
    main()
