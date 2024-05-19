import gradio as gr
from pathlib import Path
from schemas.generate_settings import (
    GenerateSettings,
    slider_setting,
    text_setting,
)
from module.inference_manager import InferenceManager

VIEW_IMG_HEIGHT, VIEW_IMG_WIDTH = 768, 768


def set_optional_value(
    generate_settings: GenerateSettings,
    node_name: str,
    value,
):
    generate_settings.optional_settings[node_name].params.inputs.value = value


def build_optional_params_ui(inference_manager: InferenceManager):
    optional_settings = inference_manager.generate_settings.optional_settings
    for node_name, optional_param in optional_settings.items():
        # 変数毎に関数を作成する必要があるためスコープは for 配下
        def create_change_function(node_name):
            return lambda x: set_optional_value(
                inference_manager.generate_settings, node_name, x
            )

        if optional_param.type == "slider" and isinstance(
            optional_param.params, slider_setting
        ):
            optional_slider = gr.Slider(
                minimum=optional_param.params.range[0],
                maximum=optional_param.params.range[1],
                value=optional_param.params.inputs.value,
                label=node_name,
            )
            optional_slider.change(
                fn=create_change_function(node_name),
                inputs=[optional_slider],
                outputs=None,
            )
        elif optional_param.type == "text" and isinstance(
            optional_param.params, text_setting
        ):
            optional_text = gr.Textbox(
                label=node_name, value=optional_param.params.inputs.value
            )
            optional_text.change(
                fn=create_change_function(node_name),
                inputs=[optional_text],
                outputs=None,
            )


def build_ui(
    file_path: Path,
    workflow_dir: Path,
):
    inference_manager = InferenceManager(
        workflow_dir, file_path, VIEW_IMG_HEIGHT, VIEW_IMG_WIDTH
    )
    generate_settings = inference_manager.generate_settings

    with gr.Blocks() as ui:
        with gr.Row():
            with gr.Column(scale=1):
                denoising_strength = gr.Slider(
                    minimum=0,
                    maximum=1,
                    value=generate_settings.denoising_strength,
                    label="denoising strength",
                )
                prompt = gr.Textbox(label="prompt", value=generate_settings.prompt)
                negative_prompt = gr.Textbox(
                    label="negative_prompt", value=generate_settings.negative_prompt
                )

                # UIに表示する変更可能な設定値リスト
                build_optional_params_ui(inference_manager)

                status = gr.Markdown(value="status: none")
            with gr.Column(scale=1):
                image_output = gr.Image(height=VIEW_IMG_HEIGHT, width=VIEW_IMG_WIDTH)

        denoising_strength.change(
            fn=lambda x: setattr(generate_settings, "denoising_strength", x),
            inputs=[denoising_strength],
            outputs=None,
        )
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
        ui.load(
            fn=lambda: inference_manager.run(),
            inputs=[],
            outputs=[image_output, status],
            every=0.01,
        )
    ui.queue()
    ui.launch()
