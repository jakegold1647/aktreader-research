from pathlib import Path

import pytest

from aktreader.cli import PROJECT_ROOT
from aktreader.variant_lexicon import (
    VariantLexiconError,
    VariantRelation,
    load_variant_lexicon,
)

BASE = PROJECT_ROOT / "resources" / "serock_name_lexicon.csv"
RELATIONS = PROJECT_ROOT / "resources" / "serock_variant_relations.csv"


@pytest.fixture(scope="module")
def lexicon():
    return load_variant_lexicon(BASE, RELATIONS)


def _by_form(report, form: str):
    return [proposal for proposal in report.proposals if proposal.form == form]


def test_public_lexicon_loads_with_every_anti_entry_typed(lexicon) -> None:
    ruled_out = {
        relation.form
        for relation in lexicon.relations
        if relation.relation is VariantRelation.RULED_OUT
    }

    assert {
        "Gersz Weksler",
        "Лейбъ Майковскій",
        "KANALEK",
        "Пфлюгеръ",
        "Топеръ",
        "Турецкій",
        "Sierck-les-Bains",
    } <= ruled_out


def test_rule_out_and_documented_form_remain_distinct(lexicon) -> None:
    report = lexicon.propose("Kanarek", entity_type="surname")

    kanalek = _by_form(report, "KANALEK")
    kania = _by_form(report, "Kania")
    assert len(kanalek) == len(kania) == 1
    assert kanalek[0].relation is VariantRelation.RULED_OUT
    assert kanalek[0].shared_codes == ()
    assert kania[0].relation is VariantRelation.DOCUMENTED_FORM
    assert report.literal_input == "Kanarek"


def test_querying_a_false_form_returns_what_it_was_ruled_out_against(lexicon) -> None:
    report = lexicon.propose("KANALEK", entity_type="surname")

    kanarek = _by_form(report, "Kanarek")
    assert len(kanarek) == 1
    assert kanarek[0].relation is VariantRelation.RULED_OUT
    assert kanarek[0].evidence[0].source_ref.startswith("SURV near-miss")


def test_refuted_turecki_read_points_to_the_reader_c_verdict(lexicon) -> None:
    report = lexicon.propose("Турецкій", entity_type="surname")

    verdict = _by_form(report, "Auksztukalska")
    assert len(verdict) == 1
    assert verdict[0].relation is VariantRelation.RULED_OUT
    assert verdict[0].evidence[0].source_ref.startswith("W2 arb#4")


def test_cluster_membership_is_not_silently_promoted_to_equivalence(lexicon) -> None:
    report = lexicon.propose("Мяра", entity_type="surname")

    micznik = _by_form(report, "Micznik")
    assert len(micznik) == 1
    assert micznik[0].relation is VariantRelation.DOCUMENTED_FORM
    assert report.query_codes == ()


def test_explicit_variant_is_symmetric_for_search_without_rewriting(lexicon) -> None:
    report = lexicon.propose("Goldsztajn", entity_type="surname", include_phonetic=False)

    canonical = _by_form(report, "Goldsztejn")
    assert len(canonical) == 1
    assert canonical[0].relation is VariantRelation.ATTESTED_VARIANT
    assert report.literal_input == "Goldsztajn"


def test_unknown_spelling_gets_only_phonetic_candidates(lexicon) -> None:
    report = lexicon.propose("Goldstein", entity_type="surname")

    assert report.query_codes == ("584360",)
    assert {proposal.form for proposal in report.proposals} == {
        "Goldsztejn",
        "Goldsztajn",
    }
    assert all(
        proposal.relation is VariantRelation.PHONETIC_CANDIDATE for proposal in report.proposals
    )


def test_phonetic_candidates_can_be_disabled(lexicon) -> None:
    report = lexicon.propose("Goldstein", entity_type="surname", include_phonetic=False)

    assert report.query_codes == ()
    assert report.proposals == ()


def test_town_seed_keeps_false_friend_beside_attested_forms(lexicon) -> None:
    report = lexicon.propose("Serock", entity_type="town", include_phonetic=False)

    by_form = {proposal.form: proposal.relation for proposal in report.proposals}
    assert by_form["Sierck-les-Bains"] is VariantRelation.RULED_OUT
    assert by_form["Serock u/Narwią"] is VariantRelation.ATTESTED_VARIANT
    assert by_form["Serok"] is VariantRelation.ATTESTED_VARIANT


def _write_pair(tmp_path: Path, base_rows: str, relation_rows: str) -> tuple[Path, Path]:
    base = tmp_path / "base.csv"
    relations = tmp_path / "relations.csv"
    base.write_text(
        "normalized_form,type,variant,script,source_tier,source_ref\n" + base_rows,
        encoding="utf-8",
    )
    relations.write_text(
        "canonical_form,entity_type,form,relation,script,source_tier,source_ref\n" + relation_rows,
        encoding="utf-8",
    )
    return base, relations


def test_ruled_out_evidence_beats_a_real_phonetic_collision(tmp_path: Path) -> None:
    base, relations = _write_pair(
        tmp_path,
        "Cats,surname,Cats,latin,1,source A\nCats,surname,Katz,latin,2,source B\n",
        "Cats,surname,Katz,RULED_OUT,latin,1,source C\n",
    )

    report = load_variant_lexicon(base, relations).propose("Cats")

    katz = _by_form(report, "Katz")
    assert len(katz) == 1
    assert katz[0].relation is VariantRelation.RULED_OUT
    assert katz[0].shared_codes
    assert katz[0].evidence[0].source_ref == "source C"


def test_anti_entry_without_explicit_rule_fails_closed(tmp_path: Path) -> None:
    base, relations = _write_pair(
        tmp_path,
        "Phantom,anti-entry,PHANTOM,latin,1,refuted source\n",
        "Known,surname,Knowns,ATTESTED_VARIANT,latin,1,known source\n",
    )

    with pytest.raises(VariantLexiconError, match="lacks an explicit RULED_OUT"):
        load_variant_lexicon(base, relations)


def test_anti_entry_requires_matching_source_evidence(tmp_path: Path) -> None:
    base, relations = _write_pair(
        tmp_path,
        "Phantom,anti-entry,PHANTOM,latin,1,refuted source\n",
        "Known,surname,PHANTOM,RULED_OUT,latin,2,different source\n",
    )

    with pytest.raises(VariantLexiconError, match="matching source evidence"):
        load_variant_lexicon(base, relations)


def test_declared_script_must_match_the_form(tmp_path: Path) -> None:
    base, relations = _write_pair(
        tmp_path,
        "Known,surname,Мяра,latin,1,known source\n",
        "Known,surname,Knowns,ATTESTED_VARIANT,latin,1,known source\n",
    )

    with pytest.raises(VariantLexiconError, match="declared latin script"):
        load_variant_lexicon(base, relations)


def test_conflicting_explicit_relationship_fails_closed(tmp_path: Path) -> None:
    base, relations = _write_pair(
        tmp_path,
        "Known,surname,Known,latin,1,known source\n",
        "Known,surname,Knowns,ATTESTED_VARIANT,latin,1,source A\n"
        "Known,surname,Knowns,RULED_OUT,latin,2,source B\n",
    )

    with pytest.raises(VariantLexiconError, match="both ATTESTED_VARIANT and RULED_OUT"):
        load_variant_lexicon(base, relations)


def test_extra_csv_columns_fail_with_a_contract_error(tmp_path: Path) -> None:
    base, relations = _write_pair(
        tmp_path,
        "Known,surname,Known,latin,1,known source,unexpected\n",
        "Known,surname,Knowns,ATTESTED_VARIANT,latin,1,known source\n",
    )

    with pytest.raises(VariantLexiconError, match="more columns than the CSV header"):
        load_variant_lexicon(base, relations)
