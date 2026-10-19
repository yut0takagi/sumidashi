"""評価ハーネスそのものと、ready の静的チェックがゲートを通ることを確かめる。"""

from run_evals import _match, evaluate_applicability, evaluate_checks


def loc(file, start, end=None):
    return {"location": {"file": file, "start_line": start, "end_line": end or start}}


def test_match_is_one_to_one_by_file_and_overlap():
    expected = [{"file": "a.ts", "start_line": 3, "end_line": 5}, {"file": "a.ts", "start_line": 4, "end_line": 4}]
    actual = [loc("a.ts", 4), loc("b.ts", 4)]
    pairs, missed, extra = _match(expected, actual)
    assert len(pairs) == 1 and len(missed) == 1 and extra == [actual[1]]


def test_ready_static_checks_pass_the_gate():
    results = evaluate_checks(runs=1)
    assert results, "評価ケースが 1 つもない"
    failed = {cid: r["failures"] for cid, r in results.items() if not r["passed"]}
    assert not failed, failed


def test_applicability_cases():
    r = evaluate_applicability()
    assert r["cases"] > 0
    assert r["failed"] == 0, r["failures"]
