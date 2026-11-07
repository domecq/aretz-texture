# Spec 001: chorale round trip

Issue: #7, "Read a Bach chorale and write it back as a piano score"
Status: Draft, revised with Nico's decisions of November 7, 2026, awaiting gate 1
Related: ADR 0003 (music21 boundary and runtime dependencies)

**Main point to review:** the omission criterion in section 3.5, which decides what is kept and what is dropped when a score has more than four voices. Nico approves it when he merges this spec.

## 1. Context

As a musician, Nico wants to give the tool a four voice chorale and get back a MusicXML file on a piano grand staff that he can open in Sibelius, to check by eye that nothing is lost on the way in and out. This is the first end to end slice: no reduction or analysis yet, only ingestion, the core data model and rendering.

Expected by the issue:

* A command that accepts a chorale from the music21 corpus or a MusicXML file path and writes the piano score (named `aretz-texture piano` by decision 7).
* A two staff piano score: bass and tenor in the left hand, alto and soprano in the right hand.
* Each voice keeps its own rhythm (not block chords). Pitches, accidentals, ties and rhythm must match the original exactly.
* An automated round trip over the chorales of the music21 corpus finds no lost or altered notes. This is the start of the evaluation corpus (`eval/`), marked as a slow test.

Nico added (decision 3): no harmonic information may be lost silently. When a score has more than four voices, whatever is dropped is chosen by an explicit criterion and listed in the output.

## 2. Scope

### In

* Core data model for a notated four voice score: note events (including divided events and fermatas), voices, bars, key and time signatures (`core/`).
* Omissions: the record of everything ingestion did not carry into the score, and the check of whether each one removes a pitch class (`core/`).
* Domain exceptions in `core/errors.py`.
* Reading a score (corpus identifier or MusicXML path) into the core model, choosing four voices when there are more (`ingest/`).
* Writing the core model as a MusicXML grand staff piano score (`render/`).
* Reading back a grand staff piano score written by this tool, so the round trip can be verified (`ingest/`).
* Command line entry point `aretz-texture piano`, which also prints the omission report.
* Round trip comparison and the slow corpus evaluation (`eval/`).
* Runtime dependencies music21 and pydantic, and the import contracts of ADR 0003.

### Out

* Any reduction, segmentation or analysis. The `reduce` subcommand is reserved for when reduction exists (decision 7).
* Block chords at every attack (a `chordify` style rendering mode).
* Transposing instruments, repeat expansion and the rest of the normalization step (architecture, section 3).
* **Lyrics.** Not read, not written and not compared in this slice; the piano score has no text. Respecting lyrics is a requirement for a later spec (decision 2); section 3.2 shows how they will attach to note events. When the source has lyrics, the command line says that they were ignored.
* Repeat barlines and endings (decision 4).
* Dynamics, articulations other than fermatas, slurs and tempo marks.
* Courtesy and cautionary accidentals (decision 6): music21 decides which accidentals to print from the key signature.
* Staff and instrument names on the grand staff (decision 5).
* Closed score input, where one part carries two voices throughout (for example soprano and alto on one staff), see open question 2.
* Engraving quality beyond what Sibelius needs to show the chorale correctly (beaming, spacing, system breaks).

### Delivery

The issue is larger than one small pull request. It is delivered in four pull requests, in this order, each with its own acceptance criteria:

* **001a, model and ingestion of four parts**: dependencies, `core/` models including divided events and fermatas, `core/errors.py`, `ingest/` for scores with exactly four parts. Anything that would need an omission (more than four parts, several voices in one part, grace notes, a fermata on a rest) raises `UnsupportedScoreError` in this pull request. Glossary.
* **001b, rendering and command line**: `render/`, the grand staff reader in `ingest/`, `cli.py`, `[project.scripts]`.
* **001c, evaluation**: `eval/round_trip.py` and the slow corpus test.
* **001d, omissions**: `core/omissions.py`, the omission criterion of section 3.5 in `ingest/`, the omission report in the command line and in the evaluation. The cases that raised `UnsupportedScoreError` in 001a become omissions, and the list of unsupported chorales shrinks.

## 3. Design

### 3.1 Modules touched

```
pyproject.toml                         dependencies, script, pyright and import-linter changes
src/aretz_texture/core/errors.py       domain exceptions
src/aretz_texture/core/notation.py     SpelledPitch, TieType, EventPitch, NoteEvent, VoiceRole, Voice
src/aretz_texture/core/score.py        Bar, KeySignatureChange, TimeSignatureChange, FourVoiceScore
src/aretz_texture/core/grand_staff.py  GrandStaffLayout and the default piano layout
src/aretz_texture/core/omissions.py    OmissionReason, Omission, removes_pitch_class (001d)
src/aretz_texture/ingest/music21_conversion.py   boundary: music21 stream to core
src/aretz_texture/ingest/voice_selection.py      boundary: choice of four parts and lines (001d)
src/aretz_texture/ingest/grand_staff_reader.py   boundary: music21 grand staff to core
src/aretz_texture/ingest/sources.py              boundary: file paths and corpus identifiers
src/aretz_texture/render/piano_score.py          boundary: core to music21 grand staff, MusicXML
src/aretz_texture/eval/round_trip.py             comparison and corpus evaluation
src/aretz_texture/cli.py                         argparse entry point and omission report
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
    def pitch_class(self) -> int: ...   # 0 to 11, C is 0; enharmonic spellings share it

class TieType(StrEnum):
    START = "start"
    CONTINUE = "continue"
    STOP = "stop"

class EventPitch(BaseModel):
    pitch: SpelledPitch
    tie: TieType | None # None when this pitch is not tied

class NoteEvent(BaseModel):
    onset: Fraction     # quarter lengths from the start of the first bar; >= 0
    duration: Fraction  # quarter lengths; > 0
    pitches: tuple[EventPitch, ...]   # one pitch, or several in a divided event; highest first
    fermata: bool

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
    bars: tuple[Bar, ...]                              # contiguous, starting at onset 0
    key_signatures: tuple[KeySignatureChange, ...]     # first one at onset 0
    time_signatures: tuple[TimeSignatureChange, ...]   # first one at onset 0
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
* **Divided events.** When a voice divides into a chord (for example a divided final chord in the bass), the chord is one `NoteEvent` with several `EventPitch` values, each with its own tie, as in MusicXML. This keeps every pitch of the divided chord with no loss; choosing one pitch per voice is the job of the future voicing step, not of ingestion. `pitches` is never empty, is ordered from highest to lowest sounding pitch (ties between enharmonic spellings broken by step order), and never contains the same `SpelledPitch` twice.
* **Fermatas** (decision 1) are a property of the event (`fermata`), so a fermata on a divided event covers the whole chord, as in notation.
* **Rests are not stored.** Silence in a voice is the time not covered by its events. The renderer writes rests in the gaps. This makes "no lost or altered notes" a statement about events only.
* **Spelling is kept, enharmonics are different.** F sharp 4 and G flat 4 are different `SpelledPitch` values; they share a pitch class.
* **Bars are explicit.** The renderer rebuilds bars from `bars`, not from the time signature, so pickup bars, short final bars and short bars in the middle of a chorale survive the round trip. A pickup bar is the first bar when its duration is shorter than the bar length given by its time signature.
* **Room for lyrics** (decision 2, later spec). Lyrics will attach to the note event, not to a pitch, because a syllable is sung on the event even when the voice divides. The expected shape is a field `lyrics: tuple[Lyric, ...]` on `NoteEvent`, defaulting to empty, where `Lyric` holds the verse number, the syllable text and its syllabic position (single, begin, middle, end), mirroring `music21.note.Lyric`. Because the field has a default, adding it will not break any constructor written for this spec. Nothing in this spec reads, writes or compares lyrics.
* Validators enforce the structural invariants at construction: positive durations, nonempty and ordered `pitches` without duplicates, sorted and non overlapping events within a voice, contiguous bars starting at 0, the first key and time signature at onset 0, and the voice in each field having the matching `role`. Violations raise pydantic `ValidationError`; these are programming errors, not user errors.

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

`core/omissions.py` (001d):

```python
class OmissionReason(StrEnum):
    EXTRA_PART = "extra_part"                   # the part was not chosen as one of the four voices
    EXTRA_VOICE_IN_PART = "extra_voice_in_part" # a second voice of a chosen part, with its own rhythm
    DUPLICATE_PITCH = "duplicate_pitch"         # the same spelled pitch twice in one divided event
    GRACE_NOTE = "grace_note"
    FERMATA_ON_REST = "fermata_on_rest"

class Omission(BaseModel):
    reason: OmissionReason
    part_name: str          # as written in the source; empty when the part has no name
    part_number: int        # 1 based position of the part in the score, top to bottom
    bar_number: int
    beat: Fraction          # music21 beat of the element, 1 based, as a musician counts it
    onset: Fraction
    duration: Fraction      # 0 for grace notes
    pitch: SpelledPitch | None   # None for a fermata on a rest
    removes_pitch_class: bool    # see section 3.5, rule 6

class IngestedScore(BaseModel):
    score: FourVoiceScore
    omissions: tuple[Omission, ...]   # sorted by onset, then part number
    has_lyrics: bool                  # the source had lyrics, which this spec ignores

def removes_pitch_class(pitch: SpelledPitch, onset: Fraction, duration: Fraction, score: FourVoiceScore) -> bool: ...
```

`removes_pitch_class` is pure and lives in `core/` so that it can be tested without music21. In 001a, `IngestedScore` already exists, with `omissions` always empty.

### 3.3 Domain exceptions (`core/errors.py`)

```python
class AretzTextureError(Exception): ...                # base of every domain error
class UnparseableScoreError(AretzTextureError): ...    # file missing, not MusicXML, corpus id not found
class UnsupportedScoreError(AretzTextureError): ...    # parses, but cannot be mapped to the model
class PartCountError(UnsupportedScoreError):
    part_count: int                                    # fewer than four parts
class AmbiguousVoiceMappingError(UnsupportedScoreError):
    part_names: tuple[str, ...]                        # more than four parts, names do not decide
```

`UnsupportedScoreError` is kept only for what truly cannot be mapped: fewer than four parts, more than four parts without the names to choose them, microtonal accidentals, unpitched notes, `"let-ring"` ties, and parts whose bars do not line up. `AmbiguousHarmonyError`, mentioned in `AGENTS.md`, is not created here; it belongs to the first analysis spec.

### 3.4 Ingestion (`ingest/`)

All ingestion modules are music21 boundary modules (ADR 0003): they start with the file level pyright comment and expose only core and standard library types.

`ingest/sources.py`:

```python
def read_score(source: str) -> IngestedScore: ...
def read_grand_staff_file(path: Path) -> FourVoiceScore: ...
def list_corpus_chorales() -> tuple[str, ...]: ...
```

* `read_score`: if `source` names an existing file, parse it with `music21.converter.parse(path)`; otherwise treat it as a corpus identifier and call `music21.corpus.parse(source)` (for example `"bwv66.6"` or `"bach/bwv66.6"`). Any music21 failure to find or parse the source is reraised as `UnparseableScoreError` with the original exception chained (`raise ... from error`). If the result is not a `music21.stream.Score`, raise `UnparseableScoreError`.
* `list_corpus_chorales`: the identifiers of the Bach chorales in the music21 corpus, in a stable order, obtained from `music21.corpus.chorales.Iterator(returnType="filename")` (default numbering system `"riemenschneider"`). With its default return type the iterator yields parsed `Score` objects (confirmed against music21 10.5.2); the implementer confirms with the explorer that each filename yielded with `returnType="filename"` is accepted by `music21.corpus.parse`, and adapts the conversion if not.

`ingest/music21_conversion.py`, private helpers:

* **Bars.** For each part, iterate `part.getElementsByClass(music21.stream.Measure)`. Bar onset is `measure.offset`; bar duration is the offset of the next measure minus this one, and `measure.highestTime` for the last measure; bar number is `measure.number` (`measure.numberSuffix` is ignored). The chosen parts must yield the same bars, otherwise `UnsupportedScoreError`.
* **Note events.** Inside each measure of a part without voices (`measure.hasVoices()` false), iterate `measure.notesAndRests`. A `music21.note.Note` becomes an event with one pitch; a `music21.chord.Chord` becomes a divided event with one `EventPitch` per `chord.notes` element. Rests are skipped. Onset is `Fraction(measure.offset) + Fraction(element.offset)`, duration is `Fraction(element.duration.quarterLength)`. music21 offsets are floats only when binary exact and `Fraction` otherwise (`music21.common.opFrac`), so `Fraction(value)` is exact. `music21.note.Unpitched` raises `UnsupportedScoreError`. Grace notes (`element.duration.isGrace`), measures with voices and fermatas on rests follow section 3.5 (in 001a they raise `UnsupportedScoreError`).
* **Pitch.** `pitch.step`, `pitch.implicitOctave` (the octave, defaulting to 4 when absent) and `pitch.accidental.alter` when `pitch.accidental` is not `None`, else 0. A non integer `alter` (microtone) raises `UnsupportedScoreError`.
* **Ties.** `note.tie` (for a chord, the `tie` of each element of `chord.notes`) is `None` or a `music21.tie.Tie` whose `type` is `"start"`, `"stop"` or `"continue"`, mapped to `TieType`. The types `"let-ring"` and `"continue-let-ring"` raise `UnsupportedScoreError`.
* **Fermatas.** `fermata` is true when `element.expressions` contains a `music21.expressions.Fermata`.
* **Lyrics.** Not converted. `has_lyrics` is true when any note of the chosen parts has a nonempty `note.lyrics`.
* **Key and time signatures.** From the soprano part: `part.recurse().getElementsByClass(music21.key.KeySignature)` (this includes `music21.key.Key`, a subclass) gives `sharps`; `part.recurse().getElementsByClass(music21.meter.TimeSignature)` gives `numerator` and `denominator`. Onsets come from `element.getOffsetInHierarchy(part)`. Consecutive duplicates (the same signature restated) are collapsed. A score without a time signature at onset 0 raises `UnsupportedScoreError`; a score without a key signature at onset 0 gets `sharps=0` at onset 0.

`ingest/grand_staff_reader.py`, used by `read_grand_staff_file` to read files written by `render/`:

* Parse with `music21.converter.parse`. A MusicXML part with two staves is parsed by music21 into two `music21.stream.PartStaff` objects in `score.parts`; there must be exactly two, otherwise `PartCountError`.
* Each measure of each staff holds `music21.stream.Voice` objects. Voices are identified by their position in `measure.voices` (first is voice 1, second is voice 2), then mapped to roles through `PIANO_LAYOUT`. The implementer verifies with a test that music21 preserves this order on the files the renderer writes; if it does not, identify voices by `voice.id` instead and record the finding in the PR.
* Bars, notes, chords, pitches, ties, fermatas and signatures are converted with the same rules as above, applied per voice instead of per part. Files written by this tool never produce omissions.

### 3.5 Omission criterion (001d, main point to review)

**Harmonic information** is, for this spec, the set of pitch classes sounding at each instant of the score. The criterion keeps all of it whenever the notation allows, and when it cannot, it says so for each dropped note.

1. **Exactly four parts.** They map to soprano, alto, tenor and bass in score order, top to bottom (decision 5). Part names are not used.
2. **Fewer than four parts.** `PartCountError`. Splitting a closed score into voices is a later spec (open question 2).
3. **More than four parts** (for example instrumental parts doubling or accompanying the voices). The four voices are the parts whose `part.partName`, trimmed and compared without case, is exactly `"Soprano"`, `"Alto"`, `"Tenor"` and `"Bass"`, one part each. If the names do not identify exactly one part for each role, raise `AmbiguousVoiceMappingError` listing all the part names. Every note of every other part is an omission with reason `EXTRA_PART`. The explorer lists the part names actually used in the corpus files with more than four parts; if they use other names (for example `"S."` or `"Basso"`), the PR proposes the list of accepted names for Nico to approve.
4. **Several voices in one bar of a chosen part** (`measure.hasVoices()` true). If all the voices of that bar have the same onsets and durations, they merge into divided events, with no loss. Otherwise the first voice in `measure.voices` is kept, and every note of the other voices in that bar is an omission with reason `EXTRA_VOICE_IN_PART`.
5. **Notes that carry no duration or no event.** Grace notes are omissions with reason `GRACE_NOTE`, with duration 0. A fermata on a rest is an omission with reason `FERMATA_ON_REST` and pitch `None`. The same spelled pitch twice in one divided event (a unison divided chord) keeps one copy; the other is an omission with reason `DUPLICATE_PITCH`.
6. **Lossy omissions.** An omission with a pitch is flagged `removes_pitch_class` when there is an instant within its span (from its onset to its onset plus duration; for a grace note, its onset) at which no event of the four kept voices sounds its pitch class. An event sounds from its onset until its onset plus duration. The check runs at the omission onset and at every onset of a kept event inside its span, which are the only instants where the kept pitch classes change.
7. **Report.** Every omission is listed, lossy or not, sorted by onset and then part number. No pitched note of the source is ever discarded without an omission.

Rule 4 is the place where a musical choice is made: when two voices in one part move in different rhythms, one is dropped and flagged. The alternative is to slice both voices at every attack and tie the pieces into divided events: that keeps every pitch class, but changes the notation of the source, so the round trip would no longer match it note for note. This spec proposes keeping the first voice; Nico confirms or picks the alternative at gate 1.

### 3.6 Rendering (`render/piano_score.py`)

Boundary module (ADR 0003). Public interface:

```python
def write_piano_score(score: FourVoiceScore, output_path: Path, layout: GrandStaffLayout = PIANO_LAYOUT) -> None: ...
```

Behavior, through private helpers:

* Builds a `music21.stream.Score` with two `music21.stream.PartStaff` objects (upper with `music21.clef.TrebleClef`, lower with `music21.clef.BassClef`), joined by `music21.layout.StaffGroup([upper, lower], symbol="brace")` inserted in the score. No part, staff or instrument names (decision 5).
* For every `Bar`, one `music21.stream.Measure(number=bar.number)` per staff. When the bar is shorter than its time signature, set `measure.paddingLeft` (first bar, the pickup) or `measure.paddingRight` (any later bar) to the missing length.
* Key and time signatures are inserted at the start of the bar where they change, as `music21.key.KeySignature(sharps)` and `music21.meter.TimeSignature(f"{numerator}/{denominator}")`, on both staves.
* Each measure contains two `music21.stream.Voice` objects with ids `"1"` and `"2"`, filled with the events of the roles placed there by the layout. Gaps inside a bar are filled with `music21.note.Rest` objects of exactly the gap length, so every voice fills every bar.
* An event with one pitch becomes a `music21.note.Note`; a divided event becomes a `music21.chord.Chord` of one `music21.note.Note` per pitch. Each pitch is a `music21.pitch.Pitch` built from `step`, `octave` and `music21.pitch.Accidental(alter)` when `alter != 0`; each tied pitch gets `tie = music21.tie.Tie(tie.value)` on its note. `quarterLength=duration`.
* A fermata is `music21.expressions.Fermata()` appended to `element.expressions`. In voice 2 its `type` is set to `"inverted"`, so it is printed below the staff, the usual placement for the lower voice of a staff (the implementer verifies the attribute name with the explorer).
* Stems: `stemDirection = "up"` in voice 1 and `"down"` in voice 2, the usual convention for two voices on one staff.
* Writes with `score.write("musicxml", fp=output_path)`. A failure to write raises `OSError` as is; it is an I/O error, not a domain error.

### 3.7 Command line (`cli.py`)

`src/aretz_texture/cli.py`, at the top of the package, so it can import `ingest/` and `render/` without breaking any contract. It uses only `argparse` from the standard library.

```python
def main(argv: Sequence[str] | None = None) -> int: ...
```

```
aretz-texture piano SOURCE --output PATH
```

* `SOURCE`: a MusicXML file path or a music21 corpus identifier.
* `--output`, `-o`: required; the MusicXML file to write. An existing file is overwritten.
* Flow: `read_score(source)`, `write_piano_score(ingested.score, output_path)`, then the report.
* **Report** on standard output through `sys.stdout.write` (ruff forbids `print`), in 001d. When there are omissions, a summary line with the count and the number that remove a pitch class, then one line per omission, for example: `bar 12, beat 3, part 5 "Violino 1", G#4, extra part, removes a pitch class`. When `has_lyrics` is true, a line saying that lyrics were ignored. Nothing is printed when there is nothing to report.
* Exit codes: 0 on success, also when there are omissions; 2 for usage errors (argparse default); 1 for any `AretzTextureError`, with its message written to standard error. Other exceptions propagate.
* The `reduce` subcommand does not exist yet (decision 7).

`pyproject.toml`:

```toml
[project.scripts]
aretz-texture = "aretz_texture.cli:main"
```

`main` returns the exit code; the script wrapper generated by the build backend passes it to `sys.exit`.

### 3.8 Round trip comparison (`eval/round_trip.py`)

```python
class DifferenceKind(StrEnum):
    MISSING_EVENT = "missing_event"      # in the original, not in the output
    EXTRA_EVENT = "extra_event"          # in the output, not in the original
    ALTERED_EVENT = "altered_event"      # same voice and onset, different duration, pitches, ties or fermata
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
    omissions: tuple[Omission, ...]      # from ingestion (001d); empty before
    reason: str                          # message of the UnsupportedScoreError, empty otherwise

def compare_scores(original: FourVoiceScore, returned: FourVoiceScore) -> tuple[RoundTripDifference, ...]: ...
def round_trip_chorale(identifier: str, work_directory: Path) -> ChoraleRoundTrip: ...
```

* `round_trip_chorale`: `read_score(identifier)`, `write_piano_score` into `work_directory`, `read_grand_staff_file`, `compare_scores`.
* `compare_scores` is pure. Within a voice, events are aligned by onset (a voice never has two events at the same onset). Equal means:
  * the same bars (number, onset, duration), hence the same pickup bar;
  * the same key signature changes and time signature changes;
  * in each of the four voices, the same set of onsets, and for each onset the same `duration`, the same `pitches` (each `SpelledPitch` and its `tie`, in order) and the same `fermata`.
* Deliberately ignored, because the core model does not carry them in this spec: rests (implied by the events), accidental display, mode of the key (`music21.key.Key.mode`), clefs, stem directions, fermata placement, beaming, part and instrument names, title and other metadata, lyrics, dynamics, other articulations, slurs, tempo, repeat barlines and endings, bar number suffixes, layout.

The comparison works on core objects, so it cannot see what ingestion drops. That is covered by the omissions (section 3.5, rule 7) and by acceptance criterion 26, which checks that kept and omitted notes add up to the notes music21 reads.

### 3.9 Configuration and contracts in `pyproject.toml`

* `dependencies = ["music21>=10.5,<11", "pydantic>=2.10,<3"]`, added with `uv add`, which updates `uv.lock`.
* Boundary modules start with:
  `# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportMissingTypeStubs=false` followed by `# See ADR 0003: music21 is untyped; this module is the boundary.` Only the rules that actually fire are listed.
* The accepted part names of rule 3 are a typed constant in `ingest/voice_selection.py`, with one line explaining their musical meaning.
* import-linter: set `include_external_packages = true` under `[tool.importlinter]` and add:
  * "music21 only at the boundary": forbidden, sources `core`, `analysis`, `voicing`, `eval`, `cli`, forbidden module `music21`, with `allow_indirect_imports = true` (`eval` and `cli` reach music21 through `ingest/` and `render/`, which is intended).
  * "nothing imports the command line": forbidden, sources all six subpackages, forbidden module `aretz_texture.cli`.
  * "the command line does not import eval": forbidden, source `aretz_texture.cli`, forbidden module `aretz_texture.eval`.

### 3.10 Data flow

Command line:

1. `ingest.sources.read_score(SOURCE)` returns an `IngestedScore`: the `FourVoiceScore` and its omissions.
2. `render.piano_score.write_piano_score(ingested.score, PATH)` writes the grand staff MusicXML.
3. `cli` prints the omission report.

Evaluation, per chorale:

1. Steps 1 and 2 above, writing into a temporary directory.
2. `ingest.sources.read_grand_staff_file(PATH)` reads the written file back into a `FourVoiceScore`.
3. `eval.round_trip.compare_scores(original, returned)` lists the differences; the omissions travel with the result.

## 4. Acceptance criteria

### 001a: model and ingestion of four parts

1. `music21` and `pydantic` are runtime dependencies in `pyproject.toml` and `uv.lock`, with the bounds of ADR 0003.
2. Every core model is immutable: assigning to a field raises `ValidationError`.
3. `Voice` rejects events that are unsorted or overlapping; `NoteEvent` rejects empty, unordered or duplicated `pitches`; `FourVoiceScore` rejects bars that are not contiguous from 0 or a voice whose `role` does not match its field.
4. `SpelledPitch(step="F", alter=1, octave=4)` and `SpelledPitch(step="G", alter=-1, octave=4)` are not equal and have the same `pitch_class()`.
5. `read_score("bwv66.6")` returns four voices mapped from the parts named Soprano, Alto, Tenor and Bass in that order, with three sharps, and the time signature and bars music21 reports for that chorale.
6. A note tied across a bar line in the source becomes two events with `TieType.START` and `TieType.STOP`, each with its notated duration.
7. A chord in one part becomes one divided event with every pitch and each pitch's tie.
8. A note with a fermata in the source becomes an event with `fermata` true; every other event has it false.
9. A score with fewer than four parts raises `PartCountError` carrying the actual count.
10. A microtonal accidental, an unpitched note or a `"let-ring"` tie raises `UnsupportedScoreError`; a missing file or unknown corpus identifier raises `UnparseableScoreError`. Until 001d, more than four parts, several voices in one part, a grace note and a fermata on a rest also raise `UnsupportedScoreError`.
11. `lint-imports` passes with the new contracts, and a module outside `ingest/` and `render/` that imports music21 makes it fail.

### 001b: rendering and command line

12. `write_piano_score` on BWV 66.6 writes a MusicXML file with one part of two staves (treble and bass clef) joined by a brace, soprano and alto in the upper staff, tenor and bass in the lower, and no staff or instrument names.
13. Writing any `FourVoiceScore` and reading it back with `read_grand_staff_file` gives an equal `FourVoiceScore` (hypothesis property, and the BWV 66.6 case), including divided events, ties per pitch and fermatas.
14. A pickup bar survives the round trip: same bar number, onset and duration, and `pickup_duration()` unchanged.
15. In the written file every voice fills every bar, with rests in the gaps.
16. `aretz-texture piano bwv66.6 --output PATH` exits with 0 and writes PATH; with a file path as SOURCE it behaves the same.
17. `aretz-texture piano` with an unknown source exits with 1 and writes the error message to standard error; without `--output` it exits with 2; `aretz-texture reduce` is rejected as an unknown subcommand.
18. **Manual, by Nico:** the output for BWV 66.6 opened in Sibelius shows the same chorale on two staves, with the same pitches, accidentals, ties, rhythm and fermatas as the original. Recorded as a checked box in the PR description.

### 001c: evaluation

19. `compare_scores` returns no differences for a score compared with itself, and returns exactly one difference of the right kind for each single change: a removed event, an added event, a changed pitch spelling, duration, tie or fermata, a pitch added to or removed from a divided event, a changed bar, key signature or time signature.
20. The slow corpus test runs `round_trip_chorale` on every identifier of `list_corpus_chorales()` and asserts that no chorale has outcome `DIFFERENT`.
21. The set of chorales with outcome `UNSUPPORTED` equals the list committed in `tests/eval/expected_unsupported_chorales.txt`, one identifier per line with its reason. A chorale that changes outcome in either direction fails the test, so a new rejection is a visible regression.

### 001d: omissions

22. A score with more than four parts, where exactly one part is named for each of Soprano, Alto, Tenor and Bass, keeps those four parts, and every note of the other parts is an omission with reason `EXTRA_PART`, its part name, part number, bar, beat and pitch.
23. A score with more than four parts whose names do not identify the four voices raises `AmbiguousVoiceMappingError` listing the part names.
24. A bar of a chosen part with two voices in the same rhythm becomes divided events with no omission; with two voices in different rhythms, the first voice is kept and each note of the other is an omission with reason `EXTRA_VOICE_IN_PART`.
25. A grace note, a fermata on a rest and a duplicated pitch in a divided event each produce one omission with the matching reason.
26. For every chorale accepted by ingestion in the corpus, in each source part, the number of pitches read by music21 (a note counts one, a chord counts its notes, grace notes included) equals the pitches kept from that part plus its omissions with a pitch (slow).
27. `removes_pitch_class` is false when a kept voice sounds the same pitch class (in any octave or spelling) throughout the omitted note, and true when at some instant within it no kept voice does.
28. The command line prints the omission report described in section 3.7, and the lyrics line when the source has lyrics; it prints nothing for BWV 66.6 apart from the lyrics line if that chorale has lyrics.
29. The slow corpus test also compares, per chorale, the number of omissions and of lossy omissions with `tests/eval/expected_omissions.txt`; any change fails the test, so a new loss of harmonic information is a visible regression.

### All pull requests

30. All commit checks pass (`uv run pre-commit run --all-files`), and the full test suite passes in CI.

## 5. Test plan

Tests may import music21 directly to build fixtures and to inspect written files: the import contracts apply to the package, not to `tests/`. Hand written MusicXML fixtures, if any, are tiny, written for the test and in the public domain.

### Concrete cases

* **BWV 66.6** (`"bwv66.6"`), the chorale named in the issue: four parts named Soprano, Alto, Tenor and Bass, three sharps (confirmed against music21 10.5.2 on November 7, 2026). The time signature, pickup, bar numbers and fermata positions are read from music21 once with the explorer, written as literals in the test (criteria 5 and 8) and listed in the PR so Nico can check them against the score. Rendering (criteria 12 to 15), command line (criteria 16 to 18 and 28) and evaluation tests also use it.
* **A chorale with a pickup bar** (criterion 14). If BWV 66.6 has one, it serves; otherwise the explorer picks the first chorale of `list_corpus_chorales()` whose first bar is shorter than its time signature.
* **A chorale with a tie across a bar line** (criterion 6): the explorer picks the first chorale in the corpus with a `"start"` tie on the last note of a measure, and the test names the chorale, the voice and the bar number.
* **A chorale with accidentals outside the key signature** (criteria 4 and 13): the explorer picks a chorale and bar with a raised leading tone in a minor key or a chromatic note, and the test asserts the spelled pitch of that note after ingestion and after the round trip.
* **Corpus chorales that are not four plain parts** (criteria 7, 22, 24 and 25). music21 is not installed in the repository environment at the time of writing, so the explorer searches the installed corpus for, and the tests name with bar numbers:
  * a chorale with more than four parts (instrumental parts), with the names of its parts;
  * a chorale with a `music21.chord.Chord` in a vocal part, typically a divided final chord;
  * a chorale with `measure.hasVoices()` true in a vocal part, noting whether the voices share their rhythm;
  * a chorale with a grace note, if any.
  If the corpus has no example of a case, the test builds a small score with music21 for it, and the PR says so.
* **Lossy and lossless omissions** (criterion 27), built in the test: an extra part doubling the soprano an octave lower (not lossy); an extra part sounding a seventh that no voice has (lossy); an extra part note that is covered by a kept voice only during its first half (lossy).
* **Error cases** built in the test with music21: scores with one and three parts (`PartCountError`), six parts with generic names (`AmbiguousVoiceMappingError`), a quarter tone accidental, an unpitched note and a `"let-ring"` tie (`UnsupportedScoreError`), a nonexistent path and the identifier `"bwv0.0"` (`UnparseableScoreError`).
* **Command line**: call `main([...])` directly with `tmp_path`; check the exit code, the file written, the report on standard output and the error on standard error with `capsys`.
* **Comparison** (criterion 19): start from a small `FourVoiceScore` built in the test and apply one change per test.

The chorale identifiers and bar numbers chosen by the explorer are written in the tests and listed in the PR description. This spec does not name them because they must be verified against the installed corpus, not recalled.

### Hypothesis properties

A strategy `four_voice_scores()` in `tests/strategies.py` builds valid `FourVoiceScore` values: one time signature from a small set (2/4, 3/4, 4/4, 3/2), an optional pickup bar shorter than the bar, a few bars, and for each voice a sequence of events that tiles each bar from durations in {1/2, 1, 3/2, 2, 3, 4} and triplet eighths (1/3) in groups that complete a beat, with gaps left as rests; spelled pitches with `alter` in {-1, 0, 1} within a plausible range per voice; occasional divided events of two or three pitches; occasional fermatas; and ties only between consecutive events that share the tied spelled pitch with no gap between them.

* **Round trip identity** (criterion 13): `read_grand_staff_file(write(score)) == score`. Each example writes a file, so the test uses a bounded `max_examples` and is marked slow if it exceeds a few seconds.
* **Comparison is reflexive**: `compare_scores(score, score) == ()`.
* **Comparison detects removal**: removing any one event from any voice yields exactly one `MISSING_EVENT` at that voice and onset.
* **Voice invariants**: for any generated voice, events are sorted and consecutive events do not overlap; constructing a `Voice` with any two events swapped raises `ValidationError`.
* **Bars tile the score**: the sum of bar durations equals the onset of the end of the last bar, and every event lies within the bars.
* **Doublings are never lossy**: for any generated score and any pitch sounded by a kept event, an omission with that pitch class in another octave and the same onset and duration has `removes_pitch_class` false.
* **Unsounded pitch classes are always lossy**: an omission whose pitch class no kept event sounds anywhere in the score has `removes_pitch_class` true.

## 6. Decisions

Taken by Nico on November 7, 2026:

1. **Fermatas** are kept now: in the model, the rendering and the round trip comparison.
2. **Lyrics** are out of scope for this slice and are not preserved. Respecting lyrics is a requirement for a later spec; the model leaves room for them on the note event (section 3.2), and the command line says when lyrics were ignored.
3. **Scores with more than four voices** must not lose harmonic information silently. The omission criterion in section 3.5 decides what is dropped, every omission is listed, and lossy ones are flagged. Divided chords are kept whole as divided events. Only what truly cannot be mapped is rejected with an error. Nico approves the criterion when he merges this spec.
4. **Repeats and endings** are later, out of scope.
5. **Part mapping** by score order is the default for exactly four parts; with more than four parts, part names decide (section 3.5). **No staff or instrument names** on the grand staff for now.
6. **Cautionary accidentals** are lost; acceptable.
7. **Command name**: `aretz-texture piano SOURCE --output PATH` for this slice; `reduce` is reserved for when reduction exists.

### Open questions

1. **Manual choice of voices.** When the part names do not identify the four voices, ingestion raises `AmbiguousVoiceMappingError`. Should a later spec add an option to choose the four parts by hand (for example `--voices 2,3,4,5`)?
2. **Closed score input.** Scores where one part carries two voices throughout (soprano and alto on one staff, tenor and bass on the other) currently raise `PartCountError`. Splitting them, including chords that stand for two voices, needs its own spec. Is it a priority, given that most MusicXML exported by students may look like this?

## 7. Notes for the implementer

* Verify every music21 name used here against the installed package (`.venv/lib/python3.12/site-packages/music21/`) through the explorer before writing the code that relies on it; record any difference in the PR. In particular: `chord.notes` and per note ties in a chord, `element.expressions` and the `type` attribute of `music21.expressions.Fermata`, `element.beat` in a pickup bar, and `note.lyrics`.
* ADR 0003 must be accepted by Nico together with this spec.

## 8. Corpus survey

Checked against the music21 10.5.2 corpus on November 7, 2026, to ground the omission criterion in real data. The corpus iterator yields 371 chorales.

* 351 chorales have exactly four parts. 20 have more, from 5 to 15 parts; none has fewer than four.
* Of those 20, 18 have parts named exactly Soprano, Alto, Tenor and Bass, so rule 3 of section 3.5 maps them without ambiguity. The extra parts are instruments (trumpets, horns, oboes, strings, timpani) or continuo and organ.
* Two raise `AmbiguousVoiceMappingError` under the exact name rule:
  * `bach/bwv41.6` combines voice and instrument names (`Soprano Oboe 1 Violin1`, `Alto Oboe 2 Viloin 2`, `Tenor Viola`, `Bass Continuo`; the misspelling is in the corpus).
  * `bach/bwv27.6` is a genuine five voice chorale (`Soprano 1`, `Soprano 2`, `Alto`, `Tenor`, `Bass`). Dropping a soprano here would remove a real voice, not a doubling.
* Divided chords inside a part appear in one chorale (`bach/bwv248.9-1`), and several voices inside one part in one chorale (`bach/bwv248.23-2`). These are the concrete test cases for rule 4.
* Grace notes appear in two chorales, fermatas in 370 and lyrics in 360.
* BWV 66.6: the pickup bar is number 0 and its first note has `beat` 4.0; its fermatas report `type` `"upright"`.
