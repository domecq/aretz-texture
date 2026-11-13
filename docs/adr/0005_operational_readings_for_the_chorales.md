# ADR 0005: operational readings of Fessel's features and phrase segmentation for the chorales

Date: November 12, 2026
Status: Proposed

## Context

Spec 002 computes Fessel's textural configuration of every phrase of the 350 corpus chorales. Fessel defines the five features and their cooccurrence restrictions (1996, pp. 79 to 85) and the factors that make a stratum a line (2000, pp. 84 to 88), but he does not give a procedure: he anticipates an algorithmic specification and expects it to differ from intuitive readings in revealing ways (1996, p. 90). To compute the tree, the project has to choose a local domain, a tactus, a criterion for doublings and a decision rule for each feature. These choices change musical results, so they are recorded here rather than left inside the code (AGENTS.md: musical decisions that are project decisions and not obvious need an ADR).

The corpus facts these choices rest on were verified by the main session on November 12, 2026 and are cited in spec 002, section 5.

## Decision

For the chorales, and until a later ADR replaces any of them:

1. **Local domain: the phrase, ended by fermatas** (project). Fermata ends of every notated voice of every part are clustered when closer than one tactus; the latest end of each cluster ends a phrase; music after the last fermata is a last phrase; a score without fermatas is one phrase. No part is privileged, because part order varies in the corpus and in 56 chorales the fermata ends of the first four parts disagree.
2. **Tactus: the beat of the time signature** (project), dotted in compound meters, with tactus spans on the bar grid and a pickup bar aligned to its end.
3. **Streams are notated voices** (project). One notated voice is never split (no stream segregation).
4. **Doublings** (criteria from Fessel 2000, pp. 85 to 88; thresholds project). Two notated voices fuse into one line with density when at least 9/10 of the attacks of the sparser one coincide in onset with an attack of the other sharing a pitch class (unison or octave). Fusion is computed over the whole score and is transitive. Doublings at other intervals and intermediate +P nodes are not formed.
5. **Each fused stream is a plane under the phrase's root** (project, this slice only).
6. **P** is `+` when two or more planes are present (Fessel 1996, definition).
7. **L**, at leaves only (restriction 4): `+` when, at every attack point of the plane, every voice of the plane that sounds also attacks and all attacked pitches are at the unison, octave, fourth, fifth, third or sixth, and, where they are at intervals other than unison and octave, all pitches move in the same direction at nearly every step (Fessel 1996, p. 81, scale of closeness; Fessel 2000, p. 86, registral spacing of a line with relatively constant parallelism; the shares are project settings). Decided by Nico on November 12, 2026, instead of a cutoff at the octave.
8. **D** (project reading of Fessel 1996, p. 83, to be confirmed by Nico): a tactus span diverges when two different components attack at different time points inside it; a component attacking alone, tied continuations and attacks in different tactus spans do not diverge; one divergent span makes the configuration `+D`; a root is also `+D` when one of its planes is.
9. **H** (provisional, project): `+` when the phrase has one time signature and no part changes key signature inside it; otherwise `+` recorded as an assumption. Key signatures are not compared across parts.
10. **C** (provisional, project): `+`, since the core model gives every plane the score's meter; phenomenal accents are not modeled.
11. **Every decision records its rule and an explanation** naming bars and tactus spans, following Fessel's emphasis on the factors behind a reading (2000, p. 88).

All thresholds live in typed settings (`analysis/settings.py`) with name, unit and musical meaning.

## Rationale

* **Fermatas are the chorales' own phrase marks**, and reading all voices makes the result independent of part order and of fermatas missing in some parts, both present in the corpus.
* **The beat as tactus** is the simplest reading that gives Fessel's example 6 its `+D` (all four settings of the melody in the St Matthew Passion are `+D` in their first phrase) and still separates the fully homorhythmic phrases (78 of 2107 in the probe).
* **Unison and octave doublings over the whole score** reproduce the doublings of the instrumentation found by the probe (Bass with Continuo in BWV 8.6 and BWV 248.59 6; Oboe 1, Violin 1 and Soprano in BWV 190.7) without joining voices that coincide only briefly.
* **Linearity follows Fessel's own scale of closeness**: Fessel 2000 (p. 86) treats parallel fourths, fifths, thirds and sixths with coinciding attacks as the registral spacing of one line, not as parallel lines, so cutting at the octave would contradict the model. The required attack coincidence stays strict, so a non strict doubling appears as one plane that is not a single line instead of being hidden.
* **H and C as provisional rules** are honest about what the chorales can test: one key and one meter per phrase. Recording the rule lets a musician see where the reading is an assumption.

## Consequences

* The chorale evaluation of spec 002 depends on these readings; changing any of them changes committed lists, which is visible in review.
* Fusion of doublings brings only 2 of the 19 chorales with more than four parts to four planes; grand staff rendering of the others needs more than this ADR.
* Non chorale repertoire needs its own local domain (bars or cadences), a real model of H and C, and probably segregation; each will be a new ADR.
* Nico adopted readings 1 to 6 and 8 to 11 on November 12, 2026, and decided reading 7 as written above. The ADR becomes Accepted when spec 002 is approved.

## Alternatives considered

* **Phrases from one part** (the soprano, or part 1): fails in the three chorales whose part 1 is an instrument without fermatas, and depends on part names or order (ADR 0004).
* **Majority of parts for a phrase end**: fails where instruments carry no fermatas, as in BWV 190.7.
* **Fixed windows of bars**: arbitrary in the chorales, where the fermatas mark the phrases.
* **Fusion per phrase**: joins voices that share one or two notes in a short phrase.
* **Strict attack coincidence (1) for fusion**: closest to Fessel's wording, kept available as a setting; 9/10 is the threshold the corpus facts were verified with.
* **D as the share of divergent tactus spans with a threshold above one span**: possible later; Fessel's feature is binary and the reading of one span is the simplest that agrees with example 6.

## References

Fessel, P. (1996). Hacia una caracterización formal del concepto de textura. *Revista del Instituto Superior de Música*, (5), 75–93. https://doi.org/10.14409/ism.v1i5.514

Fessel, P. (2000). Condiciones de linealidad en la música tonal. *Arte e Investigación*, *4*(4), 84–89. https://sedici.unlp.edu.ar/handle/10915/18668
