from aretz_texture.ingest.sources import list_corpus_chorales, read_score


def test_the_corpus_lists_371_chorales_in_a_stable_order() -> None:
    first = list_corpus_chorales()
    second = list_corpus_chorales()

    assert len(first) == 371
    assert first == second
    assert first[:3] == ("bach/bwv269", "bach/bwv347", "bach/bwv153.1")


def test_a_listed_identifier_can_be_read() -> None:
    assert read_score(list_corpus_chorales()[0]).score.parts
