# Anima LLLite Regional ControlNet の試し方

## 追加内容

`Anima Apps/07_LLLite領域制御_実験的.app.json`を追加しています。
既存01〜06、キャラLoRA、WAI-ANIMA、Turbo、Skin Textureの設定は維持します。

- 公式ノード: [kohya-ss/ComfyUI-Anima-LLLite](https://github.com/kohya-ss/ComfyUI-Anima-LLLite/tree/b7495bd8eb876e334509976896702484ed19cdbb)
- モデル: [Sen-sou/Anima-LLLite-Regional-Controlnet](https://huggingface.co/Sen-sou/Anima-LLLite-Regional-Controlnet)
- 重み: `anima-lllite-regional-exp-v3.safetensors`、51,133,504 bytes
- 保存先: `/workspace/comfyui/models/controlnet/anima-lllite-regional-exp-v3.safetensors`
- 使用ノードID: `AnimaLLLiteApply_sdscripts`。ComfyUI標準の`AnimaLLLiteApply`とは入力仕様が異なります。

公式ノードはコミット固定でコンテナへ同梱し、モデルは初期ダウンロードに追加しています。
追加の学習・プリプロセッサー・ControlNet Aux・Impact Packは不要です。
`DOWNLOAD_MODELS=1`、`DOWNLOAD_OPTIONAL_MODELS=1`、`INSTALL_ANIMA_APPS=1`を使用してください。
古いイメージのPodを再起動するだけでは追加されません。新イメージからPodを作成してください。
カスタム`MODEL_MANIFEST`を使っている場合は、そのmanifestにもこのControlNetの登録が必要です。

## まずは自動配置で比較

1. App 07を開き、モデルをWAI-ANIMAにします。
2. 「色マップ」は`(layout)`のまま。「領域配置」で左右・上下・3列・4列・2×2を選びます。
3. A〜Dのうち、使用する人物のLoRA・強度・トリガー・衣装を設定します。LoRAなしでも配置のテストはできます。
4. 共通プロンプトには人数・相互動作・構図・背景・照明を設定し、人物別の欄にはその人物の特徴を入れます。
5. 最初は長辺1024程度で確認し、うまくいってから普段の1536などへ上げます。縦横比を変えても色マップとマスクは連動します。

| 設定 | 初期値 |
| --- | --- |
| 初回 ControlNet 強度 | 0.6 |
| 初回 ControlNet 開始／終了 | 0.0／0.65 |
| 高解像度化 ControlNet 強度 | 0.25 |
| 高解像度化 ControlNet 開始／終了 | 0.0／1.0 |
| プロンプト境界のぼかし | 2% |
| 初回サンプラー | res_multistep / sgm_uniform、18 steps、CFG 1 |
| 高解像度化 | latent 1.5倍、8 steps、CFG 1、denoise 0.55 |

ControlNetの数値は比較実験の開始点であり、この組み合わせで画質が確認済みの推奨値ではありません。
同じシード・プロンプト・LoRAで、まず両パスのControlNet強度を0にしたものと比較してください。
次に初回だけ0.6、最後に高解像度化も0.25にして、配置と質感への影響を分けて見ます。
配置の影響が弱ければ初回0.8〜1.0、色領域へ引っ張られすぎる・質感が変わるなら0.3〜0.5を試します。
高解像度化で質感が崩れる場合は、そのパスのControlNet強度を0にできます。
開始／終了はノイズスケジュール全体の割合です。低denoiseの2パス目でも効くよう、初期値では終了を1.0にしています。
CFG 1では通常ネガティブプロンプトは効きません。

## 手描き色マップ

白地のPNGを「色マップ」にアップロードすると、配置プリセットの代わりにその形を使います。
背景に透明部分がある場合は白として扱います。外部の画像編集ソフトで作った画像を使用できます。

| 領域 | 色 | RGB |
| --- | --- | --- |
| A | 赤 | 255, 0, 0 |
| B | 青 | 0, 0, 255 |
| C | 緑 | 0, 255, 0 |
| D | 黄 | 255, 255, 0 |
| 共通背景 | 白 | 255, 255, 255 |

モデル自体は任意の色を使えますが、**このアプリのA〜D自動対応は上記4色に固定**しています。
1つの人物を複数の離れた色領域に分けても同じ人物のマスクになります。
重なった箇所は画像上で見えている色の人物に割り当たります。
出力の「制御色マップ」で、実際に渡された色と形を確認できます。
アップロード画像は生成解像度へ縦横別にリサイズするため、形を保ちたい場合は生成画像と同じ縦横比で作ります。
黒い線画や写真をそのまま入力する用途ではありません。

抱き合う構図などは、四角い左右分割よりも、相手側へ伸びる腕まで含めた色マップで試す方が意図を伝えやすくなります。
ただし、手や接触部の解剖学的な正しさまで保証するものではありません。

## 記事の構成との違いと限界

[紹介記事](https://note.com/shizunori/n/n596ae5242609)は色マップとAttention Coupleを組み合わせています。
今回のアプリは、それに代えて既存の`AnimaRegionalCharacter`によるComfyUI標準LoRA hooksと
マスク付きconditioningを維持し、LLLiteを追加した構成です。PPM／Attention Coupleの同一再現ではありません。

公式モデルは色マップだけでは色とプロンプトを自動対応付けしません。
このアプリでは同じ色マップからA〜Dマスクを作り、各人物のpositive／negativeとLoRA hookに渡します。
ControlNetは初回・高解像度化のMODELへ別々に適用します。
キャラLoRAは共通MODELへ直接積まず、人物別欄で指定してください。
共通LoRA 2へキャラLoRAを入れると画像全体へ適用されます。

これはキャラLoRAの影響を画素単位で完全遮断する機構ではありません。
衣装や髪の混同が必ず消える、接触部分が必ず自然になる、単体生成と質感が完全一致するとは保証できません。
公式モデルカードにも、遠景の被写体はマスク境界に追従しにくい場合があると説明されています。

## 確認範囲

- 公開重みを実取得し、SHA-256と`lllite.version=2`などのメタデータを確認。
- 固定した公式ノードの入力名・モデルパッチ方法・リサイズ・時間範囲をソースで確認。
- CPUテストで色の対応、白／透明背景、任意形状、ぼかし、アスペクト比、2段階の接続、同梱ノードのインストールを検証。
- 既存01〜06のワークフローJSONは変更していません。
- WAI-ANIMA＋Turbo＋Skin＋キャラLoRA hooks＋LLLiteの**GPU実生成は未検証**です。生成速度、VRAM、漏れの改善、接触部、質感はPodで確認が必要です。
- 新App 07の実ブラウザー操作・iPhone実機も未検証です。

Pod起動後の入力・モデル一覧チェック（生成は実行しません）:

```bash
python3 /opt/runpod-anima-image/scripts/check_apps.py --url http://127.0.0.1:8188
```

比較は左右分割・離れた2人から始め、次に肩寄せ、最後に抱き合う構図へ進めます。
同じシードでA/BのLoRAとプロンプトを入れ替え、髪・衣装が領域と一緒に移るか確認してください。
初回プレビューと最終画像を別々に見て、混同が発生する段階も確認します。
