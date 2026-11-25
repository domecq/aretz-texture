# ADR 0006: pure harmonic analysis, with music21 only writing the names

Date: November 25, 2026
Status: Proposed, with spec 003

## Context

Spec 003 adds the first harmonic analysis: chord identity, local key and Roman numerals, needed by the four voice reduction and by the chord names Nico wants on the score (chord symbols above the staff, Roman numerals below the bass). music21 can do each of these steps: `harmony.chordSymbolFromChord` names a chord (for the pitches B3, D4, G4, F4 it gives `G7/B`), `roman.romanNumeralFromChord` gives a Roman numeral in a key (`V65` for the same chord in C major), and `Stream.analyze("key")` finds a key. Using them from `analysis/` would break ADR 0003, which confines music21 to `ingest/` and `render/`, and the pure core of AGENTS.md, which keeps `analysis/` and `voicing/` free of anything but data in and data out.

Facts checked by the main session on November 25, 2026, with music21 10.5.2:

* music21's MusicXML exporter writes a `ChordSymbol` as `<harmony>`, with root G, kind `dominant`, inversion 1 and bass B for the chord above.
* The same exporter drops `RomanNumeral` objects: nothing is written. Roman numerals need another carrier in `render/` whatever this ADR decides.

## Decision

1. Chord identity, local key and the choice of Roman numeral are computed by the project, in pure code, from spelled pitches: `analysis/` identifies chords by stacking spelled thirds and finds the key of each phrase with a key profile; `core/` names a chord in a key (Roman numeral) and as a chord symbol, as strings derived from the core model. No music21 call takes part in any analytical decision.
2. ADR 0003 stands unchanged: music21 stays in `ingest/` and `render/`. In `render/`, music21 only writes what the analysis decided: a `<harmony>` element built from the core chord identity (root, kind, bass), and Roman numerals as lyrics on the bass. The renderer never asks music21 to name or analyze a chord.
3. Tests may compare the project's names with music21's on a sample of chords as a consistency check, since `tests/` may import music21 (spec 001, decision 12). A disagreement is reported and resolved in the project's conventions (ADR 0007), never by delegating to music21.

## Rationale

* **Determinism and auditability.** music21's naming and key finding are heuristics with their own conventions and defaults (for example, how it reads the sixth and seventh degrees in minor). A change between music21 versions would change musical results without any change in this repository, against "the reduction is deterministic and auditable" (architecture, section 2). The upper bound of ADR 0003 limits the risk but does not remove it.
* **The pure version is small.** With spelled pitches in the core model (spec 001), a chord's root is the one pitch name from which the others stack in thirds by letter name, and its quality follows from the sizes of those thirds. Nine qualities, four inversions and a figure table cover the chorales; a key profile is twelve numbers per mode. This is a few hundred lines, all testable with hypothesis (identification recovers what a generator built, names transpose with the key).
* **The dependency contract stays simple.** No new exception to the import contracts, no `Any` outside the boundary, no music21 object in a public signature of `analysis/` or `voicing/`.
* **The names belong to the project.** The textbook conventions for Roman numerals, especially in minor, are a musical decision Nico should be able to read and change in an ADR (ADR 0007), not a library default.

## Consequences

* `core/` gains a model of harmony (`core/harmony.py`, `core/roman_numerals.py`, `core/reduction.py`); `analysis/` gains segmentation, chord identification and key finding; `voicing/` gains its first module. All pure.
* The project owns its naming conventions and must document them (ADR 0007). Chords outside the vocabulary, such as augmented sixth chords, are reported as unidentified until a later spec adds them; music21 would have named some of them.
* `render/` gains a small boundary module that turns core chord names into `<harmony>` elements and lyrics. The grand staff reader ignores both.
* No change to `pyproject.toml` and no new dependency.

## Alternatives considered

* **Call music21 from `analysis/` behind a thin wrapper.** Breaks ADR 0003 and the pure core, and makes the analysis depend on music21's version for its musical results.
* **Move chord naming into `ingest/`**, so that music21 annotates the score on the way in. Ingestion would then take analytical decisions, against ADR 0004 (ingestion keeps the score and decides nothing), and the names would be computed before the segmentation that defines the windows they name.
* **Compute names in `render/` with music21** from the pitches of each reduced chord. The renderer would recompute analysis (architecture, section 4) and could disagree with the chord the reduction was built on.

## References

Spec 003, `docs/specs/003_first_reduction.md`. ADR 0003 (music21 boundary). ADR 0007 (harmonic readings for the chorales).
