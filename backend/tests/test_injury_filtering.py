"""Critical-path test 1: injury filtering (PRD §11 Test 1; ARCH §9).

WHY THIS TEST: injury-aware filtering is the product's central safety promise. If a
knee-loading exercise can reach a workout for a knee-injured member, the core value
breaks. This test asserts (a) the contraindicated set is exactly the knee-loading
set, (b) a generated workout containing a contraindicated exercise is caught, and
(c) repair removes it — i.e. the LLM is never the only safety layer.
"""

from __future__ import annotations

from app.graph.client import session
from app.safety import validator


def _knee_loading_ids() -> set[str]:
    with session() as s:
        return {r["id"] for r in s.run(
            "MATCH (e:Exercise)-[:LOADS_JOINT]->(:Joint {name:'knee'}) RETURN e.id AS id"
        )}


def test_contraindicated_equals_knee_loading_set(member_id):
    contra = validator.contraindicated_exercise_ids(member_id)
    knee = _knee_loading_ids()
    assert knee, "expected some knee-loading exercises in the library"
    assert contra == knee, "contraindicated set must equal the knee-loading set exactly"


def test_safe_candidates_exclude_all_contraindicated(member_id):
    safe = {e["id"] for e in validator.safe_exercise_candidates(member_id)}
    contra = validator.contraindicated_exercise_ids(member_id)
    assert safe, "expected at least one safe candidate"
    assert safe.isdisjoint(contra), "no safe candidate may be contraindicated"


def test_validator_rejects_contraindicated_workout(member_id):
    bad_id = next(iter(validator.contraindicated_exercise_ids(member_id)))
    workout = {"exercises": [{"exercise_id": bad_id, "name": "Knee Loader", "sets": 3, "reps": "8"}]}
    result = validator.validate_workout(member_id, workout)
    assert result["passed"] is False
    assert any(i["problem"] == "contraindicated" for i in result["issues"])


def test_repair_removes_contraindicated(member_id):
    bad_id = next(iter(validator.contraindicated_exercise_ids(member_id)))
    workout = {"title": "t", "exercises": [{"exercise_id": bad_id, "name": "Knee Loader", "sets": 3, "reps": "8"}]}
    repaired = validator.validate_and_repair(member_id, workout)
    contra = validator.contraindicated_exercise_ids(member_id)
    final_ids = [e.get("exercise_id") for e in repaired["workout"]["exercises"]]
    assert all(i not in contra for i in final_ids), "repaired workout must contain no contraindicated exercise"
