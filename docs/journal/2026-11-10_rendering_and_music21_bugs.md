# Journal: piano rendering, music21 bugs and the first manual check

Dates: November 9 and 10, 2026
Phase: F1, spec 001b

## Goal

Render four part scores on a piano grand staff, add the `piano` command, and check the result by eye in Sibelius.

## What happened

### A pull request split by its own size limit

* The `implementer` stopped by itself when 001b passed the review size limit of about 1500 lines, as instructed, instead of opening one large pull request. Its commits were already layered, so the work was split into two stacked pull requests: grand staff layout and full score writer (#10), then piano score, reader and command (#12).
* Codex found no problem in #10.

### Two bugs in music21, found by property based tests

* While preparing the second half, the hypothesis property of the full score round trip failed on a random example that had not come up in the CI run of #10. Two minimized cases showed that music21 10.5.2 changes the length of a bar when it reads back a file it wrote: it does not count chords when it decides whether a measure is a whole bar rest, and it stretches the first rest of a measure when another voice holds a whole bar rest.
* Both were confirmed in the music21 source, also in 11.0.0b14. The writers now avoid both cases, in one shared module (`render/rests.py`). The model stores no rests, so no musical content changes. Each case got a regression test written first and seen failing, and 300 extra random examples of each round trip passed.
* A report for music21 was drafted with minimal reproductions that use only music21; Nico files it from his account. The closest existing issue (#1633) is a different problem.

### The manual check

* Nico opened the piano output of BWV 66.6 in Sibelius. Everything matched the original except one difference: a natural on an E in the fifth bar as Sibelius counts it, which the original does not have.
* The pitches were right. The bar is bar 4 in the file, since the pickup is bar 0. The alto's E sharp 4 in bar 3 and the soprano's E4 in bar 4 now share the upper staff, so music21 adds a courtesy natural, as a copyist would in a piano reduction. Nico decided to keep it (decision 16).

## Notes for the article

* Property based tests found bugs in a mature dependency that no hand written test would have targeted, and the agent could trace them to specific lines of its source. A random test that passes once is not proof: the same property found the bug on its next run.
* The size limit worked because the agent obeyed it and said so, not because a tool enforced it.
* The musician's eye caught the only visible difference in the output within minutes. It was not an error, but only a musician could decide whether it was acceptable.
