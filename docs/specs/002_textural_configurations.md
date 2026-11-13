# Spec 002: textural configurations of the chorales

Issue: to be opened from the scope agreed with Nico on November 12, 2026
Status: Draft, November 12, 2026, awaiting gate 1
Related: ADR 0004 (Fessel's textural model), ADR 0005 (operational readings for the chorales, Proposed), `docs/theory/algorithmic_decomposition.md`, `docs/theory/fessel_textural_model.md`

**Main points to review:** the core model of textural configurations and its validators (section 3.2), the operational readings of the features (section 3.6 and ADR 0005), the phrase segmentation (section 3.4), and the open questions of section 8. Every decision is marked **Fessel** (with page) or **project**; only the first is theory.

## 1. Context

Nico wants the tool to describe the texture of a score the way Pablo Fessel does: for each passage, a tree of textural configurations whose nodes carry the five binary features planes (P), homogeneity (H), linearity (L), accent coincidence (C) and attack divergence (D) (Fessel, 1996, p. 79). This is the first slice from the score to that tree. It is evaluated on the 350 distinct corpus chorales, for which Fessel himself gives a reference: a phrase of "O Haupt voll Blut und Wunden" is `[+P, +H, +C, +D [-P, +H, +L, +C, -D]]`, four homogeneous lines with coincident accents and diverging attacks (1996, p. 86, example 6).

The slice is thin on purpose. It computes P, L and D from measures, gives H and C by simple rules that hold for one key and one meter per phrase, segments the chorales into phrases by their fermatas, and fuses doublings (an instrument playing the same line as a voice) into one stream, following Fessel (2000). Each feature records the rule or factor that decided it, because Fessel (2000, p. 88) values identifying the factors behind a reading more than the binary decision itself. The result is printed as a textual schema in Fessel's bracket notation through a new command.

## 2. Scope

### In

* Core model of textural configurations: a frozen pydantic tree whose nodes carry the five features, with the five feature cooccurrence restrictions of Fessel (1996, pp. 84 and 85) as validators (`core/texture.py`).
* Typed analysis settings with every threshold named, with unit and musical meaning (`analysis/settings.py`).
* The tactus of each bar and its tactus spans on the bar grid (`analysis/metric_grid.py`).
* Attacks of a notated voice (`analysis/attacks.py`).
* Phrase segmentation by fermatas, independent of part order, with a fallback for scores without fermatas (`analysis/phrases.py`).
* Fusion of doublings (unison and octave) into fused streams with density (`analysis/doublings.py`).
* Feature decisions (`analysis/features.py`) and the tree of each phrase (`analysis/texture.py`).
* The textual schema in Fessel's notation, rendered from the tree only (`render/textural_schema.py`), and the command `aretz-texture schema`.
* Evaluation over the 350 chorales with committed lists (`eval/textural_configurations.py`), including Fessel's example 6 as a named acceptance test.

### Out

* **Stream segregation** inside one notated voice (virtual polyphony). A notated voice is never split.
* **A model of phenomenal accents.** C is given by a provisional rule (section 3.6); syncopation and hemiola across planes are not detected.
* **Characterization of strata** as line, pedal, ostinato or harmonic ripieno (Fessel, 2000, p. 84), and formal variability.
* **Intermediate grouping** beyond doublings: every fused stream is a plane directly under the root. Planes in strict parallel at intervals other than unison and octave (Fessel's two oboes, 1996, pp. 85 to 88) do not form intermediate +P nodes. No case is trivial enough to include: even parallel thirds need a threshold for how strict the parallelism is.
* **Extreme spacing** that splits a doubling (Fessel, 2000, note 10): not modeled.
* **Dynamics** and the intensity factor; timbre as a criterion of H (part and instrument names are only shown in labels).
* **Comparing successive configurations** (merging adjacent phrases with the same configuration, appearance or division of planes).
* Repertoire other than the chorales, the four voice reduction, MusicXML output of the schema.

### Delivery

Four pull requests, in this order, each under about 1500 changed lines and mergeable on its own:

* **002a, core model and schema rendering** (about 850 lines): `core/texture.py`, `render/textural_schema.py`, their tests on hand built trees (example 6 and the other examples of Fessel 1996, pp. 85 to 89), glossary.
* **002b, phrases and doublings** (about 1100 lines): `analysis/settings.py`, `analysis/metric_grid.py`, `analysis/attacks.py`, `analysis/phrases.py`, `analysis/doublings.py`, with synthetic and corpus tests.
* **002c, features, tree and command** (about 1050 lines): `analysis/features.py`, `analysis/texture.py`, the `schema` subcommand in `cli.py`, architecture document sections 4 and 5 updated.
* **002d, evaluation** (about 650 lines including the committed lists): `eval/textural_configurations.py`, the slow corpus test, the committed lists and the example 6 test.

## 3. Design

### 3.1 Modules touched

```text
src/aretz_texture/core/texture.py             TimeSpan, StreamReference, TexturalFeature, DecisionRule,
                                              FeatureDecision, TexturalFeatures, TexturalConfiguration,
                                              PhraseClosing, Phrase, PhraseTexture, TexturalAnalysis
src/aretz_texture/analysis/settings.py        PhraseSegmentationSettings, DoublingSettings,
                                              FeatureSettings, TexturalAnalysisSettings
src/aretz_texture/analysis/metric_grid.py     tactus_duration, tactus_spans
src/aretz_texture/analysis/attacks.py         Attack, voice_attacks
src/aretz_texture/analysis/phrases.py         FermataEndCluster, fermata_end_clusters, segment_phrases
src/aretz_texture/analysis/doublings.py       FusedStream, coinciding_attack_proportion, fuse_doublings
src/aretz_texture/analysis/features.py        one decision function per feature
src/aretz_texture/analysis/texture.py         analyze_texture
src/aretz_texture/render/textural_schema.py   compact_schema, format_textural_schema
src/aretz_texture/eval/textural_configurations.py   corpus evaluation
src/aretz_texture/cli.py                      new subcommand: schema
```

Analysis parameters are called **settings**, never configuration, so that "configuration" always means Fessel's textural configuration (glossary).

### 3.2 Core model (`core/texture.py`, 002a)

Frozen pydantic models, `Fraction` for time, as in spec 001.

```python
class TimeSpan(BaseModel):
    onset: Fraction  # quarter lengths from the start of the first bar
    end: Fraction  # greater than onset

    def contains(self, other: "TimeSpan") -> bool: ...


class StreamReference(BaseModel):
    part_number: int  # 1 based, score order
    voice_number: int  # 1 based notated voice of that part
    part_name: str | None  # as in the source; shown in the labels of the schema

    def label(self) -> str: ...  # "Soprano (part 1, voice 1)", "unnamed (part 5, voice 1)"


class TexturalFeature(StrEnum):
    PLANES = "P"
    HOMOGENEITY = "H"
    LINEARITY = "L"
    ACCENT_COINCIDENCE = "C"
    ATTACK_DIVERGENCE = "D"


class DecisionRule(StrEnum):
    PLANE_COUNT = "plane_count"  # P from the number of planes below the node
    SINGLE_METER_AND_KEY = "single_meter_and_key"  # H, provisional rule, section 3.6
    ASSUMED_OUTSIDE_CONDITIONS = "assumed_outside_conditions"  # H outside its conditions
    SHARED_METER = "shared_meter"  # C at +P nodes, provisional rule
    SIMULTANEITY_CONDITIONS = "simultaneity_conditions"  # L at -P nodes
    ATTACKS_WITHIN_TACTUS = "attacks_within_tactus"  # D measured
    RESTRICTION_2 = "restriction_2"  # -P implies +H (Fessel 1996, p. 84)
    RESTRICTION_3 = "restriction_3"  # -C implies +P, so -P is +C
    RESTRICTION_4 = "restriction_4"  # L unspecified at +P
    RESTRICTION_5 = "restriction_5"  # +L implies -D


class FeatureDecision(BaseModel):
    value: bool | None  # True is +, False is -, None is unspecified (only L, at +P)
    rule: DecisionRule
    explanation: str  # one sentence for a musician, with bars and tactus spans


class TexturalFeatures(BaseModel):
    planes: FeatureDecision
    homogeneity: FeatureDecision
    linearity: FeatureDecision
    accent_coincidence: FeatureDecision
    attack_divergence: FeatureDecision


class TexturalConfiguration(BaseModel):
    span: TimeSpan
    features: TexturalFeatures
    children: tuple["TexturalConfiguration", ...]  # the planes below; empty exactly at -P
    streams: tuple[StreamReference, ...]  # only at -P: the notated voices it groups

    def leaves(self) -> tuple["TexturalConfiguration", ...]: ...  # -P nodes, in order

    def density(self) -> int: ...  # number of streams of a -P node


class PhraseClosing(StrEnum):
    FERMATA = "fermata"  # ends at a fermata end cluster
    SCORE_END = "score_end"  # the music after the last fermata
    NO_FERMATAS = "no_fermatas"  # the whole score, which has no fermata


class Phrase(BaseModel):
    number: int  # 1 based
    span: TimeSpan
    first_bar_number: int  # the bar containing the onset, as shown in the score
    last_bar_number: int  # the bar containing the last moment before the end
    closing: PhraseClosing


class PhraseTexture(BaseModel):
    phrase: Phrase
    configuration: TexturalConfiguration  # its span equals the span of the phrase


class TexturalAnalysis(BaseModel):
    phrases: tuple[PhraseTexture, ...]  # numbered from 1, contiguous, covering the score
```

Validators (violations raise pydantic `ValidationError`; an invalid tree is a programming error of the analysis, as in spec 001):

* `TimeSpan`: `onset < end`.
* `TexturalFeatures`, the five cooccurrence restrictions (**Fessel 1996, pp. 84 and 85**): (1) `-H` implies `+P`; (2) `-P` implies `+H`; (3) `-C` implies `+P`; (4) L is specified (not `None`) if and only if `-P`; (5) `+L` implies `-D`. Only `linearity.value` may be `None`. Restrictions 1 and 2 are contrapositives of each other as transcribed, so one check covers both (open question 7).
* `TexturalConfiguration` (**project**, following the tree of Fessel 1996, pp. 83 and 84): `+P` if and only if there are at least two children, and `-P` if and only if there are none; a `-P` node has at least one stream and a `+P` node has none of its own; every child span is contained in the parent span; no `StreamReference` (by part and voice number) appears in two leaves of one tree, since segregation is out of scope.
* `TexturalAnalysis`: phrases numbered 1, 2, ... in order; each phrase starts where the previous one ends; the first starts at 0; each configuration span equals its phrase span.

`DecisionRule` is one enumeration for all features; the core does not check that a rule fits its feature.

### 3.3 Settings (`analysis/settings.py`, 002b)

Every threshold lives here, frozen, with its unit and one line of musical meaning. Defaults are provisional and may be recalibrated only through this spec or an ADR.

```python
class PhraseSegmentationSettings(BaseModel):
    # Tactus spans. Fermata ends of different notated voices closer than this mark one
    # phrase end, so a fermata written on a slightly longer note in one voice does not
    # create a phrase of a single beat.
    fermata_alignment_tolerance: Fraction = Fraction(1)
    # Notated voices. How many notated voices must carry a fermata in a cluster for it
    # to end a phrase; 1 means any voice, so a missing fermata in other parts is harmless.
    minimum_fermata_voices: int = 1


class DoublingSettings(BaseModel):
    # Ratio from 0 to 1. Share of the attacks of the voice with fewer attacks that must
    # fall at the same onset as an attack of the other voice, with a common pitch class,
    # for the two voices to be heard as one line with density (Fessel 2000, p. 87).
    minimum_coinciding_attack_proportion: Fraction = Fraction(9, 10)


class FeatureSettings(BaseModel):
    # Interval classes in semitones modulo the octave at which simultaneous pitches of one
    # plane can still form one voice: unison and octave (0), fourth and fifth (5, 7), thirds
    # (3, 4) and sixths (8, 9), after Fessel's scale of closeness (1996, p. 81) and his
    # registral spacing of a line (2000, p. 86).
    linear_interval_classes: frozenset[int] = frozenset({0, 3, 4, 5, 7, 8, 9})
    # Ratio from 0 to 1. Share of the steps between successive attack points of a plane,
    # where it has simultaneous pitches other than unison and octave, at which all its
    # pitches move in the same direction; Fessel 2000 (p. 86) asks that the parallelism
    # be relatively constant.
    minimum_parallel_motion_proportion: Fraction = Fraction(9, 10)
    # Ratio from 0 to 1. Share of the attack points of a plane at which the conditions of
    # linearity must hold for the plane to be +L; 1 is Fessel's necessary condition.
    minimum_linear_attack_proportion: Fraction = Fraction(1)
    # Tactus spans. How many tactus spans with diverging attacks make a configuration +D.
    minimum_divergent_tactus_spans: int = 1


class TexturalAnalysisSettings(BaseModel):
    phrases: PhraseSegmentationSettings = Field(default_factory=PhraseSegmentationSettings)
    doublings: DoublingSettings = Field(default_factory=DoublingSettings)
    features: FeatureSettings = Field(default_factory=FeatureSettings)
```

The 9/10 default is the threshold of the corpus probe of November 12, 2026, whose results are cited in section 5.

### 3.4 Metric grid, attacks and phrases (002b)

**Tactus** (**project**, algorithmic decomposition step 1; Fessel 1996, p. 83 needs a tactus for D but does not fix it):

```python
def tactus_duration(time_signature: TimeSignatureChange) -> Fraction: ...


def tactus_spans(score: Score, span: TimeSpan) -> tuple[TimeSpan, ...]: ...
```

* The tactus is the beat of the time signature: `4 / denominator` quarter lengths, or `3 * 4 / denominator` (a dotted beat) when the numerator is 6, 9 or 12 (`COMPOUND_METER_NUMERATORS`, a named constant of music theory, not a setting). In the corpus: 1 for 4/4 and 3/4, 2 for 3/2, 3/2 for 12/8.
* Tactus spans tile each bar from its onset, using the time signature in effect at the bar. A first bar shorter than its meter (a pickup bar) is tiled from its end backwards, so its tactus spans fall on the last beats of a virtual complete bar; the first span may be shorter. Any other short bar is tiled from its onset, and its last span may be shorter. `tactus_spans` returns the spans that overlap `span`, clipped to it.
* For labels, tactus spans are numbered from 1 within the virtual complete bar, so the pickup of BWV 66.6, whose first note music21 reports on beat 4 (spec 001, section 8), is "bar 0, tactus 4".

**Attacks** (**project**):

```python
class Attack(BaseModel):
    onset: Fraction
    pitches: tuple[SpelledPitch, ...]  # the pitches that start here, highest first
    stream: StreamReference


def voice_attacks(score: Score, stream: StreamReference, span: TimeSpan) -> tuple[Attack, ...]: ...
```

An attack is a note event whose onset lies in the span, keeping only the pitches whose tie is not `STOP` or `CONTINUE`; an event all of whose pitches continue a tie is not an attack. Grace notes and rest fermatas are not attacks (a grace note takes no time in the bar).

**Phrases** (**project**, not Fessel: Fessel treats configurations as local, 1996, p. 90, but does not formalize the domain; ADR 0005):

```python
class FermataEndCluster(BaseModel):
    boundary: Fraction  # the latest fermata end of the cluster: where the phrase ends
    ends: tuple[Fraction, ...]  # every distinct fermata end in the cluster, ascending
    streams: tuple[StreamReference, ...]  # the notated voices that carry them


def fermata_end_clusters(
    score: Score,
    settings: PhraseSegmentationSettings,
) -> tuple[FermataEndCluster, ...]: ...


def segment_phrases(score: Score, settings: PhraseSegmentationSettings) -> tuple[Phrase, ...]: ...
```

1. Collect the fermata ends of **every notated voice of every part**: the end of each event with `fermata` true and the end of each rest fermata. No part is privileged, so the result does not depend on part order (corpus facts: in BWV 248.9 1, BWV 190.7 and BWV 248.23 2 part 1 has no fermata, and in 56 chorales the fermata ends of the first four parts disagree).
2. Sort the ends and cluster them: a cluster starts at its earliest end and takes every following end closer than `fermata_alignment_tolerance` tactus spans (tactus of the bar containing the earliest end). The boundary of the cluster is its latest end, so every fermata note of the cluster belongs to the phrase it closes.
3. A cluster ends a phrase when at least `minimum_fermata_voices` distinct notated voices contribute to it.
4. Phrases run between consecutive boundaries from 0. When the last boundary is before the end of the score, the remaining music is a last phrase with closing `SCORE_END`; a boundary at the end of the score closes the last phrase with `FERMATA`.
5. **Fallback**: a score without any fermata is one phrase covering the whole score, closing `NO_FERMATAS`.

### 3.5 Fusion of doublings (`analysis/doublings.py`, 002b)

**Fessel 2000, pp. 85 to 88**: simultaneous sounds form one line with density when their attacks coincide strictly and they move preferably in parallel; timbre cannot decide it alone. Thresholds are **project** decisions (ADR 0005). Fusion of separate notated voices stays at unison and octave; the wider set of intervals applies to linearity inside a plane (section 3.6).

```python
class FusedStream(BaseModel):
    streams: tuple[StreamReference, ...]  # sorted by part number, then voice number


def coinciding_attack_proportion(
    first: tuple[Attack, ...],
    second: tuple[Attack, ...],
) -> Fraction: ...


def fuse_doublings(score: Score, settings: DoublingSettings) -> tuple[FusedStream, ...]: ...
```

* Two attacks coincide when they have the same onset and share at least one pitch class: a doubling at the unison or at any number of octaves, so parallel motion at those intervals follows. `coinciding_attack_proportion` is the number of coinciding attack pairs divided by the attack count of the voice with fewer attacks over the whole score; it is 0 when either has no attack.
* Two notated voices are doublings of each other when the proportion is at least `minimum_coinciding_attack_proportion`. Fused streams are the connected groups of that relation (so Oboe 1, Violin 1 and Soprano join in one group if each pair or a chain of pairs qualifies). Every notated voice belongs to exactly one fused stream; most are alone.
* Fusion is computed once over the **whole score**, as in the corpus probe, because the doublings of a chorale come from its instrumentation. In a phrase, a fused stream is present when at least one of its notated voices attacks there, and its leaf lists only those voices; its density is their number.
* Fused streams are ordered deterministically by their first stream reference; planes are ordered later by register (section 3.7).

### 3.6 Feature decisions (`analysis/features.py`, 002c)

The **components** of a node are what can attack: at the root, its planes (the attacks of a plane are the union of the attacks of its notated voices in the phrase); at a leaf, its notated voices. Every decision returns a `FeatureDecision`, whose explanation names bars and tactus spans where it applies.

| Feature | At the root (+P) | At a leaf (-P) | Source |
|---|---|---|---|
| P | `+` with two or more planes present in the phrase, else the root is the single leaf; `PLANE_COUNT` | `-`; `PLANE_COUNT` | Fessel 1996, pp. 79 to 83; counting planes is the definition |
| H | `+` with `SINGLE_METER_AND_KEY` when the phrase has one time signature and no key signature change strictly inside it in any part; otherwise `+` with `ASSUMED_OUTSIDE_CONDITIONS` | `+`; `RESTRICTION_2` | Restriction from Fessel 1996, p. 84; rule is project, provisional |
| L | unspecified (`None`); `RESTRICTION_4` | measured, below; `SIMULTANEITY_CONDITIONS` | Conditions from Fessel 1996, pp. 79 to 83; thresholds project |
| C | `+`; `SHARED_METER` | `+`; `RESTRICTION_3` | Restriction from Fessel 1996, p. 84; rule is project, provisional |
| D | measured, below; `ATTACKS_WITHIN_TACTUS` | `-` with `RESTRICTION_5` when `+L`, else measured | Definition from Fessel 1996, p. 83; reading is project, to be confirmed |

**H, provisional rule.** Fessel's criteria for homogeneity in tonal music are a shared harmonic field, simple proportions between the pulses of the planes, the same spatial origin and timbral homogeneity (1996, pp. 79 to 83). In the core model every part shares the score's meter, so the pulse proportions between planes are simple when the phrase has one time signature; one key signature per part throughout the phrase stands in for one harmonic field. Key signatures are not compared across parts, because three corpus chorales (BWV 244.15, BWV 62.6, BWV 4.8) encode the soprano with another key signature while the pitches agree (journal of November 11, 2026). Outside these conditions the rule does not apply; the value `+` is then an assumption, recorded as such and listed by the evaluation.

**C, provisional rule.** `+` because every plane follows the score's single meter, which the core model guarantees. The explanation says that phenomenal accents, syncopation and hemiola are not modeled.

**L at a leaf** (necessary conditions of Fessel 1996, pp. 79 to 83). At each attack point of the plane in the phrase, the conditions hold when (a) every notated voice of the plane that sounds at that point also attacks there, and (b) every pair of pitches attacked there, within and across divided events, is at an interval class in `linear_interval_classes`. The plane is `+L` when the share of attack points meeting both is at least `minimum_linear_attack_proportion` and, if any of those attack points holds simultaneous pitches other than unison and octave, the share of steps between successive attack points at which all pitches move in the same direction (all up, all down or all repeated) is at least `minimum_parallel_motion_proportion`. Unison and octave need no parallel motion, since they are a registral duplication of one note (Fessel 2000, p. 86). The explanation names the first failing attack and the condition that failed. A single notated voice without divided events is always `+L`. The sufficient conditions (registral, timbral and dynamic continuity, formal variability) are research and out of scope.

**D** (**operational reading from the corpus facts, to be confirmed by Nico**, ADR 0005). A tactus span of the phrase is divergent when two different components attack at different time points inside it. One component attacking while the others hold or rest is not divergence, since no one to one correspondence of attacks is needed (Fessel 1996, p. 83); attacks in different tactus spans never diverge. The node is `+D` when at least `minimum_divergent_tactus_spans` tactus spans are divergent. At the root, D is also `+` when some leaf is `+D`, because Fessel's D covers divergence within or between the planes (1996, p. 83); the explanation says which case applies. The explanation gives the count of divergent spans over the total and the first divergent span with the two components involved.

### 3.7 The tree of a phrase (`analysis/texture.py`, 002c)

```python
def analyze_texture(score: Score, settings: TexturalAnalysisSettings) -> TexturalAnalysis: ...
```

1. `segment_phrases(score, settings.phrases)` and `fuse_doublings(score, settings.doublings)`.
2. For each phrase, the planes are the fused streams present in it (section 3.5). **Project, for this slice:** each present fused stream is one plane directly under the root (algorithmic decomposition, step 4, reduced to doublings). With one plane, the phrase's configuration is that leaf.
3. Leaves are built first (L, then D, then H and C by restriction), then the root (P, H, C, D).
4. Planes are ordered by register, highest first: by the mean sounding pitch of the pitches they attack in the phrase (`SpelledPitch.sounding_semitones`, exact as a `Fraction`), ties broken by the first stream reference (**project**, presentation only: Fessel's configurations are unordered, 1996, p. 79). Instruments listed first in the score therefore do not come first unless they are higher.
5. Every node's span is the phrase span.

`analyze_texture` is pure and deterministic: no I/O, no randomness, no dependence on dictionary or set iteration order.

### 3.8 Rendering (`render/textural_schema.py`, 002a) and command (`cli.py`, 002c)

```python
def compact_schema(configuration: TexturalConfiguration) -> str: ...


def format_textural_schema(analysis: TexturalAnalysis, *, explain: bool = False) -> str: ...
```

Both are pure string functions, importing only `core/`; they never recompute analysis.

* **Feature list of a node** (**Fessel 1996, pp. 84 to 89**): `[` then the specified features in the order P, H, L, C, D, each as `+` or `-` and its letter, separated by `, `. L is omitted where unspecified. Every specified feature is printed, even where Fessel abbreviates (`[-P]` for homophony, p. 89).
* **Compact form**, one line: a `+P` node is its feature list, a space, then its children's compact forms separated by single spaces, then `]`. Children whose compact forms are identical are printed once, in order of first appearance, as Fessel prints the four lines of example 6 as a single bracket (1996, p. 86, open question 7). Example 6 is therefore `[+P, +H, +C, +D [-P, +H, +L, +C, -D]]`.
* **Indented form**, one node per line with every leaf: each child indented four spaces deeper than its parent; a `+P` node opens with its feature list and closes with `]` alone on a line at its own indentation; a leaf is its feature list closed with `]`, two spaces and the labels of its streams separated by `; `. Whether this matches Fessel's layout on p. 84 is open question 7.
* `format_textural_schema` writes, per phrase, a heading line `Phrase N, bars A to B, closing: fermata` (or `score end`, `no fermatas`), the indented form and a line `Compact: ...`, with one blank line between phrases. With `explain`, each node is followed by one line per feature, indented two spaces deeper: `P +: plane_count: 4 planes below this configuration.`, using `-` and the word `unspecified` as needed.

Illustrative output for one phrase of a hypothetical four part chorale (not real corpus output):

```text
Phrase 1, bars 1 to 2, closing: fermata
[+P, +H, +C, +D
    [-P, +H, +L, +C, -D]  Soprano (part 1, voice 1)
    [-P, +H, +L, +C, -D]  Alto (part 2, voice 1)
    [-P, +H, +L, +C, -D]  Tenor (part 3, voice 1)
    [-P, +H, +L, +C, -D]  Bass (part 4, voice 1); Continuo (part 5, voice 1)
]
Compact: [+P, +H, +C, +D [-P, +H, +L, +C, -D]]
```

**Command** (002c):

```text
aretz-texture schema SOURCE [--explain]
```

`SOURCE` as in `piano`. Flow: `read_score`, `analyze_texture` with default settings, `format_textural_schema`, written to standard output. Exit codes as in spec 001 (0, 1 for any `AretzTextureError` with its message on standard error, 2 for usage). The schema does not depend on lyrics, so nothing is said about them.

### 3.9 Evaluation (`eval/textural_configurations.py`, 002d)

```python
class ChoraleTexture(BaseModel):
    identifier: str
    part_count: int
    fused_streams: tuple[FusedStream, ...]
    fermata_end_clusters: tuple[FermataEndCluster, ...]
    analysis: TexturalAnalysis


def analyze_chorale_texture(
    identifier: str,
    settings: TexturalAnalysisSettings,
) -> ChoraleTexture: ...


def is_four_line_phrase(configuration: TexturalConfiguration) -> bool: ...
```

`is_four_line_phrase` is true when the root is `+P` with exactly four leaf children, each `-P, +H, +L, +C, -D`. The slow corpus test analyzes the 350 identifiers of `list_corpus_chorales()` once and checks the committed files under `tests/eval/`, any change failing the test, as 001c does:

* `expected_texture_summary.txt`: number of phrases, number of phrases whose root is `+D` and `-D`, number of chorales `+D` in every phrase and with at least one `-D` phrase.
* `expected_homorhythmic_phrases.txt`: every phrase whose root is `-D`, as `identifier: phrase N, bars A to B`.
* `expected_texture_exceptions.txt`: one line per exception, `identifier: phrase N: reason`, with reasons `four part phrase without four lines` (and the compact form), `homogeneity assumed outside its conditions`, `fermata ends disagree` (the cluster's ends and bars, phrase omitted) and `no fermatas`.
* `expected_more_than_four_parts.txt`: for each of the 19 chorales with more than four parts, its fused streams as labels and the smallest and largest number of planes over its phrases.

### 3.10 Import contracts and dependencies

No change to `pyproject.toml`. `render/textural_schema.py` imports only `core/`, already enforced by "render consumes the tree, never the analysis"; `cli.py` may import `analysis/` (no contract forbids it, and nothing imports the command line); `eval/` may import everything. No new dependency.

### 3.11 Data flow

`cli`: `ingest.sources.read_score` gives the `Score`; `analysis.texture.analyze_texture` gives the `TexturalAnalysis` (phrases, then fused streams, then per phrase the leaves and the root); `render.textural_schema.format_textural_schema` gives the text; `cli` writes it. The evaluation runs the same chain per chorale and also keeps the fused streams and fermata end clusters for its lists.

## 4. Acceptance criteria

### 002a: core model and schema rendering

1. Every model of `core/texture.py` is immutable: assigning to a field raises `ValidationError`.
2. Over all 48 combinations of P, H, C, D in {+, -} and L in {+, -, unspecified}, `TexturalFeatures` accepts exactly those that satisfy the five restrictions of section 3.2 and raises `ValidationError` for the others; a value `None` on any feature but L is rejected.
3. `TexturalConfiguration` rejects: a `+P` node with zero or one child; a `-P` node with children; a `-P` node without streams; a `+P` node with streams of its own; a child span outside the parent span; the same part and voice number in two leaves.
4. `TexturalAnalysis` rejects phrases not numbered from 1, not contiguous, not starting at 0, and a configuration whose span differs from its phrase span.
5. `compact_schema` of a hand built tree with four identical line leaves is exactly `[+P, +H, +C, +D [-P, +H, +L, +C, -D]]` (Fessel 1996, p. 86, example 6).
6. `compact_schema` of a hand built melody with accompaniment is exactly `[+P, +H, +C, +D [-P, +H, +L, +C, -D] [-P, +H, -L, +C, +D]]` (Fessel 1996, pp. 85 to 88), and of a single leaf block of chords `[-P, +H, -L, +C, -D]`.
7. The indented form of a two level hand built tree matches section 3.8 exactly, with every leaf on its own line and its stream labels, including an unnamed part and a leaf of two streams.
8. With `explain`, every node is followed by its five decisions with value, rule and explanation, L printed as unspecified at `+P` nodes.
9. `lint-imports` passes with `render/textural_schema.py` importing only `core/`.

### 002b: phrases and doublings

10. `tactus_duration` returns 1 for 4/4 and 3/4, 2 for 3/2 and 2/2, 3/2 for 12/8 and 6/8.
11. `tactus_spans` of a 4/4 score with a pickup of one quarter returns `[0, 1)` for the pickup, labeled tactus 4 of bar 0, and then spans from the onset of bar 1; a pickup of three eighths gives a first span of one eighth; a final short bar is tiled from its onset.
12. `voice_attacks` skips events whose pitches all continue a tie, keeps only the newly attacked pitches of a divided event, and ignores grace notes and rest fermatas.
13. Fermata ends of all notated voices are used: for BWV 248.9 1, BWV 190.7 and BWV 248.23 2, whose part 1 has no fermata, `segment_phrases` returns more than one phrase.
14. Permuting the parts of a score does not change `segment_phrases` (hypothesis property, section 5).
15. Two fermata ends less than one tactus apart in different voices make one phrase end at the later one; ends exactly one tactus apart make two (synthetic).
16. Music after the last fermata forms a last phrase closing `SCORE_END`; a score without fermatas is one phrase closing `NO_FERMATAS`; phrase bar numbers are those of the bars containing the onset and the last moment before the end.
17. `fuse_doublings` fuses Bass and Continuo in BWV 8.6 and in BWV 248.59 6 and leaves the other notated voices alone, so each has four fused streams.
18. In BWV 190.7, Oboe 1, Violin 1 and Soprano form one fused stream, Violin 2 and Alto another, Viola and Tenor another, Bass and Continuo another, and the remaining notated voices stay alone: 10 fused streams from 15 parts.
19. BWV 27.6 has five fused streams, one per part; no four part chorale fuses two of its voices (slow).
20. A copy of a voice transposed by an octave fuses with it; a copy transposed by a fifth does not; a copy whose coinciding proportion is exactly 9/10 fuses and one just below does not (synthetic).

### 002c: features, tree and command

21. D: a homorhythmic synthetic phrase is `-D` at the root; adding one passing eighth to one voice makes it `+D`; a voice attacking alone while the others hold is not divergence; two voices attacking at different tactus spans are not divergence; a tied continuation is not an attack.
22. L: a leaf of one notated voice without divided events is `+L` and `-D` by `RESTRICTION_5`; a leaf of two voices fused at the octave whose attacks all coincide is `+L`; a fused leaf in which one voice attacks while the other holds is `-L`, and its D is measured; a divided event at a second makes its leaf `-L`; a succession of divided events in parallel thirds is `+L`, and the same thirds with the pitches moving in contrary motion are `-L` (synthetic).
23. H at the root is `+` with `SINGLE_METER_AND_KEY` in a phrase with one time signature and no key change inside it, and `+` with `ASSUMED_OUTSIDE_CONDITIONS` in a synthetic phrase with a time signature change inside it; leaves get H and C by `RESTRICTION_2` and `RESTRICTION_3`.
24. Every phrase of BWV 66.6 has a `+P` root with four leaves, `-P, +H, +L, +C, -D`, ordered Soprano, Alto, Tenor, Bass.
25. A score with one plane in a phrase gives a single `-P` leaf as the configuration of that phrase.
26. `analyze_texture` returns equal results on two calls with the same input, and every result passes the validators (hypothesis property).
27. `aretz-texture schema bwv66.6` exits with 0 and writes one block per phrase to standard output; `--explain` adds the decisions; an unknown source exits with 1 and a message on standard error.

### 002d: evaluation

28. Every phrase of the 350 chorales gets a valid tree (slow).
29. In every four part chorale, every phrase satisfies `is_four_line_phrase`, except those listed with reason in `expected_texture_exceptions.txt`.
30. The summary counts, the list of `-D` phrases, the exceptions and the list of chorales with more than four parts equal the committed files.
31. **Fessel's example 6**: `compact_schema` of phrase 1 of `bach/bwv244.54` (identifier to be confirmed by Nico, open question 1) is exactly `[+P, +H, +C, +D [-P, +H, +L, +C, -D]]`.

### All pull requests

32. All commit checks pass (`uv run pre-commit run --all-files`) and the full suite passes in CI.

## 5. Test plan

### Corpus facts this spec relies on

Verified by the main session on November 12, 2026 (music21 10.5.2), over the 350 chorales, all supported since 001d:

* Meters: 4/4 in 313 chorales, 3/4 in 38, 3/2 in 2, 12/8 in 1 (a chorale may have more than one).
* With a probe rule that read fermatas only in part 1, notated voice 1, three chorales (BWV 248.9 1, BWV 190.7, BWV 248.23 2) have no fermata there, and in 56 the fermata ends of the first four parts disagree (for example BWV 145.5, BWV 153.5, BWV 363, BWV 352, BWV 244.37, BWV 91.6, BWV 291, BWV 36.4 2). That probe found 2107 phrases in 347 chorales.
* With the reading of D of section 3.6, 2029 of those phrases are `+D` and 78 are `-D`; 305 chorales are `+D` in every phrase and 42 have at least one `-D` phrase, for example BWV 17.7, BWV 65.2 and BWV 184.5. The probe numbered phrases from 0: in this spec's numbering, BWV 17.7 phrases 1, 3, 5, 7 and 8, BWV 65.2 phrases 1 to 4 and BWV 184.5 phrase 3 are `-D`.
* With fusion at 9/10 over the whole score, only BWV 8.6 and BWV 248.59 6 of the 19 chorales with more than four parts reduce to four groups (Bass with Continuo). BWV 190.7 goes from 15 streams to 10 groups, BWV 248.42 4 from 12 to 8, BWV 248.9 1 from 8 to 7; BWV 112.5, BWV 251 and BWV 252 have one doubling each (a cornet or horn with the soprano). The rest have none: obbligato instruments in BWV 91.6, 29.8, 19.7, 41.6, 250, 70.11, 136.6, 172.6, 161.6 and 248.23 2, and five real voices in BWV 27.6. BWV 41.6 already encodes voice and instruments in single parts.
* **Consequence, stated plainly:** fusing doublings does not bring 17 of the 19 to four planes, so this spec does not promise grand staff rendering for them. They are the corpus's only textures with more than four planes or with planes of different kinds, and the tests use them as such.
* All four St Matthew Passion settings of the melody (BWV 244.15, 244.44, 244.54, 244.62) have a `+D` first phrase under that reading.

Because this spec's phrase rule reads every voice, its phrases differ from the probe's in at least the 59 chorales above; the counts committed in 002d are those produced by the implementation and reviewed by Nico, and the PR reports how they differ from the probe.

### Concrete cases

* **BWV 244.54, phrase 1**: example 6 (criterion 31); also BWV 244.15, 244.44 and 244.62 phrase 1 are `+D`, as the probe found.
* **BWV 66.6**: every phrase four lines, ordered Soprano to Bass (criterion 24); the pickup as tactus 4 of bar 0 in an explanation (criterion 11); the command (criterion 27).
* **BWV 17.7, BWV 65.2, BWV 184.5**: `-D` roots at the phrases listed above, if this spec's phrases coincide there with the probe's (to verify in 002b; the test names the phrase by its bars).
* **BWV 248.9 1, BWV 190.7, BWV 248.23 2**: phrases found without fermatas in part 1 (criterion 13). BWV 248.9 1 also has divided events: the test asserts the L of the leaf that holds them, whatever the interval turns out to be (to verify).
* **BWV 145.5 and BWV 153.5**: fermata ends that disagree across parts; the test asserts one phrase end per cluster and the bars where they disagree.
* **BWV 8.6, BWV 248.59 6**: four planes, with Bass and Continuo as one leaf of density 2 (criteria 17 and 24 style).
* **BWV 190.7**: the fused groups of criterion 18; phrases with up to 10 planes; trumpets and timpani as separate planes.
* **BWV 27.6**: five planes of density 1 (criterion 19).
* **BWV 41.6**: four planes, each one part, labels with the combined names verbatim, including `Alto Oboe 2 Viloin 2`.
* **BWV 244.15, BWV 62.6, BWV 4.8**: H is `+` by `SINGLE_METER_AND_KEY`, although the soprano has another key signature than the other parts.
* **Synthetic scores** built with `tests/core_builders.py`: the D, L, H, tactus, fermata clustering and fusion threshold cases of criteria 10 to 23 and 25.
* **Hand built trees** for 002a: example 6, the melody with accompaniment, a single leaf, a tree with a fused leaf and an unnamed part.

### Hypothesis properties

Using `scores()` and `four_part_scores()` from `tests/strategies.py`, and a new strategy `textural_configurations()` that builds valid trees of depth up to three:

* **Restrictions** (002a): every tree from `textural_configurations()` validates, and changing any one feature value of any node to a combination outside the restrictions raises `ValidationError`.
* **Compact form** (002a): brackets are balanced; the compact form of a node whose children are all identical is its feature list, a space, the compact form of one child and `]`, whatever the number of children.
* **Phrases tile the score** (002b): consecutive, from 0 to `score.end()`, numbered from 1.
* **Part order** (002b and 002c): permuting the parts of a score leaves the phrase spans, the compact forms and the set of stream labels per leaf unchanged, up to renumbering.
* **Fusion is an equivalence** (002b): every notated voice is in exactly one fused stream; adding to a score an exact copy of one of its parts fuses the copy with the original and nothing else.
* **Linear leaves do not diverge** (002c): for any analyzed score, every `+L` leaf is `-D`; this follows from the validator, and the property checks the analysis never relies on it failing.
* **D is monotone under added divergence** (002c): adding to a voice an attack inside a tactus span where another voice attacks at a different time point never turns a `+D` root into `-D`.
* **Determinism** (002c): two runs give equal `TexturalAnalysis` values.

## 6. Decisions

Taken in this spec; the musical ones are recorded in ADR 0005.

Nico reviewed section 8 on November 12, 2026: he adopted the recommendations of questions 2 to 4 and 6 to 8, and decided question 5 against the recommendation. Linearity follows Fessel's scale of closeness instead of being limited to unison and octave: simultaneous pitches of one plane form a voice at the unison, octave, fourth, fifth, third or sixth, with coinciding attacks and relatively constant parallel motion (Fessel 1996, p. 81; Fessel 2000, p. 86). Question 7c is closed: restriction 2 restates restriction 1, as Fessel himself notes when he calls it obvious (1996, p. 81), so the transcription is consistent. Question 1 and questions 7a and 7b wait for Nico to check the 1996 PDF.

1. **Plane and stratum** (**project**, grounded in Fessel 2000, p. 84, where the relations between strata are the H, C and D of 1996): the code calls the nodes below a `+P` configuration planes; "stratum" is kept for a plane with a characterization (line, pedal, ostinato), which a later spec adds.
2. **Streams are notated voices** (**project**): the unit the analysis groups is one notated voice of one part; segregation is out of scope.
3. **Phrases** by clustered fermata ends of every notated voice, with the fallback of section 3.4 (**project**, ADR 0005).
4. **Tactus** is the beat of the time signature, with tactus spans on the bar grid (**project**, ADR 0005).
5. **Fusion** over the whole score, unison and octave only, threshold 9/10 (**project** thresholds on **Fessel 2000** criteria, ADR 0005).
6. **Every fused stream is a plane under the root** (**project**, this slice only).
7. **Feature rules** as in section 3.6 (**Fessel 1996** definitions and restrictions; **project** rules, ADR 0005).
8. **Planes ordered by register** in the output (**project**, presentation).
9. **Command name** `schema`, after the glossary's textural schema (**project**).

## 7. To verify during implementation

Facts this spec needs that the corpus facts of November 12 do not establish. The implementer checks each with the explorer or a probe and reports it in the PR; none should change the design, and any that does comes back to this spec.

1. **Which chorale has no fermata at all.** Spec 001 (section 8) counted note fermatas in 349 of 350 chorales; that one chorale exercises the fallback. (002b)
2. **What the 56 disagreements look like**: fermata ends a fraction of a beat apart, or fermatas missing in some parts. This decides whether the one tactus tolerance absorbs them. (002b)
3. **Phrases in four part chorales where a voice does not attack**, which would give fewer than four planes and appear in the exceptions list. (002d)
4. **Time signature or key signature changes inside a phrase**, which make H an assumption. (002c)
5. **The intervals of the divided events of BWV 248.9 1**, which decide the L of that leaf. (002c)
6. **Whether whole score fusion reproduces the probe's groups** for all 19 chorales, and whether any of the 331 four part chorales fuses two voices. (002b)

## 8. Open questions for Nico

1. **Example 6.** Is Fessel's example 6 (1996, p. 86) the first phrase of `bach/bwv244.54`? The corpus has four settings of the melody in the St Matthew Passion with the same encoded first words; No. 54 is the one traditionally titled "O Haupt voll Blut und Wunden". *Recommendation:* check the music printed on p. 86 against BWV 244.54 bars 1 to the first fermata; if it matches, the test uses it, otherwise give the identifier.
2. **Reading of D.** Is a tactus span divergent when two components attack at different time points inside it, with a single component attacking alone not counting, tied continuations not counting, and one divergent span enough to make the configuration `+D`? *Recommendation:* adopt it. It matches Fessel's "no one to one correspondence is needed" and his example 6, and it makes about 4 percent of the probe's phrases `-D`, which reads well as "fully homorhythmic". Also confirm that the root is `+D` when a plane is internally `+D` (divergence within planes).
3. **Phrase segmentation.** Union of the fermata ends of all notated voices, clustered within one tactus, with the latest end as the boundary; music after the last fermata as a last phrase; a score without fermatas as one phrase. *Recommendation:* adopt it for the chorales; it is independent of part order and of fermatas missing in some parts. A score without fermatas needs a real segmentation (cadences, bars) in a later spec, not a guess here.
4. **Fusion of doublings.** Fuse over the whole score rather than per phrase, at unison and octave only, when at least 9/10 of the attacks of the sparser voice coincide? *Recommendation:* yes for this slice. Per phrase fusion would join voices that share one note in a short phrase, and Fessel's strict coincidence (1 instead of 9/10) can be tried later by changing one setting.
5. **Linearity of a doubled plane.** With the defaults, a fused plane whose doubling is not strict at every attack (a continuo adding a passing note under a held bass) is one plane that is `-L`, and its divergence is measured. And simultaneous pitches in one plane form a voice only at the unison or octave, not at the fifth or third of Fessel's ordering. *Recommendation:* keep both strict, as Fessel's necessary conditions; the evaluation lists every non strict doubling, so the decision can be revisited with examples. *Decided by Nico:* the doubling stays strict, and linearity inside a plane follows Fessel's scale (section 6).
6. **H and C provisional rules.** H is `+` with one time signature and no key signature change in any part inside the phrase, without comparing key signatures across parts; C is `+` because all planes share the meter. Outside its conditions H is `+` as a recorded assumption. *Recommendation:* adopt them as provisional; the alternative for H outside its conditions, refusing to decide, would leave phrases without a valid tree.
7. **Notation and transcription** (against the 1996 PDF). (a) Does Fessel print identical sibling configurations once, as example 6 suggests, so the compact form should collapse them? (b) What is his indentation and closing bracket convention on p. 84, so the indented form can follow it? (c) As transcribed, restriction 1 (`-H` implies `+P`) and restriction 2 (`-P` implies `+H`) are the same statement; is the transcription of restriction 2 exact? *Recommendation:* collapse identical siblings in the compact form and keep every leaf in the indented form; adjust the indentation to p. 84 before 002a; if restriction 2 is different, this spec is corrected before approval.
8. **Plane and stratum.** Treat Fessel's plane (1996) and stratum (2000) as the same domain, with "plane" for the nodes of the tree and "stratum" reserved for a characterized plane? *Recommendation:* yes; it is consistent with the 2000 article's relations being the 1996 features, and it keeps the glossary's existing entries meaningful.
