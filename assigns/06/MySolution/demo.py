"""Run with python -B -m MySolution.demo from assigns/06/."""

from __future__ import annotations

import argparse
from pathlib import Path

if __package__:
    from .compiler import compile_expr
    from .decoders import observe
    from .examples import examples
    from .target_ast import evaluate, pretty
else:
    from compiler import compile_expr
    from decoders import observe
    from examples import examples
    from target_ast import evaluate, pretty


def _nonnegative(text: str) -> int:
    number = int(text)
    if number < 0:
        raise argparse.ArgumentTypeError("budget must be nonnegative")
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-budget", type=_nonnegative, default=50000)
    parser.add_argument("--observation-budget", type=_nonnegative, default=50000)
    parser.add_argument("--divergence-budget", type=_nonnegative, default=200)
    parser.add_argument("--output-dir", type=Path,
                        default=Path(__file__).resolve().parent / "demo_output")
    args = parser.parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    failures = 0
    for example in examples():
        lines.extend([f"{example.name}: {example.description}",
                      f"  Source AST: {example.expression!r}",
                      f"  Expected: {example.expected!r}; kind: {example.kind!r}"])
        term = compile_expr(example.expression)
        path = args.output_dir / f"{example.name}.lambda.txt"
        path.write_text(pretty(term) + "\n", encoding="utf-8")
        lines.append(f"  Generated pure term: {path.resolve()}")
        budget = args.divergence_budget if example.kind is None else args.execution_budget
        if example.kind is None:
            # Never run a known divergent source example through unbounded evaluation.
            execution = evaluate(term, budget)
            lines.append("  Source evaluation: skipped for divergent example")
            observation = None
            passed = not execution.completed
        else:
            source_result = evaluate(example.expression)
            lines.append(f"  Source result (shared evaluator): {source_result.value!r}")
            result = observe(term, example.kind, budget, args.observation_budget)
            execution, observation = result.execution, result.observation
            passed = (source_result.value == example.expected and observation is not None
                      and observation.completed and observation.value == example.expected)
        lines.append(f"  Execution: {execution.status}; beta-value steps: {execution.steps}; budget: {budget}")
        if observation is None:
            lines.append(f"  Observation: skipped; beta-value steps: 0; budget: {args.observation_budget}")
            lines.append("  Decoded answer: unavailable (execution budget exhausted)")
        else:
            lines.append(f"  Observation: {observation.status}; beta-value steps: {observation.steps}; budget: {args.observation_budget}")
            lines.append(f"  Decoded answer: {observation.value!r}")
            if observation.message:
                lines.append(f"  Diagnostic: {observation.message}")
        lines.extend([f"  Check: {'PASS' if passed else 'FAIL'}", ""])
        failures += not passed
    lines.append("Budget exhaustion means more steps are needed; it does not prove nontermination.")
    lines.append(f"{len(examples()) - failures}/{len(examples())} examples passed.")
    report = "\n".join(lines) + "\n"
    (args.output_dir / "report.txt").write_text(report, encoding="utf-8")
    print(report, end="")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
