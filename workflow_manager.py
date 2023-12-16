from pydantic import BaseModel
from typing import Optional, Literal
from PIL import Image
from util import pil_to_base64
import numpy as np
import random
import json

NODE_NAME_LIST = [
    "CheckpointLoaderSimple",
    "KSampler",
    "CLIPTextEncode",  # Allow more than 2
    "ETN_LoadImageBase64",  # Allow more than 2
    "ControlNetApplyAdvanced",
]
ALLOW_MULTIPLE_NODES = ["CLIPTextEncode", "ETN_LoadImageBase64"]


class GenerateSettings(BaseModel):
    ckpt_name: str
    prompt: str = "1girl"
    negative_prompt: str = ""
    denoising_strength: float = 1.0
    control_strength: float = 1.0
    seed: int = -1
    sampler_name: str = "lcm"


class WorkflowManager:
    def __init__(self, workflow_path):
        self.load_workflow(workflow_path)

    def create(
        self,
        input_img: Image.Image,
        control_img: Optional[Image.Image],
        generate_settings: GenerateSettings,
    ):
        self._workflow[self._node_id_dict["CheckpointLoaderSimple"]]["inputs"][
            "ckpt_name"
        ] = generate_settings.ckpt_name
        if generate_settings.seed == -1:
            seed = random.randint(0, 100000)
        else:
            seed = generate_settings.seed
        self._workflow[self._node_id_dict["KSampler"]]["inputs"]["seed"] = seed
        self._workflow[self._node_id_dict["KSampler"]]["inputs"][
            "denoise"
        ] = generate_settings.denoising_strength

        # set prompt
        self._workflow[self._get_prompt_node_id("positive")]["inputs"][
            "text"
        ] = generate_settings.prompt
        self._workflow[self._get_prompt_node_id("negative")]["inputs"][
            "text"
        ] = generate_settings.negative_prompt

        # input img
        self._workflow[self._get_input_img_node_id("input")]["inputs"][
            "image"
        ] = pil_to_base64(input_img)

        if "ControlNetApplyAdvanced" in self._node_id_dict.keys():
            # control input img
            print('in workflow')
            print(type(control_img))
            if control_img is not None:
                self._workflow[self._get_input_img_node_id("control")]["inputs"][
                    "image"
                ] = pil_to_base64(control_img)
            else:
                self._workflow[self._get_input_img_node_id("control")]["inputs"][
                    "image"
                ] = pil_to_base64(input_img)
            self._workflow[self._node_id_dict["ControlNetApplyAdvanced"]][
                "inputs"
            ]["strength"] = generate_settings.control_strength
        return self._workflow

    def load_workflow(self, workflow_path: str):
        with open(workflow_path, "r") as f:
            self._workflow = json.load(f)
        self._node_id_dict = create_node_dict(self._workflow)

    def _get_prompt_node_id(self, input_type: Literal["positive", "negative"]):
        # if use controlnet, LIPTextEncode connected to ControlNetApplyAdvanced
        if "ControlNetApplyAdvanced" in self._node_id_dict.keys():
            start_from = "ControlNetApplyAdvanced"
        else:
            start_from = "KSampler"
        if input_type == "positive":
            return self._detect_node_id(
                start_from, "positive", "CLIPTextEncode"
            )
        elif input_type == "negative":
            return self._detect_node_id(
                start_from, "negative", "CLIPTextEncode"
            )
        else:
            raise ValueError("input_type must be 'positive' or 'negative'.")

    def _get_input_img_node_id(self, input_type: Literal["input", "control"]):
        if input_type == "input":
            return self._detect_node_id(
                "KSampler", "latent_image", "ETN_LoadImageBase64"
            )
        elif input_type == "control":
            return self._detect_node_id(
                "ControlNetApplyAdvanced", "image", "ETN_LoadImageBase64"
            )
        else:
            raise ValueError("input_type must be 'input' or 'control'.")

    def _detect_node_id(self, start_from: str, input_key: str, node_name: str):
        # only one input img node case.
        if node_name in self._node_id_dict.keys():
            return self._node_id_dict[node_name]
        # more than one case.
        # trace from selected node
        candidate_node_list = trace_node_ids(
            self._workflow, self._node_id_dict[start_from], input_key
        )
        candidate_img_node_list = find_values_by_partial_match(
            self._node_id_dict, node_name
        )
        candidate_id = find_common_elements(
            candidate_node_list, candidate_img_node_list
        )
        assert (
            len(candidate_id) == 1
        ), "Failed to identify input image node, format not supported by workflow."
        return candidate_id[0]


def get_key_from_class_type(workflow, class_type):
    key_list = []
    for key, value in workflow.items():
        if value["class_type"] == class_type:
            key_list.append(key)
    return key_list


def create_node_dict(workflow):
    node_dict = {}
    for node_name in NODE_NAME_LIST:
        id_list = get_key_from_class_type(workflow, node_name)
        if len(id_list) == 0:
            continue
        if len(id_list) == 1:
            node_dict[node_name] = id_list[0]
        # more than one nodes have the same name, add a number
        if len(id_list) > 1:
            assert (
                node_name in ALLOW_MULTIPLE_NODES
            ), f"workflows with multiple {node_name} are not supported."
            for i, id in enumerate(id_list):
                node_dict[f"{node_name}_{i}"] = id

    return node_dict


def trace_node_ids(workflow: dict, start_node: str, input_key: str):
    visited_nodes = set()
    nodes_to_visit = []

    start_node_data = workflow.get(start_node)
    if start_node_data:
        input_value = start_node_data["inputs"].get(input_key)
        if (
            input_value
            and isinstance(input_value, list)
            and input_value[0].isdigit()
        ):
            nodes_to_visit.append(input_value[0])

    while nodes_to_visit:
        current_node = nodes_to_visit.pop()
        if current_node not in visited_nodes:
            visited_nodes.add(current_node)

            # Check inputs and add them to the nodes to visit
            node_data = workflow.get(current_node)
            if node_data:
                for input_value in node_data["inputs"].values():
                    if (
                        isinstance(input_value, list)
                        and input_value[0].isdigit()
                    ):
                        nodes_to_visit.append(input_value[0])

    return list(visited_nodes)


def find_values_by_partial_match(data: dict, search_string: str):
    return [value for key, value in data.items() if search_string in key]


def find_common_elements(list_a: list, list_b: list) -> list:
    set_a = set(list_a)
    set_b = set(list_b)
    common_elements = list(set_a.intersection(set_b))
    return common_elements
