"""The designed layout set: section label and subtitle on content slides, plus cards, process and bands."""
from __future__ import annotations

from deck_builder.brand.layouts import (
    BODY_Y,
    FOOTER,
    HEADED_BODY_Y,
    MARGIN,
    SETS,
    TITLE_Y,
    layout_set,
    ramp,
)

W, H = 13.333, 7.5


def _by_key(name: str) -> dict:
    return {ld.key: ld for ld in layout_set(name, W, H)}


def test_designed_set_extends_full_with_the_new_layouts() -> None:
    assert set(SETS["full"]) < set(SETS["designed"])
    assert {"cards-3", "cards-4", "process-4", "process-5", "bands-3"} <= set(SETS["designed"])


def test_every_placeholder_stays_inside_the_margins_and_above_the_footer() -> None:
    for ld in layout_set("designed", W, H):
        for ph in ld.phs if not ld.bleed else []:  # a full-bleed photo runs past the margins on purpose
            assert ph.x >= MARGIN - 1e-6, (ld.key, ph.field)
            assert ph.x + ph.w <= W - MARGIN + 1e-6, (ld.key, ph.field)
            assert ph.y + ph.h <= H - FOOTER + 1e-6, (ld.key, ph.field)


def test_content_slides_get_a_kicker_and_subtitle_and_their_bodies_move_below_them() -> None:
    d = _by_key("designed")
    for key in ("content", "two-col", "comparison", "table", "chart", "cards-3", "process-5", "bands-3"):
        fields = {ph.field: ph for ph in d[key].phs}
        assert {"kicker", "subtitle", "title"} <= set(fields), key
        assert fields["kicker"].y < fields["title"].y < fields["subtitle"].y, key
        below = [ph for ph in d[key].phs if ph.field not in ("kicker", "title", "subtitle")]
        assert min(ph.y for ph in below) >= HEADED_BODY_Y - 1e-6, key


def test_slides_without_a_content_title_are_left_alone() -> None:
    d = _by_key("designed")
    for key in ("title", "section", "closing", "big-number", "quote"):
        assert "kicker" not in {ph.field for ph in d[key].phs} or key == "section"


def test_the_full_set_is_unchanged_by_the_designed_options() -> None:
    d = _by_key("full")
    assert "cards-3" not in d
    content = {ph.field: ph for ph in d["content"].phs}
    assert "subtitle" not in content and content["title"].y == TITLE_Y and content["body"].y == BODY_Y


def test_cards_are_equal_width_and_process_steps_share_a_baseline() -> None:
    d = _by_key("designed")
    labels = [ph for ph in d["cards-4"].phs if ph.field.startswith("label")]
    assert len({round(ph.w, 4) for ph in labels}) == 1
    steps = [dec for dec in d["process-5"].decor if dec.geom in ("homePlate", "chevron")]
    assert len(steps) == 5 and len({round(dec.y, 4) for dec in steps}) == 1
    assert steps[0].geom == "homePlate" and all(dec.geom == "chevron" for dec in steps[1:])


def test_every_card_step_and_band_is_required_since_its_shape_is_always_drawn() -> None:
    d = _by_key("designed")
    for key, prefixes in (("cards-3", ("label", "body")), ("cards-4", ("label", "body")),
                          ("process-4", ("step", "text")), ("process-5", ("step", "text")),
                          ("bands-3", ("label", "text"))):
        slots = [ph for ph in d[key].phs if ph.field.rstrip("0123456789") in prefixes]
        assert slots and all(ph.required for ph in slots), key


def test_ramp_starts_at_the_primary_color_and_lightens() -> None:
    assert ramp(1) == ["tx2"]
    r = ramp(5)
    assert r[0] == "tx2" and r[-1] == "tx2@60" and len(set(r)) == 5


def test_placeholder_idx_values_are_unique_within_each_layout() -> None:
    for ld in layout_set("designed", W, H):
        idxs = [ph.idx for ph in ld.phs if ph.kind != "title"]
        assert len(idxs) == len(set(idxs)), ld.key
