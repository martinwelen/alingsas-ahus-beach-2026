# -*- coding: utf-8 -*-
import fetch_matches as fm
import schedule as sch


def test_extract_result_finished():
    assert fm.extract_result({"finished": True, "homeGoals": 14, "awayGoals": 11}) == {"hg": 14, "ag": 11}


def test_extract_result_unfinished_is_none():
    assert fm.extract_result({"finished": False, "homeGoals": 0, "awayGoals": 0}) is None


def test_extract_result_missing_is_none():
    assert fm.extract_result(None) is None
    assert fm.extract_result({"finished": True, "homeGoals": None, "awayGoals": 3}) is None


def test_make_match_carries_result():
    m = sch.make_match("2026-07-17", "13:45", 7, "P15 Vit", "p15-vit", "P15",
                       "Grupp 1", "Alingsås HK VIT", "IFK Malmö HF", "Hemma",
                       result={"hg": 18, "ag": 9})
    assert m["result"] == {"hg": 18, "ag": 9}


def test_make_match_result_defaults_none():
    m = sch.make_match("2026-07-17", "13:45", 7, "P15 Vit", "p15-vit", "P15",
                       "Grupp 1", "Alingsås HK VIT", "IFK Malmö HF", "Hemma")
    assert m["result"] is None
