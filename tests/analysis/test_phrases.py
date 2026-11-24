from fractions import Fraction

from tests.core_builders import event, part_of, rest_fermata, score_of

from aretz_texture.analysis.phrases import fermata_clusters, segment_phrases
from aretz_texture.analysis.settings import PhraseSegmentationSettings
from aretz_texture.core.notation import NotatedVoice, NoteEvent, TieType
from aretz_texture.core.score import Part, Score
from aretz_texture.core.texture import PhraseClosing, StreamReference

DEFAULTS = PhraseSegmentationSettings()


def stream(part_number: int, voice_number: int = 1) -> StreamReference:
    return StreamReference(part_number=part_number, voice_number=voice_number, part_name=None)


def voice_with_fermatas(*fermatas: tuple[int, int], length: int = 12) -> list[NoteEvent]:
    """Return quarter notes of the given length, with fermata events at (onset, duration)."""
    events: list[NoteEvent] = []
    cursor = 0
    for onset, duration in fermatas:
        events += [event(n, 1) for n in range(cursor, onset)]
        events.append(event(onset, duration, fermata=True))
        cursor = onset + duration
    events += [event(n, 1) for n in range(cursor, length)]
    return events


def part_with_fermatas(*fermatas: tuple[int, int], length: int = 12) -> Part:
    return part_of(voice_with_fermatas(*fermatas, length=length))


def spans_of(
    score: Score, settings: PhraseSegmentationSettings = DEFAULTS
) -> list[tuple[Fraction, Fraction]]:
    return [(p.span.onset, p.span.end) for p in segment_phrases(score, settings)]


def test_fermatas_that_overlap_in_time_are_one_cluster_ending_at_the_latest_end() -> None:
    # As in BWV 320, bar 2: three voices hold the fermata on a dotted half, the bass on a
    # quarter and walks on below.
    held = [event(0, 3), event(3, 3, fermata=True), event(6, 2)]
    walking = [event(0, 3), event(3, 1, fermata=True), event(4, 1), event(5, 1), event(6, 2)]
    score = score_of(part_of(held), part_of(held), part_of(held), part_of(walking))

    clusters = fermata_clusters(score, DEFAULTS)

    assert len(clusters) == 1
    cluster = clusters[0]
    assert (cluster.span.onset, cluster.span.end) == (3, 6)
    assert cluster.boundary == 6
    assert cluster.ends == (Fraction(4), Fraction(6))
    assert cluster.streams == (stream(1), stream(2), stream(3), stream(4))
    assert spans_of(score) == [(0, 6), (6, 8)]


def test_fermatas_that_only_touch_are_two_clusters() -> None:
    score = score_of(
        part_of([event(0, 2), event(2, 2, fermata=True), event(4, 4)]),
        part_of([event(0, 4), event(4, 2, fermata=True), event(6, 2)]),
    )

    clusters = fermata_clusters(score, DEFAULTS)

    assert [cluster.boundary for cluster in clusters] == [4, 6]
    assert spans_of(score) == [(0, 4), (4, 6), (6, 8)]


def test_overlap_is_transitive_through_a_chain_of_fermatas() -> None:
    score = score_of(
        part_of([event(0, 2), event(2, 3, fermata=True), event(5, 3)]),
        part_of([event(0, 4), event(4, 2, fermata=True), event(6, 2)]),
        part_of([event(0, 5), event(5, 2, fermata=True), event(7, 1)]),
    )

    clusters = fermata_clusters(score, DEFAULTS)

    assert [(c.span.onset, c.span.end, c.boundary) for c in clusters] == [(2, 7, 7)]
    assert clusters[0].ends == (Fraction(5), Fraction(6), Fraction(7))


def test_ends_half_a_beat_apart_stay_in_one_cluster_with_both_ends_listed() -> None:
    score = score_of(
        part_of(
            [
                event(0, 4),
                event(4, Fraction(7, 2), fermata=True),
                event(Fraction(15, 2), Fraction(1, 2)),
            ]
        ),
        part_of([event(0, 4), event(4, 4, fermata=True)]),
        bar_durations=(4, 4),
    )

    (cluster,) = fermata_clusters(score, DEFAULTS)

    assert cluster.ends == (Fraction(15, 2), Fraction(8))
    assert cluster.boundary == 8


def test_a_fermata_on_a_rest_is_part_of_the_cluster() -> None:
    resting = NotatedVoice(events=(event(0, 2),), rest_fermatas=(rest_fermata(2, 2),))
    score = score_of(part_of(resting), part_of([event(0, 3), event(3, 3, fermata=True)]))

    (cluster,) = fermata_clusters(score, DEFAULTS)

    assert (cluster.span.onset, cluster.span.end) == (2, 6)
    assert cluster.streams == (stream(1), stream(2))


def test_clusters_need_the_minimum_number_of_voices_with_a_fermata() -> None:
    score = score_of(
        part_with_fermatas((2, 2), (6, 2), length=8),
        part_of([event(0, 6), event(6, 2, fermata=True)]),
        bar_durations=(4, 4),
    )

    clusters = fermata_clusters(score, PhraseSegmentationSettings(minimum_fermata_voices=2))

    assert [cluster.boundary for cluster in clusters] == [8]


def test_the_fermatas_of_every_voice_count_not_only_those_of_part_1() -> None:
    # Part 1 has no fermata, as in BWV 190.7 and BWV 248.9 1.
    score = score_of(part_of([event(0, 12)]), part_with_fermatas((2, 2)), bar_durations=(4, 4, 4))

    assert spans_of(score) == [(0, 4), (4, 12)]


def test_a_fermata_in_the_second_notated_voice_ends_a_phrase() -> None:
    score = score_of(part_of([event(0, 12)], voice_with_fermatas((6, 2))), bar_durations=(4, 4, 4))

    assert spans_of(score) == [(0, 8), (8, 12)]


def test_phrases_run_between_fermata_ends_and_the_last_one_is_the_score_end() -> None:
    score = score_of(part_with_fermatas((2, 2), (6, 2)), bar_durations=(4, 4, 4))

    phrases = segment_phrases(score, DEFAULTS)

    assert [(p.number, p.span.onset, p.span.end, p.closing) for p in phrases] == [
        (1, 0, 4, PhraseClosing.FERMATA),
        (2, 4, 8, PhraseClosing.FERMATA),
        (3, 8, 12, PhraseClosing.SCORE_END),
    ]


def test_a_fermata_ending_with_the_score_closes_the_last_phrase_with_a_fermata() -> None:
    score = score_of(part_with_fermatas((2, 2), (6, 2), length=8))

    phrases = segment_phrases(score, DEFAULTS)

    assert [(p.span.onset, p.span.end, p.closing) for p in phrases] == [
        (0, 4, PhraseClosing.FERMATA),
        (4, 8, PhraseClosing.FERMATA),
    ]


def test_rests_alone_after_the_last_fermata_join_the_last_phrase() -> None:
    # As in BWV 330: the last fermata ends before the score does, and only rests follow.
    score = score_of(part_with_fermatas((2, 2), (6, 1), length=7), bar_durations=(4, 4, 4))

    phrases = segment_phrases(score, DEFAULTS)

    assert [(p.span.onset, p.span.end, p.closing) for p in phrases] == [
        (0, 4, PhraseClosing.FERMATA),
        (4, 12, PhraseClosing.FERMATA),
    ]


def test_a_tied_continuation_after_the_last_fermata_is_not_music_to_attack() -> None:
    score = score_of(
        part_of(
            [
                event(0, 2),
                event(2, 2, fermata=True, tie=TieType.START),
                event(4, 4, tie=TieType.STOP),
            ]
        ),
    )

    phrases = segment_phrases(score, DEFAULTS)

    assert [(p.span.onset, p.span.end, p.closing) for p in phrases] == [
        (0, 8, PhraseClosing.FERMATA)
    ]


def test_a_score_without_fermatas_is_one_phrase_closing_with_no_fermatas() -> None:
    score = score_of(part_of([event(0, 8)]), bar_durations=(4, 4))

    phrases = segment_phrases(score, DEFAULTS)

    assert [(p.number, p.span.onset, p.span.end, p.closing) for p in phrases] == [
        (1, 0, 8, PhraseClosing.NO_FERMATAS)
    ]


def test_phrase_bar_numbers_are_those_of_the_first_moment_and_the_last_moment_before_the_end() -> (
    None
):
    score = score_of(
        part_with_fermatas((2, 2), (5, 3), length=13),
        bar_durations=(1, 4, 4, 4),
    )

    phrases = segment_phrases(score, DEFAULTS)

    assert [(p.span.onset, p.span.end, p.first_bar_number, p.last_bar_number) for p in phrases] == [
        (0, 4, 0, 1),
        (4, 8, 1, 2),
        (8, 13, 2, 3),
    ]
