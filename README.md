# PSD-WATCH-INFERENCE
`.psd` で保存された画像が更新されたことを検知し、自動でAI変換を行うツール。変換には [ComfyUI](https://github.com/comfyanonymous/ComfyUI)を使用。

## 環境構築
UI の起動にはこのリポジトリを利用し、AI変換には ComfyUI を用います。ComfyUI は別途環境構築をする必要があります。

### PSD-WATCH-INFERENCE の環境構築
```
$ pip install -r requirements.txt
```

### ComfyUI の環境構築
[ComfyUI](https://github.com/comfyanonymous/ComfyUI)のREADMEにしたがって環境構築を行ってください。  
ComfyUI の環境構築後、`setup_comfyui.sh` を実行してください。このリポジトリで使用する weight と custom_node がダウンロードされます。
```
$ ./setup_comfyui.sh <ComfyUIへのパス>
```

## 使い方
２つのターミナルを用意し、片方で ComfyUI を起動し、もう片方でこのリポジトリを起動します。`PSD-WATCH-INFERENCE` を起動する際に、監視対象の PSD ファイルを指定してください。
```
# PSD-WATCH-INFERENCE
$ python main.py -p <監視対象のPSDファイルへのパス>
# http://127.0.0.1:7860/ にアクセス。

# ComfyUI
$ python main.py
```

初期設定（読み込む重み）は `config.json` から指定できます。
- `init_workflow`: 最初に読み込むAI変換設定。起動後にも変更可能。
- `ckpt_name`: 読み込む重みの名前。
- `target_resolution`: AI変換する際の画像サイズ。
- `seed`: シード値。`-1` の場合は乱数となる。
```
# config.json
{
    "init_workflow": "sd15_img2img_lcm.json",
    "ckpt_name": "SDHK04.safetensors",
    "target_resolution": 1024,
    "seed": 1
}
```

### レイヤーについて
PSD ファイルのうち、表示されているレイヤーを統合して入力します。  
controlnetを使用するAI変換の場合、`control`という名前がついているレイヤーが存在すれば、そのレイヤーをcontrolnetの入力として使用します。無い場合は入力画像がcontrolnetの入力となります。


## Custom Workflow
AI変換に使用している設定（workflow）はカスタム可能です。以下の仕様をみたすように設定ファイルを作成してください。自分で作成する場合は `workflows` 配下のサンプルを参考にしてください。
Workflow には ComfyUI の developer mode の `Save(API Fromat)` で保存される `workflow_api.json` を使用しています。

- 入力・出力のノードには [comfyui-tooling-nodes
](https://github.com/Acly/comfyui-tooling-nodes) の `LoadImageBase64`、 `SendImageWebSocket` を使用してください。
- img2img では I/O は１つずつのみ使用可能です。ControlNet では Input は２つ指定可能です。