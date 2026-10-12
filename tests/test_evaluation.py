from app.evaluation import challenge_cases, metrics, naive_last_correction, naive_latest_approved, scoped, scoped_baseline, combined_challenges

def test_challenge_labels_and_rationales_are_complete():
    cases = challenge_cases()
    assert len(cases) == 24
    assert len({c.name for c in cases}) == len(cases)
    assert all(c.rationale for c in cases)

def test_scope_evaluator_against_labeled_synthetic_cases():
    cases = challenge_cases()
    mismatches = [(c.name, scoped(c), c.expected) for c in cases if scoped(c) != c.expected]
    assert not mismatches, mismatches

def test_baselines_have_unsafe_reuse():
    cases = challenge_cases()
    assert metrics(cases, naive_last_correction)["unsafe_reuse"] > 0
    assert metrics(cases, naive_latest_approved)["unsafe_reuse"] > 0

def test_no_unsafe_reuse_on_labeled_cases():
    assert metrics(challenge_cases(), scoped)["unsafe_reuse"] == 0

def test_context_baseline_has_unsafe_reuse_but_checks_scope():
    cases = challenge_cases()
    assert scoped_baseline(cases[1]) != scoped_baseline(cases[0])
    assert metrics(cases, scoped_baseline)["unsafe_reuse"] > 0

def test_composed_challenges():
    cases = combined_challenges()
    assert len(cases) == 8
    assert len({c.name for c in cases}) == len(cases)
    mismatches = [(c.name, scoped(c), c.expected) for c in cases if scoped(c) != c.expected]
    assert not mismatches, mismatches
