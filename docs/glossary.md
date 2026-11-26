# Glossary

This glossary defines each musical term as the code of Aretz Texture uses it. Identifiers in the code must use these names; if a term is missing, add it here in the same pull request that introduces it (AGENTS.md, "Names"). Where a term has a code identifier, it is shown in backticks. Terms of Pablo Fessel's textural model (ADR 0004, `docs/theory/fessel_textural_model.md`) that have no code yet are marked "concept, not yet implemented".

**Accent coincidence** ([± accent coincidence], C, `TexturalFeatures.accent_coincidence`): the textural feature that asks whether the phenomenal accents of the planes of a configuration coincide, assuming compatible meters (Fessel, 1996). A `-P` configuration is always `+C` (cooccurrence restriction 3). In spec 002 a `+P` configuration is `+C` by a provisional rule, because every plane shares the score's meter; phenomenal accents are not modeled. Defined by spec 002; the model is in `core/texture.py`, and the rule is in `analysis/features.py` (`decide_root_accent_coincidence`).

**Accented note**: a sounding note that starts at the onset of a tactus span; any other note is unaccented. The only metric weight of spec 003, with no strong and weak beats inside the bar (ADR 0007, reading 3). Defined by spec 003 (003a); the rule is in `analysis/non_chord_tones.py`.

**Adjacent notes**: two sounding notes of one notated voice where the first ends exactly where the second begins, so there is no rest between them. Non chord tone rules read only adjacent notes. Defined by spec 003 (003a); the rule is in `analysis/non_chord_tones.py`.

**Alter** (`SpelledPitch.alter`): the number of semitones an accidental moves a note away from its natural step: -2 double flat, -1 flat, 0 natural, 1 sharp, 2 double sharp.

**Alto**: the second voice from the top of the four voice harmonic reduction, chosen by analysis and voicing. It is never a part of the source, even one named Alto. Concept, not yet implemented.

**Anticipation** (`NonChordToneKind.ANTICIPATION`): an unaccented non chord tone, short, approached by melodic step and followed in its voice by the same pitch at the next tactus onset, where it belongs to the next harmony (ADR 0007, reading 5). Defined by spec 003 (003a); the rule is in `analysis/non_chord_tones.py`.

**Association factors**: the factors that favor hearing a succession of sounds as one line: intervallic proximity, proximity of attacks, formal variability, directional convergence and timbral similarity (Fessel, 2000). Concept, not yet implemented.

**Attack** (`Attack`): the start of a sound in a notated voice: a note event, keeping only the pitches that do not continue a tie. An event whose pitches all continue a tie is not an attack, and grace notes and rest fermatas are not attacks. Defined by spec 002; implemented in `analysis/attacks.py` (`voice_attacks`).

**Attack divergence** ([± attack divergence], D, `TexturalFeatures.attack_divergence`): the textural feature that asks whether the time points of attack within or between the planes of a configuration differ inside the span of the tactus (Fessel, 1996). In spec 002 a configuration is `+D` when, in at least one tactus span, two or more components attack and their sets of attack points inside the span are not all equal; components that share every attack point do not diverge, and one component attacking alone is not divergence (ADR 0005). A `+L` configuration is always `-D` (cooccurrence restriction 5). Defined by spec 002; the model is in `core/texture.py`, and the rule is in `analysis/features.py` (`measure_divergence` and `decide_leaf_attack_divergence` and `decide_root_attack_divergence`).

**Bar** (`Bar`): a measure of the score, with the number shown in the score, its onset and its actual duration. The code says bar, never measure, except when naming music21 objects.

**Bass**: the lowest voice of the four voice harmonic reduction, the actual bass chosen by analysis. It is never a part of the source, even one named Bass. Concept, not yet implemented.

**Chord identity** (`ChordIdentity`): what a harmonic window is as a chord: its root, its chord quality, its bass as a pitch name and its inversion, found by stacking the spelled pitches of its chord tones in thirds (ADR 0007, reading 8). Defined by spec 003 (003b); not yet implemented.

**Chord quality** (`ChordQuality`): the kind of a chord by the sizes of its third, fifth and seventh above the root: major, minor, diminished or augmented triad, or dominant, major, minor, half diminished or diminished seventh chord. Its values are the MusicXML `<kind>` names. Defined by spec 003 (003b); not yet implemented.

**Chord symbol** (`ChordIdentity.symbol`, `ChordSymbolMark`): the name of a chord by its root, quality and bass, such as `G7/B`, written above the upper staff as a MusicXML `<harmony>` element; one of the two chord names of the reduction. Defined by spec 003 (003b and 003c); not yet implemented.

**Chord tone**: a pitch sounding in a harmonic window that belongs to its harmony, that is, not removed as a non chord tone; a suspension's resolution takes the suspension's place from the tactus onset. Defined by spec 003 (003a); the removal and the replacement of a suspension are in `analysis/harmonic_segmentation.py`.

**Compact form** (`compact_schema`): a textural configuration written on one line in Fessel's bracket notation, features in the order P, H, L, C, D and children after their parent's features, with identical sibling configurations printed once, as in `[+P, +H, +C, +D [-P, +H, +L, +C, -D]]` (Fessel, 1996, p. 86). Defined by spec 002; implemented in `core/texture.py` and `render/textural_schema.py`.

**Component** (`Component`): what can attack in a configuration when attack divergence is judged: its planes at a `+P` root, its notated voices at a leaf. A plane's attack points are the union of the attack points of its notated voices in the phrase. Defined by spec 002; implemented in `analysis/features.py`.

**Cooccurrence restriction**: one of the five constraints of Fessel (1996, pp. 84 and 85) on which feature values may appear together in a configuration: (1) `-H` implies `+P`; (2) `-P` implies `+H`; (3) `-C` implies `+P`; (4) L is specified exactly when `-P`; (5) `+L` implies `-D`. Validators of `TexturalFeatures`. Defined by spec 002; implemented in `core/texture.py`.

**Decision rule** (`DecisionRule`): the rule or factor that decided the value of one feature at one node, such as `plane_count` or `restriction_5`; one enumeration for all features, whose fit to a feature the core does not check. Fessel (2000, p. 88) values the factors behind a reading more than the binary decision. Defined by spec 002; implemented in `core/texture.py`.

**Density** (`TexturalConfiguration.density`): the number of notated voices fused in one plane by doubling; 1 when the plane is not doubled. Fessel (2000) speaks of a line with thickness or density. Divided events inside one notated voice do not add to it. Defined by spec 002; implemented in `core/texture.py` and `render/textural_schema.py`.

**Dissociation factors**: the factors that favor differentiating a line from the other strata: rhythmic independence, registral separation, directional divergence, timbral dissimilarity and differences of intensity (Fessel, 2000). A strong dissociation can compensate for a weaker association. Concept, not yet implemented.

**Divided event**: a note event with more than one pitch, written as a chord inside one notated voice, such as a bass dividing into octaves on a final chord. All its pitches share onset, duration and fermata; each keeps its own tie.

**Divergent span** (`DivergentSpan`): a tactus span in which at least two components attack and their sets of attack points inside the span are not all equal, with the two components that show it. One divergent span is enough to make a configuration `+D` (`minimum_divergent_tactus_spans`). Defined by spec 002; found by `measure_divergence` in `analysis/features.py`.

**Doubling**: two or more notated voices heard as one line with density because their attacks coincide strictly and they move in parallel (Fessel, 2000). In spec 002, two notated voices are doublings when at least a set share of the attacks of the sparser one coincide in onset with an attack of the other sharing a pitch class (unison or octave), over the whole score (ADR 0005). Defined by spec 002; the proportion and the fusion are in `analysis/doublings.py`.

**Duration** (`NoteEvent.duration`, `Bar.duration`): how long an event or bar lasts, in quarter lengths, as an exact fraction.

**Event pitch** (`EventPitch`): one pitch of a note event or grace note together with its tie.

**Feature decision** (`FeatureDecision`): the value of one textural feature at one node, with the rule that decided it (`DecisionRule`) and an explanation naming bars and tactus spans, so a musician can see the factor behind the reading (Fessel, 2000, p. 88). Defined by spec 002; the model is in `core/texture.py`, and the decisions are produced by `analysis/features.py`.

**Fermata** (`NoteEvent.fermata`, `RestFermata`): a pause sign over or under a note or rest, which in chorales marks the end of a phrase. On a note it is a property of the note event; on a rest it is stored as a rest fermata.

**Fermata cluster** (`FermataCluster`): fermata notes and rests of different notated voices whose time spans overlap, heard as one stop and so marking one phrase end, at the latest of their ends (spec 002, ADR 0005). Defined by spec 002; found by `fermata_clusters` in `analysis/phrases.py`, which keeps the clusters with at least `minimum_fermata_voices` notated voices.

**Full score**: the rendering of a score with one staff per part, in score order, with part and instrument names (`render/full_score.py`). Used by the evaluation to round trip scores with any number of parts.

**Fused stream** (`FusedStream`): the notated voices joined by doubling into one stream; most fused streams hold a single notated voice. In spec 002 each fused stream present in a phrase is one plane. Defined by spec 002; computed by `fuse_doublings` in `analysis/doublings.py` over the whole score, where fusion is transitive: a notated voice that doubles two others joins them in one stream even if they do not double each other.

**Grace note** (`GraceNote`, `NotatedVoice.grace_notes`): an ornamental note or chord written small, which takes no time in the bar, so it is not a note event. Stored in its notated voice next to the note events, with the onset of the note or rest it ornaments, its pitches with their ties, its notated value (the quarter lengths of its symbol, 1/2 for an eighth) and whether it has a slash. Grace notes at one onset keep their source order and are written before the note or rest at that onset.

**Grand staff** (`GrandStaffLayout`): the two staff system of piano music, an upper staff in treble clef for the right hand and a lower staff in bass clef for the left hand, joined by a brace. `PIANO_LAYOUT` places parts 1 and 2 in score order on the upper staff and parts 3 and 4 on the lower one.

**Granularity level** (`GranularityLevel`): how coarse the harmonic reduction is: 1 surface (every harmonic window), 2 harmonic rhythm (one chord per change of function), 3 prolongation and 4 phrase (architecture, section 8). Each level is a cut of the tree of harmonic events. Spec 003 computes levels 1 and 2; 3 and 4 are reserved. Defined by spec 003 (003b and 003d); not yet implemented.

**Harmonic event** (`HarmonicEvent`): a node of the tree of harmonic events: a time span, a granularity level, a reading (a chord identity or an unidentified sonority), the harmonic windows it covers and its children at the level below (architecture, section 4). Defined by spec 003 (003b); not yet implemented.

**Harmonic reduction** (`Reduction`, `reduction_score`): the four voice chorale (soprano, alto, tenor, bass) that shows the harmonic structure supporting the texture, the product of the tool; the textural schema is its annex. In spec 003 it is a sequence of voiced chords at level 2, written on a grand staff with chord symbols and Roman numerals. Defined by spec 003 (003c); not yet implemented.

**Harmonic rhythm**: the rhythm of the changes of harmony; as a rhythmic mode of the reduction (architecture, section 9), each chord is attacked once and lasts as long as its harmonic event. Defined by spec 003 (003c); not yet implemented.

**Harmonic window** (`HarmonicWindow`): a span of time over which a single harmony is considered to hold, the result of merging reduced verticalities in harmonic segmentation (architecture, section 3). In spec 003 a new window starts where a pitch class appears that the current window does not hold, or where its lowest chord tone changes pitch class; windows never cross a phrase (ADR 0007, reading 7). Each records its chord tones, the plane note of each plane and the non chord tones it removed. Defined by spec 003 (003a); the model is in `core/harmony.py` and the segmentation is in `analysis/harmonic_segmentation.py` (`segment_harmony`).

**Homogeneity** ([± homogeneity], H, `TexturalFeatures.homogeneity`): the textural feature that asks whether the planes of a configuration are homogeneous with each other: same harmonic field, simple proportions between their pulses, same spatial origin, similar timbre (Fessel, 1996). A `-P` configuration is always `+H` (cooccurrence restriction 2). In spec 002 a `+P` configuration is `+H` by a provisional rule that holds for a phrase with one time signature and no key signature change; outside those conditions `+H` is recorded as an assumption. Defined by spec 002; the model is in `core/texture.py`, and the rule is in `analysis/features.py` (`decide_root_homogeneity`).

**Indented form**: a textural configuration written one node per line, children indented under their parent and every plane on its own line with the labels of its streams; the readable form of the textural schema (spec 002). Defined by spec 002; implemented in `core/texture.py` and `render/textural_schema.py`.

**Inversion** (`ChordIdentity.inversion`): which member of a chord is its bass: 0 the root (root position), 1 the third, 2 the fifth, 3 the seventh. Defined by spec 003 (003b); not yet implemented.

**Key profile** (`KeySettings`): twelve weights saying how well each pitch class, counted from the tonic, fits a major or a minor key; spec 003 uses the probe tone ratings of Krumhansl and Kessler (1982) to find the local key. Defined by spec 003 (003d); not yet implemented.

**Key signature** (`KeySignatureChange`): the sharps or flats written at the start of a staff, stored per part as a signed count of sharps (negative for flats) with the onset where it takes effect.

**Leaf**: a `-P` textural configuration, which groups one or more streams; `TexturalConfiguration.leaves()` returns the leaves of a tree in order, and each is printed on its own line of the indented form. Defined by spec 002; implemented in `core/texture.py`.

**Line**: a succession of sounds heard as one recognizable voice, identified from association and dissociation factors in the textural context. A line is a result of analysis: it is not given by a part or a notated voice. Concept, not yet implemented.

**Linearity** ([± linearity], L, `TexturalFeatures.linearity`): the textural feature that asks whether a plane is configured as a voice (Fessel, 1996). Specified only on `-P` configurations (cooccurrence restriction 4). In spec 002 a plane is `+L` when, at each of its attacks, every notated voice of the plane that sounds also attacks and the attacked pitches are at the unison, octave, fourth, fifth, third or sixth, and where they are at intervals other than unison and octave they move in parallel at nearly every step (Fessel 1996, p. 81; Fessel 2000, p. 86; ADR 0005, reading 7). Separate notated voices are fused into one plane only at the unison or octave, so two parts in parallel thirds stay two planes. These are Fessel's necessary conditions, and the sufficient ones are left to later work. Defined by spec 002; the model is in `core/texture.py`, and the rule is in `analysis/features.py` (`decide_linearity`).

**Local key** (`LocalKey`): the key, tonic and mode, in which the harmonic events of a passage are named as Roman numerals. In spec 003 there is one per phrase, the key whose key profile best correlates with the durations of the pitch classes of the phrase (ADR 0007, reading 9). Defined by spec 003 (003d); not yet implemented.

**Melodic step**: a melodic interval of one or two semitones between adjacent notes of a voice, chromatic steps included and the augmented second excluded (`maximum_melodic_step_semitones`). Not to be confused with step, the letter name of a pitch. Defined by spec 003 (003a); the rule is in `analysis/non_chord_tones.py`.

**Metric weight**: whether an onset is accented. In spec 003 a note is accented when it starts at the onset of a tactus span and unaccented otherwise; beat strength inside the bar is not modeled (ADR 0007, reading 3). Defined by spec 003 (003a); the rule is in `analysis/non_chord_tones.py`.

**Neighbor tone** (`NonChordToneKind.NEIGHBOR`): an unaccented, short non chord tone approached by melodic step and left by step in the opposite direction, back to the same pitch (ADR 0007, reading 5). Defined by spec 003 (003a); the rule is in `analysis/non_chord_tones.py`.

**Non chord tone** (`NonChordTone`): a sounding note, or the part of it from a tactus onset on, that does not belong to the harmony of its window and is removed by harmonic segmentation: a passing tone, neighbor tone, suspension or anticipation in spec 003. Defined by spec 003 (003a); the model is in `core/harmony.py` and the rules are in `analysis/non_chord_tones.py` (`classify_non_chord_tones`).

**Notated voice** (`NotatedVoice`, `Part.voices`): one of the voices written on the staff of a part, as in MusicXML, holding its note events in order of onset with its own rhythm. Most parts have one; a part with two voices on its staff has two. A fact of the notation, not a line.

**Note event** (`NoteEvent`): one notated note or divided chord of a notated voice, with its onset, duration, pitches with their ties, and fermata. Two notes tied together are two note events, not one.

**Onset** (`onset`): the moment an event or bar begins, in quarter lengths from the start of the first bar, as an exact fraction.

**Part** (`Part`): one part of the source score as stored in the file, identified by its position in score order (part 1 is the top one), with its name and instrument name as metadata and one or more notated voices. Ingestion keeps every part; the number and names of the parts never decide the strata (ADR 0004).

**Passing tone** (`NonChordToneKind.PASSING`): an unaccented, short non chord tone approached and left by melodic step in the same direction (ADR 0007, reading 5). Defined by spec 003 (003a); the rule is in `analysis/non_chord_tones.py`.

**Phrase** (`Phrase`): the local domain over which spec 002 computes one textural configuration. In the chorales a phrase ends at a fermata cluster; music with attacks after the last fermata is a last phrase, rests alone join the previous one, and a score without fermatas is one phrase (ADR 0005, a project decision, not Fessel's). Numbered from 1. Defined by spec 002; the model is in `core/texture.py`, and the segmentation is `segment_phrases` in `analysis/phrases.py`.

**Pickup bar**: an incomplete first bar, shorter than its time signature, that leads into the first full bar (also called anacrusis). Its length is given by `Score.pickup_duration()`.

**Pitch class** (`SpelledPitch.pitch_class()`): a pitch without its octave and spelling, as a number from 0 (C) to 11 (B). F sharp and G flat in any octave share pitch class 6.

**Pitch name** (`PitchName`): the step and alter of a pitch without its octave, such as F sharp; it names roots, chord basses and tonics. Defined by spec 003 (003a); the model is in `core/harmony.py`.

**Pitch spelling** (`SpelledPitch`): a pitch written as step, alter and octave, so that enharmonic equivalents such as F sharp and G flat remain different.

**Plane**: in Fessel (1996), an autonomous plane of musical organization distinguished in the simultaneity. In the code, the planes of a `+P` configuration are its children; a plane that is not divided further is a `-P` configuration. Spec 002 treats Fessel's plane (1996) and stratum (2000) as the same domain and keeps "stratum" for a plane with a characterization (open question 8 of spec 002). Defined by spec 002; implemented in `core/texture.py` and `render/textural_schema.py`. The planes of a phrase are ordered by register, highest first, by the mean sounding pitch of the pitches they attack in the phrase, ties broken by the first notated voice; the order is presentation only, since Fessel's configurations are unordered (1996, p. 79).

**Plane note** (`PlaneNote`): the structural note of one plane in a harmonic window: its first chord tone sounding in the window, the lowest of its notated voices for the lowest plane and the highest for the others, with the notated voice it comes from. Voicing reads it. Defined by spec 003 (003a); the model is in `core/harmony.py` and the choice is in `analysis/harmonic_segmentation.py`.

**Planes** ([± planes], P, `TexturalFeatures.planes`): the textural feature that asks whether autonomous planes are distinguished in the simultaneity. `+P` says nothing about how many there are. In the code a configuration is `+P` exactly when it has two or more children. Defined by spec 002; the model is in `core/texture.py`, and the rule is in `analysis/features.py` (`decide_planes`).

**Quarter length**: the unit of every time value in the code: one quarter note equals 1. An eighth note is 1/2 and a triplet eighth is 1/3.

**Reduced verticality**: the chord tones sounding at one attack point of a phrase, after removing non chord tones; the attack of a passing tone, neighbor tone or anticipation is no attack point, since the note is removed (ADR 0007, reading 7); harmonic segmentation merges reduced verticalities into harmonic windows. Defined by spec 003 (003a); the walk is in `analysis/harmonic_segmentation.py`.

**Rest fermata** (`RestFermata`, `NotatedVoice.rest_fermatas`): a fermata written on a notated rest. Rests are otherwise not stored (silence is the time not covered by note events), so a rest that carries a fermata is kept with the onset and duration of the notated rest, always inside a gap between the events of its notated voice. The writers give it exactly that onset and duration and never split it.

**Roman numeral** (`RomanNumeral`, `RomanNumeralMark`): the name of a chord by its degree in the local key, its quality (case and the marks `°`, `ø`, `+`, `M7`) and its inversion figure, such as `V65`; written as a lyric below the bass, because music21 does not export Roman numerals (ADR 0006, ADR 0007 reading 10). One of the two chord names of the reduction. Defined by spec 003 (003d); not yet implemented.

**Root** (`ChordIdentity.root`): the pitch name from which the other pitch names of a chord stack in thirds by letter name. Defined by spec 003 (003b); not yet implemented.

**Round trip**: reading a score into the core model, writing it out and reading the result back, then checking that nothing was lost or altered (`eval/round_trip.py`). It runs through the full score for every score and also through the grand staff for scores of four parts (`RoundTripRoute`).

**Score** (`Score`): a complete piece held in the core model: its bars, its time signatures and its parts in score order.

**Settings** (`TexturalAnalysisSettings`): the typed thresholds of the analysis, each with a name, a unit and its musical meaning. Called settings, never configuration, so that "configuration" always means a textural configuration. Defined by spec 002; in `analysis/settings.py`.

**Silent phrase** (`SilentPhraseError`): a phrase in which no notated voice attacks, so it has no plane and no textural configuration; the analysis refuses it with a domain error. It does not occur in the corpus chorales. Defined by spec 002; raised by `analyze_texture`.

**Soprano**: the highest voice of the four voice harmonic reduction, which takes the structural note of the melody chosen by analysis. It is never a part of the source, even one named Soprano. Concept, not yet implemented.

**Sounding note** (`SoundingNote`): one pitch of a notated voice from its attack to the end of its tie chain, clipped to a phrase; the unit harmonic segmentation classifies. Defined by spec 003 (003a); the model is in `core/harmony.py` and the joining is in `analysis/sounding_notes.py` (`sounding_notes`).

**Staff** (`Staff`): one of the two staves of the grand staff, `Staff.UPPER` or `Staff.LOWER`.

**Staff voice** (`StaffVoice`): a staff of the grand staff and a voice number on it, 1 for the upper voice with stems up and 2 for the lower voice with stems down.

**Step** (`SpelledPitch.step`): the letter name of a pitch, from C to B, without accidental or octave. For stepwise motion the code says melodic step.

**Stream** (`StreamReference`): the unit of sound the textural analysis groups into planes. In spec 002 a stream is one notated voice of one part, identified by part number and voice number, with the part name for labels; a notated voice is never split into several streams. Defined by spec 002; the reference is in `core/texture.py`, and `analysis/attacks.py` lists the streams of a score (`stream_references`).

**Stratum**: a relatively autonomous domain of the texture, such as a melody, a bass, a pedal or a harmonic accompaniment, characterized by its function and its relations with the other strata. Strata form a hierarchy, and their number does not follow from the number of parts or staves (ADR 0004). Concept, not yet implemented.

**Substratum**: an internal subdivision of a stratum, itself a stratum one level lower in the hierarchy. Concept, not yet implemented.

**Suspension** (`NonChordToneKind.SUSPENSION`): an accented non chord tone prepared by the same pitch in its voice (tied over or repeated), dissonant at the tactus onset and resolving down by melodic step; in spec 003 its resolution takes its place from the tactus onset (ADR 0007, reading 6). Defined by spec 003 (003a); the rule is in `analysis/non_chord_tones.py`.

**Tactus** (`tactus_duration`): the time span within which attack divergence is judged (Fessel, 1996). In spec 002 it is the beat of the time signature: a quarter in 4/4 and 3/4, a half in 3/2, a dotted quarter in 6/8 and 12/8 (ADR 0005). Defined by spec 002; implemented in `analysis/metric_grid.py`.

**Tactus span** (`tactus_spans`): one tactus on the bar grid, from a beat to the next. Spans tile each bar from its onset, except a pickup bar, which is tiled from its end so its spans fall on the last beats of a complete bar. Labels count tactus spans from 1 in the virtual complete bar, so the pickup of BWV 66.6 is "bar 0, tactus 4" and the second piece of a bar split in two continues the numbering of the first (`tactus_label`). Defined by spec 002; implemented in `analysis/metric_grid.py`.

**Tenor**: the third voice from the top of the four voice harmonic reduction, chosen by analysis and voicing. It is never a part of the source, even one named Tenor. Concept, not yet implemented.

**Textural configuration** (`TexturalConfiguration`): the organization of the texture in a passage, characterized by the values of the five textural features (Fessel, 1996). Configurations form a tree: a `+P` configuration has two or more subordinate configurations, its planes, and a `-P` configuration is a leaf that groups one or more streams. Applying the analysis recursively gives global and partial configurations, the basis of the granularity levels. Defined by spec 002; implemented in `core/texture.py` and `render/textural_schema.py`.

**Textural feature** (`TexturalFeature`): one of the five binary features of Fessel (1996) that combine to characterize a textural configuration: planes (P), homogeneity (H), linearity (L), accent coincidence (C) and attack divergence (D). Each takes a positive or negative value; L is left unspecified on `+P` configurations. Defined by spec 002; implemented in `core/texture.py` and `render/textural_schema.py`.

**Textural schema** (`format_textural_schema`): the rendering of the analysis as a hierarchy of strata with their characterization and relations, and how they change over time; one of the two renderings of the analysis, with the harmonic reduction. Spec 002 renders it as text, per phrase, in the indented form and the compact form, through `aretz-texture schema`. Defined by spec 002; the rendering is in `render/textural_schema.py`, and the command is `aretz-texture schema SOURCE [--explain]` in `cli.py`.

**Tie** (`TieType`): a curved line joining two notes of the same pitch so they sound as one. Each event pitch records its place in the tie: `START`, `CONTINUE` or `STOP`, or none.

**Time signature** (`TimeSignatureChange`): the meter written at the start of a staff, stored once for the whole score as numerator and denominator with the onset where it takes effect.

**Time span** (`TimeSpan`): a stretch of the score from an onset to a later end, in quarter lengths from the start of the first bar; the span of a phrase and of every node of its textural configuration. Defined by spec 002; implemented in `core/texture.py`.

**Unidentified sonority** (`UnidentifiedSonority`): the reading of a harmonic window whose chord tones are outside the chord vocabulary, such as an augmented sixth chord or an open fifth, with the reason. A reading, not an error: it has no chord symbol and its Roman numeral is `?`. Defined by spec 003 (003b); not yet implemented.

**Unsupported texture** (`UnsupportedTextureError`): a score that is analyzed and named but that voicing cannot reduce, because some phrase does not have exactly four planes (spec 003). Defined by spec 003 (003c); not yet implemented.

**Verticality**: everything sounding at one moment of the score across all notated voices; the starting point of harmonic segmentation (architecture, section 3).

**Voice**: one of the four lines of the harmonic reduction (soprano, alto, tenor, bass), produced by voicing. Not to be confused with a notated voice of the source or with a line in Fessel's sense.

**Voiced chord** (`VoicedChord`): one chord of the harmonic reduction: a time span, the pitch of each of the four voices or a rest, and whether it carries a fermata. Defined by spec 003 (003c); not yet implemented.

**Voicing**: the choice of which pitch each of the four voices of the harmonic reduction takes in a chord (architecture, section 7; package `voicing/`). In spec 003, for textures of four planes, each voice takes the plane note of one plane (`voice_from_planes`).
