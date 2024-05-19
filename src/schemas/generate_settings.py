from typing import Literal
from pydantic import BaseModel


class inputs_float_dict(BaseModel):
    name: str
    value: float


class inputs_str_dict(BaseModel):
    name: str
    value: str


class text_setting(BaseModel):
    inputs: inputs_str_dict


class slider_setting(BaseModel):
    inputs: inputs_float_dict
    range: list[float]


class OptionalSetting(BaseModel):
    id: str
    type: Literal["text", "slider"]
    params: text_setting | slider_setting


class GenerateSettings(BaseModel):
    denoising_strength: float
    prompt: str
    negative_prompt: str
    seed: int
    target_resolution: int
    optional_settings: dict[str, OptionalSetting]
