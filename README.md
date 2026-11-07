# Aretz Texture

An analysis tool for musicians that reads a MusicXML score, describes how its texture is organized and reduces its harmonic structure to four voices.

The analysis is based on **Pablo Fessel's model of textural strata** (Fessel, 1996; Fessel, 2000): texture as a hierarchy of relatively autonomous strata, characterized by explicit features and by the factors that make sounds form a line. A key principle of the model guides the tool: the number of instruments or staves does not determine the number of strata. See [`docs/theory/fessel_textural_model.md`](docs/theory/fessel_textural_model.md).

The tool aims to deliver two views of one analysis:

* a **textural schema**: the strata of each passage, their characterization and their relations;
* a **four voice harmonic reduction** on a piano system, in harmonic rhythm or in the representative rhythm of the piece.

The analysis is deterministic and explains the reading it chose, so a musician can check it and disagree with it. The tool is meant for understanding structure, not for producing a version to perform.

## Status

Early development. The first slice reads a Bach chorale and writes it back as a piano score ([spec 001](docs/specs/001_chorale_round_trip.md)).

## Documentation

* [Architecture](docs/architecture.md)
* [Theoretical foundation](docs/theory/fessel_textural_model.md)
* [Architecture decision records](docs/adr/)
* [Specifications](docs/specs/)
* [Domain glossary](docs/glossary.md)
* [Development pipeline with agents](docs/agent-pipeline.md)
* [Process journal](docs/journal/)

## Development

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```
uv sync
uv run pre-commit install
uv run pre-commit run --all-files
```

Conventions for humans and agents are in [`AGENTS.md`](AGENTS.md).

## References

Fessel, P. (1996). Hacia una caracterización formal del concepto de textura. *Revista del Instituto Superior de Música*, (5), 75–93. https://doi.org/10.14409/ism.v1i5.514

Fessel, P. (2000). Condiciones de linealidad en la música tonal. *Arte e Investigación*, *4*(4), 84–89. https://sedici.unlp.edu.ar/handle/10915/18668

## Name and license

Named in honor of Isabel Aretz (1909 to 2005), Argentine and Venezuelan composer and ethnomusicologist, who collected, analyzed and taught the folk music of the Americas.

Released under the [MIT License](LICENSE).
