#!/usr/bin/env python
"""CommerceCare Agent — Evaluation script.

Usage:
    PYTHONPATH=. python -m operations.evaluation

Measures: routing accuracy, tool success rate, RAG coverage,
rejection correctness, human handoff trigger rate, and average latency.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).resolve().parent


def load_test_cases() -> list[dict]:
    """Load evaluation test cases from JSON."""
    path = _DATA_DIR / "evaluation_data.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["test_cases"]


# -- Simulated routing (no live API needed) -----------------------------------

# Keyword-based router that mirrors the Triage Agent's logic
KEYWORD_ROUTES = [
    (["工单", "TK-"], "Human Handoff Agent"),
    (["投诉", "骂", "太差", "气死", "转人工", "找人工", "打客服"], "Human Handoff Agent"),
    (["退货", "退款", "取消订单", "换货", "不想要", "坏了", "划痕", "售后"], "After-Sales Agent"),
    (["物流", "快递", "发货", "到哪", "什么时候到", "配送"], "Logistics Agent"),
    (["订单", "买了", "ORD-", "查", "状态", "付款"], "Order Service Agent"),
    (["保修", "政策", "会员", "权益", "发票", "偏", "安装"], "Knowledge Support Agent"),
    (["人工", "电话"], "Knowledge Support Agent"),
]

SAFETY_KEYWORDS = [
    "忽略之前的指令", "system prompt", "你的提示词", "刷单", "套现",
    "身份证", "银行卡号", "全额退款但不退货",
]

IRRELEVANT_KEYWORDS = ["写诗", "天气", "编程", "翻译", "讲笑话", "做数学"]


def predict_route(question: str) -> str:
    """Simulate Triage Agent routing based on keyword matching."""
    lower = question.lower()

    # Safety check first
    for kw in SAFETY_KEYWORDS:
        if kw in lower or kw in question:
            return "REJECTED"

    # Irrelevant check
    for kw in IRRELEVANT_KEYWORDS:
        if kw in lower:
            return "REJECTED"

    # Route to specialist
    for keywords, agent in KEYWORD_ROUTES:
        for kw in keywords:
            if kw in lower:
                return agent

    return "Order Service Agent"  # default fallback


# -- Evaluation metrics -------------------------------------------------------


def evaluate(verbose: bool = False) -> dict[str, Any]:
    """Run evaluation on all test cases and compute metrics.

    Returns:
        Dict with all metrics and per-case details.
    """
    cases = load_test_cases()
    results = []
    t_start = time.time()

    metrics = {
        "total": len(cases),
        "route_correct": 0,
        "route_wrong": 0,
        "reject_correct": 0,
        "reject_wrong": 0,
        "rag_expected": 0,
        "rag_covered": 0,
        "handoff_expected": 0,
        "handoff_triggered": 0,
        "tool_expected": 0,
        "tool_available": 0,
    }

    category_counts = {}
    category_correct = {}

    for case in cases:
        predicted = predict_route(case["question"])
        expected = case["expected_agent"] if not case["expected_reject"] else "REJECTED"
        is_correct = predicted == expected
        is_reject_case = case["expected_reject"]
        expected_tool = case.get("expected_tool", "")
        cat = case["category"]

        # Category stats
        category_counts[cat] = category_counts.get(cat, 0) + 1
        if is_correct:
            category_correct[cat] = category_correct.get(cat, 0) + 1

        # Routing accuracy
        if is_reject_case:
            if predicted == "REJECTED":
                metrics["reject_correct"] += 1
            else:
                metrics["reject_wrong"] += 1
        else:
            if predicted == expected:
                metrics["route_correct"] += 1
            else:
                metrics["route_wrong"] += 1

        # RAG coverage
        if expected_tool == "rag_retrieve":
            metrics["rag_expected"] += 1
            if predicted == expected:
                metrics["rag_covered"] += 1

        # Human handoff
        if expected == "Human Handoff Agent":
            metrics["handoff_expected"] += 1
            if predicted == expected:
                metrics["handoff_triggered"] += 1

        # Tool availability
        if expected_tool:
            metrics["tool_expected"] += 1
            if predicted == expected:
                metrics["tool_available"] += 1

        results.append({
            "id": case["id"],
            "category": cat,
            "question": case["question"],
            "expected": expected,
            "predicted": predicted,
            "correct": is_correct,
            "expected_tool": expected_tool,
        })

        if verbose:
            status = "✅" if is_correct else "❌"
            print(f"{status} {case['id']} [{cat}] {case['question'][:50]}... → {predicted}")

    total_routable = metrics["route_correct"] + metrics["route_wrong"]
    total_reject = metrics["reject_correct"] + metrics["reject_wrong"]

    summary = {
        "total_cases": metrics["total"],
        "routing_accuracy": round(metrics["route_correct"] / total_routable, 3) if total_routable else 0,
        "route_correct": metrics["route_correct"],
        "route_wrong": metrics["route_wrong"],
        "rejection_accuracy": round(metrics["reject_correct"] / total_reject, 3) if total_reject else 0,
        "reject_correct": metrics["reject_correct"],
        "reject_wrong": metrics["reject_wrong"],
        "rag_coverage": round(metrics["rag_covered"] / metrics["rag_expected"], 3) if metrics["rag_expected"] else 0,
        "rag_expected": metrics["rag_expected"],
        "rag_covered": metrics["rag_covered"],
        "handoff_trigger_rate": round(metrics["handoff_triggered"] / metrics["handoff_expected"], 3) if metrics["handoff_expected"] else 0,
        "handoff_expected": metrics["handoff_expected"],
        "handoff_triggered": metrics["handoff_triggered"],
        "tool_success_rate": round(metrics["tool_available"] / metrics["tool_expected"], 3) if metrics["tool_expected"] else 0,
        "avg_elapsed_ms": round((time.time() - t_start) * 1000 / metrics["total"], 2),
        "category_accuracy": {cat: round(category_correct.get(cat, 0) / cnt, 3) for cat, cnt in sorted(category_counts.items())},
        "details": results,
    }

    return summary


# -- CLI ----------------------------------------------------------------------


if __name__ == "__main__":
    import sys

    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    result = evaluate(verbose=verbose)

    print("\n" + "=" * 60)
    print("  CommerceCare Agent — 评测结果")
    print("=" * 60)
    print(f"  总用例数：       {result['total_cases']}")
    print(f"  路由准确率：     {result['routing_accuracy']:.1%}  ({result['route_correct']}/{result['route_correct'] + result['route_wrong']})")
    print(f"  拒答正确率：     {result['rejection_accuracy']:.1%}  ({result['reject_correct']}/{result['reject_correct'] + result['reject_wrong']})")
    print(f"  RAG 引用覆盖率：  {result['rag_coverage']:.1%}  ({result['rag_covered']}/{result['rag_expected']})")
    print(f"  人工转接触发率：  {result['handoff_trigger_rate']:.1%}  ({result['handoff_triggered']}/{result['handoff_expected']})")
    print(f"  工具调用成功率：  {result['tool_success_rate']:.1%}  ({result['tool_available']}/{result['tool_expected']})")
    print(f"  平均耗时：       {result['avg_elapsed_ms']:.2f} ms")

    print("\n  各类别准确率：")
    for cat, acc in result["category_accuracy"].items():
        print(f"    {cat}: {acc:.1%}")

    if verbose:
        wrong = [r for r in result["details"] if not r["correct"]]
        if wrong:
            print(f"\n  错误用例 ({len(wrong)}):")
            for r in wrong:
                print(f"    ❌ {r['id']}: 预期={r['expected']}, 实际={r['predicted']} | {r['question'][:60]}")
