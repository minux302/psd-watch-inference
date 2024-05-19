from pathlib import Path
from module.ui import build_ui
import argparse


def main(psd_path, workflow_dir):
    build_ui(psd_path, workflow_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--psd_path", required=True, type=Path)
    parser.add_argument(
        "-w", "--workflow_dir", default="workflows/img2img_xl", type=Path
    )
    args = parser.parse_args()
    main(args.psd_path, args.workflow_dir)
