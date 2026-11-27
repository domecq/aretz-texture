from aretz_texture.ingest.sources import (
    list_corpus_chorales,
    list_distinct_corpus_chorales,
    read_score,
)


def test_the_corpus_lists_371_chorales_in_a_stable_order() -> None:
    first = list_corpus_chorales()
    second = list_corpus_chorales()

    assert len(first) == 371
    assert first == second
    assert first[:3] == ("bach/bwv269", "bach/bwv347", "bach/bwv153.1")


def test_a_listed_identifier_can_be_read() -> None:
    assert read_score(list_corpus_chorales()[0]).score.parts


def test_the_distinct_listing_has_350_chorales_each_at_its_first_place() -> None:
    listed = list_corpus_chorales()

    distinct = list_distinct_corpus_chorales()

    assert len(distinct) == 350
    assert len(set(distinct)) == 350
    assert [name for name in listed if name in set(distinct)][:3] == list(distinct[:3])
    assert distinct == tuple(dict.fromkeys(listed))
