from datetime import date, datetime
import pytz

from app.cultural_event import can_access_cultural_registration
from app.prasad_seva import (
    display_prasad_name_group,
    format_prasad_summary_insight,
    get_available_prasad_pooja_options,
    get_pooja_options_for_date,
    get_prasad_slot_status,
    get_prasad_slot_sort_key,
    is_prasad_seva_in_past_table,
    is_prasad_seva_visible_in_table,
    normalize_prasad_name_group,
)


def test_first_day_allows_only_evening_pooja():
    assert get_pooja_options_for_date(date(2026, 9, 14)) == ["Evening Pooja"]


def test_other_days_allow_morning_and_evening_pooja():
    options = get_pooja_options_for_date(date(2026, 9, 15))
    assert options == ["Morning Pooja", "Evening Pooja"]


def test_last_day_allows_only_morning_pooja():
    assert get_pooja_options_for_date(date(2026, 9, 20)) == ["Morning Pooja"]


def test_current_morning_slot_is_hidden_after_3_pm_central():
    cst = pytz.timezone("US/Central")
    before_cutoff = cst.localize(datetime(2026, 9, 15, 14, 59))
    at_cutoff = cst.localize(datetime(2026, 9, 15, 15, 0))

    assert is_prasad_seva_visible_in_table(date(2026, 9, 15), "Morning Pooja", before_cutoff)
    assert not is_prasad_seva_visible_in_table(date(2026, 9, 15), "Morning Pooja", at_cutoff)
    assert is_prasad_seva_visible_in_table(date(2026, 9, 15), "Evening Pooja", at_cutoff)
    assert is_prasad_seva_visible_in_table(date(2026, 9, 16), "Morning Pooja", at_cutoff)
    assert is_prasad_seva_in_past_table(date(2026, 9, 15), "Morning Pooja", at_cutoff)
    assert not is_prasad_seva_in_past_table(date(2026, 9, 15), "Evening Pooja", at_cutoff)
    assert is_prasad_seva_in_past_table(date(2026, 9, 14), "Morning Pooja", at_cutoff)
    assert get_available_prasad_pooja_options(date(2026, 9, 15), at_cutoff) == ["Evening Pooja"]
    assert get_available_prasad_pooja_options(date(2026, 9, 15), before_cutoff) == [
        "Morning Pooja",
        "Evening Pooja",
    ]


def test_name_group_normalization_merges_separators_spacing_and_case():
    variants = [
        "Veeraswamy & Sivaparvathi",
        "Veeraswamy and Sivaparvathi",
        "  veeraswamy,   sivaparvathi  ",
    ]
    assert len({normalize_prasad_name_group(name) for name in variants}) == 1
    assert display_prasad_name_group(variants[1]) == "Veeraswamy & Sivaparvathi"


def test_empty_prasad_summary_insights_are_not_rendered():
    assert format_prasad_summary_insight("No service yet", "None") == ""
    assert "Busiest slot" in format_prasad_summary_insight("Busiest slot", "15-Sep · Morning Pooja")


def test_prasad_slot_status_tracks_completed_current_and_upcoming_slots():
    cst = pytz.timezone("US/Central")
    before_cutoff = cst.localize(datetime(2026, 9, 16, 14, 59))
    after_cutoff = cst.localize(datetime(2026, 9, 16, 15, 0))

    assert get_prasad_slot_status(date(2026, 9, 15), "Evening Pooja", before_cutoff) == "completed"
    assert get_prasad_slot_status(date(2026, 9, 16), "Morning Pooja", before_cutoff) == "current"
    assert get_prasad_slot_status(date(2026, 9, 16), "Evening Pooja", before_cutoff) == "upcoming"
    assert get_prasad_slot_status(date(2026, 9, 16), "Evening Pooja", after_cutoff) == "current"
    assert get_prasad_slot_status(date(2026, 9, 17), "Morning Pooja", after_cutoff) == "upcoming"


def test_prasad_slot_sort_keeps_morning_before_evening():
    slots = [(date(2026, 9, 16), "Evening Pooja"), (date(2026, 9, 16), "Morning Pooja")]
    assert sorted(slots, key=get_prasad_slot_sort_key) == [
        (date(2026, 9, 16), "Morning Pooja"),
        (date(2026, 9, 16), "Evening Pooja"),
    ]


def test_cultural_registration_requires_login():
    assert can_access_cultural_registration({}) is False
    assert can_access_cultural_registration({"admin_logged_in": False}) is False
    assert can_access_cultural_registration({"admin_logged_in": True}) is True
