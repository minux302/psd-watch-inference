COMFY_PATH=$1
PWD=$PWD
DIR_NAME=$(basename "$COMFY_PATH")
if [ "$DIR_NAME" != "ComfyUI" ]; then
    echo "Error: 'ComfyUI' のリポジトリのパスを引数に指定してください。"
    exit 1
fi

wget https://huggingface.co/852wa/SDHK/resolve/main/SDHK04.safetensors -P $COMFY_PATH/models/checkpoints
wget https://huggingface.co/latent-consistency/lcm-lora-sdv1-5/resolve/main/pytorch_lora_weights.safetensors
mv pytorch_lora_weights.safetensors lcm-lora-sdv1-5.safetensors
mv lcm-lora-sdv1-5.safetensors $COMFY_PATH/models/loras/
wget https://huggingface.co/lllyasviel/ControlNet-v1-1/resolve/main/control_v11p_sd15s2_lineart_anime.pth -P $COMFY_PATH/models/controlnet
wget https://huggingface.co/lllyasviel/ControlNet-v1-1/resolve/main/control_v11p_sd15_scribble.pth -P $COMFY_PATH/models/controlnet

cd $COMFY_PATH/custom_nodes
git clone https://github.com/Acly/comfyui-tooling-nodes.git
git reset --hard 0cf4e8693945d68000e37fe291f877eff9ef0aaa
cd $PWD