from app.scenarios import cases
from app.scope import evaluate, naive_reuse, Decision


def main():
    rows = cases()
    baseline_errors = sum((Decision.REUSE if naive_reuse(c, o) else Decision.IGNORE) != expected for _, c, o, expected in rows)
    candidate_errors = sum(evaluate(c, o).decision != expected for _, c, o, expected in rows)
    print(f'Baseline disagreements with fixture labels: {baseline_errors}/{len(rows)}')
    print(f'Scope evaluator disagreements: {candidate_errors}/{len(rows)}')
    for name, correction, order, _ in rows:
        result = evaluate(correction, order)
        print(f'{name:29} {result.decision.value:7} {", ".join(result.reasons)}')


if __name__ == '__main__':
    main()
