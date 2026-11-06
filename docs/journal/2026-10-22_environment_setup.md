# Journal: environment setup and first music21 spike

Date: October 22, 2026 (includes notes from October 17)
Phase: F0, before the repository exists

## Goal

Prepare the local environment and confirm, under musical supervision, that music21 produces correct results before adopting it as the base of the project.

## What happened

### First exposure to music21, with musical supervision

This was the first contact with the library, so the goal was not only to run it but to see how it works and whether its output can be trusted.

* Parsed chorale BWV 66.6 from the music21 corpus, ran `chordify()` and exported both the original and the chordified version as MusicXML.
* Nico reviewed both files in Sibelius as a musician, comparing the chordified version against the original chorale. He checked accidentals, ties and rhythm; all three were correct.
* Why this matters: the whole architecture rests on music21 for ingestion and harmonic analysis, and the Bach chorales are the main regression test. Before writing any infrastructure, a human with musical judgment confirmed that the library reads the chorale faithfully.
* Note for F1: `chordify()` slices at every attack in any voice, so passing tones in inner voices show up as chords of their own. The gap between raw verticalities and actual harmonic changes is exactly what the harmonic segmentation step has to close.

### Choosing tools

* Chose uv to manage the environment instead of the previous package managers. uv replaces pip, venv, pyenv and pipx with a single tool and pins the Python version per project.
* Evaluated Abjad as an alternative to music21 and discarded it as the base. Abjad builds LilyPond files for engraving and is oriented toward composition; it does not import MusicXML, has no harmonic analysis and ships no corpus. It remains a candidate for an optional engraved PDF renderer.

### Environment friction on macOS 14 (to review: may not belong in the article)

* Installing uv with Homebrew first failed because the Command Line Tools were older than the installed macOS. Reinstalling them fixed that error.
* The next attempt failed because Homebrew no longer builds bottles for macOS 14 and treats it as a Tier 3 configuration, so it tried to compile the dependency chain from source. The build failed while compiling z3.
* Switched to the official uv installer, which ships a precompiled binary and depends on neither Homebrew nor the Command Line Tools.

### Decisions

* Package name: `textural_reduction`.
* Everything in English: code, comments, docstrings, documentation, specs, ADRs and this journal. The existing design documents were translated.

## Open items

* Update the Command Line Tools to the version Homebrew recommends (Xcode 16.2).
* Remove or renew the expired `HOMEBREW_GITHUB_API_TOKEN`.
* Pending F0 decisions: public or private repository (branch protection on private repositories requires a paid GitHub plan), Codex availability for external review, Claude Code installation.
* Choose between a `src/` layout and a top level package (candidate for an ADR).

## Notes for the article

* Human musical supervision came first, before any automated test existed: the musician validated the library before the pipeline was built to depend on it.
* The language policy was set before any code existed, so changing it cost only a document translation.
