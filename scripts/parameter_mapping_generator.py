"""
A helper Python script to create a dict that contains the mappings between the various assays
that the proteomics pipeline can run, and the unique parameter files that each of the assays
requires.
"""

from pathlib import Path
from typing import Any

from pydantic import (
    BaseModel, ConfigDict, AliasGenerator, ValidationError, field_validator,
)

TEMPLATE_DIR = Path(__file__).parent.parent / "inputs/templates/msgfplus"


class CromwellInputFile(BaseModel):
    model_config = ConfigDict(
        # Removes "proteomics_msgfplus." during field generation
        alias_generator=AliasGenerator(
            validation_alias=lambda field_name: f"proteomics_msgfplus.{field_name}"
        ),
    )


class DockerImages(CromwellInputFile):
    ascore_docker: str | None = None
    masic_docker: str
    msconvert_docker: str
    msgf_docker: str
    mzidtotsvconverter_docker: str
    phrp_docker: str
    ppm_errorcharter_docker: str
    wrapper_docker: str

    @field_validator("*")
    @classmethod
    def remove_prefix(cls, data: Any) -> str:
        """Removes the gcp-parameters/ prefix during field value validation."""
        if isinstance(data, str):
            if "docker-repository" in data:
                return data.replace(
                    "docker-repository", "us-docker.pkg.dev/motrpac-portal/proteomics"
                )
        return data


class RawInputsFile(CromwellInputFile):
    ascore_parameter_p: str | None = None
    masic_parameter: str
    msgf_identification_parameter: str
    msgf_tryptic_mzrefinery_parameter: str
    phrp_parameter_m: str
    phrp_parameter_n: str
    phrp_parameter_t: str

    @field_validator("*")
    @classmethod
    def remove_prefix(cls, data: Any) -> str:
        """Removes the gcp-parameters/ prefix during field value validation."""
        if isinstance(data, str):
            if "gcp-parameters" in data:
                return data.replace("gcp-parameters/", "")
        return data


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
