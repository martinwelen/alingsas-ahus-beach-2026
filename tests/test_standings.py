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
