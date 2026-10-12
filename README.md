# Correction Scope Lab

A small experiment about learning from human corrections in an AI-assisted quoting workflow.

## The question

A sales rep substitutes a different plywood brand because the requested brand is unavailable at one branch. Should that correction affect the customer's next quote?

Not necessarily. The correction could describe a temporary stockout, a one-off exception, or an approved preference. Remembering the substitution without its context could turn a reasonable exception into a persistent mistake.

This project compares two deliberately simple policies over synthetic examples.

* **Baseline:** reuse any prior substitution for the same requested SKU.
* **Scope evaluator:** consider the customer, branch, validity dates, policy version, reason for correction, availability, and whether a preference was explicitly approved.

The evaluator returns `REUSE`, `REVIEW`, or `IGNORE` with a reason and the source order that supplied the correction. `REVIEW` is not automatic permission to change the order.

## Run

```bash
python -m pytest -q
python run_lab.py
```

The runner prints disagreements with **hand-authored fixture labels**. These are checks of intended behavior, not evidence of accuracy on real distributor data. The baseline is intentionally naive, and the examples are constructed to expose its limitations.

## Design decisions

Corrections are records of what happened, not universal rules. A source order and correction ID preserve lineage. Effective dates and policy versions make validity explicit. A temporary stockout never becomes a durable customer preference merely because the same substitution was accepted once. When a policy changes or the substitution requires new approval, the evaluator asks for review instead of guessing.

The experiment treats `approved_as_preference` as trusted input. In a real workflow, that flag would need to come from an authorized human action with an audit record, not an LLM inference.

## What this does not solve

No product matching, price calculation, ERP integration, concurrency, or real model inference. It does not determine the correct substitution, infer the correction reason from conversation, or verify whether the salesperson had authority. It assumes clean product IDs, accurate inventory and policy version inputs. It also evaluates one correction at a time; competing corrections and precedence are left out.

A real system would need to evaluate temporal changes against authoritative inventory and contract data, represent explicit approval and revocation, and measure unsafe reuse against independently labeled customer workflows.

This is an independent investigation motivated by public descriptions of AI-assisted order entry, not a representation of Ventura's internal implementation or a claim that Ventura lacks this capability.

## Second experiment: conflicting correction authority

`app/authority.py` extends the original single-correction experiment. A historical substitution is not a standing customer preference simply because a salesperson made it. The evaluator distinguishes observations, sales approvals, and explicitly approved customer directives. It also checks the effective contract version at the order date, requires source references, and keeps explicit supersession relationships.

Two active customer directives for different substitutes block reuse. A newer timestamp does **not** silently overrule an older directive. Only an explicit, valid supersession can remove the old directive from consideration. A contract revision likewise cannot inherit approval from an earlier version without review. This is intentionally conservative: the result is a proposal to reuse, not an order submission.

The first experiment's 10 hand-authored scenarios remain available. The second adds adversarial tests for competing approvals, unauthorized learning, changing contract versions, temporal validity, and provenance. The tests are specification examples, **not** a claim of real-world accuracy or a learned model. No real distributor, customer, or ERP data is included.

**Important limitations:** This lab assumes that source identities, correction scope, policy effective dates, and supersession links have already been correctly established. It does not parse emails, verify that a person has authority to approve a preference, model multiple overlapping contracts, or make ERP writes. An actual deployment would need those controls and evaluation against labeled operational corrections before allowing automatic reuse.

## Adversarial synthetic comparison

Run `python -m app.evaluation` to compare two deliberately simple reuse policies with the scope evaluator on 24 labeled synthetic cases. The cases include cross-customer leakage, temporary substitutions, policy changes, conflicting directives, and supersession.

| Decision policy | Correct / 24 | Unsafe reuse | Unnecessary review | Missed reuse |
| --- | ---: | ---: | ---: | ---: |
| Latest correction with matching SKU | 7 | 17 | 0 | 0 |
| Latest approved correction with matching SKU | 8 | 14 | 2 | 0 |
| Authority-aware scope evaluator | 24 | 0 | 0 | 0 |

Unsafe reuse means returning `REUSE` when the reference label is not `REUSE`. Unnecessary review means returning `REVIEW` when the reference label is `IGNORE`. Missed reuse means not returning `REUSE` when the label is `REUSE`.

**Limits:** These are hand-authored cases labeled using the intended policy semantics, not a blinded external holdout or an estimate of production accuracy. The baselines are deliberately weak. The evaluator's perfect result on these cases is a regression check, not proof of generalization. The next meaningful validation would require real, permissioned distributor decisions with independently adjudicated labels and time-based separation between training and evaluation.
