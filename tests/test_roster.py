# -*- coding: utf-8 -*-
"""Tester för spelardatan (roster_data) och dess koppling till lagen."""

import roster_data as rd
import matches_data as md

SLUGS = {t["slug"] for t in md.teams}


def test_rosters_is_dict():
    assert isinstance(rd.rosters, dict)


def test_keys_match_team_slugs_exactly():
    # Varje nyckel ska vara en känd lag-slug, och alla lag ska finnas med.
    assert set(rd.rosters.keys()) == SLUGS


def test_every_player_has_nonempty_name():
    for slug, players in rd.rosters.items():
        for p in players:
            assert p.get("namn"), f"{slug}: spelare saknar namn: {p!r}"


def test_pos_when_set_is_mv_or_ut():
    for slug, players in rd.rosters.items():
        for p in players:
            if "pos" in p:
                assert p["pos"] in ("MV", "UT"), f"{slug}: ogiltig pos {p['pos']!r}"


def test_p15_bla_has_six_players():
    assert len(rd.rosters["p15-bla"]) == 6


def test_known_goalkeeper_and_nickname_present():
    bla = {p["namn"]: p for p in rd.rosters["p15-bla"]}
    assert bla["Alfred Lindblad"]["pos"] == "MV"
    assert bla["Alfred Lindblad"]["smek"] == "Affe"
