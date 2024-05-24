"""
A helper Python script to create a dict that contains the mappings between the various assays
that the proteomics pipeline can run, and the unique parameter files that each of the assays
requires.
"""

from pathlib import Path
from typing import Any, Annotated

from pydantic import BaseModel, ConfigDict, AliasGenerator, ValidationError
from pydantic.functional_validators import BeforeValidator

TEMPLATE_DIR = Path(__file__).parent.parent / "inputs/templates/msgfplus"


def remove_prefix(v: Any) -> str:
    """Removes the gcp-parameters/ prefix during field value validation."""
    if isinstance(v, str):
        if "gcp-parameters" in v:
            return v.replace("gcp-parameters/", "")
    return v


class RawInputsFile(BaseModel):
    model_config = ConfigDict(
        # Removes "proteomics_msgfplus." during field generation
        alias_generator=AliasGenerator(
            validation_alias=lambda field_name: f"proteomics_msgfplus.{field_name}"
        ),
    )

    ascore_parameter_p: Annotated[str | None, BeforeValidator(remove_prefix)] = None
    masic_parameter: Annotated[str, BeforeValidator(remove_prefix)]
    msgf_identification_parameter: Annotated[str, BeforeValidator(remove_prefix)]
    msgf_tryptic_mzrefinery_parameter: Annotated[str, BeforeValidator(remove_prefix)]
    phrp_parameter_m: Annotated[str, BeforeValidator(remove_prefix)]
    phrp_parameter_n: Annotated[str, BeforeValidator(remove_prefix)]
    phrp_parameter_t: Annotated[str, BeforeValidator(remove_prefix)]


class QuantMethodMap(BaseModel):
    lf: RawInputsFile
    tmt11: RawInputsFile
    tmt16: RawInputsFile
    tmt18: RawInputsFile


class ParameterMap(BaseModel):
    pr: QuantMethodMap
    ph: QuantMethodMap
    ac: QuantMethodMap
    ub: QuantMethodMap


def parse_inputs_file(inputs_file_path) -> tuple[tuple[str, str], RawInputsFile]:
    """Parses a Cromwell inputs file to the BaseModel"""
    split_fn = (
        inputs_file_path.name.removeprefix("config-msgfplus-")
        .removesuffix(".json")
        .split("-")
    )
    exp_quant_comb = (split_fn[0], split_fn[1])
    with inputs_file_path.open("r") as f_obj:
        try:
            validated_model = RawInputsFile.model_validate_json(f_obj.read())
        except ValidationError as err:
            print(f"Error while parsing {inputs_file_path}")
            raise err

    return exp_quant_comb, validated_model


def main() -> None:
    """Run the script"""
    file_templates = {}
    for p in TEMPLATE_DIR.glob("*.json"):
        k, v = parse_inputs_file(p)
        file_templates[k] = v

    parameter_mapping = ParameterMap(
        **{
            # here we build the experiments mapping
            experiment: QuantMethodMap(
                **{
                    # and for each experiment, we build the methods mapping
                    method: file_templates[(experiment, method)]
                    for method in ["lf", "tmt11", "tmt16", "tmt18"]
                }
            )
            for experiment in ["pr", "ph", "ac", "ub"]
        }
    )

    print(parameter_mapping.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
