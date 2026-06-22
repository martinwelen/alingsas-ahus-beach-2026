# -*- coding: utf-8 -*-
"""Enhetstester för fetch_standings transformfunktioner (offline, syntetiska entiteter)."""


import fetch_standings as fs


def test_winner_side_home():
    assert fs.winner_side({"finished": True, "homeGoals": 14, "awayGoals": 11}) == "home"


def test_winner_side_away():
    assert fs.winner_side({"finished": True, "homeGoals": 9, "awayGoals": 12}) == "away"


def test_winner_side_unfinished_is_none():
    assert fs.winner_side({"finished": False, "homeGoals": 0, "awayGoals": 0}) is None


def test_winner_side_missing_result_is_none():
    assert fs.winner_side(None) is None


def test_winner_side_tie_is_none():
    # Slutspel kan inte sluta lika (sudden death), men var defensiv.
    assert fs.winner_side({"finished": True, "homeGoals": 10, "awayGoals": 10}) is None


def _row(name, tid, played, won, tied, lost, gf, ga, points, stage_id):
    """Bygger en syntetisk Division$ConferenceTableRow."""
    return {
        "name": {"sv": name}, "team": {"href": f"Team({{id:{tid}}})"},
        "played": played, "won": won, "tied": tied, "lost": lost,
        "goalsWon": gf, "goalsLost": ga, "points": points,
        "targetStage": {"href": f"Stage({{categoryId:1,stageId:{stage_id},tournamentId:2}})"},
    }


def test_stage_id_extracts_int():
    assert fs._stage_id("Stage({categoryId:1,stageId:70944379,tournamentId:2})") == 70944379


def test_stage_id_missing_is_none():
    assert fs._stage_id("") is None


def test_table_row_maps_fields_and_tier():
    tier_by_stage = {379: "A-Slutspel"}
    r = fs.table_row(_row("Alingsås HK VIT", 74904168, 4, 3, 0, 1, 55, 44, 6, 379),
                     alingsas_ids={74904168}, tier_by_stage=tier_by_stage)
    assert r["name"] == "Alingsås HK VIT"
    assert r["team_id"] == 74904168
    assert r["is_alingsas"] is True
    assert r["played"] == 4 and r["won"] == 3 and r["tied"] == 0 and r["lost"] == 1
    assert r["goals_for"] == 55 and r["goals_against"] == 44
    assert r["diff"] == 11
    assert r["points"] == 6
    assert r["tier"] == "A-Slutspel"


def test_table_row_non_alingsas():
    r = fs.table_row(_row("H43 Lund HF 1", 74504786, 4, 4, 0, 0, 60, 41, 8, 379),
                     alingsas_ids={74904168}, tier_by_stage={379: "A-Slutspel"})
    assert r["is_alingsas"] is False


def test_tier_spans_groups_consecutive_positions():
    rows = [
        {"tier": "A-Slutspel"}, {"tier": "A-Slutspel"},
        {"tier": "A-Slutspel"}, {"tier": "A-Slutspel"},
        {"tier": "B-Slutspel"}, {"tier": "B-Slutspel"}, {"tier": "B-Slutspel"},
        {"tier": "C-Slutspel"}, {"tier": "C-Slutspel"}, {"tier": "C-Slutspel"},
    ]
    spans = fs.tier_spans(rows)
    assert spans == [
        {"tier": "A-Slutspel", "from": 1, "to": 4},
        {"tier": "B-Slutspel", "from": 5, "to": 7},
        {"tier": "C-Slutspel", "from": 8, "to": 10},
    ]


def test_is_descending_points_true():
    assert fs.is_descending_points([{"points": 8}, {"points": 6}, {"points": 6}, {"points": 1}]) is True


def test_is_descending_points_false():
    assert fs.is_descending_points([{"points": 3}, {"points": 6}]) is False


def _playoff_store():
    """Syntetisk store för en spelad slutspelsmatch (hemmavinst 15-12)."""
    return {
        "Match({id:900})": {
            "__typename": "Match", "id": 900, "start": 1784741400000,
            "home": {"href": "MatchActor({actor:\"home\",id:900})"},
            "away": {"href": "MatchActor({actor:\"away\",id:900})"},
            "arena": {"href": "Arena({id:11})"},
            "round": {"href": "Round({id:5})"},
            "result": {"href": "MatchResult({id:900})"},
        },
        "MatchActor({actor:\"home\",id:900})": {
            "__typename": "MatchActor", "name": {"sv": "Alingsås HK VIT"},
            "team": {"href": "Team({id:74904168})"}},
        "MatchActor({actor:\"away\",id:900})": {
            "__typename": "MatchActor", "name": {"sv": "Lugi HF 2"},
            "team": {"href": "Team({id:77344845})"}},
        "Arena({id:11})": {"__typename": "Arena", "fieldName": "Bana 11"},
        "Round({id:5})": {"__typename": "Round", "name": {"sv": "Kvartsfinal"}},
        "MatchResult({id:900})": {
            "__typename": "MatchResult", "finished": True,
            "homeGoals": 15, "awayGoals": 12},
    }


def test_bracket_match_finished_home_win():
    store = _playoff_store()
    m = fs.bracket_match(store["Match({id:900})"], store, alingsas_ids={74904168})
    assert m["id"] == 900
    assert m["bana"] == 11
    assert m["round"] == "Kvartsfinal"
    assert m["home"]["label"] == "Alingsås HK VIT"
    assert m["home"]["is_alingsas"] is True
    assert m["home"]["goals"] == 15
    assert m["away"]["label"] == "Lugi HF 2"
    assert m["away"]["goals"] == 12
    assert m["winner"] == "home"


def test_bracket_match_placeholder_unplayed():
    """Oavgjord seedmatch: platshållarnamn, inga mål, ingen vinnare."""
    store = {
        "Match({id:901})": {
            "__typename": "Match", "id": 901, "start": 1784741400000,
            "home": {"href": "MatchActor({actor:\"home\",id:901})"},
            "away": {"href": "MatchActor({actor:\"away\",id:901})"},
            "arena": {"href": "Arena({id:12})"},
            "round": {"href": "Round({id:6})"},
            "result": {"href": "MatchResult({id:901})"},
        },
        "MatchActor({actor:\"home\",id:901})": {
            "__typename": "MatchActor", "name": {"sv": "1:an i Grupp 1"}, "team": None},
        "MatchActor({actor:\"away\",id:901})": {
            "__typename": "MatchActor", "name": {"sv": "4:an i Grupp 3"}, "team": None},
        "Arena({id:12})": {"__typename": "Arena", "fieldName": "Bana 12"},
        "Round({id:6})": {"__typename": "Round", "name": {"sv": "Åttondelar"}},
        "MatchResult({id:901})": {"__typename": "MatchResult", "finished": False,
                                  "homeGoals": 0, "awayGoals": 0},
    }
    m = fs.bracket_match(store["Match({id:901})"], store, alingsas_ids={74904168})
    assert m["home"]["label"] == "1:an i Grupp 1"
    assert m["home"]["team_id"] is None
    assert m["home"]["is_alingsas"] is False
    assert m["home"]["goals"] is None
    assert m["winner"] is None


def test_group_rounds_orders_by_first_start():
    matches = [
        {"round": "Final", "start": 400, "id": 4},
        {"round": "Åttondelar", "start": 100, "id": 1},
        {"round": "Åttondelar", "start": 100, "id": 2},
        {"round": "Semifinal", "start": 300, "id": 3},
        {"round": "Kvartsfinal", "start": 200, "id": 5},
    ]
    rounds = fs.group_rounds(matches)
    assert [r["name"] for r in rounds] == ["Åttondelar", "Kvartsfinal", "Semifinal", "Final"]
    assert [m["id"] for m in rounds[0]["matches"]] == [1, 2]
    assert len(rounds) == 4


def test_group_rounds_sorts_matches_within_round_by_start_then_id():
    matches = [
        {"round": "Åttondelar", "start": 100, "id": 9},
        {"round": "Åttondelar", "start": 100, "id": 2},
        {"round": "Åttondelar", "start": 50, "id": 7},
    ]
    rounds = fs.group_rounds(matches)
    assert [m["id"] for m in rounds[0]["matches"]] == [7, 2, 9]
