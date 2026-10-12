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

No product matching, price calculation, ERP integration, concurrency, or real model inference. It does not determine the correct substitution, infer the correction reason from conversation, or verify whether the salesperson had authority. It assumes clean product IDs, accurate inventory and policy version inputs. The original single-correction evaluator does not handle competing corrections; the second experiment below addresses some precedence cases.

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

## Second-stage comparison

Run `python -m app.evaluation` to see the original 24 specification cases and a separate set of eight *composed* synthetic cases. The additional baseline checks customer, branch, product, effective dates, and availability but deliberately omits authority and contract precedence.

| Policy | Original correct / 24 | Original unsafe reuse | Composed correct / 8 | Composed unsafe reuse |
| --- | ---: | ---: | ---: | ---: |
| Context-aware baseline | 11 | 13 | 4 | 3 |
| Authority-aware evaluator | 24 | 0 | 8 | 0 |

These are **not** independently labeled real customer examples. Both sets were constructed by the project author and express its intended business semantics. The second set combines conditions not isolated in the original examples, but is not a blinded holdout. The reported numbers are regression checks, not evidence of production accuracy or model generalization. In particular, this experiment does not measure how often the inputs themselves misstate authority, product identity, or effective contract terms.

### Remaining failure modes

A source reference and an `approved_by` string do not prove that an approver was authorized. A malicious or mistaken input can therefore appear to be a valid customer directive. The resolver also assumes trusted policy snapshots and clean correction identities. It does not implement a revocation registry, enforce a full directed acyclic supersession graph, or account for cost and risk differences between automatic reuse and human review.

Before deployment, the highest-value test would use permissioned historical distributor corrections, verified approval provenance, time-separated evaluation, and a loss-weighted metric for wrong automatic substitutions versus avoidable reviews.

## Source-linked request dependency experiment

`app/request_context.py` uses the **public illustrated RFQ** on [Ventura's product page](https://ventura.ai/product/) as a reference: a request for 120 sheets of 23/32 plywood and 60 pieces of SPF 2×4 lumber, where the lumber length is unspecified. The example and missing-length issue are public; the source IDs, revision numbers, derived choice, and variations below are **synthetic**. This is not Ventura's code or a reproduction of its implementation.

The additional experiment models a derived catalog choice with explicit dependencies on source facts and the request, catalog, and policy revisions used to derive it. A missing length, contradictory length, revised request, changed catalog, or changed operating rule makes the choice ineligible for reuse until re-evaluated. An unrelated note does not change the result. Each result carries source references and reasons. This is a structured-input experiment, not an email/PDF parser or product matcher.

Run `python -m pytest -q` for these regression cases. The experiment deliberately does **not** infer product identity, decide what counts as an equivalent product, verify a human approver's identity, or price a quote. It illustrates a dependency and provenance problem that could arise in this type of workflow.

## Adversarial review and next validation

A review found a genuine authority problem in the first implementation: a record marked as an observation could explicitly supersede a customer directive, removing it from consideration. Supersession now requires a newer, approved customer directive, and a regression test exercises an unauthorized attempt. This check still relies on the correctness of the supplied authority metadata.

The comparison results above remain **author-labeled synthetic checks**. They should not be interpreted as accuracy estimates. A more meaningful independent evaluation would require permissioned real quote revisions, independent labels, time-based splitting, and an explicit cost model for wrong substitutions versus human review. The public product example grounds the *shape of one input*, not the empirical distribution of real errors.
