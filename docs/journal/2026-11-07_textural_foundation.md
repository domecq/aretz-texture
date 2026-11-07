# Journal: first spec and a theoretical foundation

Date: November 7, 2026
Phase: F1, before any implementation

## Goal

Write the first specification (issue #7): read a Bach chorale and write it back as a piano score that Nico can open in Sibelius, as a thin slice through ingestion, core model and rendering.

## What happened

### The first spec, from the architect agent

* The issue was written in musical language, and the `architect` subagent turned it into spec 001, ADR 0003 (music21 allowed in `ingest/` and `render/`, music21 and pydantic as dependencies) and a first glossary.
* The agent could not install music21, so several facts in its draft were marked as unconfirmed. The main session checked them against music21 10.5.2: licenses, the key signature of BWV 66.6, the type returned by the corpus iterator, the `py.typed` marker. Delegating the writing did not remove the need to verify it.
* Nico answered seven musical questions: keep fermatas, leave lyrics for later but treat them as a requirement, repeats later, no staff names, cautionary accidentals may be lost, and the command is called `piano` until the tool actually reduces.
* His answer on scores with more than four parts set the tone: no harmonic information may be lost by elimination, and anything dropped must be listed. The agent proposed an omission criterion, and a survey of the corpus grounded it in data: 351 of 371 chorales have four parts, 20 have between 5 and 15, mostly instruments doubling the voices, and one (BWV 27.6) has five real voices.

### A CI failure that pre-commit did not catch

* The spec contains Python code blocks. ruff also formats code blocks inside Markdown, and CI runs `ruff format --check .` over the whole repository, while the pre-commit hook only looked at Python files. The commit passed locally and failed in CI.
* The pre-commit hook now checks Markdown too. Layer 4 caught a gap between layers 3 and 4, which is what it is there for.

### From isolated decisions to a model

* Reviewing the omission criterion, Nico pointed out that answering musical questions one at a time would not give the product a coherent musical view. He proposed basing the analysis on Pablo Fessel's model of textural strata, which he agrees with and which matches, in a more structured form, what he had in mind. He wrote study notes with sources (`docs/theory/`).
* The model's central principle, that the number of parts or staves does not determine the number of strata, showed that the omission criterion was wrong in kind: choosing Soprano, Alto, Tenor and Bass by name at ingestion decided about the texture before analyzing it.
* Decisions (ADR 0004): the analysis is based on Fessel's model; ingestion keeps every part without loss; the product delivers two renderings of one analysis, a textural schema and the four voice harmonic reduction. The project description and README now credit Fessel's work.
* Spec 001 was paused (its pull request back to draft) and rewritten on that basis: lossless ingestion of any number of parts, piano rendering only for four part scores until the textural analysis exists. The questions about which part to drop disappeared instead of being answered.
* Bibliographic data of the 1996 and 2000 articles were checked again against their repositories.

## Open items

* Approve ADR 0004 and the rewritten spec 001 (gate 1, by merging their pull request).
* Initial weights of the association and dissociation factors, and how to notate the textural schema.
* Dynamics are needed later for the intensity factor.

## Notes for the article

* The most important decision of the day did not come from the agents. They answered each question competently, but only the musician noticed that the questions themselves lacked a frame. Agents optimize locally; a domain expert decides what the whole should mean.
* A theory chosen early is cheaper than a theory retrofitted: the switch cost one spec rewrite, before any analysis code existed.
* Nico plans to show the finished work to Pablo Fessel. The project may open a line of academic research alongside the tool, which is one more reason to keep the attribution precise: the docs separate what Fessel wrote from the project's own didactic adaptation of it.
