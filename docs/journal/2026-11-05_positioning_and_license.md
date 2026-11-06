# Journal: product positioning, license and name

Date: November 5, 2026 (includes the market research from October 22)
Phase: F0, before the repository exists

## Goal

Decide whether the repository starts public or private, which requires deciding the license, which in turn requires deciding whether the project has commercial ambitions. Then give the project its final name before creating the repository.

## What happened

### Public or private

* Chose a public repository from the first commit. The journal, the PRs and the reviews are the process the article will describe, and a public history makes that verifiable.
* Technical reasons pointed the same way: on GitHub Free, branch protection and rulesets are only available for public repositories, and the CI quality gate depends on them.
* Making a private repository public later does not hide anything: the whole history is published at that moment.

### Commercial potential

Market research before choosing a license:

* Notation software offers reduction functions that merge staves mechanically. Users in composer forums report that no commercial tool produces a musically intelligent reduction.
* Academic research treats automatic piano reduction as an open problem, partly because there are no datasets pairing ensemble scores with their reductions.
* Harmonic analysis from MusicXML is already available in several open source projects. One of them combines music21, a Viterbi style dynamic programming step for SATB voicing and an optional LLM explainer that never changes the labels: almost the same architecture as this project.
* The main barrier for a commercial product is input: students rarely have MusicXML files.

Conclusion: commercial potential as complementary income exists but is modest. The project is positioned as a free tool for education and for musicians.

### Product framing

* Nico's own motivation as a former student: point a tool at a MusicXML file and get the reduction with its chords, saving a lot of preliminary analysis.
* Tension identified: what saves a student time can look like a shortcut to a teacher. Framing the tool as "check your analysis" or "start from the structure" makes it usable in class. The granularity levels support this: a teacher can show level 4 and ask students to complete level 2.

### License

* Chose MIT (ADR 0001). It is the most widely used open source license, the one Nico knows best, and the best fit for maximum adoption of a free educational tool.
* AGPL was considered (Grafana, Synapse and Mastodon use it), but it mainly protects projects sold as a service. Since Nico is the sole author, the license of future code can still change.

### Layout

* Chose the `src/` layout (ADR 0002), so tests always run against the installed package.

### Name

* The working name was Textural Reduction (`textural_reduction`).
* Nico first proposed Béla Texture, as a homage to Béla Bartók. It was dropped because Bela is already an established open source music technology platform, born at Queen Mary University of London and used in education, so the name would compete for the same audience and the same searches.
* Final name: **Aretz Texture** (`aretz_texture`), in honor of Isabel Aretz, Argentine and Venezuelan composer and ethnomusicologist. No software with that name was found.
* The homage keeps a link with the first idea: like Bartók, Aretz was a composer who collected and analyzed folk music.

## Notes for the article

* The market research found near copies of the planned architecture, built recently and in the open. With agents, the generic part of an idea is cheap to replicate; the value moves to musical judgment and to the parts nobody else has solved.
* The order of decisions mattered: visibility depended on the license, and the license depended on the business intent. Answering them in the wrong order would have forced rework.
* Naming was checked against existing projects before creating the repository. Renaming after the first push would have meant changing the package, the repository and every document.
