from psd_tools import PSDImage
from PIL import Image


def parse_psd(file_path) -> tuple[Image.Image, Image.Image]:
    psd = PSDImage.open(file_path)
    image = Image.new("RGBA", psd.size, (255, 255, 255, 255))
    control_image = Image.new("RGBA", psd.size, (255, 255, 255, 255))

    for layer in psd:
        layer_name = layer.name
        if layer.is_visible():
            layer_image = layer.topil()

            if "control" in layer_name:
                control_image.paste(
                    layer_image,
                    (layer.offset[0], layer.offset[1]),
                    layer_image,
                )
            else:
                image.paste(
                    layer_image,
                    (layer.offset[0], layer.offset[1]),
                    layer_image,
                )

    return image, control_image


if __name__ == "__main__":
    from pathlib import Path

    file_path = Path("/Users/azuma/Desktop/sample.psd")
    output_path = file_path.parent / (file_path.stem + ".png")
    control_output_path = file_path.parent / (file_path.stem + "_control.png")
    image, control_image = parse_psd(file_path)
    # image.save(output_path)
    # control_image.save(control_output_path)
