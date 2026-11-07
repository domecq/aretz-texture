# Pablo Fessel: textural analysis and reduction

Study notes with sources, the theoretical foundation of Aretz Texture (ADR 0004).
Date: November 7, 2026.

This is an English version of the notes Nico wrote in Spanish, kept in their original language at `sources/fessel_analisis_y_reduccion_textural.es.md`. Quotations and page references follow that original.

## 1. Starting point

Pablo Fessel proposes to study musical texture not only through traditional categories such as monody, homophony and polyphony, but through **textural configurations** identified by explicit features. His 1996 proposal belongs to a generative model of tonal music and treats texture as a level of representation of musical organization (Fessel, 1996, pp. 75 to 77).

**A note on terms.** Fessel develops a **model for textural analysis and characterization**. The phrase "textural reduction", understood as simplifying a score into a schema of its strata, names here a **didactic application of the model**, not a reduction procedure attributed literally to the author.

## 2. The five textural features

In *Hacia una caracterización formal del concepto de textura* (Towards a formal characterization of the concept of texture), Fessel proposes five binary features: each one is described by a positive (+) or negative (−) value (Fessel, 1996, p. 79).

| Feature | Analytical question |
|---|---|
| **[± planes]** | Are autonomous planes of musical organization distinguished in the simultaneity? |
| **[± homogeneity]** | Are the planes considered homogeneous with each other? |
| **[± linearity]** | Do the components form recognizable voices or lines? |
| **[± accent coincidence]** | Do their accents coincide? |
| **[± attack divergence]** | Do the time points of attack of their sounds differ? |

These are not five classes of texture nor five successive steps: they are **features that combine** to characterize a configuration. Because the analysis can be applied recursively, it can study global configurations and partial configurations at several levels of organization (Fessel, 1996).

## 3. Textural strata and their hierarchy

In *Condiciones de linealidad en la música tonal* (Conditions of linearity in tonal music), Fessel (2000, p. 84) characterizes texture by a **hierarchical structure of relatively autonomous domains**, called *textural strata*. He names three dimensions for their representation:

1. **Number of strata** at each level of the hierarchy: a melody, a bass, a harmonic accompaniment, and so on; each one may admit internal subdivisions.
2. **Characterization of the strata**: for example, line, ostinato, pedal or harmonic accompaniment.
3. **Relations between strata**: tonal and metric homogeneity or heterogeneity, coincidence of accents or attacks, among others.

The analytical consequence is important: **the number of instruments or staves does not by itself determine the number of strata**. An instrumental group can work as a single plane, and a single instrumental part can contribute to different organizations depending on the passage.

## 4. What makes a line recognizable?

For Fessel (2000, pp. 84 and 85), a musical line is not a given: its identification depends on the global textural context. He distinguishes factors of **internal association** and of **dissociation from other strata**.

**Factors that favor associating sounds into a line:**

* Intervallic proximity.
* Proximity of attacks.
* Formal variability.
* Directional convergence.
* Timbral similarity.

**Factors that favor its differentiation from other strata:**

* Rhythmic independence.
* Registral separation.
* Directional divergence.
* Timbral dissimilarity.
* Differences of intensity.

Fessel holds that both groups of factors complement each other: a very clear differentiation from the rest of the texture can compensate for a weaker internal cohesion of the sounds of the line (Fessel, 2000, pp. 84 and 85).

## 5. Practical application: a "textural reduction"

**The following sequence is a pedagogical adaptation** built from the concepts above; it should not be cited as a protocol prescribed by Fessel.

1. **Delimit a fragment.** Select a passage with a relatively stable textural organization, or several passages to study how it changes.
2. **Recognize sound groupings.** Listen and look for which sounds form coherent units. Avoid automatically equating a track, an instrument or a staff with a stratum.
3. **Represent the strata.** Describe each one by its function and behavior: melody, low support, pedal, ostinato, harmonic mass, and so on. Check whether it contains subdivisions.
4. **Examine the relations.** Consider whether the strata are homogeneous, whether they keep rhythmic independence, whether they synchronize in attacks and accents, and whether they form differentiated lines.
5. **Build a hierarchical schema.** Replace the details of each part with a representation of the groupings and their relations. **The reduction must preserve the relevant textural differences**, even if it omits pitches, notes or figurations that are not essential for the purpose of the analysis.
6. **Compare successive configurations.** Identify the appearance, disappearance, division, fusion or reorganization of strata over time.

### Hypothetical example

Consider a piece for flute, violin, piano and double bass:

* Flute and violin double the same melodic figure, with variations.
* The piano plays arpeggiated chords.
* The double bass sustains long notes.

A hypothesis of **reduction to three strata** would be:

```text
Global textural configuration
├── Stratum A: shared melodic figure
│   ├── Flute
│   └── Violin
├── Stratum B: arpeggiated accompaniment
│   └── Piano
└── Stratum C: low support
    └── Double bass
```

The hypothesis must be tested against listening and against the analysis of attacks, accents, registers, timbres and the autonomy of the components. It could turn out, for example, that piano and double bass are heard as parts of a hierarchically higher accompaniment stratum. Neither reading should be assumed without analyzing the fragment.

## 6. Scope and limits

The 1996 formalization is mainly intended for **tonal music** (Fessel, 1996, p. 75). Its notions of stratification, association and dissociation are useful tools for thinking about other musics, but applying them directly to, for example, an electroacoustic piece requires justifying the perceptual and analytical criteria used. The original model does not automatically solve the particularities of space, noise, synthesis or spectral masses.

The book *Textura musical: Teoría, historia, estética* (Musical texture: theory, history, aesthetics) widens the discussion from a historical and aesthetic perspective, and addresses concepts such as heterophony, stratification, weave and sound surfaces (Fessel, 2026). No claims are attributed here to specific pages of that book, because its full text was not checked.

## 7. Summary

Fessel's central contribution is to move from **labeling a texture** to **describing its organization**: which components are differentiated, how they are characterized, what relations they keep and how they group hierarchically. A graphic reduction can serve as a result or as a tool of that analysis, as long as it is presented as the analyst's elaboration.

## 8. How Aretz Texture uses the model

This section is not part of the original notes; it records how the project applies them (ADR 0004).

* **Strata, not parts.** Ingestion keeps every part of the score. Which notes form the melody, the bass or the accompaniment is decided by analysis, by identifying strata, never by the number or the names of the parts.
* **Measurable factors.** Most association and dissociation factors can be computed from a score: intervallic proximity, proximity of attacks, directional convergence and divergence, rhythmic independence and registral separation. Timbre comes from the instrument of each part and intensity from the dynamics. Accent coincidence and attack divergence are measured on the metric grid.
* **Judgment stays explicit.** Features such as homogeneity and linearity depend on perception and context. The tool implements them as deterministic heuristics with named, configurable weights, calibrated against human musical review, and its output explains the reading it chose so a musician can disagree with it.
* **Two outputs from one analysis.** The textural schema (strata, their characterization and relations, and how they change over time) and the four voice harmonic reduction are both renderings of the same analysis.
* **Recursion as granularity.** The recursive application of the model, global and partial configurations, is the basis for the granularity levels.

## References (APA 7th edition)

Fessel, P. (1996). Hacia una caracterización formal del concepto de textura. *Revista del Instituto Superior de Música*, (5), 75–93. https://doi.org/10.14409/ism.v1i5.514

Fessel, P. (2000). Condiciones de linealidad en la música tonal. *Arte e Investigación*, *4*(4), 84–89. https://sedici.unlp.edu.ar/handle/10915/18668

Fessel, P. (2026). *Textura musical: Teoría, historia, estética*. Editorial de la Universidad Nacional de Quilmes. https://ediciones.unq.edu.ar/769-textura-musical.html

### Links

* [1996 article, first part, PDF reproduction](https://www.hugoribeiro.com.br/biblioteca-digital/Fessel-Caracterizacion_formal_concepto_textura-Part-01.pdf)
* [2000 article, UNLP institutional repository](https://sedici.unlp.edu.ar/handle/10915/18668)
* [Publisher page of the 2026 book](https://ediciones.unq.edu.ar/769-textura-musical.html)

> **Note on sources.** Nico checked directly the available text of the 1996 article, the 2000 article and the publisher page of the 2026 book. The bibliographic data of the 1996 and 2000 articles were checked again against their repositories on November 7, 2026; the publisher page could not be fetched from the agent environment. The example and the reduction sequence are didactic elaborations, not quotations or original examples by Fessel.
