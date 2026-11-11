# Journal: corpus evaluation, grace notes and fermatas on rests

Dates: November 10 and 11, 2026
Phase: F1, specs 001c and 001d

## Goal

Close spec 001: compare every corpus chorale with what the tool writes and reads back through both routes (001c), then keep the grace notes and fermatas on rests that ingestion still rejected (001d).

## What happened

### Facts before delegation

* Before handing each delivery to the `implementer`, the main session ran a prototype over the corpus and probed music21 directly, and passed the results to the agent as verified facts. The prototype of 001c already showed the expected result: no chorale different through either route, two unsupported chorales (the grace notes of BWV 299 and BWV 315) and 22 skips of the grand staff route.
* Nineteen of those skips are chorales with more than four parts. The other three (BWV 244.15, BWV 62.6 and BWV 4.8) have four parts, but in the corpus encoding the soprano has another key signature than the other three parts. The pitches of the four parts agree with each other, since the soprano carries explicit accidentals, so this looks like an encoding problem of the corpus. The full score keeps them as they are; the grand staff cannot write two key signatures on one staff, so the three are listed with their reason.

### 001c: the evaluation

* `eval/round_trip.py` compares scores level by level and records every difference with its route, part, notated voice and bar. One slow test computes the 350 results once and checks criteria 27 to 29. The two committed lists make any change of outcome visible. CI now takes about four minutes.
* Codex found no problem.
* The `implementer` reported, unprompted, that test first was partial: the comparison and round trip tests were seen failing first, but the hypothesis properties and the corpus tests were written after the code and passed on their first run.

### 001d: grace notes and fermatas on rests

* The three grace notes of the corpus are all in the soprano, written as eighths with a slash before the main note. They are now kept as `GraceNote` values next to the events, and fermatas on rests as `RestFermata` values. All 350 chorales are now supported and identical through both routes; the list of unsupported chorales is empty.
* Extending the hypothesis strategies to generate both found, on their first run, that music21 merges three consecutive fermata rests of triplet eighths into one quarter rest. The writers now keep those rests as written.
* Two limits remain, both outside the corpus and left for Nico to decide: a fermata rest of exactly a whole or a breve in a bar of another length, alone in its measure, which music21 stretches to the whole bar on reading (the same behavior found in 001b, now without the option of splitting the rest); and a grace note with nothing after it in its bar. Both raise `UnsupportedScoreError`.

## Notes for the article

* Handing the agent verified facts and an expected result turned the slow corpus test into a confirmation instead of a discovery. Discoveries still came, but from the property based tests, where they belong.
* The partial test first report repeated the pattern of 001a. The rule holds where the agent can see a test fail (new names, new behavior) and slips where the code already exists and the new test passes at once. Writing the property and the corpus test before the code would have turned each into a real check.
* A difference in the source looked like a bug in the tool until the pitches were checked part by part. Telling an encoding error of the corpus from an error of the tool required looking at the music, not only at the counts.
