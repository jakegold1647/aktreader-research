import pytest

from aktreader.variants import daitch_mokotoff_codes


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Golden", "583600"),
        ("Kleinman", "586660"),
        ("Lipshitz", "874400"),
        ("Lewinsky", "876450"),
        ("Levinski", "876450"),
        ("Szlamawicz", "486740"),
        ("Shlamovitz", "486740"),
    ],
)
def test_published_examples_include_the_documented_code(name: str, expected: str) -> None:
    assert expected in daitch_mokotoff_codes(name)


def test_ambiguous_sound_returns_every_branch() -> None:
    assert daitch_mokotoff_codes("Auerbach") == ("097400", "097500")


def test_attested_lexicon_spellings_share_a_retrieval_key() -> None:
    goldsztejn = set(daitch_mokotoff_codes("Goldsztejn"))
    goldsztajn = set(daitch_mokotoff_codes("Goldsztajn"))
    sterdyner = set(daitch_mokotoff_codes("Sterdyner"))
    sterdiner = set(daitch_mokotoff_codes("Sterdiner"))

    assert goldsztejn & goldsztajn
    assert sterdyner & sterdiner


def test_transliteration_round_trip_is_retrievable_but_not_asserted_equivalent() -> None:
    jarzabek = set(daitch_mokotoff_codes("Jarząbek"))
    iazhombek = set(daitch_mokotoff_codes("IAZHOMBEK"))

    assert jarzabek & iazhombek


def test_documented_false_friend_does_not_share_a_key() -> None:
    serock = set(daitch_mokotoff_codes("Serock"))
    sierck_les_bains = set(daitch_mokotoff_codes("Sierck-les-Bains"))

    assert serock.isdisjoint(sierck_les_bains)


def test_spacing_punctuation_case_and_common_diacritics_are_mechanical() -> None:
    assert daitch_mokotoff_codes("  Ben-Aron ") == daitch_mokotoff_codes("benaron")
    assert daitch_mokotoff_codes("Bogusławska") == daitch_mokotoff_codes("Boguslawska")


@pytest.mark.parametrize("name", ["", "---", "Мяра"])
def test_empty_or_unsupported_input_fails_closed(name: str) -> None:
    with pytest.raises(ValueError):
        daitch_mokotoff_codes(name)
