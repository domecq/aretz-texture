# ADR 0004: Fessel's textural model as the theoretical foundation

Date: November 7, 2026
Status: Proposed

## Context

The first design decisions about how to read a score were taken one at a time: which part is the soprano, what to drop when a score has more than four parts, how to score the representative rhythm. While specifying the first slice (spec 001), the elimination criterion for scores with more than four parts showed the problem: each answer was reasonable on its own, but together they did not add up to a coherent musical view, and several of them decided about the texture before analyzing it.

Pablo Fessel's work on musical texture offers a systematic answer to the question those decisions were circling (Fessel, 1996; Fessel, 2000). It describes texture as a hierarchy of relatively autonomous strata, characterized by five binary features (planes, homogeneity, linearity, accent coincidence and attack divergence) and by factors of association and dissociation that explain when sounds form a line. Its central principle is that the number of instruments or staves does not determine the number of strata. Nico agrees with the model and finds it matches, in a more structured form, what he had in mind for the tool.

The model is described in `docs/theory/fessel_textural_model.md`, with Nico's original notes in Spanish under `docs/theory/sources/`.

## Decision

Aretz Texture bases its analysis on Pablo Fessel's model of textural strata.

* Ingestion keeps every part of a score without loss. It never decides which notes are melody, bass or accompaniment.
* The analysis identifies strata, their characterization and their relations, recursively, using the features and factors of the model.
* The product delivers two renderings of that one analysis: a **textural schema** (strata, their characterization and relations, and their changes over time) and the **four voice harmonic reduction** that was the original goal.

## Rationale

* **One coherent view instead of isolated decisions.** Role classification, the choice of the representative rhythm and the granularity levels follow from the same model, so later decisions can be checked against it.
* **Musically grounded.** The model comes from published research on tonal music, by an author Nico considers sound, and gives the tool a vocabulary musicians and teachers can discuss.
* **Computable.** Most factors are measurable from a score: intervallic proximity, proximity of attacks, directional convergence and divergence, rhythmic independence, registral separation, accent coincidence and attack divergence on the metric grid, timbre through the instrument of each part and intensity through dynamics. This keeps the analysis deterministic and auditable.
* **Fits the existing architecture.** The hierarchical event tree extends naturally to configurations and strata, and the recursive application of the model gives a principled basis for the granularity levels.

## Consequences

* Spec 001 changes: ingestion keeps all parts; the elimination criterion for scores with more than four parts is removed. Piano rendering in that slice applies only to four part scores until the textural analysis exists.
* The architecture replaces "role classification" with strata identification, and the textural schema becomes a second output.
* Features that depend on perception, such as homogeneity and linearity, are implemented as heuristics with named, configurable weights, calibrated against human musical review. This is partly research: the output must explain the reading it chose, so a musician can disagree with it.
* The model is formulated mainly for tonal music (Fessel, 1996, p. 75). Applying it to other repertoires will need its own justification.
* The glossary adopts the model's terms, and the project description credits Fessel's work.
* Dynamics, which the first slice does not ingest, become necessary for the intensity factor.

## References

Fessel, P. (1996). Hacia una caracterización formal del concepto de textura. *Revista del Instituto Superior de Música*, (5), 75–93. https://doi.org/10.14409/ism.v1i5.514

Fessel, P. (2000). Condiciones de linealidad en la música tonal. *Arte e Investigación*, *4*(4), 84–89. https://sedici.unlp.edu.ar/handle/10915/18668
