import functools
import numpy as np
from PIL import Image
import math
import os
import gradio as gr

from client import Client
from workflow_manager import GenerateSettings, WorkflowManager
from pydantic import BaseModel
from psd import parse_psd

result_img = np.zeros([0, 0, 0])
workflow_list = os.listdir("workflows")


class FileStatus(BaseModel):
    path: str
    last_modified_time: float

    def check_changed(self):
        return os.path.getmtime(self.path) != self.last_modified_time

    def update_last_modified_time(self):
        self.last_modified_time = os.path.getmtime(self.path)


def load_workflow(workflow_name: str, workflow_manager: WorkflowManager):
    # For convenience of gradio's event handler, set the variable specified
    # by functool to the back
    workflow_manager.load_workflow(f"workflows/{workflow_name}")
    if "control" in workflow_name:
        return gr.update(visible=True)
    else:
        return gr.update(visible=False)


def calc_target_size(input_w: int, input_h: int, target_resolution: int = 786):
    resize_ratio = math.sqrt(
        target_resolution * target_resolution / (input_w * input_h)
    )
    return (
        int(input_w * resize_ratio) // 64 * 64,
        int(input_h * resize_ratio) // 64 * 64,
    )


def resize_target_resolution(
    image: Image.Image, target_resolution: int = 786
) -> Image.Image:
    resized_w, resized_h = calc_target_size(
        image.size[0], image.size[1], target_resolution
    )
    return image.resize((resized_w, resized_h), Image.BICUBIC)


def run_generate(
    file_status: FileStatus,
    config: dict,
    workflow_manager: WorkflowManager,
    generate_settings: GenerateSettings,
    client: Client,
):
    global result_img

    if file_status.check_changed():
        print("catch file change event.")
        file_status.last_modified_time = os.path.getmtime(file_status.path)
        file_status.update_last_modified_time()
        input_img, control_img = parse_psd(file_status.path)

        orig_hw_ratio = input_img.size[1] / input_img.size[0]
        input_img = resize_target_resolution(
            input_img, config["target_resolution"]
        )
        control_img = resize_target_resolution(
            control_img, config["target_resolution"]
        )

        workflow = workflow_manager.create(
            input_img=input_img,
            control_img=control_img,
            generate_settings=generate_settings,
        )
        prompt_id = client.enqueue(workflow)
        generated_img = client.polling(prompt_id)
        _result_img = generated_img.resize(
            (input_img.size[0], int(orig_hw_ratio * input_img.size[0])),
            Image.BICUBIC
        )
        result_img = np.array(_result_img)
        img_h, img_w, _ = result_img.shape

        return gr.update(value=result_img, height=img_h, width=img_w)

    if result_img.size == 0:
        return

    img_h, img_w, _ = result_img.shape
    return gr.update(value=result_img, height=img_h, width=img_w)


def ui(
    config: dict,
    workflow_manager: WorkflowManager,
    generate_settings: GenerateSettings,
    client: Client,
    file_path: str,
):
    assert os.path.exists(file_path), f"{file_path} does not exist."
    file_status = FileStatus(
        path=file_path, last_modified_time=os.path.getmtime(file_path)
    )
    with gr.Blocks() as ui:
        prompt = gr.Textbox(label="prompt", value="1girl")
        negative_prompt = gr.Textbox(label="negative_prompt", value="")
        ckpt_name = gr.Textbox(label="ckpt_name", value=config["ckpt_name"])
        denoising_strength = gr.Slider(
            minimum=0, maximum=1, value=1.0, label="denoising strength"
        )
        control_strength = gr.Slider(
            minimum=0,
            maximum=1,
            value=1.0,
            label="control strength",
            visible=False,
        )
        workflow_dropdown = gr.Dropdown(
            choices=[x for x in workflow_list],
            label="workflow",
            value=config["init_workflow"],
        )
        image_output = gr.Image()
        prompt.change(
            fn=lambda x: setattr(generate_settings, "prompt", x),
            inputs=[prompt],
            outputs=None,
        )
        negative_prompt.change(
            fn=lambda x: setattr(generate_settings, "negative_prompt", x),
            inputs=[negative_prompt],
            outputs=None,
        )
        ckpt_name.change(
            fn=lambda x: setattr(generate_settings, "ckpt_name", x),
            inputs=[ckpt_name],
            outputs=None,
        )
        denoising_strength.change(
            fn=lambda x: setattr(generate_settings, "denoising_strength", x),
            inputs=[denoising_strength],
            outputs=None,
        )
        control_strength.change(
            fn=lambda x: setattr(generate_settings, "control_strength", x),
            inputs=[control_strength],
            outputs=None,
        )
        workflow_dropdown.change(
            fn=functools.partial(
                load_workflow, workflow_manager=workflow_manager
            ),
            inputs=[workflow_dropdown],
            outputs=[control_strength],
        )
        ui.load(
            fn=lambda: run_generate(
                file_status,
                config,
                workflow_manager,
                generate_settings,
                client,
            ),
            inputs=[],
            outputs=image_output,
            every=0.01,
        )
    ui.queue()
    ui.launch()
