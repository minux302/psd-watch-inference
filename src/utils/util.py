from pathlib import Path
from PIL import Image
import logging
import logging.handlers
import io
import base64
import math

from psd_tools import PSDImage


def pil_to_base64(img: Image.Image):
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()


def create_logger(name: str, path: Path):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    file_handler = logging.handlers.RotatingFileHandler(
        path, encoding="utf-8", maxBytes=10 * 1024 * 1024, backupCount=4
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    )
    logger.addHandler(file_handler)
    return logger


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


def parse_psd(file_path) -> Image.Image:
    psd = PSDImage.open(file_path)
    image = Image.new("RGBA", psd.size, (255, 255, 255, 255))

    for layer in list(psd.descendants()):
        if layer.is_group():
            continue
        if layer.is_visible():
            try:
                layer_image = layer.topil()
                image.paste(
                    layer_image,
                    (layer.offset[0], layer.offset[1]),
                    layer_image,
                )
            except ValueError:
                continue

    return image
