# Spec 003: first four voice reduction of the chorales

Issue: #25, "Spec 003: first four voice reduction of the chorales"
Status: Approved by Nico, November 26, 2026 (gate 1)
Related: ADR 0003 (music21 boundary), ADR 0005 (readings of spec 002), ADR 0006 (pure harmonic analysis, Accepted), ADR 0007 (harmonic readings for the chorales, Accepted), spec 002

**Main points to review:** the slices and where the first Sibelius output appears (section 2, "Delivery"); harmonic segmentation (section 3.4); the decision to keep harmonic analysis pure (ADR 0006); the open questions of section 8. Every musical choice is marked **theory** (with source) or **project**.

## 1. Context

The product of Aretz Texture is the reduction of the harmony to a four voice chorale (architecture, sections 1, 3 and 7 to 9); the textural analysis of spec 002 is the structure it rests on. Nico wants an agile path to a first working version, adjusted in practice afterwards. As agreed on November 25, 2026, the first version is:

* **Repertoire:** the four part chorales of the corpus, which the reduction should return almost unchanged; they are the regression test (architecture, section 10).
* **Granularity:** level 2 only, one chord per actual change of function (architecture, section 8).
* **Rhythm:** harmonic rhythm, the reduced mode; the representative rhythm (section 6) is out.
* **First step:** harmonic segmentation (architecture, section 3, step 2): verticalities merged into harmonic windows, filtering passing tones, neighbor tones, suspensions and anticipations by metric weight, duration and stepwise motion.
* **Chord names on the score, both selectable by the user**, because each serves a different aim of study: chord symbols (`G7/B`) above the staff, as MusicXML `<harmony>`; Roman numerals (`V65`) below the bass, from the local key.
* The reduction consumes the textural tree of spec 002 (`TexturalAnalysis`), not the schema.

## 2. Scope

### In

* Core model of harmony: sounding notes, non chord tones, harmonic windows, chord identity, local key, Roman numerals, harmonic events with their granularity level (`core/harmony.py`, `core/roman_numerals.py`).
* Harmonic segmentation consuming the phrases and planes of `TexturalAnalysis` (`analysis/sounding_notes.py`, `analysis/non_chord_tones.py`, `analysis/harmonic_segmentation.py`).
* Chord identification by stacked thirds and chord symbols (`analysis/chords.py`), in pure code (ADR 0006).
* Local key per phrase by key profile (`analysis/keys.py`) and level 2 events (`analysis/harmony.py`).
* Voicing of four plane textures from their planes (`voicing/planes.py`) and the reduced score (`core/reduction.py`).
* Chord symbols as `<harmony>` and Roman numerals as lyrics on the bass, in the piano writer (`render/chord_names.py`, `render/piano_score.py`).
* The command `aretz-texture reduce`, reserved by spec 001 (decision 8), with the choice of chord names.
* Evaluation as one committed file of chords per phrase over the 350 chorales (`eval/reductions.py`).

### Out

* Levels 3 and 4, the representative rhythm, the textual description.
* **Cost based voicing** (architecture, section 7, dynamic programming): textures without four planes are analyzed and named, but not voiced (section 3.7, open question 3).
* Accented non chord tones other than suspensions (accented passing tones, appoggiaturas), escape tones, pedal points, retardations (suspensions resolving up), stream segregation.
* Chords outside the vocabulary of section 3.5: augmented sixth chords, ninth chords, chords without a third. They appear as unidentified sonorities.
* Applied chord notation (`V/V`) and tonicization inside a phrase; modulation is read only from phrase to phrase.
* Beat strength inside the bar (strong and weak beats); metric weight is only on or off the tactus.
* Repertoire other than the chorales.

### Delivery

Four pull requests, in this order, each under about 1500 changed lines and mergeable on its own. The order of the issue is kept except that voicing and the command come before the key, so that Nico sees the reduction in Sibelius one slice earlier.

* **003a, harmonic segmentation** (about 1300 lines): the segmentation half of `core/harmony.py`, `analysis/sounding_notes.py`, `analysis/non_chord_tones.py`, `analysis/harmonic_segmentation.py`, `NonChordToneSettings`, glossary. Synthetic tests and the BWV 66.6 cases of section 7.
* **003b, chord identity, chord symbols and the evaluation file** (about 950 lines plus the committed file): chord identity in `core/harmony.py`, `analysis/chords.py`, level 1 events in `analysis/harmony.py`, `eval/reductions.py` and `tests/eval/expected_reductions.txt`. From here on, any change of segmentation or naming is visible in review.
* **003c, voicing, rendering and the `reduce` command** (about 1000 lines): `voicing/planes.py`, `core/reduction.py`, `UnsupportedTextureError`, `render/chord_names.py`, the `chord_names` parameter of `write_piano_score`, the `reduce` subcommand with chord symbols at level 1. **This is the first output Nico can open in Sibelius.**
* **003d, local key, Roman numerals and level 2** (about 1300 lines plus the regenerated file): `analysis/keys.py`, `KeySettings`, `core/roman_numerals.py`, level 2 merging and `HarmonicAnalysis`, Roman numerals as lyrics, the `--names` option, level 2 as the output of `reduce`, architecture sections 4, 7 and 8 updated.

## 3. Design

### 3.1 Modules touched

```text
src/aretz_texture/core/harmony.py                 PitchName, SoundingNote, NonChordToneKind, NonChordTone,
                                                  PlaneNote, HarmonicWindow (003a); ChordQuality,
                                                  ChordIdentity, UnidentifiedSonority, GranularityLevel,
                                                  HarmonicEvent (003b); Mode, LocalKey, PhraseHarmony,
                                                  HarmonicAnalysis (003d)
src/aretz_texture/core/roman_numerals.py          RomanNumeral, roman_numeral (003d)
src/aretz_texture/core/reduction.py               VoicedChord, Reduction, ChordSymbolMark, reduction_score,
                                                  chord_symbol_marks (003c); RomanNumeralMark,
                                                  ChordNameSelection, chord_name_marks (003d)
src/aretz_texture/core/errors.py                  UnsupportedTextureError (003c)
src/aretz_texture/analysis/settings.py            NonChordToneSettings (003a), KeySettings,
                                                  HarmonicAnalysisSettings (003d)
src/aretz_texture/analysis/sounding_notes.py      sounding_notes (003a)
src/aretz_texture/analysis/non_chord_tones.py     classify_non_chord_tones (003a)
src/aretz_texture/analysis/harmonic_segmentation.py   segment_harmony (003a)
src/aretz_texture/analysis/chords.py              identify_chord (003b)
src/aretz_texture/analysis/harmony.py             analyze_surface_harmony (003b), analyze_harmony (003d)
src/aretz_texture/analysis/keys.py                phrase_key (003d)
src/aretz_texture/voicing/planes.py               voice_from_planes (003c)
src/aretz_texture/render/chord_names.py           boundary: <harmony> and lyrics (003c, 003d)
src/aretz_texture/render/piano_score.py           keyword parameter chord_names (003c)
src/aretz_texture/eval/reductions.py              corpus lines (003b, extended in 003d)
src/aretz_texture/cli.py                          new subcommand: reduce (003c, --names in 003d)
```

Each slice implements the part of a model it needs; a model introduced in one slice may gain fields in a later one, since no release separates them.

### 3.2 Architecture and ADR 0006

Chord identity, key and names are computed in pure code (ADR 0006): `analysis/` takes the analytical decisions, `core/` holds the results and derives their names as strings, `voicing/` reads only `core/`, and `render/` uses music21 only to write the names it receives. `analysis/` and `voicing/` stay independent (import contract), so everything voicing needs travels in the core harmonic events: the structural note of each plane in each window (traceability, architecture section 4). The command line is the only place that chains analysis, voicing and rendering. No change to `pyproject.toml`, no new dependency.

### 3.3 Core model of the segmentation (`core/harmony.py`, 003a)

Frozen pydantic models, `Fraction` for time, as in specs 001 and 002.

```python
class PitchName(BaseModel):
    step: StepName
    alter: int  # -2 to 2, as in SpelledPitch

    def text(self) -> str: ...  # "F#", "Bb", "C"; ASCII sharps and flats


class SoundingNote(BaseModel):
    stream: StreamReference  # the notated voice it sounds in
    pitch: SpelledPitch
    onset: Fraction  # attack of the first event of its tie chain
    end: Fraction  # end of the last event of the chain, clipped to the phrase


class NonChordToneKind(StrEnum):
    PASSING = "passing"
    NEIGHBOR = "neighbor"
    SUSPENSION = "suspension"
    ANTICIPATION = "anticipation"


class NonChordTone(BaseModel):
    note: SoundingNote
    kind: NonChordToneKind
    from_onset: Fraction  # where it stops being a chord tone: the tactus onset for a
    #                       suspension, the note's onset for the other kinds
    resolution: SpelledPitch | None  # only for a suspension: the pitch it resolves to


class PlaneNote(BaseModel):
    plane_number: int  # 1 is the highest plane of the phrase (spec 002, section 3.7)
    pitch: SpelledPitch  # the structural note of the plane in the window
    stream: StreamReference  # where it comes from


class HarmonicWindow(BaseModel):
    span: TimeSpan
    phrase_number: int
    plane_count: int  # planes of the phrase in the textural tree
    chord_tones: tuple[SpelledPitch, ...]  # highest first, doublings kept
    plane_notes: tuple[PlaneNote, ...]  # one per plane sounding in the window, by plane number
    non_chord_tones: tuple[NonChordTone, ...]  # those whose from_onset lies in the window
    fermata: bool  # last window of a phrase that closes at a fermata

    def bass(self) -> SpelledPitch: ...  # the lowest chord tone
```

Validators: `chord_tones` not empty and ordered highest first; `plane_notes` ordered by plane number, without repeats, each at most `plane_count`; `resolution` given exactly for suspensions.

### 3.4 Harmonic segmentation (003a)

```python
def sounding_notes(
    score: Score, stream: StreamReference, span: TimeSpan
) -> tuple[SoundingNote, ...]: ...


def classify_non_chord_tones(
    score: Score, notes: tuple[SoundingNote, ...], settings: NonChordToneSettings
) -> tuple[NonChordTone, ...]: ...


def segment_harmony(
    score: Score, texture: TexturalAnalysis, settings: NonChordToneSettings
) -> tuple[HarmonicWindow, ...]: ...
```

**Sounding notes** (project). Per notated voice of each leaf of the phrase, each pitch of each event becomes a sounding note, joined with the following events of its tie chain. A chain that crosses a phrase boundary is clipped, so each phrase is analyzed alone. Grace notes and rest fermatas are ignored. Two notes of one voice are **adjacent** when the first ends exactly where the second begins.

**Non chord tones.** Only notes of voices without a divided event at the note or its two neighbors are classified. Metric weight is on or off the tactus: a note is **accented** when it starts at the onset of a tactus span (`tactus_spans`, spec 002), **unaccented** otherwise (project). A **melodic step** is an interval of 1 to `maximum_melodic_step_semitones` semitones (project; chromatic steps count, the augmented second does not). The tactus T is that of the bar holding the note.

| Kind | Rule | Source |
|---|---|---|
| Passing tone | Unaccented, lasts at most `maximum_unaccented_duration` × T, adjacent to a previous and a next note, both melodic steps in the same direction | Theory (common practice voice leading); thresholds project |
| Neighbor tone | Same conditions, steps in opposite directions, previous and next notes of the same pitch | As above |
| Anticipation | Unaccented, as short, approached by step from an adjacent note, followed by an adjacent note of the same pitch that starts at the next tactus onset | As above |
| Suspension | Sounds at a tactus onset t that lies after its onset (tied over), or starts at t after an adjacent note of the same pitch (repeated); its preparation is consonant: at the onset of the note (tied over) or of the previous note (repeated), it forms none of the dissonances below with the pitches sounding there; at t it forms a second or seventh with another pitch sounding at t, or a fourth above the lowest pitch sounding at t; the next adjacent note is a melodic step below and starts no later than t + `maximum_suspension_duration` × T | As above; dissonance by the intervals of two voice counterpoint (theory); thresholds project |

Each rule reads only the note, its adjacent notes and the pitches sounding with them in the raw score, never other classifications. The suspension rule is checked first, and a note that is a suspension is no other kind; the three unaccented kinds apply only to the other notes and exclude each other by the motion after the note. The consonant preparation is what tells a suspension from an unaccented note tied across a tactus onset: a neighbor tone C4 sounding from beat 1.75 to 2.25 over G2, B3 and D4, between two B3, is dissonant from its start (a fourth above the bass), so it is not prepared and stays a neighbor tone (Codex review of #26). Consonance is not checked for the three unaccented kinds (project: in the chorales an unaccented consonant passing tone does not change the harmony). The interval classes of dissonance are named constants of music theory, not settings: `DISSONANT_INTERVAL_CLASSES = {1, 2, 10, 11}` and `DISSONANT_ABOVE_BASS_INTERVAL_CLASSES = {5}`.

**Reduced verticalities** (project). The instants of a phrase at which a reduced verticality is read are: every attack of a sounding note that is not a passing tone, neighbor tone or anticipation (attacks of suspensions count); every end, before the end of the phrase, of a sounding note that is a chord tone; and every tactus onset t of a suspension. Without the ends, a bass G2 ending on beat 2 while B3, D4 and G4 continue would leave G2 as the bass of the window until beat 3 (Codex review of #26). Verticalities are not read at the attack of a non chord tone: a passing tone in the lowest voice would otherwise leave the verticality without its bass and open a window, against ADR 0007 reading 7 and the passing tone property of section 5 (found while implementing 003a). At each instant, the reduced verticality is the set of pitches sounding there that are chord tones: a passing tone, neighbor tone or anticipation counts nowhere; a suspension counts as a chord tone before t and, from t until it ends, is replaced by its resolution (decided by Nico on November 26, 2026 (open question 2): resolved directly). A verticality read at the end of a note holds the pitches sounding from that instant on.

**Windows** (project, ADR 0007 reading 7). Walking the reduced verticalities of a phrase in order, the first one that is not empty opens a window; each later one opens a new window when it holds a pitch class the current window does not hold, or when its lowest pitch has another pitch class than the lowest of the window; otherwise it joins the current window, so a reattacked chord or a chord losing a voice continues. A window's chord tones are those of the verticality that opened it. Windows are contiguous: each ends where the next begins, and the last ends at the latest end of a sounding note of the phrase, so rests after a final fermata stay rests. Silence before the first attack of a phrase belongs to no window.

**Plane notes** (project). For each plane (leaf of the phrase's tree, in register order), its structural note in a window is its first chord tone sounding in the window: the one sounding at the onset (the resolution, for a suspension), else the first chord tone it attacks in the window. Among the voices of a plane, the lowest pitch is taken for the lowest plane (the actual bass of a continuo doubling) and the highest pitch for the other planes. A plane without a chord tone in the window has no plane note there (for example a bass that ends its fermata early, as in BWV 320, bar 2).

**Settings** (`analysis/settings.py`):

```python
class NonChordToneSettings(BaseModel):
    # Ratio of the tactus, from 0 to 1. Longest a passing tone, neighbor tone or anticipation
    # may last; longer unaccented notes are heard as chord tones. 1/2 is an eighth in 4/4.
    maximum_unaccented_duration: Proportion = Fraction(1, 2)
    # Ratio of the tactus, from 0 to 1. Longest a suspension may sound after the tactus
    # onset before its resolution; a later resolution makes it a chord tone.
    maximum_suspension_duration: Proportion = Fraction(1)
    # Semitones, from 1 to 3. Largest melodic interval heard as a step; 2 keeps the
    # augmented second (3 semitones) a leap.
    maximum_melodic_step_semitones: Annotated[int, Field(ge=1, le=3)] = 2
```

### 3.5 Chord identity and chord symbols (003b)

```python
class ChordQuality(StrEnum):  # values are the MusicXML <kind> names
    MAJOR = "major"
    MINOR = "minor"
    DIMINISHED = "diminished"
    AUGMENTED = "augmented"
    DOMINANT_SEVENTH = "dominant"
    MAJOR_SEVENTH = "major-seventh"
    MINOR_SEVENTH = "minor-seventh"
    HALF_DIMINISHED_SEVENTH = "half-diminished"
    DIMINISHED_SEVENTH = "diminished-seventh"


class ChordIdentity(BaseModel):
    root: PitchName
    quality: ChordQuality
    bass: PitchName
    inversion: int  # 0 root position, 1 first, 2 second, 3 third (sevenths only)

    def symbol(self) -> str: ...  # "G7/B"


class UnidentifiedSonority(BaseModel):
    pitch_names: tuple[PitchName, ...]  # distinct, in letter order from C
    reason: str  # "no third above any pitch", "C and C# in one window", ...


class GranularityLevel(IntEnum):
    SURFACE = 1
    HARMONIC_RHYTHM = 2
    PROLONGATION = 3  # reserved, not computed
    PHRASE = 4  # reserved, not computed


class HarmonicEvent(BaseModel):
    level: GranularityLevel
    span: TimeSpan
    reading: ChordIdentity | UnidentifiedSonority
    windows: tuple[HarmonicWindow, ...]  # traceability: the windows it covers, in order
    children: tuple["HarmonicEvent", ...]  # events of the level below; empty at level 1


def identify_chord(window: HarmonicWindow) -> ChordIdentity | UnidentifiedSonority: ...


def analyze_surface_harmony(
    score: Score, texture: TexturalAnalysis, settings: NonChordToneSettings
) -> tuple[HarmonicEvent, ...]: ...  # one level 1 event per window
```

An unidentified sonority is a reading, not an error: one augmented sixth chord must not stop the reduction of a chorale. `AmbiguousHarmonyError` is still not created.

**Identification** (theory: tertian harmony; vocabulary and fallbacks project, ADR 0007 reading 8). Take the distinct pitch names of the chord tones. Two names on one letter make the sonority unidentified. A root is a name from which every other name lies 2, 4 or 6 letters above (third, fifth, seventh) and at least one lies 2 letters above. The sizes in semitones of the third (3 or 4), fifth (6, 7 or 8, or absent) and seventh (9, 10 or 11, or absent) give the quality: (4, 7) major, (3, 7) minor, (3, 6) diminished, (4, 8) augmented, (4, 7, 10) dominant seventh, (4, 7, 11) major seventh, (3, 7, 10) minor seventh, (3, 6, 10) half diminished, (3, 6, 9) diminished seventh. An absent fifth is read as perfect. Any other combination, or no root, is unidentified with its reason. At most one root qualifies (hypothesis property). The inversion is the position of the window's bass name: root 0, third 1, fifth 2, seventh 3.

**Chord symbol** (project, ASCII, as music21 writes its figures): root text, then `""`, `m`, `dim`, `aug`, `7`, `maj7`, `m7`, `m7b5` or `dim7`, then `/` and the bass text when the inversion is not 0. The verified example: B3, D4, G4, F4 is `G7/B`. In the MusicXML file Sibelius shows the `<harmony>` element in its own chord symbol style; this string is for the evaluation file and messages.

### 3.6 Key and Roman numerals (003d)

```python
class Mode(StrEnum):
    MAJOR = "major"
    MINOR = "minor"


class LocalKey(BaseModel):
    tonic: PitchName
    mode: Mode

    def label(self) -> str: ...  # "A:" for A major, "f#:" for F sharp minor


class RomanNumeral(BaseModel):
    degree: int  # 1 to 7, letter distance from the tonic plus one
    figure: str  # "V65", "bII6", "viiø7"; the key label ("f#: i") is added by the marks


def roman_numeral(chord: ChordIdentity, key: LocalKey) -> RomanNumeral: ...  # core, pure


def phrase_key(
    notes: tuple[SoundingNote, ...],
    reference_key_signature: KeySignatureChange,
    settings: KeySettings,
) -> LocalKey: ...  # the key signature of the lowest plane's part at the phrase onset
```

**Key of a phrase** (theory: Krumhansl and Kessler 1982 profiles, Krumhansl 1990 key finding; one key per phrase is project, decided by Nico on November 26, 2026 (open question 4)). Sum the durations of the sounding notes of the phrase per pitch class, non chord tones included, and choose among the 24 keys the profile rotation with the greatest correlation. The ranking is computed exactly with `Fraction`: the sign of the covariance times its square, over the variance of the profile, which orders keys as the correlation does without square roots. Ties go to the key closest to `reference_key_signature`, the key signature in effect at the phrase onset in the part of the lowest plane's first notated voice, which the caller passes because `phrase_key` sees only sounding notes (Codex review of #26); then major before minor. The tonic takes the spelling of its pitch class with the longest duration in the phrase, or, when absent, the spelling with the fewest accidentals in its key signature.

```python
# Probe tone ratings of Krumhansl and Kessler (1982), from the tonic up by semitone.
KRUMHANSL_KESSLER_MAJOR = tuple(
    Fraction(rating)
    for rating in (
        "6.35",
        "2.23",
        "3.48",
        "2.33",
        "4.38",
        "4.09",
        "2.52",
        "5.19",
        "2.39",
        "3.66",
        "2.29",
        "2.88",
    )
)
KRUMHANSL_KESSLER_MINOR = tuple(
    Fraction(rating)
    for rating in (
        "6.33",
        "2.68",
        "3.52",
        "5.38",
        "2.60",
        "3.53",
        "2.54",
        "4.75",
        "3.98",
        "2.69",
        "3.34",
        "3.17",
    )
)


class KeySettings(BaseModel):
    # Unitless weights per pitch class from the tonic: how well each degree fits a major key.
    major_profile: tuple[Fraction, ...] = KRUMHANSL_KESSLER_MAJOR
    # The same for minor keys.
    minor_profile: tuple[Fraction, ...] = KRUMHANSL_KESSLER_MINOR


class HarmonicAnalysisSettings(BaseModel):
    non_chord_tones: NonChordToneSettings = Field(default_factory=NonChordToneSettings)
    keys: KeySettings = Field(default_factory=KeySettings)
```

The values are exact decimal fractions, so no float enters the analysis; a validator requires twelve positive values per profile. They match the published table as reproduced in the AMADS library documentation (checked November 25, 2026); the implementer checks them once more against Krumhansl (1990).

**Roman numeral** (project, following common textbook practice, ADR 0007 reading 10). Degree from the letter distance between tonic and root. Accidental before the numeral (`b`, `#`) from the root's alter against the reference scale: the major scale in major; in minor the natural minor scale, except that a root on the raised seventh takes none (V, vii°). Uppercase for major, augmented, dominant seventh and major seventh; lowercase otherwise. Marks: `°` diminished triad, `°7` diminished seventh, `ø7` half diminished, `+` augmented, `M7` major seventh, `7` the other sevenths. Figures: triads `""`, `6`, `64`; sevenths `7`, `65`, `43`, `42`, replacing the `7`. Examples: G7/B in C is `V65` (the verified music21 figure); B D F A in C is `viiø7`; G# B D F in A minor is `vii°7`; Bb/D in A minor is `bII6`; G major in A minor is `VII`; C/G in C is `I64` (decided by Nico on November 26, 2026 (open question 2), cadential six four). The marks `°` and `ø` are Latin 1 characters, present in every text font; `♭` and `♯` are avoided for Sibelius lyric fonts.

### 3.7 Levels, voicing and the reduced score (003c, 003d)

```python
class PhraseHarmony(BaseModel):  # 003d
    phrase: Phrase
    key: LocalKey
    events: tuple[HarmonicEvent, ...]  # level 2, each with its level 1 children


class HarmonicAnalysis(BaseModel):  # 003d
    phrases: tuple[PhraseHarmony, ...]  # one per phrase of the textural analysis

    def cut(self, level: GranularityLevel) -> tuple[HarmonicEvent, ...]: ...  # 1 or 2


def analyze_harmony(
    score: Score, texture: TexturalAnalysis, settings: HarmonicAnalysisSettings
) -> HarmonicAnalysis: ...
```

**Level 2** (project, decided by Nico on November 26, 2026 (open question 1)): consecutive level 1 events of one phrase merge when both are identified with the same root and the same quality, whatever the inversion (I and I6 merge, V and V7 do not). The level 2 event spans its children and takes the reading of the first. Unidentified sonorities never merge. `cut` raises `ValueError` for levels 3 and 4, which are not computed.

**Voicing** (`voicing/planes.py`, project, decided by Nico on November 26, 2026 (open question 3)):

```python
class VoicedChord(BaseModel):
    span: TimeSpan
    soprano: SpelledPitch | None  # None: the voice rests during this chord
    alto: SpelledPitch | None
    tenor: SpelledPitch | None
    bass: SpelledPitch | None
    fermata: bool


class Reduction(BaseModel):
    chords: tuple[VoicedChord, ...]  # in order, never overlapping


def voice_from_planes(events: tuple[HarmonicEvent, ...]) -> Reduction: ...
```

Soprano, alto, tenor and bass take the plane notes of planes 1 to 4 of the event's first window; a plane without a plane note rests. Every event must come from a phrase with exactly four planes, otherwise `UnsupportedTextureError` (a new `AretzTextureError`) names the first phrase, its bars and its plane count. With fusion of doublings this admits the 331 four part chorales and BWV 8.6 and BWV 248.59 6 (section 7, item 1).

**Reduced score** (`core/reduction.py`, project):

```python
def reduction_score(reduction: Reduction, source: Score) -> Score: ...
```

Four parts without names, one notated voice each, with the bars and time signatures of the source and the key signatures of the part holding the lowest plane in phrase 1. Each voiced chord becomes one note per sounding voice for its whole span (harmonic rhythm: every chord is attacked, even when a voice repeats its pitch), split at bar lines with ties, and at durations that cannot be written as one note value (section 7, item 5). Fermatas go on every voice of a chord with `fermata`. `piano_layout` accepts the result, so `write_piano_score` places soprano and alto on the upper staff and tenor and bass on the lower.

### 3.8 Chord names on the score (003c, 003d)

```python
class ChordSymbolMark(BaseModel):
    onset: Fraction
    root: PitchName
    quality: ChordQuality
    bass: PitchName


class RomanNumeralMark(BaseModel):  # 003d
    onset: Fraction
    text: str  # "V65", with the key label before the first chord of a phrase: "f#: i"


class ChordNameSelection(StrEnum):  # 003d
    SYMBOLS = "symbols"
    ROMAN = "roman"
    BOTH = "both"
    NONE = "none"


def chord_symbol_marks(events: tuple[HarmonicEvent, ...]) -> tuple[ChordSymbolMark, ...]: ...


def chord_name_marks(
    analysis: HarmonicAnalysis, level: GranularityLevel, selection: ChordNameSelection
) -> tuple[ChordSymbolMark | RomanNumeralMark, ...]: ...


def write_piano_score(
    score: Score,
    layout: GrandStaffLayout,
    output_path: Path,
    *,
    chord_names: tuple[ChordSymbolMark | RomanNumeralMark, ...] = (),
) -> None: ...
```

* **Chord symbols** above the upper staff: `render/chord_names.py` builds a music21 `harmony.ChordSymbol` from root, kind and bass, never from a figure or from pitches (ADR 0006), and inserts it at its onset in the upper staff, so the exporter writes `<harmony>`. Unidentified sonorities get no symbol.
* **Roman numerals below the bass** (project, decided by Nico on November 26, 2026, open question 5): music21 drops `RomanNumeral` objects on export, so each numeral is written as a lyric on the note of staff voice 2 of the lower staff (the bass) at its onset. Lyrics sit below the staff, align with the note, and Sibelius imports them as lyrics, which teachers already use for Roman numerals. An unidentified sonority writes `?`. The key label goes before the first numeral of the first phrase and of every phrase whose key differs from the previous one.
* The default `chord_names` is empty, so `piano` and every existing call are unchanged. The grand staff reader ignores harmonies and lyrics.

### 3.9 Command (003c, 003d)

```text
aretz-texture reduce SOURCE --output PATH [--names {symbols,roman,both,none}] [--level {1,2}]
```

Flow: `read_score`, `analyze_texture` and `analyze_harmony` with default settings, `cut(HARMONIC_RHYTHM)`, `voice_from_planes`, `reduction_score`, `chord_name_marks`, `piano_layout`, `write_piano_score`. `--names` defaults to `both` (open question 5). `--level` defaults to 2, harmonic rhythm; `--level 1` writes the level 1 events instead (`cut(SURFACE)`), the chorale almost as written with its chord names, for comparison with the source and in class (open question 1). In 003c the command writes level 1 events with chord symbols and has neither option; 003d adds both. Exit codes and the lyrics line as in `piano`; `UnsupportedTextureError` exits with 1, and no file is written.

### 3.10 Evaluation (`eval/reductions.py`, 003b, 003d)

In the spirit of 002d: one committed file that makes any change visible in review.

```python
def reduction_lines(
    identifier: str, score: Score, analysis: HarmonicAnalysis
) -> tuple[str, ...]: ...


def corpus_reduction_lines(settings: HarmonicAnalysisSettings) -> tuple[str, ...]: ...
```

* One line per phrase of the 350 distinct chorales, all of them, since segmentation and naming work for any number of planes: `identifier: phrase N, bars A to B, KEY: CHORDS`. `KEY` is the key label in words (`f# minor`); `CHORDS` lists the level 2 events as `POSITION SYMBOL ROMAN` separated by ` | `. `POSITION` is `B.T`, bar and tactus number as in `tactus_label`, or `B.T+F` when the event starts F quarter lengths after the tactus onset. An unidentified sonority prints `?(` its pitch names `)` in both places. In 003b, before keys exist, lines have no `KEY` and the tokens are level 1 `POSITION SYMBOL`.
* Illustrative, not real output: `bach/bwv66.6: phrase 1, bars 0 to 1, f# minor: 0.4 C#/E# V6 | 1.1 F#m i | 1.2 B/D# IV6 | 1.3 C#7 V7`.
* `tests/eval/expected_reductions.txt` holds the lines; the slow test compares them and reports the first differences; `uv run python -m aretz_texture.eval.reductions` regenerates it, and the PR that changes it explains why.
* One line per chorale that `voice_from_planes` refuses, after its phrase lines: `identifier: not voiced: phrase N has P planes`, so the scope of voicing is visible too.

### 3.11 Data flow

`cli`: `read_score` gives the `Score`; `analyze_texture` the `TexturalAnalysis`; `analyze_harmony` segments each phrase (sounding notes, non chord tones, windows with plane notes), identifies each window, finds the phrase key and merges level 2; `cut` gives the events; `voice_from_planes` the `Reduction`; `reduction_score` the four part `Score`; `chord_name_marks` the names; `write_piano_score` the file. The evaluation runs the chain up to `analyze_harmony` and `voice_from_planes`.

## 4. Acceptance criteria

### 003a: harmonic segmentation

1. Every model of section 3.3 is immutable, and the validators reject unordered chord tones, repeated or unordered plane notes, and a resolution on a kind other than suspension.
2. `sounding_notes` joins a tie chain (start, continue, stop) into one note from its first onset to its last end, keeps each pitch of a divided event apart, clips at the phrase span, and ignores grace notes and rest fermatas.
3. In 4/4, soprano eighths C5, D5 then a quarter E5 from beat 1: D5 is a passing tone; C5, D5, C5 makes D5 a neighbor tone; C5, B4, C5 a neighbor tone; C5, C#5, D5 makes C#5 a passing tone; C5, D#5, E5 does not (augmented second); a quarter D5 on beat 2 between quarters C5 and E5 is a chord tone (accented). With `maximum_unaccented_duration` 1/4, the eighth D5 is a chord tone.
4. In 3/2, a quarter passing tone on the second quarter of a half note tactus is a passing tone.
5. In 4/4, soprano eighths D5 on beat 3 and C5 on beat 3 and a half, followed by C5 on beat 4, make the eighth C5 an anticipation; followed by B4 instead, it is a passing tone.
6. Over a G2 bass with D4 and G4, an alto C4 tied over the bar line onto beat 1 that moves to B3 on the next eighth is a suspension resolving to B3; the same with C4 repeated instead of tied also is; with C4 unprepared, moving up to D4, or resolving after more than `maximum_suspension_duration` it is not. The window at beat 1 holds G2, B3, D4, G4. A C4 from beat 1.75 to 2.25 over G2, B3 and D4, between two B3, is a neighbor tone, not a suspension, since its preparation is dissonant. A bass G2 ending on beat 2 under B3, D4 and G4 held to beat 3 opens a window at beat 2 with B3 as its lowest pitch.
7. Windows of a phrase are contiguous, the first starting at the first attack of the phrase and the last ending at the latest end of a note in it; no window crosses a phrase boundary.
8. A new window starts at a new pitch class and at a change of the bass pitch class (C E G over C, then over E); a reattacked identical chord and a chord that loses a voice join the current window.
9. Plane notes: one per sounding plane by plane number; in BWV 8.6 the plane of Bass and Continuo gives the lower of the two; a plane that does not sound in a window has no plane note there (synthetic). (Corrected in 003a: in BWV 320, bar 2, the bass walks on after its fermata, so plane 4 has a plane note in every window.)
10. The last window of every phrase closing at a fermata has `fermata` true; no other window has.
11. BWV 66.6: the notes listed in section 7, item 2 are classified with the kind listed there.

### 003b: chord identity, chord symbols and the evaluation file

12. For every quality, root spelling with alter from -1 to 1, inversion, octave placement and doubling, `identify_chord` returns that root, quality and inversion (hypothesis property).
13. C E is C major without fifth; C E Bb is a dominant seventh; C G, C with C#, and Ab C Eb F# (an augmented sixth chord) are unidentified with a reason; B D F Ab has root B (diminished seventh) and C E G# root C (augmented).
14. `symbol()` gives `G7/B` for B3, D4, G4, F4, and `Bdim`, `F#m7b5`, `Bbmaj7`, `Ebaug`, `C#dim7/E` for their chords.
15. `analyze_surface_harmony` gives one level 1 event per window, with that window as its only one and no children.
16. The lines of `corpus_reduction_lines` with default settings equal `tests/eval/expected_reductions.txt`, one per phrase of the 350 chorales (2143 lines) plus one per chorale not voiced (slow).

### 003c: voicing, rendering and the command

17. `voice_from_planes` gives one voiced chord per event with the event's span, the plane notes of planes 1 to 4 as soprano to bass, rests for planes without a plane note, and the window's fermata.
18. `voice_from_planes` raises `UnsupportedTextureError` for BWV 27.6 (five planes), with the phrase, its bars and the count in the message.
19. `reduction_score` of BWV 66.6 has four parts with one notated voice each, the bars and time signatures of the source, an attack in every sounding voice at every chord onset and nowhere else, ties exactly where a chord crosses a bar line, and is accepted by `piano_layout`.
20. Writing a synthetic reduction of the chord B3, D4, G4, F4 writes a `<harmony>` on the upper staff with root G, kind `dominant`, inversion 1 and bass B; an unidentified sonority writes none.
21. Reading back with `read_grand_staff_file` the file written for any reduction gives `reduction_score` of it without part names (hypothesis property and BWV 66.6).
22. `aretz-texture reduce bwv66.6 --output PATH` exits with 0 and writes PATH; `reduce bwv27.6` exits with 1, explains that this version voices only four planes and writes no file; an unknown source exits with 1.
23. **Manual, by Nico:** the output for BWV 66.6 opened in Sibelius shows the chorale in harmonic rhythm on two staves, with a chord symbol above each chord. Recorded as a checked box in the PR description.

### 003d: key, Roman numerals and level 2

24. `phrase_key` of a phrase on the C major scale is C major, on A harmonic minor A minor; transposing a phrase by any interval with spelling transposes its key (hypothesis); equal correlations are broken as section 3.6 says.
25. `roman_numeral` gives `V65` for G7/B in C major, the examples of section 3.6, and in C major `I`, `ii`, `iii`, `IV`, `V`, `vi`, `vii°`, `IM7`, `V42`, `I64`; in A minor `i`, `ii°`, `III`, `iv`, `V`, `VI`, `vii°`, `VII`, `#iv°7` (D# F# A C).
26. Roman numerals do not change when chord and key are transposed together (hypothesis).
27. Level 2: I then I6 make one event with two children and the reading of I; V then V7 stay two events; an unidentified sonority never merges; no event crosses a phrase. `reduce bwv66.6 --level 1` writes one chord per level 1 event, and its default output equals `--level 2`.
28. With `--names roman` the file has a lyric on the bass at every chord onset and no `<harmony>`; with `symbols` the reverse; `both` has both; `none` neither. The first numeral carries the key label, and so does the first numeral of a phrase whose key changes.
29. The committed file is regenerated with keys, level 2 events and Roman numerals; its line for BWV 66.6 phrase 1 starts with the key of section 7, item 2.
30. **Manual, by Nico:** the BWV 66.6 output opened in Sibelius shows chord symbols above and Roman numerals below the bass, readable.

### All pull requests

31. Every analysis function is deterministic (two runs, equal results) and permuting the parts of a score does not change windows, readings or keys (hypothesis).
32. All commit checks pass (`uv run pre-commit run --all-files`) and the full suite passes in CI, including the committed files of specs 001 and 002, unchanged.

## 5. Test plan

### Concrete cases

* **BWV 66.6**, reference chorale: non chord tones of section 7, item 2 (criterion 11); the reduction and its file (criteria 19, 21, 22); the manual checks (criteria 23, 30); phrase 1 in the committed file (criterion 29).
* **BWV 8.6, BWV 248.59 6**: a doubled bass plane gives one plane note, the lower (criterion 9); both are voiced.
* **BWV 320, bar 2**: a plane that ends early has no plane note; its voice rests in the reduction (criteria 9, 17).
* **BWV 27.6, BWV 190.7**: analyzed and named in the committed file, refused by voicing (criteria 16, 18).
* **Synthetic scores** with `tests/core_builders.py`: criteria 3 to 8, 13, 17, 20, 24, 25, 27, 28.

### Hypothesis properties

New strategies: `spelled_chords()` (quality, root, inversion, voicing over several octaves with doublings) and `transpositions()` (a spelled interval).

* **Identification recovers the chord** (criterion 12) and **at most one root qualifies** for any set of pitch names.
* **Windows tile each phrase** from its first attack (criterion 7), for any score from `scores()`.
* **Adding an unaccented passing tone does not change the windows**: inserting, in any voice, an eighth by step between two notes a third apart, off the tactus, leaves the chord tones of every window unchanged.
* **Transposition**: transposing a score with spelling transposes roots, basses and keys and leaves Roman numerals unchanged (criteria 24, 26).
* **Part order** and **determinism** (criterion 31).
* **Harmonic rhythm**: in `reduction_score`, every voice attacks exactly at chord onsets where it sounds; the voices never overlap; the total duration equals the span of the chords.
* **Round trip of the reduction** (criterion 21).

Tests may also compare `symbol()` and `roman_numeral` with music21's `chordSymbolFromChord` and `romanNumeralFromChord` on the chords of criteria 14 and 25 (ADR 0006, decision 3); differences are listed in the test with their reason, not hidden.

## 6. Decisions taken in this spec

Musical readings are in ADR 0007; architecture in ADR 0006.

1. **Pure harmonic analysis** (project, ADR 0006): no music21 in analytical decisions; music21 only writes names.
2. **Segmentation rules** of section 3.4 (theory of common practice voice leading for the kinds; project for thresholds and the window rule).
3. **Vocabulary of chords** (section 3.5): nine qualities; unidentified sonorities are readings, not errors.
4. **Evaluation over all 350 chorales**, voiced or not (section 3.10).
5. **Reattacks:** every chord is attacked in every sounding voice (harmonic rhythm), even when a voice keeps its pitch.
6. **Key signature of the reduction** from the part of the lowest plane, since three chorales encode the soprano with another key signature (spec 002, section 3.6).

## 7. To verify before implementation

Facts this spec relies on that need running code; the main session probes them and the answers are written here before 003a starts.

1. **Scope of voicing:** the chorales whose every phrase has exactly four planes; expected 333 (the 331 four part chorales, BWV 8.6, BWV 248.59 6). *Verified November 25, 2026:* 333, exactly those. The other 17 have between 5 and 10 planes in some phrase (BWV 41.6, 248.9 1 and 29.8 have four planes in some phrases only).
2. **BWV 66.6 cases:** with the rules of section 3.4, one passing tone, one neighbor tone, one suspension and one anticipation if present (part, bar, tactus), to name in criterion 11; the key of each phrase by the rule of section 3.6, and music21's `analyze("key")` on the same phrase for comparison; its final chord.

   *Segmentation part, established November 26, 2026 (003a, default settings):* BWV 66.6 has 21 non chord tones in its six phrases: 12 passing, 5 neighbor, 4 suspension and no anticipation. The cases for criterion 11, with the tactus label of `tactus_label`, all in 4/4 with a quarter as tactus:
   * **Passing tone:** Alto D4, bar 8, tactus 1, half a beat after the tactus onset. The alto rises C#4, D4, E4 in the penultimate bar while soprano, tenor and bass hold; D4 is the eighth between the other two. The pickup has three passing tones at once, Soprano B4 (C#5, B4, A4), Tenor B3 (A3, B3, C#4) and Bass G#3 (A3, G#3, F#3), parallel eighths into bar 1.
   * **Neighbor tone:** Bass F#3, bar 4, tactus 1, half a beat after the onset. The bass goes G#3, F#3, G#3 in eighths under the E major chord over G# and then A3 and B3; F#3 is the lower neighbor of G#3.
   * **Suspension:** Alto F#4, bar 4, tactus 1, from onset 13, resolving to E4 a beat later. The alto holds F#4 from the F# minor chord of bar 3, beat 4, and attacks it again on the first beat of bar 4, where the bass moves to G#3 and the soprano and tenor sound B4 and B3. F#4 is a seventh above G#3 and falls by step to E4, a 7 to 6 suspension (repeated, not tied).
   * **Anticipation:** none in BWV 66.6. BWV 347 has one: Alto E4, bar 7, tactus 3, half a beat after the onset; the alto goes F#4, E4, E4 and the eighth E4 sounds the note of the next beat early.
   * Two readings of the rules to know. In bar 7 (phrase 5) the alto F#4 on the first beat is a suspension resolving to E#4, and that E#4 is itself a neighbor tone between two F#4: both fire. The syncopated Tenor C#4 of bar 8 (from beat 2, a second over the bass B2 at beat 3, resolving to B3 at beat 4) is a suspension; the Alto E4 of the same bar is not, because it is already dissonant when it starts, over the soprano F#4 (a second), so its preparation is not consonant.

   The key and the final chord are left to 003b and 003d.
3. **`<harmony>` from a ChordSymbol built from root, kind and bass** (no figure): music21 writes root, kind, inversion and bass; in which container it must be inserted (measure of the upper `PartStaff`, not a `Voice`) to appear above the upper staff; the grand staff reader ignores it. *Verified November 25, 2026:* `ChordSymbol(root='G', bass='B', kind='dominant-seventh')` inserted at offset 0 of the measure of the upper `PartStaff` is written as `<harmony>` with root G, kind `dominant`, inversion 1, bass B and `<staff>1</staff>`, before the first note, and reads back as `G7/B`. Whether `read_score` ignores it is left to 003c.
4. **Lyrics on staff voice 2 of the lower staff:** exported as `<lyric>` below the staff, read back, with `°`, `ø`, `#`, `/` and `:` intact. *Verified November 25, 2026:* a lyric `f#: vii°7/V bII6 iiø7` on voice 2 of the lower `PartStaff` is written as one `<lyric>` and reads back unchanged.
5. **Durations:** whether `write_piano_score` writes and reads back exactly a note of 5/2 or 7/4 quarter lengths inside a bar, and a note starting off the beat that crosses it. If not, `reduction_score` splits durations into single note values itself (section 3.7). *Verified November 25, 2026:* `write_piano_score` writes 5/2 as a half tied to an eighth and 9/4 as a half tied to a sixteenth, 7/4 as one double dotted quarter, and a dotted half starting on the second eighth as one note; `read_score` reads them back with the same sounding durations, the split values as tied events. So `reduction_score` does not need to split durations; comparisons must join ties into sounding notes.
6. **Corpus estimate with the rules of 3.4 and 3.5:** the share of unidentified windows and their most frequent pitch sets; the number of windows shorter than one tactus; the number of windows where a plane other than the lowest has a chord tone below the bass plane (voice crossing); the number of level 2 merges. This sizes open questions 1 to 3 with examples.

   *Established November 26, 2026 (003a, default settings, over the 350 distinct chorales, music21 10.5.2):* the unidentified windows and the level 2 merges need 003b and 003d. What 003a measures, over the 333 chorales with four planes in every phrase and over all 350:

   | | 333 with four planes | all 350 |
   |---|---|---|
   | Harmonic windows | 19994 | 21471 |
   | Windows shorter than one tactus | 8818 (44%) | 9666 (45%) |
   | Windows with a voice crossing | 95, in 64 chorales | 137, in 71 chorales |

   A voice crossing is a window whose lowest plane has a plane note and some other plane has a plane note lower than it, for example the tenor below the bass. Examples of short windows: BWV 269, bar 3, tactus 2, two windows of an eighth each; BWV 347, bar 0, tactus 4 (the pickup), the same. Examples of crossing: BWV 83.5, phrase 3, bar 6, tactus 3 (soprano G4, alto D4, tenor G3 below the bass B3); BWV 10.7, phrase 2, bar 7, tactus 3 (C5, Eb4, tenor G3 below the bass C4); BWV 320, phrase 2, bar 4, tactus 2 (tenor F3 below the bass A3). Crossings are about 1 window in 210 of the four plane chorales.

   The windows are read at the instants of section 3.4: attacks of notes that are not passing tones, neighbor tones or anticipations, ends of chord tones before the end of the phrase, and the tactus onsets of suspensions. The ends raise the count a great deal: reading only the attacks of such notes (the first reading of 003a, before the review of #26) gave 17279 windows, 3691 shorter than a tactus and 94 crossings over the 333, and 18642, 4330 and 138 over all 350. Of the 21471 windows over the 350, 3751 start exactly where a passing tone, neighbor tone or anticipation starts. There the chord tone that the ornament replaces has ended, and the verticality read at that end lacks the voice; when it is the lowest voice, the bass changes pitch class and a window opens. In the pickup of BWV 66.6, three parallel passing tones (Soprano B4, Tenor B3, Bass G#3) leave the alto E4 alone in a window of an eighth. The passing tone property of section 5 therefore holds for the voices that are not the only lowest note at that moment, not for the bass. The suspension rule with a consonant preparation also lowers the suspensions of the corpus from 3007 to 2501.

## 8. Open questions for Nico

All answered by Nico on November 26, 2026: he adopted the recommendations of questions 2 to 5, and for question 1 the recommended rule (same root and quality, inversion ignored, so V and V7 stay two chords) together with `--level 1`. He kept V and V7 apart on purpose: a reading that merges them by function would hide a trait he wants to see when studying the characteristic features of a work.

1. **What counts as a change of function at level 2?** *Recommendation:* same root and same quality, inversion ignored: I and I6 are one chord, V and V7 two, C major and C7 two (the seventh may make it V7 of IV). The merged chord is named and voiced as its first window, so the reduction loses bass motion within a harmony (I to I6). This is also why "almost unchanged" holds at level 1 rather than level 2: should `reduce` offer `--level 1` as well? It costs a few lines, since level 1 is computed anyway.
2. **Suspensions and the cadential six four.** Resolved directly, so the reduced chord at the beat is the chord of resolution and the suspension is only recorded in the traceability? And the cadential six four named `I64` as a chord of its own, rather than `V64` over a dominant? *Recommendation:* yes to both for this version (architecture, section 11 lists the first as open); showing suspensions belongs with the representative rhythm.
3. **Voicing from the planes.** For four plane textures, the four voices take the four planes' notes, so the chorales return with their own voice leading, and the cost based voicing of architecture section 7 waits for textures without four lines. Where the tenor crosses below the bass, the bass voice keeps the bass plane, while the chord's inversion follows the lowest note. *Recommendation:* adopt; the alternative, sorting the four pitches by height at each chord, guarantees the bass is the lowest note but breaks lines at every crossing. Section 7, item 6 counts the crossings.
4. **Key per phrase.** One key per phrase by the Krumhansl and Kessler profile, tonicizations inside a phrase written as chromatic degrees (II for V of V)? *Recommendation:* adopt for the first version; applied chord notation (`V/V`) is the natural next step and could be a small spec of its own.
5. **Carrier and default of the names.** Roman numerals as lyrics on the bass, with ASCII accidentals (`bII6`) and the key label (`f#: i`) at each change of key; chord names `both` by default? *Recommendation:* yes to lyrics (they align with the notes and Sibelius edits them as text; a text direction below the staff does not align) and to `both` as default, since a student can hide either in Sibelius.
