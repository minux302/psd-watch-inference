from pathlib import Path
from PIL import Image
from utils.util import pil_to_base64
import random
import json
from schemas.generate_settings import GenerateSettings

DEFAULT_NODE_NAME_LIST = ["KSampler", "CLIPTextEncode", "ETN_LoadImageBase64"]
ALLOW_MULTIPLE_NODES = ["CLIPTextEncode"]


class WorkflowManager:
    def __init__(self, workflow_dir):
        self.load_workflow(workflow_dir)

    def create(
        self,
        input_img: Image.Image,
        generate_settings: GenerateSettings,
    ):
        # Ksamplerの設定
        if generate_settings.seed == -1:
            seed = random.randint(0, 100000)
        else:
            seed = generate_settings.seed
        self._workflow[self._node_id_dict["KSampler"]]["inputs"]["seed"] = seed
        self._workflow[self._node_id_dict["KSampler"]]["inputs"][
            "denoise"
        ] = generate_settings.denoising_strength

        # プロンプトの設定
        self._workflow[self._positive_prompt_node_id]["inputs"][
            "text"
        ] = generate_settings.prompt
        self._workflow[self._negative_prompt_node_id]["inputs"][
            "text"
        ] = generate_settings.negative_prompt

        # 追加パラメータの設定
        for optional_setting in generate_settings.optional_settings.values():
            node_id = optional_setting.id
            param = optional_setting.params.inputs
            self._workflow[node_id]["inputs"][param.name] = param.value

        #  入力画像の設定
        self._workflow[self._node_id_dict["ETN_LoadImageBase64"]]["inputs"][
            "image"
        ] = pil_to_base64(input_img)

        return self._workflow

    def load_workflow(self, workflow_dir: Path):
        with open(workflow_dir / "workflow_api.json", "r") as f:
            self._workflow = json.load(f)

        self._node_id_dict = create_node_dict(self._workflow)

        self._positive_prompt_node_id = trace_node_ids_by_key(
            self._workflow, self._node_id_dict["KSampler"], "positive"
        )
        self._negative_prompt_node_id = trace_node_ids_by_key(
            self._workflow, self._node_id_dict["KSampler"], "negative"
        )
        assert (
            self._positive_prompt_node_id is not None
        ), "ポジティブプロンプト（CLIPTextEncode）の特定に失敗しました。対応していない workflow です。"
        assert (
            self._negative_prompt_node_id is not None
        ), "ネガティブプロンプト（CLIPTextEncode）の特定に失敗しました。対応していない workflow です。"


def get_key_from_class_type(workflow, class_type):
    key_list = []
    for key, value in workflow.items():
        if value["class_type"] == class_type:
            key_list.append(key)
    return key_list


def create_node_dict(workflow: dict):
    node_dict = {}
    for node_name in DEFAULT_NODE_NAME_LIST:
        id_list = get_key_from_class_type(workflow, node_name)
        assert len(id_list) != 0, f"{node_name} が workflow に存在しません。対応していない workflow です。"
        if len(id_list) == 1:
            node_dict[node_name] = id_list[0]
        # more than one nodes have the same name, add a number
        elif len(id_list) > 1:
            assert (
                node_name in ALLOW_MULTIPLE_NODES
            ), f"{node_name} が複数存在する workflow には対応していません。"
            for i, id in enumerate(id_list):
                node_dict[f"{node_name}_{i}"] = id

    return node_dict


def trace_node_ids_by_key(workflow: dict, start_node: str, input_key: str):
    visited_nodes = []

    node_data = workflow.get(start_node)
    while node_data:
        try:
            next_node = node_data["inputs"].get(input_key)[0]
            if next_node.isdigit():
                visited_nodes.append(next_node)
                node_data = workflow.get(next_node)
            else:
                node_data = None
        except TypeError:  # next_node = None
            node_data = None
    return visited_nodes[-1]
