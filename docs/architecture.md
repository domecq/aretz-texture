# Aretz Texture: architecture

Version 0.4, November 2026. Living document: every new decision is recorded as an ADR in `docs/adr/` and summarized here.

## 1. Goal

Analysis tool for musicians that takes a score and shows the harmonic structure supporting its texture, reduced to a four voice chorale.

The purpose is **understanding the structure**, not producing a version to perform. Playability at the piano is used as a readability criterion (two staff system, reasonable hand spans), not as a goal.

Intended users: students of analysis and harmony, teachers, arrangers, conductors.

The project is named in honor of Isabel Aretz (1909 to 2005), Argentine and Venezuelan composer and ethnomusicologist, who collected, analyzed and taught the folk music of the Americas.

## 2. Decisions made

* **Distribution**: free tool for education and for musicians, in a public repository under the MIT License (ADR 0001).
* **Language**: Python. Base library: music21. Package name: `aretz_texture`, under `src/` (ADR 0002).
* **Project language**: English everywhere: code, comments, docstrings, documentation, specs, ADRs and the development journal.
* **Input**: MusicXML. Optical music recognition (OMR) is out of scope for the first version and will be added later as one more input adapter.
* **Output**: MusicXML on a piano system, plus a textual description of the analysis.
* **The reduction is deterministic and auditable.** An LLM only writes the textual description from the structured analysis; it never invents voices or chords.
* **Two rhythmic modes**: harmonic rhythm (reduced) and the representative rhythm of the piece.
* **Four granularity levels selectable by the user.** The first version implements only level 2, but the data model supports all four from the start.
* **Abjad evaluated and discarded as the base.** It builds LilyPond files for engraving, but it does not import MusicXML, has no harmonic analysis and ships no corpus. It remains a candidate for an optional engraved PDF renderer.

## 3. Analysis pipeline

1. **Normalization**: MusicXML parsing, transposing instruments to concert pitch, expansion of repeats.
2. **Harmonic segmentation**: slicing into verticalities and merging into harmonic windows, filtering passing tones, neighbor tones, suspensions and anticipations by metric weight, duration and stepwise motion. This is the heart of the system: in reduced mode, the output rhythm is literally the result of this step.
3. **Role classification**: per segment, melody, actual bass (accounting for octave doublings), harmonic filler and doublings to collapse.
4. **Harmonic analysis**: chord identity, local key and functional degree.
5. **Representative rhythm selection** (see section 5).
6. **Four voice generation**: dynamic programming optimization over the chord sequence (see section 6).
7. **Rendering**: according to the chosen mode and level.

## 4. Data model

The analysis produces a **hierarchical tree of harmonic events**. Each node contains:

* time span (onset and duration on the metric grid)
* chord (pitches, root, inversion)
* function and scale degree in the local key
* assigned voices (soprano, alto, tenor, bass)
* hierarchical level and references to its children
* traceability: which notes of the original score justify it

Each granularity level is a **cut of the tree**. Renderers consume the cut; they never recompute analysis. This separates analysis from presentation and allows adding modes or levels without touching the core.

## 5. Representative rhythm

Candidates: melody, bass, union of textures, and the accompaniment pattern if there is one. Each receives a score combining:

1. **Harmonic coverage**: proportion of chord changes that fall on an attack in that layer. Necessary condition.
2. **Correlation with the composite rhythm**: on the metric grid, count how many voices attack at each position; the layer that best correlates with that profile wins.
3. **Parsimony**: density penalty, so the union does not always win by covering everything.
4. **Recurrence**: bonus for patterns that repeat bar to bar.

Additional rules:

* The choice is made **per section**, not for the whole piece.
* **Hysteresis** is applied to avoid switching layers on isolated bars.
* The system **explains its choice** in the output and the user can force another layer.

The weights of the combination are configurable parameters, calibrated against the evaluation corpus.

## 6. Voice generation

* Soprano takes the structural note of the melody in each window; bass takes the actual bass.
* Alto and tenor are chosen among candidate voicings by minimizing a cost: stepwise motion, parallel fifths and octaves, doublings, spacing between voices.
* Piano readability constraint: left hand takes bass and tenor, right hand takes alto and soprano, each hand within a reasonable span.
* Solved by dynamic programming (Viterbi style). Linear complexity in the length of the piece.

## 7. Granularity levels

1. **Surface**: every verticality, without passing or neighbor tones.
2. **Harmonic rhythm**: one chord per actual change of function. **First version.**
3. **Prolongation**: chords that prolong another one are absorbed (for example, a neighboring V7 between two tonics).
4. **Phrase**: functional skeleton (tonic, predominant, dominant, cadence).

Levels 3 and 4 involve prolongation judgments close to Schenkerian analysis, with real ambiguity among analysts. They are treated as a second stage.

The levels also support classroom use: a teacher can show a coarse level and ask students to work out a finer one.

## 8. Output modes

* **Harmonic rhythm**: each chord lasts as long as its function.
* **Representative rhythm**: the same four voices rearticulated according to the layer chosen in section 5.
* **Textual description**: written by an LLM from the event tree, with references to bar numbers.

## 9. Evaluation

* **Bach chorales** (music21 corpus): already in four voices; the system should return them almost unchanged. This is the main regression test.
* **Pieces with a published piano reduction**: chords and bass compared against the human reduction. Scores protected by copyright stay out of the public repository.
* **Human musical review** of a fixed sample of pieces in every version.

## 10. Open decisions

* Suspensions and anticipations: shown, or resolved directly?
* Pedal points: new chord, or same chord over a sustained bass?
* Arpeggios hiding the actual harmony: grouping criterion.
* Initial weights for the representative rhythm score.

## 11. Out of scope for the first version

* OMR (image or PDF to MusicXML)
* Levels 3 and 4
* Web interface (planned with Verovio to render MusicXML in the browser)
