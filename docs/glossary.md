# Glossary

This glossary defines each musical term as the code of Aretz Texture uses it. Identifiers in the code must use these names; if a term is missing, add it here in the same pull request that introduces it (AGENTS.md, "Names"). Where a term has a code identifier, it is shown in backticks. Terms of Pablo Fessel's textural model (ADR 0004, `docs/theory/fessel_textural_model.md`) that have no code yet are marked "concept, not yet implemented".

**Accent coincidence** ([± accent coincidence], C, `TexturalFeatures.accent_coincidence`): the textural feature that asks whether the phenomenal accents of the planes of a configuration coincide, assuming compatible meters (Fessel, 1996). A `-P` configuration is always `+C` (cooccurrence restriction 3). In spec 002 a `+P` configuration is `+C` by a provisional rule, because every plane shares the score's meter; phenomenal accents are not modeled. Defined by spec 002, not yet implemented.

**Alter** (`SpelledPitch.alter`): the number of semitones an accidental moves a note away from its natural step: -2 double flat, -1 flat, 0 natural, 1 sharp, 2 double sharp.

**Alto**: the second voice from the top of the four voice harmonic reduction, chosen by analysis and voicing. It is never a part of the source, even one named Alto. Concept, not yet implemented.

**Association factors**: the factors that favor hearing a succession of sounds as one line: intervallic proximity, proximity of attacks, formal variability, directional convergence and timbral similarity (Fessel, 2000). Concept, not yet implemented.

**Attack** (`Attack`): the start of a sound in a notated voice: a note event, keeping only the pitches that do not continue a tie. An event whose pitches all continue a tie is not an attack, and grace notes and rest fermatas are not attacks. Defined by spec 002, not yet implemented.

**Attack divergence** ([± attack divergence], D, `TexturalFeatures.attack_divergence`): the textural feature that asks whether the time points of attack within or between the planes of a configuration differ inside the span of the tactus (Fessel, 1996). In spec 002 a configuration is `+D` when, in at least one tactus span, two different components attack at different time points; one component attacking alone is not divergence (ADR 0005, a reading to be confirmed by Nico). A `+L` configuration is always `-D` (cooccurrence restriction 5). Defined by spec 002, not yet implemented.

**Bar** (`Bar`): a measure of the score, with the number shown in the score, its onset and its actual duration. The code says bar, never measure, except when naming music21 objects.

**Bass**: the lowest voice of the four voice harmonic reduction, the actual bass chosen by analysis. It is never a part of the source, even one named Bass. Concept, not yet implemented.

**Compact form** (`compact_schema`): a textural configuration written on one line in Fessel's bracket notation, features in the order P, H, L, C, D and children after their parent's features, with identical sibling configurations printed once, as in `[+P, +H, +C, +D [-P, +H, +L, +C, -D]]` (Fessel, 1996, p. 86). Defined by spec 002, not yet implemented.

**Cooccurrence restriction**: one of the five constraints of Fessel (1996, pp. 84 and 85) on which feature values may appear together in a configuration: (1) `-H` implies `+P`; (2) `-P` implies `+H`; (3) `-C` implies `+P`; (4) L is specified exactly when `-P`; (5) `+L` implies `-D`. Validators of `TexturalFeatures`. Defined by spec 002, not yet implemented.

**Density** (`TexturalConfiguration.density`): the number of notated voices fused in one plane by doubling; 1 when the plane is not doubled. Fessel (2000) speaks of a line with thickness or density. Divided events inside one notated voice do not add to it. Defined by spec 002, not yet implemented.

**Dissociation factors**: the factors that favor differentiating a line from the other strata: rhythmic independence, registral separation, directional divergence, timbral dissimilarity and differences of intensity (Fessel, 2000). A strong dissociation can compensate for a weaker association. Concept, not yet implemented.

**Divided event**: a note event with more than one pitch, written as a chord inside one notated voice, such as a bass dividing into octaves on a final chord. All its pitches share onset, duration and fermata; each keeps its own tie.

**Doubling**: two or more notated voices heard as one line with density because their attacks coincide strictly and they move in parallel (Fessel, 2000). In spec 002, two notated voices are doublings when at least a set share of the attacks of the sparser one coincide in onset with an attack of the other sharing a pitch class (unison or octave), over the whole score (ADR 0005). Defined by spec 002, not yet implemented.

**Duration** (`NoteEvent.duration`, `Bar.duration`): how long an event or bar lasts, in quarter lengths, as an exact fraction.

**Event pitch** (`EventPitch`): one pitch of a note event or grace note together with its tie.

**Feature decision** (`FeatureDecision`): the value of one textural feature at one node, with the rule that decided it (`DecisionRule`) and an explanation naming bars and tactus spans, so a musician can see the factor behind the reading (Fessel, 2000, p. 88). Defined by spec 002, not yet implemented.

**Fermata** (`NoteEvent.fermata`, `RestFermata`): a pause sign over or under a note or rest, which in chorales marks the end of a phrase. On a note it is a property of the note event; on a rest it is stored as a rest fermata.

**Fermata end cluster** (`FermataEndCluster`): the ends of fermata notes and rests of different notated voices that lie closer together than a set number of tactus spans and so mark one phrase end, at the latest of them (spec 002, ADR 0005). Defined by spec 002, not yet implemented.

**Full score**: the rendering of a score with one staff per part, in score order, with part and instrument names (`render/full_score.py`). Used by the evaluation to round trip scores with any number of parts.

**Fused stream** (`FusedStream`): the notated voices joined by doubling into one stream; most fused streams hold a single notated voice. In spec 002 each fused stream present in a phrase is one plane. Defined by spec 002, not yet implemented.

**Grace note** (`GraceNote`, `NotatedVoice.grace_notes`): an ornamental note or chord written small, which takes no time in the bar, so it is not a note event. Stored in its notated voice next to the note events, with the onset of the note or rest it ornaments, its pitches with their ties, its notated value (the quarter lengths of its symbol, 1/2 for an eighth) and whether it has a slash. Grace notes at one onset keep their source order and are written before the note or rest at that onset.

**Grand staff** (`GrandStaffLayout`): the two staff system of piano music, an upper staff in treble clef for the right hand and a lower staff in bass clef for the left hand, joined by a brace. `PIANO_LAYOUT` places parts 1 and 2 in score order on the upper staff and parts 3 and 4 on the lower one.

**Harmonic reduction**: the four voice chorale (soprano, alto, tenor, bass) that shows the harmonic structure supporting the texture, one of the two renderings of the analysis. Concept, not yet implemented.

**Harmonic window** (`HarmonicWindow`): a span of time over which a single harmony is considered to hold, the result of merging verticalities in harmonic segmentation (architecture, section 3).

**Homogeneity** ([± homogeneity], H, `TexturalFeatures.homogeneity`): the textural feature that asks whether the planes of a configuration are homogeneous with each other: same harmonic field, simple proportions between their pulses, same spatial origin, similar timbre (Fessel, 1996). A `-P` configuration is always `+H` (cooccurrence restriction 2). In spec 002 a `+P` configuration is `+H` by a provisional rule that holds for a phrase with one time signature and no key signature change; outside those conditions `+H` is recorded as an assumption. Defined by spec 002, not yet implemented.

**Indented form**: a textural configuration written one node per line, children indented under their parent and every plane on its own line with the labels of its streams; the readable form of the textural schema (spec 002). Defined by spec 002, not yet implemented.

**Key signature** (`KeySignatureChange`): the sharps or flats written at the start of a staff, stored per part as a signed count of sharps (negative for flats) with the onset where it takes effect.

**Line**: a succession of sounds heard as one recognizable voice, identified from association and dissociation factors in the textural context. A line is a result of analysis: it is not given by a part or a notated voice. Concept, not yet implemented.

**Linearity** ([± linearity], L, `TexturalFeatures.linearity`): the textural feature that asks whether a plane is configured as a voice (Fessel, 1996). Specified only on `-P` configurations (cooccurrence restriction 4). In spec 002 a plane is `+L` when, at each of its attacks, every notated voice of the plane that sounds also attacks and the attacked pitches are at the unison or octave; these are Fessel's necessary conditions, and the sufficient ones are left to later work. Defined by spec 002, not yet implemented.

**Notated voice** (`NotatedVoice`, `Part.voices`): one of the voices written on the staff of a part, as in MusicXML, holding its note events in order of onset with its own rhythm. Most parts have one; a part with two voices on its staff has two. A fact of the notation, not a line.

**Note event** (`NoteEvent`): one notated note or divided chord of a notated voice, with its onset, duration, pitches with their ties, and fermata. Two notes tied together are two note events, not one.

**Onset** (`onset`): the moment an event or bar begins, in quarter lengths from the start of the first bar, as an exact fraction.

**Part** (`Part`): one part of the source score as stored in the file, identified by its position in score order (part 1 is the top one), with its name and instrument name as metadata and one or more notated voices. Ingestion keeps every part; the number and names of the parts never decide the strata (ADR 0004).

**Phrase** (`Phrase`): the local domain over which spec 002 computes one textural configuration. In the chorales a phrase ends at a fermata end cluster; the music after the last fermata is a last phrase, and a score without fermatas is one phrase (ADR 0005, a project decision, not Fessel's). Numbered from 1. Defined by spec 002, not yet implemented.

**Pickup bar**: an incomplete first bar, shorter than its time signature, that leads into the first full bar (also called anacrusis). Its length is given by `Score.pickup_duration()`.

**Pitch class** (`SpelledPitch.pitch_class()`): a pitch without its octave and spelling, as a number from 0 (C) to 11 (B). F sharp and G flat in any octave share pitch class 6.

**Pitch spelling** (`SpelledPitch`): a pitch written as step, alter and octave, so that enharmonic equivalents such as F sharp and G flat remain different.

**Plane**: in Fessel (1996), an autonomous plane of musical organization distinguished in the simultaneity. In the code, the planes of a `+P` configuration are its children; a plane that is not divided further is a `-P` configuration. Spec 002 treats Fessel's plane (1996) and stratum (2000) as the same domain and keeps "stratum" for a plane with a characterization (open question 8 of spec 002). Defined by spec 002, not yet implemented.

**Planes** ([± planes], P, `TexturalFeatures.planes`): the textural feature that asks whether autonomous planes are distinguished in the simultaneity. `+P` says nothing about how many there are. In the code a configuration is `+P` exactly when it has two or more children. Defined by spec 002, not yet implemented.

**Quarter length**: the unit of every time value in the code: one quarter note equals 1. An eighth note is 1/2 and a triplet eighth is 1/3.

**Rest fermata** (`RestFermata`, `NotatedVoice.rest_fermatas`): a fermata written on a notated rest. Rests are otherwise not stored (silence is the time not covered by note events), so a rest that carries a fermata is kept with the onset and duration of the notated rest, always inside a gap between the events of its notated voice. The writers give it exactly that onset and duration and never split it.

**Round trip**: reading a score into the core model, writing it out and reading the result back, then checking that nothing was lost or altered (`eval/round_trip.py`). It runs through the full score for every score and also through the grand staff for scores of four parts (`RoundTripRoute`).

**Score** (`Score`): a complete piece held in the core model: its bars, its time signatures and its parts in score order.

**Settings** (`TexturalAnalysisSettings`): the typed thresholds of the analysis, each with a name, a unit and its musical meaning. Called settings, never configuration, so that "configuration" always means a textural configuration. Defined by spec 002, not yet implemented.

**Soprano**: the highest voice of the four voice harmonic reduction, which takes the structural note of the melody chosen by analysis. It is never a part of the source, even one named Soprano. Concept, not yet implemented.

**Staff** (`Staff`): one of the two staves of the grand staff, `Staff.UPPER` or `Staff.LOWER`.

**Staff voice** (`StaffVoice`): a staff of the grand staff and a voice number on it, 1 for the upper voice with stems up and 2 for the lower voice with stems down.

**Step** (`SpelledPitch.step`): the letter name of a pitch, from C to B, without accidental or octave.

**Stream** (`StreamReference`): the unit of sound the textural analysis groups into planes. In spec 002 a stream is one notated voice of one part, identified by part number and voice number, with the part name for labels; a notated voice is never split into several streams. Defined by spec 002, not yet implemented.

**Stratum**: a relatively autonomous domain of the texture, such as a melody, a bass, a pedal or a harmonic accompaniment, characterized by its function and its relations with the other strata. Strata form a hierarchy, and their number does not follow from the number of parts or staves (ADR 0004). Concept, not yet implemented.

**Substratum**: an internal subdivision of a stratum, itself a stratum one level lower in the hierarchy. Concept, not yet implemented.

**Tactus** (`tactus_duration`): the time span within which attack divergence is judged (Fessel, 1996). In spec 002 it is the beat of the time signature: a quarter in 4/4 and 3/4, a half in 3/2, a dotted quarter in 6/8 and 12/8 (ADR 0005). Defined by spec 002, not yet implemented.

**Tactus span** (`tactus_spans`): one tactus on the bar grid, from a beat to the next. Spans tile each bar from its onset, except a pickup bar, which is tiled from its end so its spans fall on the last beats of a complete bar. Defined by spec 002, not yet implemented.

**Tenor**: the third voice from the top of the four voice harmonic reduction, chosen by analysis and voicing. It is never a part of the source, even one named Tenor. Concept, not yet implemented.

**Textural configuration** (`TexturalConfiguration`): the organization of the texture in a passage, characterized by the values of the five textural features (Fessel, 1996). Configurations form a tree: a `+P` configuration has two or more subordinate configurations, its planes, and a `-P` configuration is a leaf that groups one or more streams. Applying the analysis recursively gives global and partial configurations, the basis of the granularity levels. Defined by spec 002, not yet implemented.

**Textural feature** (`TexturalFeature`): one of the five binary features of Fessel (1996) that combine to characterize a textural configuration: planes (P), homogeneity (H), linearity (L), accent coincidence (C) and attack divergence (D). Each takes a positive or negative value; L is left unspecified on `+P` configurations. Defined by spec 002, not yet implemented.

**Textural schema** (`format_textural_schema`): the rendering of the analysis as a hierarchy of strata with their characterization and relations, and how they change over time; one of the two renderings of the analysis, with the harmonic reduction. Spec 002 renders it as text, per phrase, in the indented form and the compact form, through `aretz-texture schema`. Defined by spec 002, not yet implemented.

**Tie** (`TieType`): a curved line joining two notes of the same pitch so they sound as one. Each event pitch records its place in the tie: `START`, `CONTINUE` or `STOP`, or none.

**Time signature** (`TimeSignatureChange`): the meter written at the start of a staff, stored once for the whole score as numerator and denominator with the onset where it takes effect.

**Voice**: one of the four lines of the harmonic reduction (soprano, alto, tenor, bass), produced by voicing. Not to be confused with a notated voice of the source or with a line in Fessel's sense.

**Voicing**: the choice of which pitch each of the four voices of the harmonic reduction takes in a chord (architecture, section 6; package `voicing/`).
