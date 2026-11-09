# Spec 001: chorale round trip

Issue: #7, "Read a Bach chorale and write it back as a piano score"
Status: Draft, rewritten on November 7, 2026 after the change of theoretical foundation (ADR 0004), awaiting gate 1
Related: ADR 0003 (music21 boundary and runtime dependencies), ADR 0004 (Fessel's textural model), `docs/theory/fessel_textural_model.md`

**Main points to review:** the lossless core model of section 3.2 (every part, every notated voice, divided events kept whole) and the scope of the `piano` command in section 3.7 (exactly four parts, placed in score order). Nico approves both when he merges this spec.

## 1. Context

As a musician, Nico wants to give the tool a four voice chorale and get back a MusicXML file on a piano grand staff that he can open in Sibelius, to check by eye that nothing is lost on the way in and out. This is the first end to end slice: no reduction or analysis yet, only ingestion, the core data model and rendering.

Expected by the issue:

* A command that accepts a chorale from the music21 corpus or a MusicXML file path and writes the piano score (named `aretz-texture piano` by decision 8).
* A two staff piano score: the two lower parts in the left hand, the two upper parts in the right hand.
* Each part keeps its own rhythm (not block chords). Pitches, accidentals, ties and rhythm must match the original exactly.
* An automated round trip over the chorales of the music21 corpus finds no lost or altered notes. This is the start of the evaluation corpus (`eval/`), marked as a slow test.

Since the issue was written, Nico decided that the analysis is based on Pablo Fessel's model of textural strata (ADR 0004). Its key principle is that the number of parts or staves does not determine the number of strata: which notes form melody, bass or accompaniment is decided by analysis, never by part count or part names. For this slice that means ingestion keeps every part of every score, whatever their number, and drops nothing (decision 3).

## 2. Scope

### In

* Core data model for a notated score with any number of parts: note events (including divided events and fermatas), notated voices, parts with their name and instrument, bars, key and time signatures (`core/`).
* Domain exceptions in `core/errors.py`.
* Reading a score (corpus identifier or MusicXML path) into the core model with no loss of notes (`ingest/`).
* Writing the core model as a MusicXML full score, one staff per part (`render/`), used by the evaluation.
* Writing a score of exactly four parts as a MusicXML grand staff piano score (`render/`), and reading it back (`ingest/`).
* Command line entry point `aretz-texture piano`.
* Round trip comparison and the slow corpus evaluation over the 350 distinct corpus chorales (`eval/`).
* Grace notes and fermatas on rests, in the last pull request (section 2, "Delivery").
* Runtime dependencies music21 and pydantic, and the import contracts of ADR 0003.

### Out

* Any textural or harmonic analysis: no strata, no lines, no mapping of parts to soprano, alto, tenor and bass (decision 3). The `reduce` subcommand is reserved for when reduction exists (decision 8).
* Grand staff rendering of scores that do not have exactly four parts (decision 6); it needs the textural analysis of a later spec.
* Block chords at every attack (a `chordify` style rendering mode).
* Transposing instruments, repeat expansion and the rest of the normalization step (architecture, section 3); see open question 2.
* **Lyrics.** Not read, not written and not compared in this slice. Respecting lyrics is a requirement for a later spec (decision 2); section 3.2 shows how they will attach to note events. When the source has lyrics, the command line says that they were ignored.
* **Dynamics**, articulations other than fermatas, slurs and tempo marks. Dynamics are a later addition needed for the intensity factor of the textural model (section 3.3).
* Repeat barlines and endings (decision 5).
* Courtesy and cautionary accidentals (decision 7): music21 decides which accidentals to print from the key signature.
* Staff and instrument names on the grand staff (decision 6). The full score does carry part and instrument names.
* Clefs of the source and the grouping of several staves into one instrument (for example the two staves of an organ part, which become two parts of the model, both with the instrument name).
* Engraving quality beyond what Sibelius needs to show the chorale correctly (beaming, spacing, system breaks).

### Delivery

The issue is larger than one small pull request. It is delivered in four pull requests, in this order, each with its own acceptance criteria:

* **001a, model and ingestion**: dependencies, `core/` models, `core/errors.py`, `ingest/sources.py` and `ingest/music21_conversion.py` for any number of parts and notated voices. Grace notes and fermatas on rests raise `UnsupportedScoreError` in this pull request. The slow lossless count over the corpus. Glossary.
* **001b, rendering and command line**: `core/grand_staff.py`, `render/full_score.py`, `render/piano_score.py`, `ingest/grand_staff_reader.py`, `cli.py`, `[project.scripts]`.
* **001c, evaluation**: `eval/round_trip.py`, the slow corpus test and the committed lists of unsupported chorales and grand staff skips.
* **001d, grace notes and fermatas on rests**: the two model additions of section 3.2, their ingestion, rendering on both routes and comparison. The chorales that were unsupported only because of them leave the committed list.

## 3. Design

### 3.1 Modules touched

```text
pyproject.toml                         dependencies, script, pyright and import-linter changes
src/aretz_texture/core/errors.py       domain exceptions
src/aretz_texture/core/notation.py     SpelledPitch, TieType, EventPitch, NoteEvent, NotatedVoice
                                       (GraceNote, RestFermata in 001d)
src/aretz_texture/core/score.py        Bar, KeySignatureChange, TimeSignatureChange, Part, Score,
                                       IngestedScore
src/aretz_texture/core/grand_staff.py  Staff, StaffVoice, GrandStaffLayout, PIANO_LAYOUT, piano_layout
src/aretz_texture/ingest/music21_conversion.py   boundary: music21 stream to core
src/aretz_texture/ingest/grand_staff_reader.py   boundary: music21 grand staff to core
src/aretz_texture/ingest/sources.py              boundary: file paths and corpus identifiers
src/aretz_texture/render/full_score.py           boundary: core to music21, one staff per part
src/aretz_texture/render/piano_score.py          boundary: core to music21 grand staff
src/aretz_texture/eval/round_trip.py             comparison and corpus evaluation
src/aretz_texture/cli.py                         argparse entry point
```

Module names may change during implementation if the glossary names suggest better ones; public names and types may not without updating this spec.

### 3.2 Core data model (`core/`)

All models are pydantic `BaseModel` with `model_config = ConfigDict(frozen=True)`. Time values are `fractions.Fraction` in quarter lengths (pydantic supports `Fraction` natively since 2.10). Floats never appear in the core.

`core/notation.py`:

```python
StepName = Literal["C", "D", "E", "F", "G", "A", "B"]


class SpelledPitch(BaseModel):
    step: StepName
    alter: int  # semitones: -2 double flat to 2 double sharp
    octave: int  # scientific pitch notation, middle C is C4

    def pitch_class(self) -> int: ...  # 0 to 11, C is 0


class TieType(StrEnum):
    START = "start"
    CONTINUE = "continue"
    STOP = "stop"


class EventPitch(BaseModel):
    pitch: SpelledPitch
    tie: TieType | None  # None when this pitch is not tied


class NoteEvent(BaseModel):
    onset: Fraction  # quarter lengths from the start of the first bar
    duration: Fraction  # quarter lengths, greater than 0
    pitches: tuple[EventPitch, ...]  # several in a divided event; highest first
    fermata: bool


class NotatedVoice(BaseModel):
    events: tuple[NoteEvent, ...]  # sorted by onset, never overlapping
```

`core/score.py`:

```python
class Bar(BaseModel):
    number: int  # the bar number shown in the score; a pickup bar is usually 0
    onset: Fraction
    duration: Fraction  # actual length; shorter than the meter in a pickup bar


class KeySignatureChange(BaseModel):
    onset: Fraction
    sharps: int  # negative for flats


class TimeSignatureChange(BaseModel):
    onset: Fraction
    numerator: int
    denominator: int


class Part(BaseModel):
    name: str | None  # part name as written in the source
    instrument_name: str | None  # source of the timbre factor (ADR 0004)
    key_signatures: tuple[KeySignatureChange, ...]  # first one at onset 0
    voices: tuple[NotatedVoice, ...]  # at least one; notated voice 1 first


class Score(BaseModel):
    bars: tuple[Bar, ...]  # contiguous, starting at onset 0
    time_signatures: tuple[TimeSignatureChange, ...]  # first one at onset 0
    parts: tuple[Part, ...]  # score order, top to bottom; at least one

    def pickup_duration(self) -> Fraction: ...  # 0 when the first bar is complete


class IngestedScore(BaseModel):
    score: Score
    has_lyrics: bool  # the source had lyrics, which this spec ignores
```

Decisions in the model:

* **Parts, not voices of a texture** (decision 3, ADR 0004). A score is a list of parts in score order, top to bottom, whatever their number. A part is identified by its position (part 1 is the top part); its name and instrument are metadata kept for display and, later, for the timbre factor. Nothing in the core says which part is a melody or a bass, and nothing reads part names to decide anything.
* **Notated voices** (decision 4). A part holds one notated voice, or several when the source writes several voices on its staff (MusicXML `<voice>`, music21 `stream.Voice`). Each notated voice keeps its own rhythm. Notated voice number k of a part is, in every bar, the voice in position k of that bar; in a bar without voices every note belongs to notated voice 1, so a part that divides only in a few bars has notated voice 2 only there. A notated voice is a fact of the notation, not a line in Fessel's sense: whether it is heard as a line is a question for the analysis.
* **A note event is a notated note, not a sounding note.** Two notes tied across a bar line are two events, the first with `TieType.START` and the second with `TieType.STOP`. Merging tied notes into one sounding note is analysis work for a later spec. This keeps the round trip exact.
* **Divided events.** When a notated voice divides into a chord (for example a divided final chord in the bass), the chord is one `NoteEvent` with several `EventPitch` values, each with its own tie, as in MusicXML. Every pitch is kept, including a unison written as the same spelled pitch twice. `pitches` is never empty and is ordered from highest to lowest sounding pitch, with ties between enharmonic spellings broken by ascending step order (F sharp 4 comes before G flat 4; decision 10) and repeated spelled pitches kept next to each other.
* **Fermatas** (decision 1) are a property of the event (`fermata`), so a fermata on a divided event covers the whole chord, as in notation.
* **Rests are not stored.** Silence in a notated voice is the time not covered by its events. The renderers write rests in the gaps. This makes "no lost or altered notes" a statement about events only. The exception is a rest that carries a fermata, kept from 001d on (below).
* **Spelling is kept, enharmonics are different.** F sharp 4 and G flat 4 are different `SpelledPitch` values; they share a pitch class.
* **Bars and meter belong to the score; key signatures belong to each part.** Ingestion rejects parts whose bars or time signatures do not line up, since the model cannot represent them. Key signatures are kept per part so that the full score writes back what each staff had.
* **Room for lyrics** (decision 2, later spec). Lyrics will attach to the note event, not to a pitch, because a syllable is sung on the event even when the voice divides. The expected shape is a field `lyrics: tuple[Lyric, ...]` on `NoteEvent`, defaulting to empty, where `Lyric` holds the verse number, the syllable text and its syllabic position (single, begin, middle, end), mirroring `music21.note.Lyric`. Because the field has a default, adding it will not break any constructor written for this spec.
* Validators enforce the structural invariants at construction: positive durations; nonempty and ordered `pitches`; sorted and non overlapping events within a notated voice; at least one notated voice per part, and content in the last one when there are several (otherwise it would not survive writing); at least one part; contiguous bars starting at 0; the first key and time signature at onset 0; every event ending no later than the end of the last bar. Violations raise pydantic `ValidationError`; these are programming errors, not user errors.

**Grace notes and fermatas on rests (001d).** Both are kept, not rejected: a grace note is a pitched note of the source, and the lossless principle of decision 3 does not allow dropping it. A grace note takes no time, so it cannot be a `NoteEvent` without breaking the invariants that every analysis will rely on (positive duration, no overlap). It is therefore stored next to the events, in its own tuple. 001d adds:

```python
class GraceNote(BaseModel):
    onset: Fraction  # onset of the note or rest it ornaments
    pitches: tuple[EventPitch, ...]  # highest first
    notated_value: Fraction  # quarter lengths of the symbol, 1/2 for an eighth
    slash: bool  # written with a slash through the stem


class RestFermata(BaseModel):
    onset: Fraction
    duration: Fraction  # the notated rest that carries the fermata


class NotatedVoice(BaseModel):
    events: tuple[NoteEvent, ...]
    grace_notes: tuple[GraceNote, ...] = ()  # sorted by onset, source order kept
    rest_fermatas: tuple[RestFermata, ...] = ()  # each inside a gap between events
```

The defaults keep every constructor written in 001a valid. Until 001d, ingestion raises `UnsupportedScoreError` for grace notes and fermatas on rests, which is explicit and visible in the committed list of unsupported chorales.

### 3.3 Relation to the textural model

This slice makes no textural decision. It prepares the data that the analysis of ADR 0004 needs, so that later specs can identify strata from the notes instead of from the layout of the score:

* **Per part notes with exact onsets and durations**, on explicit bars and time signatures: the material for proximity of attacks, rhythmic independence, attack divergence and accent coincidence on the metric grid.
* **Spelled pitches**, every one of them, including the pitches of divided events: the material for intervallic proximity, registral separation and directional convergence and divergence.
* **Timbre through the instrument** of each part (`Part.instrument_name`), and the part name as written: the material for timbral similarity and dissimilarity. A finer identity of the instrument (family, General MIDI program) can be added when the analysis needs it.
* **Notated voices and parts as source facts only.** Fessel's point that a part may contribute to several strata, and several parts to one stratum, is respected by keeping parts and notated voices exactly as written and leaving every grouping to the analysis.
* **Dynamics are a later addition**, needed for the intensity factor (differences of intensity, a dissociation factor). They will attach to parts as timed marks; this spec neither reads nor writes them.

The grand staff of this slice is a notational check, not a reduction: it places parts 1 to 4 in score order and is not the four voice harmonic reduction, whose voices will be chosen by analysis.

### 3.4 Domain exceptions (`core/errors.py`)

```python
class AretzTextureError(Exception): ...  # base of every domain error


class UnparseableScoreError(AretzTextureError): ...  # missing, not MusicXML


class UnsupportedScoreError(AretzTextureError): ...  # parses, cannot be represented


class GrandStaffMappingError(AretzTextureError):
    part_count: int  # parts of the score that the grand staff could not place
```

* `UnparseableScoreError`: file missing, not MusicXML, corpus identifier not found.
* `UnsupportedScoreError` is kept only for what truly cannot be represented: microtonal accidentals, unpitched notes, `"let-ring"` ties, parts whose bars or time signatures do not line up, notes outside the voices of a bar that has voices, and transposing parts (open question 2). Until 001d, also grace notes and fermatas on rests.
* `GrandStaffMappingError`: the score is valid but cannot be placed on the grand staff of this slice (section 3.6). It is not an `UnsupportedScoreError`, because the score is ingested and round tripped normally.
* `AmbiguousHarmonyError`, mentioned in `AGENTS.md`, is not created here; it belongs to the first analysis spec.

### 3.5 Ingestion (`ingest/`)

All ingestion modules are music21 boundary modules (ADR 0003): they start with the file level pyright comment and expose only core and standard library types.

`ingest/sources.py`:

```python
def read_score(source: str) -> IngestedScore: ...


def read_grand_staff_file(path: Path, layout: GrandStaffLayout) -> Score: ...


def list_corpus_chorales() -> tuple[str, ...]: ...
```

* `read_score`: if `source` names an existing file, parse it with `music21.converter.parse(path)`; otherwise treat it as a corpus identifier and call `music21.corpus.parse(source)` (for example `"bwv66.6"` or `"bach/bwv66.6"`). Any music21 failure to find or parse the source is reraised as `UnparseableScoreError` with the original exception chained (`raise ... from error`). If the result is not a `music21.stream.Score`, raise `UnparseableScoreError`. The same function reads back the full scores written by `render/full_score.py`.
* `list_corpus_chorales`: the identifiers of the Bach chorales in the music21 corpus, in a stable order, from `music21.corpus.chorales.Iterator(returnType="filename")` (default numbering system `"riemenschneider"`). The implementer confirms with the explorer that each filename yielded is accepted by `music21.corpus.parse`, and adapts the conversion if not.

`ingest/music21_conversion.py`, private helpers:

* **Parts.** Every element of `score.parts`, in order, becomes one `Part`; a `music21.stream.PartStaff` counts as a part. `name` is `part.partName` trimmed, or `None` when absent or empty. `instrument_name` is the `instrumentName` of `part.getInstrument(returnDefault=False)`, trimmed, or `None` when there is no instrument or no name. The implementer checks with the explorer whether music21 fills one of the two names from the other when reading or writing; if it does, the PR reports it and proposes the normalization before coding it.
* **Bars.** For part 1, iterate `part.getElementsByClass(music21.stream.Measure)`. Bar onset is `measure.offset`; bar duration is the offset of the next measure minus this one, and `measure.highestTime` for the last measure; bar number is `measure.number` (`measure.numberSuffix` is ignored). Every other part must yield the same bars, otherwise `UnsupportedScoreError`.
* **Notated voices.** In a measure without voices (`measure.hasVoices()` false), `measure.notesAndRests` belong to notated voice 1. In a measure with voices, the element in position k of `measure.voices` holds notated voice k; a note or chord directly in such a measure, outside its voices, raises `UnsupportedScoreError`. A part has as many notated voices as the largest k that has content in any of its bars; voices that hold only rests in every bar are not created.
* **Note events.** A `music21.note.Note` becomes an event with one pitch; a `music21.chord.Chord` becomes a divided event with one `EventPitch` per element of `chord.notes`. Rests are skipped. Onset is `Fraction(measure.offset) + Fraction(element.offset)`, duration is `Fraction(element.duration.quarterLength)`. music21 offsets are floats only when binary exact and `Fraction` otherwise (`music21.common.opFrac`), so `Fraction(value)` is exact. `music21.note.Unpitched` raises `UnsupportedScoreError`. A grace note (`element.duration.isGrace`) and a fermata on a rest raise `UnsupportedScoreError` in 001a and are converted from 001d on.
* **Pitch.** `pitch.step`, `pitch.implicitOctave` and `pitch.accidental.alter` when `pitch.accidental` is not `None`, else 0. A non integer `alter` (microtone) raises `UnsupportedScoreError`.
* **Ties.** `note.tie` (for a chord, the `tie` of each element of `chord.notes`) is `None` or a `music21.tie.Tie` whose `type` is `"start"`, `"stop"` or `"continue"`, mapped to `TieType`. The types `"let-ring"` and `"continue-let-ring"` raise `UnsupportedScoreError`.
* **Fermatas.** `fermata` is true when `element.expressions` contains a `music21.expressions.Fermata`.
* **Lyrics.** Not converted. `has_lyrics` is true when any note of any part has a nonempty `note.lyrics`.
* **Key signatures**, per part: `part.recurse().getElementsByClass(music21.key.KeySignature)` (this includes `music21.key.Key`) gives `sharps`, with onsets from `element.getOffsetInHierarchy(part)`. Consecutive duplicates are collapsed. A part without a key signature at onset 0 gets `sharps=0` at onset 0.
* **Time signatures**, from part 1 the same way, giving `numerator` and `denominator`. Every other part must have the same changes, otherwise `UnsupportedScoreError`. A time signature change that does not fall on a bar line also raises `UnsupportedScoreError`, because bars are defined by the meter. Key signature changes, in contrast, may fall anywhere in a bar and keep their exact onset. A score without a time signature at onset 0 raises `UnsupportedScoreError`.
* **Transposing parts.** A part whose instrument has a `transposition` that is not `None` raises `UnsupportedScoreError` until open question 2 is decided.

`ingest/grand_staff_reader.py`, used by `read_grand_staff_file` to read files written by `render/piano_score.py`:

* Parse with `music21.converter.parse`. A MusicXML part with two staves is parsed into two `music21.stream.PartStaff` objects in `score.parts`; there must be exactly two, otherwise `UnsupportedScoreError`.
* Each measure of each staff holds `music21.stream.Voice` objects, identified by their position in `measure.voices`, then mapped back to parts 1 to 4 through the layout. The implementer verifies with a test that music21 preserves this order on the files the renderer writes; if it does not, identify voices by `voice.id` instead and record the finding in the PR.
* Notes, chords, pitches, ties, fermatas, bars and signatures are converted with the same rules as above, applied per staff voice. Each part gets the key signatures of its staff, one notated voice, and `None` as name and instrument name, since the grand staff carries none.

### 3.6 Rendering (`render/`)

Both modules are boundary modules (ADR 0003).

`core/grand_staff.py`, shared by the piano renderer and the grand staff reader, which cannot import each other:

```python
class Staff(StrEnum):
    UPPER = "upper"  # right hand, treble clef
    LOWER = "lower"  # left hand, bass clef


class StaffVoice(BaseModel):
    staff: Staff
    voice_number: int  # 1 is the upper voice of the staff, stems up; 2 the lower


class GrandStaffLayout(BaseModel):
    placements: tuple[StaffVoice, ...]  # placement of parts 1 to 4 in score order

    def placement(self, part_number: int) -> StaffVoice: ...  # 1 based


PIANO_LAYOUT: GrandStaffLayout  # parts 1, 2 upper voices 1, 2; parts 3, 4 lower


def piano_layout(score: Score) -> GrandStaffLayout: ...
```

`piano_layout` is pure. It returns `PIANO_LAYOUT` when the score has exactly four parts, each with one notated voice, all with the same key signature changes. Otherwise it raises `GrandStaffMappingError` with the part count and a message such as: `aretz-texture piano renders only scores with exactly four parts; this score has 15 parts: Trumpet 1, Trumpet 2, Trumpet 3, Timpani, ... Grand staff rendering of other textures needs the textural analysis of a later spec.` The conditions on notated voices and key signatures are provisional (open question 1); their messages say which part breaks them.

`render/full_score.py`:

```python
def write_full_score(score: Score, output_path: Path) -> None: ...
```

* One `music21.stream.Part` per model part, in order, with `partName` set from `name` and an instrument whose `instrumentName` is `instrument_name`, when they are not `None`. The clef of each part is chosen with `music21.clef.bestClef`; clefs are not compared.
* For every `Bar`, one `music21.stream.Measure(number=bar.number)` per part. When the bar is shorter than its time signature, set `measure.paddingLeft` (first bar, the pickup) or `measure.paddingRight` (any later bar) to the missing length.
* Time signatures are inserted in every part at the start of the bar where they change, as `music21.meter.TimeSignature(f"{numerator}/{denominator}")`; ingestion guarantees that every time signature change falls on a bar line. Key signatures of each part are inserted as `music21.key.KeySignature(sharps)` in that part, at their stored onset relative to the containing bar (`measure.insert(onset - bar.onset, ...)`), so a change in the middle of a bar stays where it was. MusicXML represents it as an `attributes` element inside the measure.
* In a bar where only notated voice 1 has content, the notes go directly into the measure. Otherwise, with k the highest notated voice with content in that bar, the measure holds k `music21.stream.Voice` objects with ids `"1"` to `"k"`, in order, each filled with the events of its notated voice and rests in every gap, so a voice with no content in that bar is a whole bar rest. This is what makes reading by position (section 3.5) recover the same numbering.

`render/piano_score.py`:

```python
def write_piano_score(
    score: Score,
    layout: GrandStaffLayout,
    output_path: Path,
) -> None: ...
```

* Builds a `music21.stream.Score` with two `music21.stream.PartStaff` objects (upper with `music21.clef.TrebleClef`, lower with `music21.clef.BassClef`), joined by `music21.layout.StaffGroup([upper, lower], symbol="brace")` inserted in the score. No part, staff or instrument names (decision 6).
* Bars, padding, key signatures (those of parts 1 and 3, equal to the others by `piano_layout`) and time signatures as in the full score, on both staves.
* Each measure contains two `music21.stream.Voice` objects with ids `"1"` and `"2"`, filled with the events of the parts placed there by the layout, with rests in the gaps, so every staff voice fills every bar.
* Stems: `stemDirection = "up"` in voice 1 and `"down"` in voice 2. A fermata in voice 2 has its `type` set to `"inverted"`, printed below the staff (the implementer verifies the attribute name with the explorer).

Shared by both renderers: an event with one pitch becomes a `music21.note.Note`; a divided event becomes a `music21.chord.Chord` of one `music21.note.Note` per pitch. Each pitch is a `music21.pitch.Pitch` built from `step`, `octave` and `music21.pitch.Accidental(alter)` when `alter != 0`; each tied pitch gets `tie = music21.tie.Tie(tie.value)` on its note; `quarterLength=duration`. A fermata is `music21.expressions.Fermata()` appended to `element.expressions`. Files are written with `score.write("musicxml", fp=output_path)`; a failure to write raises `OSError` as is. The conversion of one event appears in two renderers; it is extracted into a shared private module of `render/` only if a third use appears (AGENTS.md, "Duplication").

In 001d, both renderers write grace notes before the event at their onset (`note.getGrace()`, with the notated value as the duration type and `duration.slash` as stored) and split the rest that fills a gap so that a rest of exactly the stored onset and duration carries the fermata.

### 3.7 Command line (`cli.py`)

`src/aretz_texture/cli.py`, at the top of the package, so it can import `ingest/`, `render/` and `core/` without breaking any contract. It uses only `argparse` from the standard library.

```python
def main(argv: Sequence[str] | None = None) -> int: ...
```

```text
aretz-texture piano SOURCE --output PATH
```

* `SOURCE`: a MusicXML file path or a music21 corpus identifier.
* `--output`, `-o`: required; the MusicXML file to write. An existing file is overwritten.
* Flow: `read_score(source)`, `piano_layout(ingested.score)`, `write_piano_score(ingested.score, layout, output_path)`. The layout is checked before writing, so no file is written for a score with another number of parts.
* When `has_lyrics` is true, one line on standard output (through `sys.stdout.write`; ruff forbids `print`) says that lyrics were ignored. Nothing else is printed on success.
* Exit codes: 0 on success; 2 for usage errors (argparse default); 1 for any `AretzTextureError`, including `GrandStaffMappingError`, with its message written to standard error. Other exceptions propagate.
* The `reduce` subcommand does not exist yet (decision 8).

`pyproject.toml`:

```toml
[project.scripts]
aretz-texture = "aretz_texture.cli:main"
```

`main` returns the exit code; the script wrapper generated by the build backend passes it to `sys.exit`.

### 3.8 Round trip comparison (`eval/round_trip.py`)

```python
class RoundTripRoute(StrEnum):
    FULL_SCORE = "full_score"  # one staff per part, any number of parts
    GRAND_STAFF = "grand_staff"  # piano, four parts only


class DifferenceKind(StrEnum):
    PART_COUNT = "part_count"
    PART_NAME = "part_name"
    INSTRUMENT_NAME = "instrument_name"
    VOICE_COUNT = "voice_count"  # notated voices in a part
    MISSING_EVENT = "missing_event"  # in the original, not in the output
    EXTRA_EVENT = "extra_event"  # in the output, not in the original
    ALTERED_EVENT = "altered_event"  # same onset, other duration, pitches or fermata
    BARS = "bars"
    KEY_SIGNATURES = "key_signatures"
    TIME_SIGNATURES = "time_signatures"


class RoundTripDifference(BaseModel):
    route: RoundTripRoute
    kind: DifferenceKind
    part_number: int | None  # 1 based; None for score level differences
    voice_number: int | None  # 1 based; None above the notated voice
    onset: Fraction | None  # None for differences that are not about one event
    description: str  # human readable, includes the bar number when known


class ChoraleOutcome(StrEnum):
    IDENTICAL = "identical"
    DIFFERENT = "different"
    UNSUPPORTED = "unsupported"  # ingestion raised UnsupportedScoreError


class ChoraleRoundTrip(BaseModel):
    identifier: str
    outcome: ChoraleOutcome
    part_count: int  # 0 when unsupported
    differences: tuple[RoundTripDifference, ...]
    grand_staff_skip_reason: str  # empty when the grand staff route ran
    unsupported_reason: str  # message of the UnsupportedScoreError, or empty


def compare_scores(
    original: Score,
    returned: Score,
    route: RoundTripRoute,
) -> tuple[RoundTripDifference, ...]: ...


def without_part_metadata(score: Score) -> Score: ...


def round_trip_chorale(identifier: str, work_directory: Path) -> ChoraleRoundTrip: ...
```

* `round_trip_chorale`:
  1. `read_score(identifier)`; an `UnsupportedScoreError` gives outcome `UNSUPPORTED` with its message.
  2. Full score route, for every chorale: `write_full_score` into `work_directory`, `read_score` on the written file, `compare_scores(original, returned, RoundTripRoute.FULL_SCORE)`.
  3. Grand staff route: `piano_layout(original)`; on `GrandStaffMappingError`, record its message in `grand_staff_skip_reason` and stop. Otherwise `write_piano_score`, `read_grand_staff_file` and `compare_scores(without_part_metadata(original), returned, RoundTripRoute.GRAND_STAFF)`.
  4. Outcome `DIFFERENT` when either route has a difference, `IDENTICAL` otherwise. A domain error while reading back a file written by this tool is a bug and propagates.
* `without_part_metadata` sets every part `name` and `instrument_name` to `None`, since the grand staff carries none (decision 6).
* `compare_scores` is pure. Parts are aligned by position and notated voices by number; within a notated voice, events are aligned by onset (a notated voice never has two events at the same onset). Equal means: the same number of parts; the same name and instrument name per part; the same key signature changes per part; the same number of notated voices per part; the same bars (number, onset, duration), hence the same pickup bar; the same time signature changes; and in each notated voice the same set of onsets, and for each onset the same `duration`, the same `pitches` (each `SpelledPitch` and its `tie`, in order) and the same `fermata`. From 001d on, also the same grace notes and rest fermatas, with two more difference kinds.
* Deliberately ignored, because the core model does not carry them in this spec: rests without fermata, accidental display, mode of the key (`music21.key.Key.mode`), clefs, stem directions, fermata placement, beaming, staff grouping, title and other metadata, lyrics, dynamics, other articulations, slurs, tempo, repeat barlines and endings, bar number suffixes, layout.

The comparison works on core objects, so it cannot see what ingestion drops. That is covered by acceptance criterion 10, which checks that the pitches of the model add up to the pitches music21 reads.

### 3.9 Configuration and contracts in `pyproject.toml`

* `dependencies = ["music21>=10.5,<11", "pydantic>=2.10,<3"]`, added with `uv add`, which updates `uv.lock`.
* Boundary modules start with:
  `# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportMissingTypeStubs=false` followed by `# See ADR 0003: music21 is untyped; this module is the boundary.` Only the rules that actually fire are listed.
* This slice has no weights, thresholds or tolerances, so it adds no configuration.
* import-linter: set `include_external_packages = true` under `[tool.importlinter]` and add:
  * "music21 only at the boundary": forbidden, sources `core`, `analysis`, `voicing`, `eval`, `cli`, forbidden module `music21`, with `allow_indirect_imports = true` (`eval` and `cli` reach music21 through `ingest/` and `render/`, which is intended).
  * "nothing imports the command line": forbidden, sources all six subpackages, forbidden module `aretz_texture.cli`.
  * "the command line does not import eval": forbidden, source `aretz_texture.cli`, forbidden module `aretz_texture.eval`.

### 3.10 Data flow

Command line:

1. `ingest.sources.read_score(SOURCE)` returns an `IngestedScore` with every part of the source.
2. `core.grand_staff.piano_layout(score)` returns `PIANO_LAYOUT` or raises `GrandStaffMappingError`.
3. `render.piano_score.write_piano_score(score, layout, PATH)` writes the grand staff MusicXML.
4. `cli` reports ignored lyrics, or the error and exit code 1.

Evaluation, per chorale: `read_score`, then the full score route (`write_full_score`, `read_score`, `compare_scores`) and, when `piano_layout` accepts the score, the grand staff route (`write_piano_score`, `read_grand_staff_file`, `compare_scores` against `without_part_metadata(original)`).

## 4. Acceptance criteria

### 001a: model and ingestion

1. `music21` and `pydantic` are runtime dependencies in `pyproject.toml` and `uv.lock`, with the bounds of ADR 0003.
2. Every core model is immutable: assigning to a field raises `ValidationError`.
3. `NotatedVoice` rejects events that are unsorted or overlapping; `NoteEvent` rejects empty or unordered `pitches` and accepts the same spelled pitch twice; `Part` rejects zero notated voices and a last notated voice without content when there are several; `Score` rejects zero parts, bars that are not contiguous from 0 and an event ending after the last bar.
4. `SpelledPitch(step="F", alter=1, octave=4)` and `SpelledPitch(step="G", alter=-1, octave=4)` are not equal and have the same `pitch_class()`.
5. `read_score("bwv66.6")` returns four parts in score order, named Soprano, Alto, Tenor and Bass as in the source, each with one notated voice and three sharps, with the time signature and bars music21 reports for that chorale and a pickup bar numbered 0.
6. A note tied across a bar line in the source becomes two events with `TieType.START` and `TieType.STOP`, each with its notated duration.
7. A chord in one part becomes one divided event with every pitch and each pitch's tie (BWV 248.9 1, bar chosen by the explorer).
8. A part with several voices in a bar keeps each as its own notated voice with its own onsets and durations, and the notes of that part in bars without voices belong to notated voice 1 (BWV 248.23 2, bar chosen by the explorer).
9. Scores with more than four parts keep every part with its name and instrument name: BWV 27.6 has five parts named `Soprano 1`, `Soprano 2`, `Alto`, `Tenor` and `Bass`; BWV 41.6 keeps its combined names verbatim, including `Alto Oboe 2 Viloin 2`; BWV 190.7 has fifteen parts.
10. For every chorale of `list_corpus_chorales()` accepted by ingestion, in each source part, the number of pitches read by music21 (a note counts one, a chord counts its notes) equals the number of pitches in the events of the corresponding model part (slow). From 001d on, grace notes are counted on both sides.
11. A note with a fermata in the source becomes an event with `fermata` true; every other event has it false.
12. A microtonal accidental, an unpitched note, a `"let-ring"` tie, parts whose bars or time signatures do not line up, a time signature change that does not fall on a bar line, a note outside the voices of a bar with voices and a transposing part each raise `UnsupportedScoreError`; a missing file or unknown corpus identifier raises `UnparseableScoreError`. Until 001d, a grace note and a fermata on a rest also raise `UnsupportedScoreError`.
13. `has_lyrics` is true exactly when some note of some part of the source has a lyric.
14. `lint-imports` passes with the new contracts, and a module outside `ingest/` and `render/` that imports music21 makes it fail.

### 001b: rendering and command line

15. Writing any `Score` with `write_full_score` and reading it back with `read_score` gives an equal `Score` (hypothesis property, and BWV 27.6, BWV 248.9 1 and BWV 248.23 2).
16. The full score of BWV 27.6 has five parts with the source part names; a bar where only notated voice 1 has content is written without `music21.stream.Voice` objects.
17. `piano_layout` returns `PIANO_LAYOUT` for a score of four parts with one notated voice each and the same key signatures, and raises `GrandStaffMappingError` carrying the part count for any other number of parts, for a part with several notated voices and for differing key signatures.
18. `write_piano_score` on BWV 66.6 writes a MusicXML file with one part of two staves (treble and bass clef) joined by a brace, parts 1 and 2 in the upper staff, parts 3 and 4 in the lower, and no staff or instrument names.
19. Writing any four part score accepted by `piano_layout` and reading it back with `read_grand_staff_file` gives the original with every part name and instrument name set to `None` (hypothesis property, and BWV 66.6), including divided events, ties per pitch and fermatas.
20. A pickup bar survives both routes: same bar number, onset and duration, and `pickup_duration()` unchanged.
21. In the written piano file every staff voice fills every bar, with rests in the gaps.
22. `aretz-texture piano bwv66.6 --output PATH` exits with 0 and writes PATH; with a file path as SOURCE it behaves the same.
23. `aretz-texture piano bwv27.6 --output PATH` exits with 1, writes to standard error a message that names the five parts and says that grand staff rendering of other textures needs a later spec, and does not create PATH.
24. `aretz-texture piano` with an unknown source exits with 1 and writes the error message to standard error; without `--output` it exits with 2; `aretz-texture reduce` is rejected as an unknown subcommand.
25. **Manual, by Nico:** the output for BWV 66.6 opened in Sibelius shows the same chorale on two staves, with the same pitches, accidentals, ties, rhythm and fermatas as the original. Recorded as a checked box in the PR description.

### 001c: evaluation

26. `compare_scores` returns no differences for a score compared with itself, and returns exactly one difference of the right kind for each single change: a removed event, an added event, a changed pitch spelling, duration, tie or fermata, a pitch added to or removed from a divided event, a changed part name or instrument name, an added part, an added notated voice, a changed bar, key signature or time signature.
27. The slow corpus test runs `round_trip_chorale` on the 350 distinct identifiers of `list_corpus_chorales()` and asserts that no chorale has outcome `DIFFERENT`.
28. The set of chorales with outcome `UNSUPPORTED` equals the list committed in `tests/eval/expected_unsupported_chorales.txt`, one identifier per line with its reason. A chorale that changes outcome in either direction fails the test, so a new rejection is a visible regression.
29. Every supported chorale with exactly four parts takes the grand staff route, except those listed with their reason in `tests/eval/expected_grand_staff_skips.txt`; every supported chorale with more than four parts records the part count reason. Any change to the set fails the test.

### 001d: grace notes and fermatas on rests

30. A grace note in the source becomes a `GraceNote` in its notated voice with its onset, pitches, ties, notated value and slash, in source order; it survives both routes, and `compare_scores` reports a removed or altered grace note.
31. A fermata on a rest becomes a `RestFermata` with the onset and duration of the rest; it survives both routes, and `compare_scores` reports a removed one.
32. The two corpus chorales with grace notes are ingested, and the committed unsupported list no longer contains any chorale whose only reason was a grace note or a fermata on a rest.

### All pull requests

33. All commit checks pass (`uv run pre-commit run --all-files`), and the full test suite passes in CI.

## 5. Test plan

Tests may import music21 directly to build fixtures and to inspect written files: the import contracts apply to the package, not to `tests/`. Hand written MusicXML fixtures, if any, are tiny, written for the test and in the public domain.

### Concrete cases

* **BWV 66.6** (`"bwv66.6"`), the chorale named in the issue: four parts named Soprano, Alto, Tenor and Bass, three sharps, a pickup bar numbered 0 whose first note has beat 4 (section 8). The time signature, bar numbers and fermata positions are read from music21 once with the explorer, written as literals in the test (criteria 5 and 11) and listed in the PR so Nico can check them against the score. Rendering (criteria 18 to 21), command line (criteria 22 and 25) and evaluation tests also use it. It is the pickup case of criterion 20.
* **BWV 248.9 1** (`"bach/bwv248.9-1"`), divided chords inside a part (criteria 7 and 15): the test names the part and bar of a divided event and asserts all its pitches in order, highest first.
* **BWV 248.23 2** (`"bach/bwv248.23-2"`), several voices inside one part (criteria 8 and 15): the test names the part and the first bar with voices, and asserts the onsets and durations of each notated voice there and that the bars before it belong to notated voice 1. If the chorale has exactly four parts, it is also a grand staff skip of criterion 29 (open question 1).
* **BWV 27.6** (`"bach/bwv27.6"`), a genuine five voice chorale: five parts kept (criterion 9), identical full score round trip (criterion 15), and the `piano` command refusing it with the part count message (criterion 23).
* **BWV 41.6** (`"bach/bwv41.6"`): part names that combine a voice and its doubling instruments are kept verbatim, misspelling included (criterion 9).
* **BWV 190.7** (`"bach/bwv190.7"`), fifteen parts: every part kept with its name and instrument name as music21 reports them (criterion 9), and an identical full score round trip.
* **A chorale with a tie across a bar line** (criterion 6): the explorer picks the first chorale in the corpus with a `"start"` tie on the last note of a measure, and the test names the chorale, the part and the bar number.
* **A chorale with accidentals outside the key signature** (criteria 4 and 15): the explorer picks a chorale and bar with a raised leading tone in a minor key or a chromatic note, and the test asserts the spelled pitch of that note after ingestion and after both routes.
* **Grace notes** (001d, criteria 30 and 32): the two corpus chorales with grace notes, named by the explorer with part and bar. **A fermata on a rest** (criterion 31): the explorer searches the corpus; if there is no example, the test builds a small score with music21 and the PR says so.
* **Error cases** built in the test with music21: a quarter tone accidental, an unpitched note, a `"let-ring"` tie, two parts whose bars differ, two parts whose time signatures differ, a time signature change in the middle of a bar, a note outside the voices of a measure with voices and a part with a transposing instrument (`UnsupportedScoreError`); a nonexistent path and the identifier `"bwv0.0"` (`UnparseableScoreError`).
* **Key signature change in the middle of a bar** (criteria 4 and 15), built in the test with music21: a part whose key signature changes on beat 3 of a bar keeps that exact onset after ingestion, and again after the full score and grand staff round trips. No corpus chorale has such a change (section 8), so the case is synthetic.
* **Grand staff mapping** (criterion 17), built in the test: scores of one, three and five parts, a four part score with two notated voices in part 2, and a four part score where part 4 has a different key signature.
* **Command line**: call `main([...])` directly with `tmp_path`; check the exit code, the file written or not written, the lyrics line on standard output and the error on standard error with `capsys`.
* **Comparison** (criterion 26): start from a small `Score` built in the test and apply one change per test.

Chorale identifiers above come from the corpus survey of section 8; bar numbers chosen by the explorer are written in the tests and listed in the PR description, because they must be verified against the installed corpus, not recalled.

### Hypothesis properties

Two strategies in `tests/strategies.py`:

* `scores()`: one time signature from a small set (2/4, 3/4, 4/4, 3/2), an optional pickup bar shorter than the bar, a few bars, one to six parts, each with a name or `None`, an instrument name or `None`, a key signature, and one to three notated voices. Each notated voice is a sequence of events that tiles each bar from durations in {1/2, 1, 3/2, 2, 3, 4} and triplet eighths (1/3) in groups that complete a beat, with gaps left as rests, including bars where notated voice 2 is silent and bars where notated voice 1 is silent while notated voice 2 sounds. Spelled pitches with `alter` in {-1, 0, 1} within a plausible range; occasional divided events of two or three pitches, occasionally with a repeated spelled pitch; occasional fermatas; ties only between consecutive events of one notated voice that share the tied spelled pitch with no gap between them.
* `four_part_scores()`: the same, restricted to four parts with one notated voice each and the same key signature in every part.

Properties:

* **Full score identity** (criterion 15): `read_score(path).score == score` after `write_full_score(score, path)`. Each example writes a file, so the test uses a bounded `max_examples` and is marked slow if it exceeds a few seconds.
* **Grand staff identity** (criterion 19): reading back the piano file gives the score with part metadata removed.
* **The grand staff only accepts four parts**: for any score from `scores()` whose part count is not four, `piano_layout` raises `GrandStaffMappingError` with that count.
* **Comparison is reflexive**: `compare_scores(score, score, route) == ()`.
* **Comparison detects removal**: removing any one event from any notated voice yields exactly one `MISSING_EVENT` at that part, notated voice and onset.
* **Notated voice invariants**: for any generated notated voice, events are sorted and consecutive events do not overlap; constructing one with any two events swapped raises `ValidationError`.
* **Divided event order**: for any generated divided event, pitches go from highest to lowest sounding pitch.
* **Bars tile the score**: the sum of bar durations equals the onset of the end of the last bar, and every event lies within the bars.

## 6. Decisions

Taken by Nico on November 7, 2026. Decisions 3, 4 and 6 replace the omission criterion of the previous draft, after the adoption of Fessel's textural model (ADR 0004).

1. **Fermatas** are kept: in the model, the rendering and the round trip comparison.
2. **Lyrics** are out of scope for this slice and are not preserved. Respecting lyrics is a requirement for a later spec; the model leaves room for them on the note event (section 3.2), and the command line says when lyrics were ignored.
3. **Ingestion is lossless for every part.** The core model keeps a score as a list of parts with their notes and metadata (part name, instrument when available), whatever the number of parts. No note is dropped. Parts are not mapped to soprano, alto, tenor and bass in ingestion or in the core model: which notes form melody, bass or accompaniment is decided by analysis (ADR 0004).
4. **Divided chords and several voices inside one part are kept without loss**, as divided events and as notated voices with their own rhythm. Grace notes are kept (001d). Only what truly cannot be represented is rejected with `UnsupportedScoreError`.
5. **Repeats and endings** are later, out of scope.
6. **Piano rendering** in this slice applies only to scores with exactly four parts, placed in score order: parts 1 and 2 on the right hand staff, parts 3 and 4 on the left hand staff, each keeping its own rhythm. Other scores are ingested and round tripped by the evaluation, and the `piano` command exits with a clear message. **No staff or instrument names** on the grand staff.
7. **Cautionary accidentals** may be lost; acceptable.
8. **Command name**: `aretz-texture piano SOURCE --output PATH` for this slice; `reduce` is reserved for when reduction exists.
9. **The evaluation covers the 350 distinct corpus chorales** (decision 11), including the 19 with more than four parts, through the full score; four part chorales also go through the grand staff. Expected result: no chorale `DIFFERENT`, with a committed list of `UNSUPPORTED` chorales.

Taken by Nico on November 7, 2026, while reviewing 001a:

10. **Enharmonic order in a divided event**: pitches that sound the same are ordered by ascending step, so F sharp 4 comes before G flat 4.
11. **Distinct chorales**: the corpus iterator lists 21 chorales twice. Evaluation and corpus tests run over the 350 distinct chorales, each once.
12. **Tests at the music21 boundary**: tests that build music21 objects share the relaxed pyright rules of the boundary through an execution environment for `tests/` in `pyproject.toml`, not through comments in each file. Source modules keep the rules of ADR 0003.

Taken by Nico on November 9, 2026, while reviewing 001b:

13. **Part name filled from the instrument name**: music21 names an unnamed part after its instrument when it reads it back. The comparison in 001c accepts a part name equal to the instrument name as equivalent to no name; ingestion does not normalise it.
14. **Refusal message of the piano command**: besides the part count, it lists the part names in score order, with `part N (no name)` for unnamed parts.
15. **Key signature change in the middle of a bar while every notated voice holds a note across it**: music21 cannot write it, so the writers raise `UnsupportedScoreError`. No corpus chorale has the case; it stays an explicit error for now.

### Open questions

1. **Closed score input and notated voices on the grand staff.** A closed score (two voices on one staff, for example soprano and alto on the upper staff and tenor and bass on the lower) is now representable: two parts, each with two notated voices, or divided events when the source writes the voices as chords. This slice ingests it without loss and round trips it through the full score, but the `piano` command refuses it, because it has two parts, and likewise refuses a four part score where some part has several notated voices. Should a later spec, before the textural analysis exists, place notated voices directly on the grand staff (for example a closed score copied staff by staff, or up to four voices per staff with their stem directions)? Is it a priority, given that much MusicXML exported by students may look like this?
2. **Transposing parts.** This draft rejects a part with a transposing instrument (`UnsupportedScoreError`), so that no written pitch is ever taken for a sounding one silently; the explorer reports in 001a how many corpus chorales this affects. The alternative is to keep the written pitches and store the transposition interval on the part, leaving the conversion to concert pitch to normalization. Which one?
3. **Full score from the command line.** The full score writer exists only for the evaluation in this slice. Should a later spec expose it (for example `aretz-texture score SOURCE --output PATH`) so that Nico can check by eye in Sibelius the chorales with more than four parts?

## 7. Notes for the implementer

* Verify every music21 name used here against the installed package (`.venv/lib/python3.12/site-packages/music21/`) through the explorer before writing the code that relies on it; record any difference in the PR. In particular: `chord.notes` and per note ties in a chord, duplicated pitches in a chord, `measure.voices` order, `part.getInstrument(returnDefault=False)` and `instrumentName`, `instrument.transposition`, `element.expressions` and the `type` attribute of `music21.expressions.Fermata`, `note.lyrics`, and, for 001d, `note.getGrace()` and `duration.slash`.
* ADR 0003 and ADR 0004 must be accepted by Nico together with this spec.

## 8. Corpus survey

Checked against the music21 10.5.2 corpus on November 7, 2026. The corpus iterator yields 371 entries, but 21 of them repeat a chorale already listed (for example `bach/bwv112.5`), so the corpus has 350 distinct chorales. The figures below count distinct chorales; an earlier version of this section counted the repeated entries.

* 331 chorales have exactly four parts. 19 have more, from 5 to 15 parts (the largest is `bach/bwv190.7`, with 15); none has fewer than four. Under this spec all 350 are ingested with every part, and only the 331 four part chorales can take the grand staff route.
* Of those 19, 17 have parts named exactly Soprano, Alto, Tenor and Bass plus instrumental parts: trumpets, horns, oboes, strings, timpani, continuo or organ. Many of these instruments double a vocal part; whether a doubling joins the stratum of its voice is a question for the textural analysis, not for ingestion.
* Two show why part names and part counts cannot decide the strata (ADR 0004):
  * `bach/bwv41.6` combines voice and instrument names in each part (`Soprano Oboe 1 Violin1`, `Alto Oboe 2 Viloin 2`, `Tenor Viola`, `Bass Continuo`; the misspelling is in the corpus): one part stands for a voice and its doubling instruments.
  * `bach/bwv27.6` is a genuine five voice chorale (`Soprano 1`, `Soprano 2`, `Alto`, `Tenor`, `Bass`).
* Divided chords inside a part appear in one chorale (`bach/bwv248.9-1`), and several voices inside one part in one chorale (`bach/bwv248.23-2`). They are the concrete cases for divided events and notated voices.
* Grace notes appear in two chorales (kept from 001d on), fermatas in 349 and lyrics in 339.
* BWV 66.6: the pickup bar is number 0 and its first note has `beat` 4.0; its fermatas report `type` `"upright"`.
* Checked by the main session after the rewrite (music21 10.5.2, November 7, 2026):
  * No part in the 350 chorales has a transposing instrument, so rejecting transposing parts (open question 2) affects no corpus chorale.
  * Instrument names in the corpus are generic: in BWV 66.6, `part.getInstrument().instrumentName` is `"Instrument 1"` while `part.partName` is `"Soprano"`, and only 4 of 1461 parts have an instrument name equal to the part name. Until the timbre factor is designed, the part name is the more informative source of timbre in this corpus; ingestion keeps both as they are.
  * `measure.voices` keeps the voice order: in BWV 248.23-2 the two voices of the oboe parts have ids `"1"` and `"2"`, in that order.
  * `bach/bwv190.7` has 15 parts.
  * No key signature or time signature in the corpus changes in the middle of a bar.
