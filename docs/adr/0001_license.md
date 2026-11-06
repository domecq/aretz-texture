# ADR 0001: License

Date: November 5, 2026
Status: Accepted

## Context

The repository will be public from the first commit, so it needs a license before the first push. A public repository without a license keeps all rights reserved: anyone can read the code, but nobody can legally reuse it.

Before choosing, the commercial potential of the project was evaluated (October 2026):

* Notation software (Sibelius, Dorico, Finale) offers reduction functions that merge staves mechanically, without musical judgment. Automatic reduction remains an open research problem.
* Harmonic analysis from MusicXML already exists in several open source projects, some with an architecture very close to this one. The differentiators of this project are the reduction of real textures, the representative rhythm and the granularity levels.
* The main commercial barrier is input: students rarely have the MusicXML of the pieces they study.
* Commercial potential as complementary income exists but is modest.

Based on this, the project is positioned as a **free tool for education and for musicians**.

Options considered: MIT, Apache 2.0 and AGPLv3.

## Decision

The project is released under the **MIT License**.

## Rationale

* A free educational tool benefits most from maximum adoption by students, teachers and institutions.
* MIT is the most widely used open source license and the one the maintainer knows best. It creates no friction for anyone who wants to use or integrate the code.
* It is compatible with the main dependency: music21 is released under the BSD 3 clause license.
* The decision is reversible for future code. As sole copyright holder, the maintainer can change the license of new code later, as Grafana and Synapse did when they moved from Apache 2.0 to AGPLv3.

## Consequences

* Anyone can use, modify and integrate the code, including in closed products, as long as the copyright and license notice are kept.
* Versions published under MIT remain under MIT permanently. If the license changes in the future, earlier versions can still be forked.
* External contributions under MIT can be incorporated into code under a different license later, as long as their notice is kept, so no contributor license agreement is required.
* Scores protected by copyright stay out of the repository. Only public domain material and the music21 corpus (which ships with the library) are used in tests.
