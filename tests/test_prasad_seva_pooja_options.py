from datetime import date

from app.prasad_seva import display_prasad_name_group, get_pooja_options_for_date, normalize_prasad_name_group


def test_first_day_allows_only_evening_pooja():
    assert get_pooja_options_for_date(date(2026, 9, 14)) == ["Evening Pooja"]


def test_other_days_allow_morning_and_evening_pooja():
    options = get_pooja_options_for_date(date(2026, 9, 15))
    assert options == ["Morning Pooja", "Evening Pooja"]


def test_name_group_normalization_merges_separators_spacing_and_case():
    variants = [
        "Veeraswamy & Sivaparvathi",
        "Veeraswamy and Sivaparvathi",
        "  veeraswamy,   sivaparvathi  ",
    ]
    assert len({normalize_prasad_name_group(name) for name in variants}) == 1
    assert display_prasad_name_group(variants[1]) == "Veeraswamy & Sivaparvathi"
