"""End-to-end API flow: import sets, gate levels, answer, track progress, export."""

from fastapi.testclient import TestClient
from tests.conftest import make_flashcard, make_question, make_set


def _import(client: TestClient, data: dict) -> None:
    response = client.post("/api/sets/import", json=data)
    assert response.status_code == 200, response.text


def _seed_two_levels(client: TestClient) -> None:
    for level in (1, 2):
        questions = [make_question(f"q{i}") for i in range(4)]
        _import(client, make_set(f"ai-l{level}", level=level, questions=questions))


def test_health(client: TestClient):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_import_and_list_sets(client: TestClient):
    _seed_two_levels(client)
    sets = client.get("/api/sets").json()
    assert [(s["id"], s["question_count"]) for s in sets] == [("ai-l1", 4), ("ai-l2", 4)]


def test_import_rejects_invalid_set(client: TestClient):
    bad = make_set("bad", questions=[make_question("q1")])
    del bad["questions"][0]["correct_index"]
    assert client.post("/api/sets/import", json=bad).status_code == 422


def test_reimport_updates_in_place(client: TestClient):
    _import(client, make_set("ai-l1", questions=[make_question("q1")]))
    updated = make_set("ai-l1", questions=[make_question("q1"), make_question("q2")])
    updated["title"] = "Updated title"
    _import(client, updated)
    sets = client.get("/api/sets").json()
    assert len(sets) == 1
    assert sets[0]["title"] == "Updated title"
    assert sets[0]["question_count"] == 2


def test_locked_level_is_refused(client: TestClient):
    _seed_two_levels(client)
    response = client.post(
        "/api/quiz/start", json={"track": "ai-engineer", "level": 2, "mode": "level"}
    )
    assert response.status_code == 403
    assert "locked" in response.json()["detail"]


def _play_level(client: TestClient, level: int, *, correct: bool = True) -> dict:
    """Start a session and answer every card (correctly by default)."""
    start = client.post(
        "/api/quiz/start", json={"track": "ai-engineer", "level": level, "mode": "level"}
    )
    assert start.status_code == 200, start.text
    session = start.json()
    for question in session["questions"]:
        chosen = question["correct_index"] if correct else question["correct_index"] + 1
        result = client.post(
            "/api/quiz/answer",
            json={
                "session_id": session["id"],
                "question_id": question["id"],
                "chosen_index": chosen % len(question["options"]),
            },
        )
        assert result.status_code == 200, result.text
        assert result.json()["correct"] is correct
    finish = client.post(f"/api/quiz/{session['id']}/finish")
    assert finish.status_code == 200
    return session


def test_passing_level_one_unlocks_level_two(client: TestClient):
    _seed_two_levels(client)
    _play_level(client, 1, correct=True)

    progress = client.get("/api/results/progress", params={"track": "ai-engineer"}).json()
    by_level = {lp["level"]: lp for lp in progress["levels"]}
    assert by_level[1]["passed"] is True
    assert by_level[2]["unlocked"] is True
    assert progress["highest_unlocked"] == 2

    # And starting a level-2 session now succeeds.
    assert (
        client.post(
            "/api/quiz/start", json={"track": "ai-engineer", "level": 2, "mode": "level"}
        ).status_code
        == 200
    )


def test_failing_level_keeps_next_locked(client: TestClient):
    _seed_two_levels(client)
    _play_level(client, 1, correct=False)
    progress = client.get("/api/results/progress", params={"track": "ai-engineer"}).json()
    by_level = {lp["level"]: lp for lp in progress["levels"]}
    assert by_level[1]["passed"] is False
    assert by_level[2]["unlocked"] is False


def test_flashcard_flow_and_typicality_filter(client: TestClient):
    questions = [make_question("q1"), make_flashcard("fc1")]
    questions[0]["tags"]["typicality"] = "occasional"
    _import(client, make_set("mixed", level=1, questions=questions))

    # Filtering to "common" leaves only the flashcard.
    start = client.post(
        "/api/quiz/start",
        json={"track": "ai-engineer", "mode": "typical-drill", "typicality": ["common"]},
    )
    assert start.status_code == 200
    session = start.json()
    assert [q["id"] for q in session["questions"]] == ["mixed::fc1"]

    result = client.post(
        "/api/quiz/answer",
        json={"session_id": session["id"], "question_id": "mixed::fc1", "self_rating": "partial"},
    ).json()
    assert result["score"] == 0.5
    assert result["correct"] is False


def test_export_summary_shape(client: TestClient):
    _seed_two_levels(client)
    _play_level(client, 1, correct=True)
    export = client.get("/api/results/export").json()
    assert export["total_answers"] == 4
    assert [t["track"] for t in export["tracks"]] == ["ai-engineer"]
    assert export["weak_topics"][0]["topic"] == "Transformers"
    assert export["weak_topics"][0]["accuracy"] == 1.0


def test_answer_rejects_mismatched_kind(client: TestClient):
    _seed_two_levels(client)
    session = _play_level(client, 1)
    question_id = session["questions"][0]["id"]
    response = client.post(
        "/api/quiz/answer",
        json={"session_id": session["id"], "question_id": question_id, "self_rating": "nailed"},
    )
    assert response.status_code == 422
