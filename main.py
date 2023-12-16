import json

from client import Client
from ui import ui
from workflow_manager import GenerateSettings, WorkflowManager
import argparse


def main(psd_path, config_path):
    with open(config_path, "r") as f:
        config = json.load(f)
    workflow_manager = WorkflowManager(f"workflows/{config['init_workflow']}")
    generate_settings = GenerateSettings(**config)
    client = Client()
    ui(config, workflow_manager, generate_settings, client, psd_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--psd_path", required=True)
    parser.add_argument("-c", "--config_path", default="config.json")
    args = parser.parse_args()
    main(args.psd_path, args.config_path)
