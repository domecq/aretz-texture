import pytest
from hypothesis import assume, given
from hypothesis import strategies as st
from pydantic import ValidationError
from tests.core.test_texture import satisfies_restrictions
from tests.strategies import textural_configurations

from aretz_texture.core.texture import FeatureDecision, TexturalConfiguration, TexturalFeatures

FEATURE_NAMES = ("planes", "homogeneity", "linearity", "accent_coincidence", "attack_divergence")


def all_nodes(node: TexturalConfiguration) -> list[TexturalConfiguration]:
    return [node, *(below for child in node.children for below in all_nodes(child))]


def values_of(features: TexturalFeatures) -> list[bool | None]:
    return [getattr(features, name).value for name in FEATURE_NAMES]


def with_value(
    features: TexturalFeatures, name: str, value: bool | None
) -> dict[str, FeatureDecision]:
    fields: dict[str, FeatureDecision] = {
        feature: getattr(features, feature) for feature in FEATURE_NAMES
    }
    old = fields[name]
    fields[name] = FeatureDecision(value=value, rule=old.rule, explanation=old.explanation)
    return fields


@given(textural_configurations())
def test_every_generated_tree_satisfies_the_restrictions_at_every_node(
    tree: TexturalConfiguration,
) -> None:
    assert all(satisfies_restrictions(*values_of(node.features)) for node in all_nodes(tree))


@given(
    textural_configurations(),
    st.data(),
)
def test_changing_one_feature_to_a_forbidden_combination_raises_validation_error(
    tree: TexturalConfiguration, data: st.DataObject
) -> None:
    node = data.draw(st.sampled_from(all_nodes(tree)))
    name = data.draw(st.sampled_from(FEATURE_NAMES))
    new_value = data.draw(st.sampled_from([True, False, None]))
    fields = with_value(node.features, name, new_value)
    mutated = [fields[feature].value for feature in FEATURE_NAMES]
    assume(not satisfies_restrictions(*mutated))
    with pytest.raises(ValidationError):
        TexturalFeatures(**fields)
