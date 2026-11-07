# Glossary

This glossary defines each musical term as the code of Aretz Texture uses it. Identifiers in the code must use these names; if a term is missing, add it here in the same pull request that introduces it (AGENTS.md, "Names"). Where a term has a code identifier, it is shown in backticks.

**Alter** (`SpelledPitch.alter`): the number of semitones an accidental moves a note away from its natural step: -2 double flat, -1 flat, 0 natural, 1 sharp, 2 double sharp.

**Alto** (`VoiceRole.ALTO`): the second voice from the top in a four voice texture. On the grand staff it is the lower voice of the upper staff.

**Bar** (`Bar`): a measure of the score, with the number shown in the score, its onset and its actual duration. The code says bar, never measure, except when naming music21 objects.

**Bass** (`VoiceRole.BASS`): the lowest voice in a four voice texture. On the grand staff it is the lower voice of the lower staff.

**Beat** (`Omission.beat`): the position of a note within its bar as a musician counts it, starting at 1 and taking a pickup bar into account. Used only to locate notes in reports.

**Divided event**: a note event with more than one pitch, written as a chord inside one voice, such as a bass dividing into octaves on a final chord. All its pitches share onset, duration and fermata; each keeps its own tie.

**Duration** (`NoteEvent.duration`, `Bar.duration`): how long an event or bar lasts, in quarter lengths, as an exact fraction.

**Event pitch** (`EventPitch`): one pitch of a note event together with its tie.

**Extra part** (`OmissionReason.EXTRA_PART`): a part of the source that was not chosen as one of the four voices, such as an instrumental part doubling the choir.

**Fermata** (`NoteEvent.fermata`): a pause sign over or under a note, which in chorales marks the end of a phrase. Stored as a property of the note event.

**Grand staff** (`GrandStaffLayout`): the two staff system of piano music, an upper staff in treble clef for the right hand and a lower staff in bass clef for the left hand, joined by a brace. `PIANO_LAYOUT` places soprano and alto on the upper staff and tenor and bass on the lower one.

**Harmonic information**: the set of pitch classes sounding at each instant of the score. Ingestion may drop notes, but never harmonic information without reporting it.

**Harmonic window** (`HarmonicWindow`): a span of time over which a single harmony is considered to hold, the result of merging verticalities in harmonic segmentation (architecture, section 3).

**Key signature** (`KeySignatureChange`): the sharps or flats written at the start of a staff, stored as a signed count of sharps (negative for flats) with the onset where it takes effect.

**Lossy omission** (`Omission.removes_pitch_class`): an omission whose pitch class is not sounded by any of the four kept voices at some instant within its span, so dropping it removes harmonic information.

**Note event** (`NoteEvent`): one notated note or divided chord of a voice, with its onset, duration, pitches with their ties, and fermata. Two notes tied together are two note events, not one.

**Omission** (`Omission`, `OmissionReason`): an element of the source that ingestion did not carry into the score, such as a note of an extra part or a grace note. Every omission is reported with its part, bar, beat and pitch.

**Onset** (`onset`): the moment an event or bar begins, in quarter lengths from the start of the first bar, as an exact fraction.

**Part**: one line of the source score as stored in the file, such as the soprano part of a chorale. Ingestion maps four parts to the four voices, by score order or, when there are more than four parts, by name; the code keeps the word part for the source file only.

**Pickup bar**: an incomplete first bar, shorter than its time signature, that leads into the first full bar (also called anacrusis). Its length is given by `FourVoiceScore.pickup_duration()`.

**Pitch class** (`SpelledPitch.pitch_class()`): a pitch without its octave and spelling, as a number from 0 (C) to 11 (B). F sharp and G flat in any octave share pitch class 6.

**Pitch spelling** (`SpelledPitch`): a pitch written as step, alter and octave, so that enharmonic equivalents such as F sharp and G flat remain different.

**Quarter length**: the unit of every time value in the code: one quarter note equals 1. An eighth note is 1/2 and a triplet eighth is 1/3.

**Round trip**: reading a score into the core model, writing it out and reading the result back, then checking that nothing was lost or altered (`eval/round_trip.py`).

**Score** (`FourVoiceScore`): a complete piece held in the core model: its bars, key and time signatures and its four voices.

**Soprano** (`VoiceRole.SOPRANO`): the highest voice in a four voice texture, usually carrying the melody. On the grand staff it is the upper voice of the upper staff.

**Staff** (`Staff`): one of the two staves of the grand staff, `Staff.UPPER` or `Staff.LOWER`.

**Step** (`SpelledPitch.step`): the letter name of a pitch, from C to B, without accidental or octave.

**Tenor** (`VoiceRole.TENOR`): the third voice from the top in a four voice texture. On the grand staff it is the upper voice of the lower staff.

**Tie** (`TieType`): a curved line joining two notes of the same pitch so they sound as one. Each event pitch records its place in the tie: `START`, `CONTINUE` or `STOP`, or none.

**Time signature** (`TimeSignatureChange`): the meter written at the start of a staff, stored as numerator and denominator with the onset where it takes effect.

**Voice** (`Voice`, `VoiceRole`): one of the four lines of the texture (soprano, alto, tenor, bass), holding its note events in order of onset. Within a voice, events never overlap.

**Voicing**: the choice of which pitch each of the four voices takes in a chord (architecture, section 6; package `voicing/`).
