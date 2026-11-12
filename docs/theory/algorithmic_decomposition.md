# Fessel's model as an algorithm: a first decomposition

Working document for scoping the textural analysis (spec 002 onward).
Date: November 12, 2026.

This document breaks Fessel's model into steps that can be computed from a score. Each step says whether its content comes from **Fessel** or is a **project decision**: only the first is theory, and the second can be changed by an ADR. It is based on the two articles (Fessel, 1996; Fessel, 2000), read in transcriptions Nico made from the scanned originals, and on the study notes in [`fessel_textural_model.md`](fessel_textural_model.md). The transcriptions are kept in the private project space and not in this repository, because the articles are under copyright; this document cites them by page.

## 1. What the two articles contribute

### 1996: textural configurations as feature trees

* A **textural configuration** (CT, *configuración textural*) is an unordered set of five binary features (p. 79): planes **P**, homogeneity **H**, linearity **L**, accent coincidence **C** and attack divergence **D**.
* Configurations nest. A single context free rule schema, `X → X*, Y*`, expands every configuration with **+P** into subordinate configurations until it reaches configurations with **−P**, which are terminal (pp. 83 and 84). The result is a tree: the root is the global configuration and the leaves are planes that are not divided further.
* **Feature co-occurrence restrictions** (pp. 84 and 85, *Restricciones a la Co-ocurrencia de Rasgos*):
  1. −H implies +P.
  2. −P implies +H.
  3. −C implies +P.
  4. L is specified if and only if the configuration is −P (printed without a sign; every example in the article reads this way).
  5. +L implies −D.
* **Definitions** (pp. 79 to 83):
  * **P**: whether autonomous planes of syntactic organization are formed. −P is *homophonic* in Fessel's sense (one plane, which may be a block of chords). +P says nothing about how many planes there are.
  * **H**: whether the planes are homogeneous with each other. In tonal music the criteria include the same harmonic field (repertoire of pitches), simple proportions between the pulses of the planes at each metric level, the same spatial origin and timbral homogeneity. −H is *heterophonic* in Fessel's sense.
  * **L**: whether a plane is configured as a voice, defined by restrictions on simultaneity: simultaneous sounds belong to one voice only if their attacks coincide and they are close in interval, in the order unison, octave, fifth, third. Doublings (a continuo bass played by several instruments) are one voice. These are necessary conditions; the sufficient ones (registral, timbral and dynamic continuity, melodic divergence, motivic logic) are left to research.
  * **C**: whether the phenomenal accents (in the sense of Lerdahl and Jackendoff) of the planes coincide, assuming compatible meters: same beats, different placement of strong beats. +C is *homorhythmic* and −C *polyrhythmic*. A difference in the proportions of the beats themselves belongs to H, not to C.
  * **D**: whether attack points diverge within or between planes **inside the span of the tactus**. A one to one correspondence is not needed for −D; divergence across a larger span than the tactus does not make it +.
* **Worked representations** (pp. 85 to 88). A Bach chorale phrase ("O Haupt voll Blut und Wunden") is `[+P, +H, +C, +D [-P, +H, +L, +C, -D]]`: four homogeneous lines with coincident accents and diverging attacks. Planes in strict parallel (the two oboes of the Trio of the first Brandenburg Concerto) form a +P node with −D below the root. A melody with accompaniment is `[+P, +H, +C, +D [-P, +H, +L, +C, -D] [-P, +H, -L, +C, +D]]`.
* **Traditional categories** (p. 89): homophony `[-P]`; polyphony `[+P [-P, +L]]`; heterophony `[+P, -H [...]]`; monody `[-P, +L]`; accompanied monody `[+P [-P, +L] [-P, -L]]`.
* **Out of the model**: density (note 1) and imitation, which Fessel considers and leaves out (p. 83).
* **An algorithm is anticipated** (p. 90): Fessel expects differences between an algorithmic specification of the features and intuitive characterizations, and considers those differences revealing for research.

### 2000: what makes a stratum a line

* The three dimensions of a textural structure (p. 84): the number of strata at each level, their characterization (line, ostinato, pedal, harmonic *ripieno*) and their relations (tonal and metric homogeneity, accent and attack coincidence). The relations are the H, C and D of 1996 seen between strata.
* The first distinction in the characterization is linear against non linear strata. A line is a function of the global texture, decided by **association** factors (intervallic proximity, proximity of attacks, formal variability, directional convergence, timbral similarity) and **dissociation** factors (rhythmic independence, registral separation, directional divergence, timbral dissimilarity, differences of intensity), which compensate each other (p. 85).
* **How the factors interact** (pp. 85 to 88):
  * Intervallic proximity is the strongest condition. The more a line is separated in register from the other strata, the less intervallic proximity it needs.
  * Proximity of attacks only associates when intervallic proximity holds; stream segregation shows the priority of the first.
  * Formal variability is a minimum of melodic movement that tells a line from a pedal or an ostinato.
  * Timbre and intensity cannot by themselves associate or dissociate: a unison played by four instruments with the same attacks is one line.
  * Simultaneous sounds can form one line, with thickness or density, when their attacks coincide strictly and, preferably, they move in parallel. Without those conditions, registral separation dissociates. Extreme spacing can split a doubling into different strata even with synchronous attacks (note 10).
  * Whether a stratum is linear is not always decidable; what matters is identifying the factors behind each reading.

## 2. Steps

### 0. Input

The core model of spec 001: events per notated voice with onset, duration and pitches, bars and meter, and part and instrument names as the only source of timbre. Dynamics are not ingested yet; Fessel (2000) says intensity cannot decide a line by itself, which lowers their priority.

### 1. Local domain (project decision)

Fessel treats configurations as local and almost instantaneous (1996, p. 90) but does not formalize the domain. Analyze by windows, by phrase where the music marks it (in the chorales, the fermatas) or by bar, and merge adjacent windows with the same configuration. D also needs the **tactus** of each window, which comes from the meter (project decision: the beat of the time signature).

### 2. Sound streams (project decision, grounded in Fessel 2000)

Start from the events of each notated voice. Two refinements come from the 2000 article:

* **Fusion of doublings**: units whose attacks coincide strictly and that move in parallel (unison, octave and, with less weight, fifth, fourth, third and sixth) become one line with density. In the corpus this covers the instruments that double the voices in the 19 chorales with more than four parts.
* **Stream segregation**: one notated voice can hold more than one line when its intervals are discontinuous (virtual polyphony). Detecting it is research, and the chorales barely need it.

### 3. Measuring the factors (factors from Fessel 2000, measures are project decisions)

For each stream and each pair of streams in a window:

| Factor | Possible measure | Kind |
|---|---|---|
| Intervallic proximity | size of the melodic intervals within the stream | association |
| Proximity of attacks | time between successive attacks, only where intervals are close | association |
| Formal variability | amount of pitch change; none means pedal, a repeated pattern means ostinato | association |
| Directional convergence and divergence | similar, oblique or contrary motion between two streams | both |
| Timbral similarity and dissimilarity | same instrument or family; never decisive alone | both |
| Rhythmic independence | proportion of attacks two streams do not share | dissociation |
| Registral separation | distance and overlap of the ranges of two streams | dissociation |
| Differences of intensity | dynamics, not ingested yet; never decisive alone | dissociation |

### 4. Grouping into planes and building the tree (tree and restrictions from Fessel 1996, grouping is a project decision)

Group streams into planes with an association score built from the factors, with named, configurable weights, and with the compensation and priorities above written into the formula. Planes that are themselves grouped (strict parallels such as the two oboes) form intermediate +P nodes. The leaves are −P configurations.

### 5. Specifying the features (features from Fessel 1996, decision rules are project decisions)

At each node:

* **P**: + when the node has more than one plane below it.
* **H**: compare the harmonic fields and the metric proportions of the children, and timbre as a weak criterion.
* **L**, leaves only: + when the plane meets the conditions of linearity (attack coincidence and interval closeness for any simultaneity, plus the factors of step 3).
* **C**: needs a model of phenomenal accents and of the metric placement of each plane; with a single shared meter and no syncopation across planes it is +.
* **D**: + when attacks diverge within the tactus, within or between the planes below the node.

Every tree is checked against the five co-occurrence restrictions, which become validators of the data model.

### 6. Characterizing the strata (from Fessel 2000, rules are project decisions)

L says only whether a plane is a line; Fessel (1996, p. 87) notes that −L cannot tell block chords from an Alberti bass. The 2000 characterization adds the kind of stratum: line, pedal, ostinato, harmonic *ripieno*, and the density of a line with doublings.

### 7. Comparing successive configurations (practice of Fessel 1996, the Ives example, pp. 87 and 88)

Detect over time the appearance, disappearance, division, fusion or reorganization of planes.

### 8. Outputs (project decision, ADR 0004)

The textural schema, written in Fessel's own notation and as a readable tree, and the four voice harmonic reduction, both rendered from the same analysis. The analysis records which factors decided each grouping and feature, since Fessel (2000, p. 88) values identifying those factors more than the binary decision.

## 3. What this says about scope

* **Fessel gives a ground truth for the corpus**: a chorale phrase is `[+P, +H, +C, +D [-P, +H, +L, +C, -D]]` (1996, p. 86). A first spec can compute the tree for every phrase of the 350 chorales and compare it with that representation, the same way 001c compares the round trip.
* **Measurable now from the existing model**: steps 1, 3 and the features P, L and D. H and C need simple rules that hold for the chorales (one key, one meter) and real models later.
* **Fusion of doublings** would let the 19 chorales with more than four parts reach four planes and, with them, the grand staff.
* **Research**: the weights of step 4, stream segregation, a model of phenomenal accents for C and the characterization of step 6.
* **The chorales are a poor corpus for texture variety**: they validate the measures and the feature rules, but calibrating the grouping needs other public domain repertoire, such as Romantic piano music, Haydn or Mozart.

## References

Fessel, P. (1996). Hacia una caracterización formal del concepto de textura. *Revista del Instituto Superior de Música*, (5), 75–93. https://doi.org/10.14409/ism.v1i5.514

Fessel, P. (2000). Condiciones de linealidad en la música tonal. *Arte e Investigación*, *4*(4), 84–89. https://sedici.unlp.edu.ar/handle/10915/18668
