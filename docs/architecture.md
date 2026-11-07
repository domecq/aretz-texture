# Aretz Texture: architecture

Version 0.5, November 2026. Living document: every new decision is recorded as an ADR in `docs/adr/` and summarized here.

## 1. Goal

Analysis tool for musicians that takes a score and shows how its texture is organized and the harmonic structure supporting it. The analysis is based on Pablo Fessel's model of textural strata (ADR 0004, `docs/theory/fessel_textural_model.md`), and it delivers two renderings: a textural schema of the strata and their relations, and a reduction of the harmony to a four voice chorale.

The purpose is **understanding the structure**, not producing a version to perform. Playability at the piano is used as a readability criterion (two staff system, reasonable hand spans), not as a goal.

Intended users: students of analysis and harmony, teachers, arrangers, conductors.

The project is named in honor of Isabel Aretz (1909 to 2005), Argentine and Venezuelan composer and ethnomusicologist, who collected, analyzed and taught the folk music of the Americas.

## 2. Decisions made

* **Distribution**: free tool for education and for musicians, in a public repository under the MIT License (ADR 0001).
* **Language**: Python. Base library: music21. Package name: `aretz_texture`, under `src/` (ADR 0002).
* **Project language**: English everywhere: code, comments, docstrings, documentation, specs, ADRs and the development journal.
* **Input**: MusicXML. Optical music recognition (OMR) is out of scope for the first version and will be added later as one more input adapter.
* **Theoretical foundation**: Pablo Fessel's model of textural strata (ADR 0004). The number of parts or staves does not determine the number of strata; which notes form melody, bass or accompaniment is decided by analysis.
* **Outputs**: a textural schema and a four voice harmonic reduction on a piano system, both as MusicXML, plus a textual description of the analysis.
* **The reduction is deterministic and auditable.** An LLM only writes the textual description from the structured analysis; it never invents voices or chords.
* **Two rhythmic modes**: harmonic rhythm (reduced) and the representative rhythm of the piece.
* **Four granularity levels selectable by the user.** The first version implements only level 2, but the data model supports all four from the start.
* **Abjad evaluated and discarded as the base.** It builds LilyPond files for engraving, but it does not import MusicXML, has no harmonic analysis and ships no corpus. It remains a candidate for an optional engraved PDF renderer.

## 3. Analysis pipeline

1. **Normalization**: MusicXML parsing, transposing instruments to concert pitch, expansion of repeats. Every part is kept without loss; no textural decision is taken here.
2. **Harmonic segmentation**: slicing into verticalities and merging into harmonic windows, filtering passing tones, neighbor tones, suspensions and anticipations by metric weight, duration and stepwise motion. This is the heart of the system: in reduced mode, the output rhythm is literally the result of this step.
3. **Strata identification** (section 5): the textural configuration of each passage, recursively. Its strata (for example melody, low support, harmonic accompaniment, pedal), their characterization and their relations, and how they appear, divide, merge or disappear over time. Melody, actual bass, harmonic filler and doublings to collapse come from this step.
4. **Harmonic analysis**: chord identity, local key and functional degree.
5. **Representative rhythm selection** (see section 6).
6. **Four voice generation**: dynamic programming optimization over the chord sequence (see section 7).
7. **Rendering**: according to the chosen mode and level.

## 4. Data model

The analysis produces two linked hierarchies.

The **textural configuration tree** follows Fessel's recursive model. Each node is a configuration or a stratum and contains:

* time span
* its children (strata, or substrata)
* its characterization (line, ostinato, pedal, harmonic accompaniment, and so on)
* the values of the five features (planes, homogeneity, linearity, accent coincidence, attack divergence) and the relations with its sibling strata
* traceability: which notes of which parts belong to it, and the measured factors that justify the grouping

The **hierarchical tree of harmonic events** describes the harmony that the strata project. Each node contains:

* time span (onset and duration on the metric grid)
* chord (pitches, root, inversion)
* function and scale degree in the local key
* assigned voices (soprano, alto, tenor, bass)
* hierarchical level and references to its children
* traceability: which notes of the original score justify it

Each granularity level is a **cut of the trees**. Renderers consume the cut; they never recompute analysis. This separates analysis from presentation and allows adding modes or levels without touching the core.

## 5. Strata identification

Based on Fessel's model (`docs/theory/fessel_textural_model.md`). Sounds are grouped into lines and strata by weighing:

* **Association factors**: intervallic proximity, proximity of attacks, formal variability, directional convergence, timbral similarity.
* **Dissociation factors**: rhythmic independence, registral separation, directional divergence, timbral dissimilarity, differences of intensity.

Most factors are measured directly from the score; timbre comes from the instrument of each part and intensity from dynamics. A part may contribute to several strata, and several parts may form one stratum. Features that depend on perception, such as homogeneity and linearity, are deterministic heuristics with named, configurable weights, calibrated against human musical review. The output explains the reading it chose, so a musician can disagree with it and override it.

## 6. Representative rhythm

Candidates: the strata identified in section 5 (melody, bass, union of textures, and the accompaniment pattern if there is one). Each receives a score combining:

1. **Harmonic coverage**: proportion of chord changes that fall on an attack in that layer. Necessary condition.
2. **Correlation with the composite rhythm**: on the metric grid, count how many voices attack at each position; the layer that best correlates with that profile wins.
3. **Parsimony**: density penalty, so the union does not always win by covering everything.
4. **Recurrence**: bonus for patterns that repeat bar to bar.

Additional rules:

* The choice is made **per section**, not for the whole piece.
* **Hysteresis** is applied to avoid switching layers on isolated bars.
* The system **explains its choice** in the output and the user can force another layer.

The weights of the combination are configurable parameters, calibrated against the evaluation corpus.

## 7. Voice generation

* Soprano takes the structural note of the melody in each window; bass takes the actual bass.
* Alto and tenor are chosen among candidate voicings by minimizing a cost: stepwise motion, parallel fifths and octaves, doublings, spacing between voices.
* Piano readability constraint: left hand takes bass and tenor, right hand takes alto and soprano, each hand within a reasonable span.
* Solved by dynamic programming (Viterbi style). Linear complexity in the length of the piece.

## 8. Granularity levels

1. **Surface**: every verticality, without passing or neighbor tones.
2. **Harmonic rhythm**: one chord per actual change of function. **First version.**
3. **Prolongation**: chords that prolong another one are absorbed (for example, a neighboring V7 between two tonics).
4. **Phrase**: functional skeleton (tonic, predominant, dominant, cadence).

Levels 3 and 4 involve prolongation judgments close to Schenkerian analysis, with real ambiguity among analysts. They are treated as a second stage.

Fessel's recursive analysis (global and partial configurations) applies to the textural tree at the same levels.

The levels also support classroom use: a teacher can show a coarse level and ask students to work out a finer one.

## 9. Output modes

* **Textural schema**: the strata of each passage and their relations, as a score with one staff per stratum plus their characterization.
* **Harmonic rhythm**: each chord lasts as long as its function.
* **Representative rhythm**: the same four voices rearticulated according to the layer chosen in section 6.
* **Textual description**: written by an LLM from the event tree, with references to bar numbers.

## 10. Evaluation

* **Bach chorales** (music21 corpus): already in four voices; the system should return them almost unchanged. This is the main regression test.
* **Pieces with a published piano reduction**: chords and bass compared against the human reduction. Scores protected by copyright stay out of the public repository.
* **Lossless ingestion**: every chorale of the corpus, whatever its number of parts, survives a round trip with no lost or altered notes.
* **Human musical review** of a fixed sample of pieces in every version, including the strata identified.

## 11. Open decisions

* Suspensions and anticipations: shown, or resolved directly?
* Pedal points: new chord, or same chord over a sustained bass?
* Arpeggios hiding the actual harmony: grouping criterion.
* Initial weights for the representative rhythm score.
* Initial weights of the association and dissociation factors, and how the textural schema is notated.

## 12. Out of scope for the first version

* OMR (image or PDF to MusicXML)
* Levels 3 and 4
* Web interface (planned with Verovio to render MusicXML in the browser)
