# ADR 0007: harmonic readings for the first reduction of the chorales

Date: November 25, 2026
Status: Accepted, November 26, 2026, with spec 003

## Context

Spec 003 builds the first four voice reduction of the corpus chorales: harmonic segmentation, chord identity, local key and level 2 of the granularity levels (architecture, sections 3, 7 and 8). Each step needs readings that change musical results: which notes are non chord tones, when a new harmony starts, which chords the vocabulary names, how a key is found, how a Roman numeral is written, what counts as a change of function. As with ADR 0005, they are recorded here so that code can reference them (AGENTS.md: a musical decision that is not obvious references its ADR) and so that changing one is visible in review. Each reading says whether it is **theory** (with its source) or a **project** decision.

## Decision

For the chorales, and until a later ADR replaces any of them:

1. **Domain of the harmony: the phrase of spec 002** (project). Harmonic windows never cross a phrase boundary, and each phrase has one local key. The reduction reads the textural tree (`TexturalAnalysis`): its phrases, its planes ordered by register and the notated voices of each plane.
2. **Sounding notes** (project): the notes of a notated voice joined across ties, each pitch of a divided event on its own. Grace notes and rest fermatas take no part in the harmony.
3. **Metric weight: on or off the tactus** (project, after spec 002's tactus). A note starting at the onset of a tactus span is accented; any other note is unaccented.
4. **Melodic step: one or two semitones** (project). Chromatic steps count; the augmented second is a leap.
5. **Unaccented non chord tones** (theory of common practice voice leading; thresholds project): a passing tone or a neighbor tone is unaccented, lasts at most half a tactus by default, and is approached and left by step with no rest, in the same direction (passing) or in opposite directions back to the same pitch (neighbor). An anticipation is unaccented, as short, approached by step and followed by the same pitch at the next tactus onset. Consonance is not checked for these three. Accented passing tones, appoggiaturas, escape tones and pedal points are chord tones in this version.
6. **Suspensions** (theory of common practice voice leading; thresholds project): a note sounding at a tactus onset, prepared by the same pitch in its voice (tied over or repeated), dissonant there (a second or seventh with another sounding pitch, or a fourth above the lowest), and resolving down by step within one tactus by default. Decided by Nico on November 26, 2026 (open question 2): from the tactus onset on, the suspension is replaced by its resolution (resolved directly).
7. **Harmonic windows** (project): after removing non chord tones, a new window starts where a pitch class appears that the current window does not hold, or where the lowest chord tone changes pitch class; otherwise the verticality joins the current window. A reattacked chord continues its window. These windows are level 1 (surface).
8. **Chord identity by stacked thirds** (theory: tertian harmony; vocabulary project): the root is the pitch name from which every other one lies a third, fifth or seventh above by letter name, and the quality follows from the sizes of those intervals. Vocabulary: major, minor, diminished and augmented triads, and dominant, major, minor, half diminished and diminished seventh chords. A missing fifth is read as perfect; a missing third leaves the sonority unidentified, as do two spellings of one letter (C and C sharp) and anything outside the vocabulary (augmented sixth chords among them). The inversion follows from the lowest chord tone.
9. **Local key per phrase by key profile** (theory: Krumhansl and Kessler, 1982, as used in Krumhansl's key finding algorithm, 1990; one key per phrase is project). The key of a phrase is the one of the 24 whose profile correlates best with the durations of the pitch classes sounding in it. The tonic takes the spelling most heard in the phrase. Decided by Nico on November 26, 2026 (open question 4).
10. **Roman numerals** (project, following common textbook practice): the degree is the letter distance from the tonic; uppercase for major, augmented and dominant qualities and lowercase for the others, with `°`, `ø`, `+` and `M7` marks; inversion figures 6, 64, 7, 65, 43 and 42. In major, accidentals are measured against the major scale. In minor, against the natural minor scale, except that a root on the raised seventh degree takes no accidental, so that V and vii° are written plain. Applied chords are written as chromatic degrees (II for V of V); the `V/x` notation is out of this version.
11. **Level 2, one chord per change of function** (project). Decided by Nico on November 26, 2026 (open question 1): consecutive windows of one phrase merge when their chords have the same root and the same quality, whatever the inversion; the merged chord is named and voiced as its first window. Unidentified sonorities never merge.
12. **Voicing from the planes** (project, four plane textures only). Decided by Nico on November 26, 2026 (open question 3): the four voices take the structural note of the four planes, highest plane to soprano, at the onset of each chord.
13. **Every window records its traceability**: the non chord tones it removed with their kind, and the structural note of each plane with the notated voice it came from (architecture, section 4).

All thresholds live in typed settings (`analysis/settings.py`) with name, unit and musical meaning.

## Rationale

* **The tactus of spec 002 is the natural metric weight here.** In the chorales the harmony changes mostly once per beat, so notes off the beat and shorter than it are the ornamental ones; quarter note passing tones on the beat of 4/4 become passing chords, as harmony textbooks read them in this repertoire.
* **Stacking spelled thirds names a chord without templates over pitch classes**, so the diminished seventh and the augmented triad, symmetric as pitch class sets, get the root their spelling says.
* **A key per phrase** follows the chorales' own segmentation: a phrase normally cadences in the key that governs it. Tonicizations inside a phrase appear as chromatic degrees, which keeps the first version honest about what it does not model.
* **Voicing from the planes** is what "the chorales come back almost unchanged" (architecture, section 10) requires, and a four plane texture already has four lines; the cost based voicing of architecture section 7 is needed only where the texture does not provide them.

## Consequences

* The chorale evaluation of spec 003 depends on these readings; changing one changes the committed file of reductions, which is visible in review.
* Chords outside the vocabulary, accented non chord tones and tonicizations are visible as unidentified sonorities, odd windows or chromatic degrees in the committed file. They are the list of work for the next specs.
* Scores whose phrases do not all have four planes are analyzed and named but not voiced.
* Readings 6, 9, 11 and 12 become accepted when Nico answers the questions of spec 003, section 8.

## Alternatives considered

* **Beat strength inside the bar** (strong and weak beats) for metric weight: needed for quarter note passing tones; out of this version.
* **Pitch class set templates** for chord identity: cannot name the root of symmetric chords without a rule that spelling already gives.
* **A sliding key window** or a key per cadence: better for modulating phrases, larger, and harder to explain; possible later.
* **Merging on the root alone** at level 2: merges I with I7 where the seventh makes it V7 of IV.

## References

Krumhansl, C. L., & Kessler, E. J. (1982). Tracing the dynamic changes in perceived tonal organization in a spatial representation of musical keys. *Psychological Review*, *89*(4), 334–368.

Krumhansl, C. L. (1990). *Cognitive foundations of musical pitch*. Oxford University Press.
