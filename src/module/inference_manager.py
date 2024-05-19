import json
from pathlib import Path
import numpy as np
from PIL import Image
import os
import gradio as gr

from schemas.generate_settings import GenerateSettings
from module.client import Client
from module.workflow_manager import WorkflowManager
from pydantic import BaseModel
from utils.util import parse_psd, resize_target_resolution
from logging import getLogger, StreamHandler, DEBUG

logger = getLogger(__name__)
logger.setLevel(DEBUG)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.addHandler(handler)


class FileStatus(BaseModel):
    path: str | Path
    last_modified_time: float

    def check_changed(self):
        return os.path.getmtime(self.path) != self.last_modified_time

    def update_status(self):
        self.last_modified_time = os.path.getmtime(self.path)


class InferenceManager:
    def __init__(
        self,
        workflow_dir: Path,
        file_path: Path,
        view_img_height: int,
        view_img_width: int,
        server_ip: str = "http://127.0.0.1",
        port_port: str = "8188",
    ):
        assert (
            workflow_dir / "workflow_api.json"
        ).exists(), f"{workflow_dir}/workflow_api.json が見つかりません。"
        assert (
            workflow_dir / "settings.json"
        ).exists(), f"{workflow_dir}/settings.json が見つかりません。"

        # gradio の仕様上、生成設定と結果画像の状態を保持したほうが扱いやすいため本クラスを作成
        with open(workflow_dir / "settings.json", "r") as f:
            config = json.load(f)
        self._generate_settings = GenerateSettings(**config)
        self._result_img = np.zeros([0, 0, 0])

        assert os.path.exists(file_path), f"{file_path} does not exist."
        # PSD ファイルの状態を管理するモジュール
        self._file_status = FileStatus(
            path=file_path,
            last_modified_time=os.path.getmtime(file_path),
        )

        self._processing = False
        self._view_img_height = view_img_height
        self._view_img_width = view_img_width

        # ComfyUI Workflow API を動的に変更するモジュール
        self._workflow_manager = WorkflowManager(workflow_dir)

        # ComfyUI の API を監視するクライアント
        self._client = Client(ip=server_ip, port=port_port)

    @property
    def generate_settings(self):
        return self._generate_settings

    @generate_settings.setter
    def generate_settings(self, generate_settings: GenerateSettings):
        self._generate_settings = generate_settings

    def run(self):
        status = "waiting"

        # processing になったことを一旦 UI に伝える
        if self._file_status.check_changed() and self._processing is False:
            logger.debug("catch file change event.")
            self._processing = True
            status = "processing"
        # processing になったことを UI に伝えたあとに処理を開始
        elif self._file_status.check_changed() and self._processing is True:
            input_img = parse_psd(self._file_status.path)
            orig_hw_ratio = input_img.size[1] / input_img.size[0]
            input_img = resize_target_resolution(
                input_img, self._generate_settings.target_resolution
            )

            # workflow api にパラメータを設定
            workflow = self._workflow_manager.create(
                input_img=input_img,
                generate_settings=self._generate_settings,
            )

            # ComfyUI に処理をリクエストし完了するまで待機
            prompt_id = self._client.enqueue(workflow)
            generated_img = self._client.polling(prompt_id)

            if isinstance(generated_img, Image.Image):
                status = "finished"
                _result_img = generated_img.resize(
                    (input_img.size[0], int(orig_hw_ratio * input_img.size[0])),
                    Image.BICUBIC,
                )
                self._result_img = np.array(_result_img)
                self._file_status.update_status()
                self._processing = False

                return (
                    gr.update(
                        value=self._result_img,
                        height=self._view_img_height,
                        width=self._view_img_width,
                    ),
                    gr.update(value=f"status: {status}"),
                )

            # 同設定の場合 ComfyUI の処理がスキップされるため、そのまま終了する
            self._file_status.update_status()
            self._processing = False
            status = "skip"

        if self._result_img.size == 0:
            return None, gr.update(value=f"status: {status}")

        return (
            gr.update(
                value=self._result_img,
                height=self._view_img_height,
                width=self._view_img_width,
            ),
            gr.update(value=f"status: {status}"),
        )
