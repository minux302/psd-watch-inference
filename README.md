# PSD-WATCH-INFERENCE
`.psd` で保存された画像が更新されたことを検知し、自動でAI変換を行うツール。変換には [ComfyUI](https://github.com/comfyanonymous/ComfyUI)を使用。

## 環境構築
UI の起動にはこのリポジトリを利用し、AI変換には ComfyUI を用います。ComfyUI は別途環境構築をする必要があります。

### PSD-WATCH-INFERENCE の環境構築
```
$ python -m venv venv
$ source venv/bin/activate
$ pip install -r requirements.txt
```

### ComfyUI の環境構築
[ComfyUI](https://github.com/comfyanonymous/ComfyUI)のREADMEにしたがって環境構築を行ってください。すでに構築している場合は ComfyUI の新規の環境構築は不要です。
ComfyUI の環境構築後、下記コマンドで `comfyui-tooling-nodes` をインストールしてください。
```
# ComfyUI のディレクトリに移動
$ cd <ComfyUIへのパス>
$ cd custom_nodes
$ git clone https://github.com/Acly/comfyui-tooling-nodes.git
$ git reset --hard 0cf4e8693945d68000e37fe291f877eff9ef0aaa
```

### 重みのダウンロード
ComfyUI で動かしたいワークフローが動作するよう適宜重みを配置してください。ファイルを ComfyUI の画面にアップロードし、読み込んだワークフローが動作すれば構築完了です。
- [img2img_xl](workflows/img2img_xl/workflow_api_debug.json)
- [scribble_xl](workflows/852_a_scribble_xl/workflow_api_debug.json)
- [lineart_xl](workflows/kataragi_lineart_xl/workflow_api_debug.json)


## 使い方
２つのターミナルを用意し、片方で ComfyUI を起動し、もう片方でこのリポジトリを起動します。  
`localhost:8188` につながる状態であれば、リモートサーバーでも使用可能です。
`PSD-WATCH-INFERENCE` を起動する際に、監視対象の PSD ファイルを指定してください。PSD は `1024x1024` で作成することを推奨します。
```
# ComfyUI の起動
$ python main.py

# PSD-WATCH-INFERENCE の起動
# img2img_xl を起動する場合
$ python src/main.py -p <PSDのパス>
# scribble_xl を起動する場合
$ python src/main.py -p <PSDのパス> -w workflows/852_a_scribble_xl
# lineart_xl を起動する場合
$ python src/main.py -p <PSDのパス> -w workflows/kataragi_lineart_xl
# http://127.0.0.1:7860/ にアクセス。
```


## Custom Workflow
AI変換に使用している設定（workflow）は独自のものを仕様可能です。以下の仕様をみたすように設定ファイル(`workflow_api.json`, `settings.json`)を作成してください。`workflows/` 配下のサンプルを参考にしてください。
`workflow_api.json` は ComfyUI の developer mode の `Save(API Fromat)` で保存されるファイルを使用しています。

### workflow_api.json
- 入力・出力のノードには [comfyui-tooling-nodes
](https://github.com/Acly/comfyui-tooling-nodes) の `LoadImageBase64`、 `SendImageWebSocket` を使用してください。これらのノードは workflow 内に１つづつ必要です。
- `KSampler`は１つのみ

### settings.json
- `workflow/settings.json` の `optional_settings` でUI上で変更できるパラメータを指定できます。
- `id` は `workflow_api.json` の中身を確認し、変更したいパラメータを持つノードを記載してください。
- `type` は `slider`、または `text` です。
- `inputs` には `workflow_api.json` の対応するパラメータ名と初期値を記載してください。
```
# slider の場合
...
"control_strength": {
    "id": "53",
    "type": "text",
    "params": {
        "inputs": {
            "name": "text",
            "value": "1girl, masterpiece"
        },
    }
},
...

# text の場合
...
"control_strength": {
    "id": "53",
    "type": "slider",
    "params": {
        "inputs": {
            "name": "strength",
            "value": 1.0
        },
        "range": [0, 1]
    }
},
...
```
