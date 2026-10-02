"""Overflow tolerance against font metrics: a word box spans the font's full ascent and descent."""
from deck_builder.qa.measure import Box, overshoot

BOX = Box(left=50.4, top=93.6, right=922.0, bottom=288.0)  # the generator's big-number placeholder


def test_tall_metric_font_inside_its_box_is_not_overflow():
    # Avenir Next "18%" at 96 pt as pdftotext reports it: 131 pt tall, 12.3 pt past the bottom edge,
    # with the ink well inside the box
    assert overshoot(BOX, [Box(50.4, 169.2, 261.9, 300.3)]) == 0.0


def test_a_spilled_line_is_overflow():
    # a second 131 pt line below the first
    assert overshoot(BOX, [Box(50.4, 169.2, 261.9, 300.3), Box(50.4, 300.3, 200.0, 431.4)]) > 100


def test_small_text_keeps_the_fixed_tolerance():
    # a 14 pt line, 5 pt past the bottom: past the 3 pt tolerance, which outweighs 15% of the line
    assert overshoot(BOX, [Box(60.0, 275.0, 120.0, 293.0)]) == 5.0


def test_horizontal_overshoot_has_no_metric_slack():
    assert overshoot(BOX, [Box(900.0, 150.0, 930.0, 280.0)]) == 8.0
