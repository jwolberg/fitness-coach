"""Critical-path test 2: graph retrieval correctness (PRD §11 Test 2; ARCH §9).

WHY THIS TEST: every downstream safety and explanation behavior depends on the
traversal surfacing the correct neighborhood. This asserts the
``Member → Injury → Joint ← Exercise`` path resolves the right contraindicated set
and that the member-graph endpoint returns a coherent, safety-relevant subgraph
(injury → joint edges present, excluded exercises linked) — not the whole graph.
"""

from __future__ import annotations

from app.graph.client import session
from app.retrieval.retriever import member_graph
from app.safety import validator


def test_member_injury_joint_exercise_traversal(member_id):
    # The traversal that the safety guarantee rests on.
    with session() as s:
        rows = s.run(
            """
            MATCH (:Member {id:$mid})-[:HAS_INJURY]->(:Injury)-[:AFFECTS_JOINT]->(j:Joint)
                  <-[:LOADS_JOINT]-(e:Exercise)
            RETURN collect(DISTINCT e.id) AS ids, collect(DISTINCT j.name) AS joints
            """,
            mid=member_id,
        ).single()
    assert "knee" in rows["joints"], "Maya's injury must affect the knee joint"
    # Traversal result equals the deterministic contraindication core.
    assert set(rows["ids"]) == validator.contraindicated_exercise_ids(member_id)
    assert len(rows["ids"]) > 0


def test_contraindicated_exercises_actually_load_injured_joint(member_id):
    injured = {"knee"}
    for ex in validator.contraindicated_exercises(member_id):
        assert injured.intersection(ex["affected_joints"]), (
            f"{ex['name']} flagged contraindicated but loads {ex['affected_joints']}, not an injured joint"
        )


def test_member_graph_neighborhood_is_coherent(member_id):
    graph = member_graph(member_id)
    types = {n["type"] for n in graph["nodes"]}
    edge_types = {e["type"] for e in graph["edges"]}
    assert {"Member", "Injury", "Joint"}.issubset(types)
    # The safety path edges must be present.
    assert "AFFECTS_JOINT" in edge_types
    assert "LOADS_JOINT" in edge_types
    # Focused, not the whole library: excluded exercises only (21), not all 50.
    exercise_nodes = [n for n in graph["nodes"] if n["type"] == "Exercise"]
    assert 0 < len(exercise_nodes) < 50
