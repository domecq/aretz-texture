# Fessel's model as an algorithm: a first decomposition

Working document for scoping the textural analysis (spec 002 onward).
Date: November 12, 2026.

This document breaks the model described in [`fessel_textural_model.md`](fessel_textural_model.md) into steps that can be computed from a score. Each step says whether its content comes from **Fessel** or is a **project decision**, because only the first is theory and the second can be changed by an ADR. It is based on Nico's study notes: the available copies of the 1996 and 2000 articles are scanned images that could not be read from the agent environment, so the points marked **undefined** need the original texts.

## Summary of the model

Fessel moves from labeling a texture (homophony, polyphony) to describing its organization.

1. **Hierarchical strata** (Fessel, 2000). Texture is a hierarchy of relatively autonomous strata, represented in three dimensions: the number of strata at each level, the characterization of each stratum (line, ostinato, pedal, harmonic accompaniment) and the relations between strata. The number of parts or staves does not determine the number of strata.
2. **Conditions of linearity** (Fessel, 2000). Whether a group of sounds is heard as a line depends on factors of internal association (intervallic proximity, proximity of attacks, formal variability, directional convergence, timbral similarity) and of dissociation from other strata (rhythmic independence, registral separation, directional divergence, timbral dissimilarity, differences of intensity). The two groups compensate each other.
3. **Five binary features** (Fessel, 1996). Planes, homogeneity, linearity, accent coincidence and attack divergence characterize a configuration. They can be applied recursively, to global and to partial configurations.

## Steps

### 0. Input

The core model of spec 001: events per notated voice with onset, duration and pitches, bars and meter, and part and instrument names as the only source of timbre. Dynamics are not ingested yet and are needed for the intensity factor.

### 1. Initial units (project decision)

Each notated voice is a candidate unit. Fessel does not prescribe this unit, and one part can contribute to several strata, so later steps must be able to group units and also to split them, for example a divided event whose pitches belong to different strata.

### 2. Segmentation in time (didactic adaptation, not Fessel)

Cut the piece into windows, by bar or by phrase (in the chorales, phrases end at fermatas), compute the configuration of each window, and merge adjacent windows with the same configuration.

### 3. Measuring the factors (factors from Fessel, measures are project decisions)

For each unit and each pair of units in a window:

| Factor | Possible measure | Kind |
|---|---|---|
| Intervallic proximity | size of the melodic intervals within the unit | association |
| Proximity of attacks | time between successive attacks within the unit | association |
| Formal variability | **undefined**, needs the original | association |
| Directional convergence and divergence | similar, oblique or contrary motion between two units | both |
| Timbral similarity and dissimilarity | same instrument or family | both |
| Rhythmic independence | proportion of attacks two units do not share | dissociation |
| Registral separation | distance and overlap of the ranges of two units | dissociation |
| Differences of intensity | dynamics, not ingested yet | dissociation |

### 4. Grouping into strata (project decision)

Combine the factors into an association score between units, with named, configurable weights (AGENTS.md, configuration). The compensation Fessel describes belongs in the formula: a strong dissociation from the rest can make up for a weak internal cohesion. Doubling is the clearest case: the same pitch classes and the same attacks, even at the octave, make two units fuse.

### 5. Hierarchy (recursion from Fessel, mechanism is a project decision)

Repeat the grouping with stricter thresholds to build a tree: global configuration, strata, substrata. Each level of the tree is a level of granularity.

### 6. Characterizing each stratum (categories from Fessel, rules are project decisions)

* Pedal: one pitch sustained or repeated.
* Ostinato: a repeated pattern.
* Harmonic accompaniment: several simultaneous pitches, attacked together.
* Low support: the stratum in the lowest register.
* Line: what meets the conditions of linearity.

### 7. The five features (features from Fessel, decision rules **undefined**)

Computed at each node of the tree:

* Planes: more than one stratum at that level.
* Homogeneity: the strata are of the same kind.
* Linearity: the components are lines.
* Accent coincidence: needs a model of accents (metric, agogic and contour).
* Attack divergence: proportion of onsets the components do not share.

The original is needed for the operative definitions of the features, for any dependency between them (for example whether homogeneity applies only when there is more than one plane) and for any table that maps combinations of features to traditional categories.

### 8. Relations between strata (dimension 3 from Fessel)

Tonal and metric homogeneity or heterogeneity, and coincidence of accents and attacks, for each pair of strata.

### 9. Comparing successive configurations (didactic adaptation)

Detect over time the appearance, disappearance, division, fusion or reorganization of strata.

### 10. Outputs (project decision, ADR 0004)

The textural schema (the tree with its characterizations and how it changes over time) and the four voice harmonic reduction, both rendered from the same analysis.

## What this says about scope

* **Steps 1, 3 and 8 are measurable now** from the existing model, without interpretation. They are a natural first spec.
* **Steps 4, 5 and 6 are research**: weights, thresholds and calibration against Nico's musical review.
* **Step 7 and the formal variability factor need the original articles**, which Nico will look into.
* **The chorales are a poor corpus for texture**: almost all are four nearly homorhythmic lines. They are good for validating the measures; calibrating the grouping into strata needs other public domain repertoire, such as Romantic piano music, Haydn or Mozart.
