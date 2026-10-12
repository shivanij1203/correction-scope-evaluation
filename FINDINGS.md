# Findings and limitations

This note separates what can be verified from what remains hypothetical.

## Evidence

- Ventura's product page publicly illustrates an RFQ with 120 sheets of 23/32 plywood and 60 pieces of SPF 2x4, with the lumber length missing. https://ventura.ai/product/
- Ventura's quoting and order-entry pages describe customer/branch context, product matching, operating rules, exception review, and ERP handoff. https://ventura.ai/solutions/ai-quoting/ and https://ventura.ai/solutions/ai-order-entry/

These pages ground the shape of the inputs. Nothing here describes Ventura's internal implementation.

## Experiment and observation

The main finding is that a historical correction should not automatically become a reusable customer preference. A stockout substitution, a one-time change, or a correction made under an older contract can look like a preference if only the latest correction is considered.

The original correction-scope experiment is a structured-policy model, not a learned system. A synthetic comparison shows its intended behavior, but labels and rules are not independent. A separate source-linked example demonstrates that derived quote choices can become stale after revisions to source facts, catalog, or operating rules.

An adversarial code review exposed a specific authorization flaw: a lower-authority observation could supersede a valid customer directive. This was corrected and covered by a regression test.

## Open questions

1. **Where does authority come from?** Currently it is supplied metadata. There is no verification of approver identity or delegated permission.
2. **Are the examples representative?** No. One publicly illustrated RFQ grounds the data shape; all transformations and labels are synthetic.
3. **Does a revision always invalidate a choice?** The model uses coarse version dependencies and may trigger unnecessary recomputation. A production dependency graph would need field-level and entity-level change detection.
4. **What does REVIEW cost?** Not measured. A business evaluation must weigh incorrect auto-reuse against review volume and delay.
5. **Does this solve product matching?** No. Catalog resolution, dimensions, units, substitutions, and price are deliberately outside scope.
6. **What would convince a customer?** Independently adjudicated historical corrections and revised RFQs, sampled across branches and time, with metrics for unsafe reuse, missed safe reuse, and review workload.

## Conclusion

Correction reuse depends on scope, authority, and the contract in effect, and derived quote choices need explicit links to the facts and revisions behind them. On the synthetic cases, the authority-aware evaluator avoids the unsafe reuse the simpler baselines produce.

Unverified: the cases are author-labeled, so results are regression checks, not accuracy measurements. Approval authority is trusted metadata, revision invalidation is coarse-grained, and review cost, product matching, and real ERP behavior are not modeled.
