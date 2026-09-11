from datetime import date

from app.prasad_seva import get_pooja_options_for_date


def test_first_day_allows_only_evening_pooja():
    assert get_pooja_options_for_date(date(2026, 9, 14)) == ["Evening Pooja"]


def test_other_days_allow_morning_and_evening_pooja():
    options = get_pooja_options_for_date(date(2026, 9, 15))
    assert options == ["Morning Pooja", "Evening Pooja"]
