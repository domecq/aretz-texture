# Spec 001: chorale round trip

Issue: #7, "Read a Bach chorale and write it back as a piano score"
Status: Draft, awaiting gate 1
Related: ADR 0003 (music21 boundary and runtime dependencies)

## 1. Context

As a musician, Nico wants to give the tool a four voice chorale and get back a MusicXML file on a piano grand staff that he can open in Sibelius, to check by eye that nothing is lost on the way in and out. This is the first end to end slice: no reduction or analysis yet, only ingestion, the core data model and rendering.

Expected by the issue:

* A command such as `aretz-texture reduce bwv66.6 --output bwv66_6_piano.musicxml`, accepting a chorale from the music21 corpus or a MusicXML file path.
* A two staff piano score: bass and tenor in the left hand, alto and soprano in the right hand.
* Each voice keeps its own rhythm (not block chords). Pitches, accidentals, ties and rhythm must match the original exactly.
* An automated round trip over the chorales of the music21 corpus finds no lost or altered notes. This is the start of the evaluation corpus (`eval/`), marked as a slow test.

## 2. Scope

### In

* Core data model for a notated four voice score: note events, voices, bars, key and time signatures (`core/`).
* Domain exceptions in `core/errors.py`.
* Reading a four part score (corpus identifier or MusicXML path) into the core model (`ingest/`).
* Writing the core model as a MusicXML grand staff piano score (`render/`).
* Reading back a grand staff piano score written by this tool, so the round trip can be verified (`ingest/`).
* Command line entry point `aretz-texture reduce`.
* Round trip comparison and the slow corpus evaluation (`eval/`).
* Runtime dependencies music21 and pydantic, and the import contracts of ADR 0003.

### Out

* Any reduction, segmentation or analysis. `reduce` passes the four voices through unchanged in this spec.
* Block chords at every attack (a `chordify` style rendering mode).
* Transposing instruments, repeat expansion and the rest of the normalization step (architecture, section 3).
* Lyrics, fermatas, dynamics, articulations, slurs, tempo marks, repeat barlines and endings, unless Nico decides otherwise (section 6).
* Chords inside a single part, several voices inside a single part, grace notes, microtones and unpitched notes. Ingestion rejects them with `UnsupportedScoreError` rather than dropping anything silently.
* Engraving quality beyond what Sibelius needs to show the chorale correctly (beaming, spacing, system breaks).

### Delivery

The issue is larger than one small pull request. It is delivered in three pull requests, each with its own acceptance criteria below, in this order:

* **001a, model and ingestion**: dependencies, `core/`, `core/errors.py`, `ingest/` for four part scores, glossary.
* **001b, rendering and command line**: `render/`, the grand staff reader in `ingest/`, `cli.py`, `[project.scripts]`.
* **001c, evaluation**: `eval/round_trip.py` and the slow corpus test.

## 3. Design

### 3.1 Modules touched

```
pyproject.toml                         dependencies, script, pyright and import-linter changes
src/aretz_texture/core/errors.py       domain exceptions
src/aretz_texture/core/notation.py     SpelledPitch, TieType, NoteEvent, VoiceRole, Voice
src/aretz_texture/core/score.py        Bar, KeySignatureChange, TimeSignatureChange, FourVoiceScore
src/aretz_texture/core/grand_staff.py  GrandStaffLayout and the default piano layout
src/aretz_texture/ingest/music21_conversion.py   boundary: music21 stream to core (four parts)
src/aretz_texture/ingest/grand_staff_reader.py   boundary: music21 grand staff to core
src/aretz_texture/ingest/sources.py              boundary: file paths and corpus identifiers
src/aretz_texture/render/piano_score.py          boundary: core to music21 grand staff, MusicXML
src/aretz_texture/eval/round_trip.py             comparison and corpus evaluation
src/aretz_texture/cli.py                         argparse entry point
```

Module names may change during implementation if the glossary names suggest better ones; public names and types may not without updating this spec.

### 3.2 Core data model (`core/`)

All models are pydantic `BaseModel` with `model_config = ConfigDict(frozen=True)`. Time values are `fractions.Fraction` in quarter lengths (pydantic supports `Fraction` natively since 2.10). Floats never appear in the core.

```python
StepName = Literal["C", "D", "E", "F", "G", "A", "B"]

class SpelledPitch(BaseModel):
    step: StepName
    alter: int          # semitones: -2 double flat, -1 flat, 0 natural, 1 sharp, 2 double sharp
    octave: int         # scientific pitch notation, middle C is C4

class TieType(StrEnum):
    START = "start"
    CONTINUE = "continue"
    STOP = "stop"

class NoteEvent(BaseModel):
    onset: Fraction     # quarter lengths from the start of the first bar; >= 0
    duration: Fraction  # quarter lengths; > 0
    pitch: SpelledPitch
    tie: TieType | None # None when the note is not tied

class VoiceRole(StrEnum):
    SOPRANO = "soprano"
    ALTO = "alto"
    TENOR = "tenor"
    BASS = "bass"

class Voice(BaseModel):
    role: VoiceRole
    events: tuple[NoteEvent, ...]   # sorted by onset, never overlapping

class Bar(BaseModel):
    number: int          # the bar number shown in the score; a pickup bar is usually 0
    onset: Fraction      # quarter lengths
    duration: Fraction   # actual length of the bar; shorter than the time signature in a pickup bar

class KeySignatureChange(BaseModel):
    onset: Fraction
    sharps: int          # negative for flats

class TimeSignatureChange(BaseModel):
    onset: Fraction
    numerator: int
    denominator: int

class FourVoiceScore(BaseModel):
    bars: tuple[Bar, ...]                         # contiguous, starting at onset 0
    key_signatures: tuple[KeySignatureChange, ...]  # first one at onset 0
    time_signatures: tuple[TimeSignatureChange, ...]  # first one at onset 0
    soprano: Voice
    alto: Voice
    tenor: Voice
    bass: Voice

    def voice(self, role: VoiceRole) -> Voice: ...
    def voices(self) -> tuple[Voice, Voice, Voice, Voice]: ...  # soprano, alto, tenor, bass
    def pickup_duration(self) -> Fraction: ...   # 0 when the first bar is complete
```

Decisions in the model:

* **A note event is a notated note, not a sounding note.** Two notes tied across a bar line are two events, the first with `TieType.START` and the second with `TieType.STOP`. Merging tied notes into one sounding note is analysis work for a later spec. This keeps the round trip exact.
* **Rests are not stored.** Silence in a voice is the time not covered by its events. The renderer writes rests in the gaps. This makes "no lost or altered notes" a statement about events only.
* **Spelling is kept, enharmonics are different.** F sharp 4 and G flat 4 are different `SpelledPitch` values.
* **Bars are explicit.** The renderer rebuilds bars from `bars`, not from the time signature, so pickup bars, short final bars and short bars in the middle of a chorale survive the round trip. A pickup bar is the first bar when its duration is shorter than the bar length given by its time signature.
* Validators enforce the structural invariants at construction: positive durations, sorted and non overlapping events within a voice, contiguous bars starting at 0, the first key and time signature at onset 0, and the voice in each field having the matching `role`. Violations raise pydantic `ValidationError`; these are programming errors, not user errors.

`core/grand_staff.py`:

```python
class Staff(StrEnum):
    UPPER = "upper"   # right hand, treble clef
    LOWER = "lower"   # left hand, bass clef

class StaffVoice(BaseModel):
    staff: Staff
    voice_number: int   # 1 is the upper voice of the staff (stems up), 2 the lower (stems down)

class GrandStaffLayout(BaseModel):
    placements: tuple[tuple[VoiceRole, StaffVoice], ...]
    def placement(self, role: VoiceRole) -> StaffVoice: ...

PIANO_LAYOUT: GrandStaffLayout  # soprano UPPER 1, alto UPPER 2, tenor LOWER 1, bass LOWER 2
```

The layout lives in `core/` because both the renderer (to write) and the grand staff reader (to read back) need it, and they cannot import each other.

### 3.3 Domain exceptions (`core/errors.py`)

```python
class AretzTextureError(Exception): ...          # base of every domain error
class UnparseableScoreError(AretzTextureError): ...  # file missing, not MusicXML, corpus id not found
class UnsupportedScoreError(AretzTextureError): ...  # parses, but outside what the tool handles
class PartCountError(UnsupportedScoreError):
    part_count: int                               # number of parts actually found
```

`AmbiguousHarmonyError`, mentioned in `AGENTS.md`, is not created here; it belongs to the first analysis spec.

### 3.4 Ingestion (`ingest/`)

All three modules are music21 boundary modules (ADR 0003): they start with the file level pyright comment and expose only core and standard library types.

`ingest/sources.py`:

```python
def read_four_voice_score(source: str) -> FourVoiceScore: ...
def read_grand_staff_file(path: Path) -> FourVoiceScore: ...
def list_corpus_chorales() -> tuple[str, ...]: ...
```

* `read_four_voice_score`: if `source` names an existing file, parse it with `music21.converter.parse(path)`; otherwise treat it as a corpus identifier and call `music21.corpus.parse(source)` (for example `"bwv66.6"` or `"bach/bwv66.6"`). Any music21 failure to find or parse the source is reraised as `UnparseableScoreError` with the original exception chained (`raise ... from error`). If the result is not a `music21.stream.Score`, raise `UnparseableScoreError`.
* `list_corpus_chorales`: the identifiers of the Bach chorales in the music21 corpus, in a stable order, obtained from `music21.corpus.chorales.Iterator(returnType="filename")` (default numbering system `"riemenschneider"`). With its default return type the iterator yields parsed `Score` objects (confirmed against music21 10.5.2); the implementer confirms with the explorer that each filename yielded with `returnType="filename"` is accepted by `music21.corpus.parse`, and adapts the conversion if not.

`ingest/music21_conversion.py`, private helpers used by `sources.py`:

* **Part mapping.** `score.parts` must contain exactly four parts, otherwise `PartCountError(part_count=len(score.parts))`. Parts map to roles by score order, top to bottom: soprano, alto, tenor, bass. Part names are not used (see open question 5).
* **Bars.** For each part, iterate `part.getElementsByClass(music21.stream.Measure)`. Bar onset is `measure.offset`; bar duration is the offset of the next measure minus this one, and `measure.highestTime` for the last measure; bar number is `measure.number` (`measure.numberSuffix` is ignored). The four parts must yield the same bars, otherwise `UnsupportedScoreError`.
* **Note events.** Inside each measure: if `measure.hasVoices()` is true, raise `UnsupportedScoreError` (several voices in one part). Iterate `measure.notesAndRests`; skip `music21.note.Rest`; raise `UnsupportedScoreError` for `music21.chord.Chord`, `music21.note.Unpitched`, and any element with `element.duration.isGrace`. For each `music21.note.Note`: onset is `Fraction(measure.offset) + Fraction(note.offset)`, duration is `Fraction(note.duration.quarterLength)`. music21 offsets are floats only when binary exact and `Fraction` otherwise (`music21.common.opFrac`), so `Fraction(value)` is exact.
* **Pitch.** `note.pitch.step`, `note.pitch.implicitOctave` (the octave, defaulting to 4 when absent) and `note.pitch.accidental.alter` when `note.pitch.accidental` is not `None`, else 0. A non integer `alter` (microtone) raises `UnsupportedScoreError`.
* **Ties.** `note.tie` is `None` or a `music21.tie.Tie` whose `type` is `"start"`, `"stop"` or `"continue"`, mapped to `TieType`. The types `"let-ring"` and `"continue-let-ring"` raise `UnsupportedScoreError`.
* **Key and time signatures.** From the soprano part: `part.recurse().getElementsByClass(music21.key.KeySignature)` (this includes `music21.key.Key`, a subclass) gives `sharps`; `part.recurse().getElementsByClass(music21.meter.TimeSignature)` gives `numerator` and `denominator`. Onsets come from `element.getOffsetInHierarchy(part)`. Consecutive duplicates (the same signature restated) are collapsed. A score without a time signature at onset 0 raises `UnsupportedScoreError`; a score without a key signature at onset 0 gets `sharps=0` at onset 0.

`ingest/grand_staff_reader.py`, used by `read_grand_staff_file` to read files written by `render/`:

* Parse with `music21.converter.parse`. A MusicXML part with two staves is parsed by music21 into two `music21.stream.PartStaff` objects in `score.parts`; there must be exactly two, otherwise `PartCountError`.
* Each measure of each staff holds `music21.stream.Voice` objects. Voices are identified by their position in `measure.voices` (first is voice 1, second is voice 2), then mapped to roles through `PIANO_LAYOUT`. The implementer verifies with a test that music21 preserves this order on the files the renderer writes; if it does not, identify voices by `voice.id` instead and record the finding in the PR.
* Bars, notes, pitches, ties and signatures are converted with the same rules as above, applied per voice instead of per part.

### 3.5 Rendering (`render/piano_score.py`)

Boundary module (ADR 0003). Public interface:

```python
def write_piano_score(score: FourVoiceScore, output_path: Path, layout: GrandStaffLayout = PIANO_LAYOUT) -> None: ...
```

Behavior, through private helpers:

* Builds a `music21.stream.Score` with two `music21.stream.PartStaff` objects (upper with `music21.clef.TrebleClef`, lower with `music21.clef.BassClef`), joined by `music21.layout.StaffGroup([upper, lower], symbol="brace")` inserted in the score.
* For every `Bar`, one `music21.stream.Measure(number=bar.number)` per staff. When the bar is shorter than its time signature, set `measure.paddingLeft` (first bar, the pickup) or `measure.paddingRight` (any later bar) to the missing length.
* Key and time signatures are inserted at the start of the bar where they change, as `music21.key.KeySignature(sharps)` and `music21.meter.TimeSignature(f"{numerator}/{denominator}")`, on both staves.
* Each measure contains two `music21.stream.Voice` objects with ids `"1"` and `"2"`, filled with the events of the roles placed there by the layout. Gaps inside a bar are filled with `music21.note.Rest` objects of exactly the gap length, so every voice fills every bar.
* Each event becomes a `music21.note.Note` with `quarterLength=duration`, a `music21.pitch.Pitch` built from `step`, `octave` and `music21.pitch.Accidental(alter)` when `alter != 0`, and `note.tie = music21.tie.Tie(tie.value)` when tied. Stems: `note.stemDirection = "up"` in voice 1 and `"down"` in voice 2, the usual convention for two voices on one staff.
* Writes with `score.write("musicxml", fp=output_path)`. A failure to write raises `OSError` as is; it is an I/O error, not a domain error.

Instrument and staff names are left empty until Nico decides (open question 5).

### 3.6 Command line (`cli.py`)

`src/aretz_texture/cli.py`, at the top of the package, so it can import `ingest/` and `render/` without breaking any contract. It uses only `argparse` from the standard library.

```python
def main(argv: Sequence[str] | None = None) -> int: ...
```

```
aretz-texture reduce SOURCE --output PATH
```

* `SOURCE`: a MusicXML file path or a music21 corpus identifier.
* `--output`, `-o`: required; the MusicXML file to write. An existing file is overwritten.
* Flow: `read_four_voice_score(source)` then `write_piano_score(score, output_path)`.
* Exit codes: 0 on success; 2 for usage errors (argparse default); 1 for any `AretzTextureError`, with its message written to standard error through `sys.stderr.write` (ruff forbids `print`). Other exceptions propagate.

`pyproject.toml`:

```toml
[project.scripts]
aretz-texture = "aretz_texture.cli:main"
```

`main` returns the exit code; the script wrapper generated by the build backend passes it to `sys.exit`.

### 3.7 Round trip comparison (`eval/round_trip.py`)

```python
class DifferenceKind(StrEnum):
    MISSING_EVENT = "missing_event"      # in the original, not in the output
    EXTRA_EVENT = "extra_event"          # in the output, not in the original
    ALTERED_EVENT = "altered_event"      # same voice and onset, different pitch, duration or tie
    BARS = "bars"
    KEY_SIGNATURES = "key_signatures"
    TIME_SIGNATURES = "time_signatures"

class RoundTripDifference(BaseModel):  # frozen
    kind: DifferenceKind
    role: VoiceRole | None               # None for score level differences
    onset: Fraction | None               # None for score level differences
    description: str                     # human readable, includes the bar number when known

class ChoraleOutcome(StrEnum):
    IDENTICAL = "identical"
    DIFFERENT = "different"
    UNSUPPORTED = "unsupported"          # ingestion raised UnsupportedScoreError

class ChoraleRoundTrip(BaseModel):     # frozen
    identifier: str
    outcome: ChoraleOutcome
    differences: tuple[RoundTripDifference, ...]
    reason: str                          # message of the UnsupportedScoreError, empty otherwise

def compare_scores(original: FourVoiceScore, returned: FourVoiceScore) -> tuple[RoundTripDifference, ...]: ...
def round_trip_chorale(identifier: str, work_directory: Path) -> ChoraleRoundTrip: ...
```

* `round_trip_chorale`: `read_four_voice_score(identifier)`, `write_piano_score` into `work_directory`, `read_grand_staff_file`, `compare_scores`.
* `compare_scores` is pure. Within a voice, events are aligned by onset (a voice never has two events at the same onset). Equal means:
  * the same bars (number, onset, duration), hence the same pickup bar;
  * the same key signature changes and time signature changes;
  * in each of the four voices, the same set of onsets, and for each onset the same `duration`, the same `SpelledPitch` (step, alter, octave) and the same `tie`.
* Deliberately ignored, because the core model does not carry them in this spec: rests (implied by the events), accidental display (cautionary or courtesy accidentals, `Accidental.displayStatus`), mode of the key (`music21.key.Key.mode`), clefs, stem directions, beaming, part and instrument names, title and other metadata, lyrics, fermatas, dynamics, articulations, slurs, tempo, repeat barlines and endings, bar number suffixes, layout.

Because the comparison works on core objects, it cannot see what ingestion drops. Ingestion therefore never drops a pitched note silently: anything it cannot represent raises `UnsupportedScoreError` (section 3.4), and acceptance criterion 9 checks note counts directly against music21.

### 3.8 Configuration and contracts in `pyproject.toml`

* `dependencies = ["music21>=10.5,<11", "pydantic>=2.10,<3"]`, added with `uv add`, which updates `uv.lock`.
* Boundary modules start with:
  `# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportMissingTypeStubs=false` followed by `# See ADR 0003: music21 is untyped; this module is the boundary.` Only the rules that actually fire are listed.
* import-linter: set `include_external_packages = true` under `[tool.importlinter]` and add:
  * "music21 only at the boundary": forbidden, sources `core`, `analysis`, `voicing`, `eval`, `cli`, forbidden module `music21`, with `allow_indirect_imports = true` (`eval` and `cli` reach music21 through `ingest/` and `render/`, which is intended).
  * "nothing imports the command line": forbidden, sources all six subpackages, forbidden module `aretz_texture.cli`.
  * "the command line does not import eval": forbidden, source `aretz_texture.cli`, forbidden module `aretz_texture.eval`.

### 3.9 Data flow

Command line:

1. `ingest.sources.read_four_voice_score(SOURCE)` returns a `FourVoiceScore`.
2. `render.piano_score.write_piano_score(score, PATH)` writes the grand staff MusicXML.

Evaluation, per chorale:

1. Steps 1 and 2 above, writing into a temporary directory.
2. `ingest.sources.read_grand_staff_file(PATH)` reads the written file back into a `FourVoiceScore`.
3. `eval.round_trip.compare_scores(original, returned)` lists the differences.

## 4. Acceptance criteria

### 001a: model and ingestion

1. `music21` and `pydantic` are runtime dependencies in `pyproject.toml` and `uv.lock`, with the bounds of ADR 0003.
2. Every core model is immutable: assigning to a field raises `ValidationError`.
3. `Voice` rejects events that are unsorted or overlapping, and `FourVoiceScore` rejects bars that are not contiguous from 0 or a voice whose `role` does not match its field.
4. `SpelledPitch(step="F", alter=1, octave=4)` and `SpelledPitch(step="G", alter=-1, octave=4)` are not equal.
5. `read_four_voice_score("bwv66.6")` returns four voices whose roles follow score order, and its key signature, time signature and bars match the values music21 reports for that chorale.
6. A note tied across a bar line in the source becomes two events with `TieType.START` and `TieType.STOP`, each with its notated duration.
7. A score with a number of parts other than four raises `PartCountError` carrying the actual count.
8. A part containing a chord, several voices, a grace note or a microtonal accidental raises `UnsupportedScoreError`; a missing file or unknown corpus identifier raises `UnparseableScoreError`.
9. For every chorale accepted by ingestion in the corpus, the number of events in each voice equals the number of `music21.note.Note` objects in the corresponding part (slow).
10. `lint-imports` passes with the new contracts, and a module outside `ingest/` and `render/` that imports music21 makes it fail.

### 001b: rendering and command line

11. `write_piano_score` on BWV 66.6 writes a MusicXML file with one part of two staves (treble and bass clef) joined by a brace, soprano and alto in the upper staff, tenor and bass in the lower.
12. Writing any `FourVoiceScore` and reading it back with `read_grand_staff_file` gives an equal `FourVoiceScore` (hypothesis property, and the BWV 66.6 case).
13. A pickup bar survives the round trip: same bar number, onset and duration, and `pickup_duration()` unchanged.
14. In the written file every voice fills every bar, with rests in the gaps.
15. `aretz-texture reduce bwv66.6 --output PATH` exits with 0 and writes PATH; with a file path as SOURCE it behaves the same.
16. `aretz-texture reduce` with an unknown source exits with 1 and writes the error message to standard error; without `--output` it exits with 2.
17. **Manual, by Nico:** the output for BWV 66.6 opened in Sibelius shows the same chorale on two staves, with the same pitches, accidentals, ties and rhythm as the original. Recorded as a checked box in the PR description.

### 001c: evaluation

18. `compare_scores` returns no differences for a score compared with itself, and returns exactly one difference of the right kind for each single change: a removed event, an added event, a changed pitch spelling, duration or tie, a changed bar, key signature or time signature.
19. The slow corpus test runs `round_trip_chorale` on every identifier of `list_corpus_chorales()` and asserts that no chorale has outcome `DIFFERENT`.
20. The set of chorales with outcome `UNSUPPORTED` equals the list committed in `tests/eval/expected_unsupported_chorales.txt`, one identifier per line with its reason. A chorale that changes outcome in either direction fails the test, so a new rejection is a visible regression.
21. All commit checks pass (`uv run pre-commit run --all-files`), and the full test suite passes in CI.

## 5. Test plan

Tests may import music21 directly to build fixtures and to inspect written files: the import contracts apply to the package, not to `tests/`. Hand written MusicXML fixtures, if any, are tiny, written for the test and in the public domain.

### Concrete cases

* **BWV 66.6** (`"bwv66.6"`), the chorale named in the issue. Ingestion test (criterion 5): four voices, the key signature (three sharps, confirmed against music21 10.5.2 on November 7, 2026), and the time signature, pickup and bar numbers as reported by music21. The implementer reads these expected values from music21 once with the explorer, writes them as literals in the test, and lists them in the PR so Nico can check them against the score. Rendering tests (criteria 11 to 14) and the command line tests (criteria 15 and 16) also use it.
* **A chorale with a pickup bar** (criterion 13). If BWV 66.6 has one, it serves; otherwise the explorer picks the first chorale of `list_corpus_chorales()` whose first bar is shorter than its time signature.
* **A chorale with a tie across a bar line** (criterion 6): the explorer picks the first chorale in the corpus with a `"start"` tie on the last note of a measure, and the test names the chorale, the voice and the bar number.
* **A chorale with accidentals outside the key signature** (criteria 4 and 12): the explorer picks a chorale and bar with a raised leading tone in a minor key or a chromatic note, and the test asserts the spelled pitch of that note after ingestion and after the round trip.
* **Error cases** built in the test with music21: a score with three parts and one with five parts (`PartCountError`), a part with a chord in one bar, a part with two voices in one bar, a grace note, a quarter tone accidental (`UnsupportedScoreError`), a nonexistent path and the identifier `"bwv0.0"` (`UnparseableScoreError`).
* **Command line**: call `main([...])` directly with `tmp_path`; check the exit code, the file written and the content of standard error with `capsys`.
* **Comparison** (criterion 18): start from a small `FourVoiceScore` built in the test and apply one change per test.

The chorale identifiers and bar numbers chosen by the explorer are written in the tests and listed in the PR description. This spec does not name them because they must be verified against the installed corpus, not recalled.

### Hypothesis properties

A strategy `four_voice_scores()` in `tests/strategies.py` builds valid `FourVoiceScore` values: one time signature from a small set (2/4, 3/4, 4/4, 3/2), an optional pickup bar shorter than the bar, a few bars, and for each voice a sequence of events that tiles each bar from durations in {1/2, 1, 3/2, 2, 3, 4} and triplet eighths (1/3) in groups that complete a beat, with gaps left as rests, spelled pitches with `alter` in {-1, 0, 1} within a plausible range per voice, and ties only between consecutive events of the same spelled pitch with no gap between them.

* **Round trip identity** (criterion 12): `read_grand_staff_file(write(score)) == score`. Each example writes a file, so the test uses a bounded `max_examples` and is marked slow if it exceeds a few seconds.
* **Comparison is reflexive**: `compare_scores(score, score) == ()`.
* **Comparison detects removal**: removing any one event from any voice yields exactly one `MISSING_EVENT` at that voice and onset.
* **Voice invariants**: for any generated voice, events are sorted and consecutive events do not overlap; constructing a `Voice` with any two events swapped raises `ValidationError`.
* **Bars tile the score**: the sum of bar durations equals the onset of the end of the last bar, and every event lies within the bars.

## 6. Open questions for Nico

1. **Fermatas.** Should fermatas be preserved in this spec (one more field on `NoteEvent` and in the comparison), or left for later? They mark phrase endings, which later analysis will likely want.
2. **Lyrics.** Should the chorale text be carried to the piano score (for example, under the upper staff), or dropped? Dropping is simpler; keeping helps to relate phrases to the text.
3. **Chorales that are not four plain voices.** Some corpus files may have more than four parts (instrumental parts), chords in one part (a divided final chord) or two voices in one part. This spec rejects them as unsupported and lists them. Is that acceptable for now, or should some of them be handled (for example, by taking the top note of a divided chord)?
4. **Repeats.** Chorales with repeated first phrases lose their repeat barlines and endings in this spec, and the round trip ignores them. Should the piano score show them?
5. **Part mapping and staff names.** Parts are mapped to soprano, alto, tenor and bass by score order, ignoring their names. Is that the rule you want? And which names should appear on the grand staff: "Piano", the four voice names, or nothing?
6. **Cautionary accidentals.** Courtesy accidentals in the original are not kept; music21 decides which accidentals to print from the key signature. Is that acceptable for the Sibelius check?
7. **Command name.** The issue uses `reduce`, although this slice does not reduce anything yet. Keep `reduce` from the start, or use another subcommand (for example `piano`) until the reduction exists?

## 7. Notes for the implementer

* Verify every music21 name used here against the installed package (`.venv/lib/python3.12/site-packages/music21/`) through the explorer before writing the code that relies on it; record any difference in the PR.
* ADR 0003 must be accepted by Nico together with this spec.
