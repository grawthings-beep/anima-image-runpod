# Anima LLLite + Attention Couple: 通常ワークフロー

ファイル: [anima_lllite_regional_ppm.json](workflows/graphs/anima_lllite_regional_ppm.json)

**App Modeではない、ノードを配線した通常グラフです。**
[紹介記事](https://note.com/shizunori/n/n596ae5242609)と同じ、色マップ・KJNodesの色抽出・
PPMのAttention Couple・Anima LLLiteを使用します。LoRA hooksによる代用ではありません。
既存の一括生成・高解像度化・インペイント・Apps 01〜07は残しています。

## 配線

```text
LoadImage -> ImageScale -> PreviewBridge -> GetImageSizeAndCount
                                RGB image |          | width/height
                                          |          +-> EmptyLatentImage / SolidMask
                                          +-> AnimaLLLiteApply_sdscripts.image
                                          +-> ColorToMask x3 -> AttentionCouplePPM.mask_1..3

WAI-ANIMA -> NegPiP -> Turbo -> Skin Texture -> LLLite -> AttentionCouplePPM -> KSampler -> VAE -> SaveImage
Qwen CLIP -> NegPiP -> Global / Red / Blue / Green text encoders
Global prompt -----------------------------> base_cond -----------> positive
Global full-frame mask --------------------> base_mask
Red / Blue / Green prompts -----------------> cond_1 / cond_2 / cond_3
```

PPMはLLLiteの後に置きます。AnimaではPPMがcross-attentionへ領域別テキストを適用し、
LLLiteは同じ色マップから空間的な制御を加えます。**1つのKSamplerで1枚を生成**します。
この版は記事方式を比較するための1パス版です。既存の高解像度化ワークフローは別に残っています。

NegPiPは初期値OFFです。ONにすると正プロンプト内の `(text:-0.5)` などを使用できます。
通常ネガティブ欄を有効にする機能ではありません。NegPiPはAttentionCouplePPMより前に置き、
MODEL/CLIP両方の出力を使います。比較方法と検証範囲は[NEGPIP.md](NEGPIP.md)を参照してください。

## 導入

新しい `ghcr.io/grawthings-beep/anima-image-runpod:cuda12.8` からPodを作成します。
起動時に通常のワークフロー一覧直下へ `anima_lllite_regional_ppm.json` が入ります。
`Anima Apps` フォルダーではありません。初期色マップもinputへ配置します。

`INSTALL_ANIMA_REGIONAL_GRAPH=1` が既定値。`INSTALL_ANIMA_APPS=0` でもこのグラフは導入されます。
既存Podの単なる再起動ではコンテナの中身は更新されません。

固定した以下の公式ノードをイメージへ同梱します。Pod起動時のpip installは不要です。

- [ComfyUI-Anima-LLLite](https://github.com/kohya-ss/ComfyUI-Anima-LLLite/tree/b7495bd8eb876e334509976896702484ed19cdbb)
- [ComfyUI-ppm](https://github.com/pamparamm/ComfyUI-ppm/tree/6c6c360155cace9d7091306c1b8e26d9c7438620)
- [ComfyUI-KJNodes](https://github.com/kijai/ComfyUI-KJNodes/tree/d7641533d6634eb05f8570c980fce8fc8528dc7b)
- [ComfyUI-Impact-Pack](https://github.com/ltdrdata/ComfyUI-Impact-Pack/tree/429d0159ad429e64d2b3916e6e7be9c22d025c3c)

必要モデルは既存manifestのWAI-ANIMA、Qwen 0.6B、Qwen Image VAE、Turbo、Skin Texture、
`models/controlnet/anima-lllite-regional-exp-v3.safetensors`です。
独自manifest使用時や任意モデルのダウンロードを無効にしている場合は別途用意してください。
`AnimaLLLiteApply_sdscripts`と標準の`AnimaLLLiteApply`は別物です。

Impact Pack/KJNodesの読み込みに必要な画像処理パッケージはビルド時に導入します。
CUDA版torch・torchvision・torchaudioなど既存MLパッケージの版を制約として保護します。
ControlNet Aux、ONNX Runtime、MediaPipe、SAM2やSAMの重みは導入・取得しません。
Impact PackのSAM2未導入の警告は、このグラフでは問題ありません。

## 使い方

1. 通常グラフを開き、左の `RGB color map / persistent input` で色マップを選びます。
   初期状態では赤・青の人物領域と緑の物体領域を描いたサンプルが入っています。
2. `Output resolution` のwidth/heightだけ変更します。初期値は1152×1536。
   色マップ・各マスク・latentは同じサイズへ連動します。縦横とも16の倍数を使用してください。
3. `Global` に人数・絡み・背景・光、赤・青・緑の各欄にはその領域の要素だけを書きます。
   例: 赤=Aの顔・髪・服、青=Bの顔・髪・服、緑=机上の物体。
4. 白背景に赤 `255,0,0`、青 `0,0,255`、緑 `0,255,0` を不透明で描きます。
   緑を使わない場合は色マップから緑を消せば、その領域マスクは0になります。
5. PreviewBridgeまでを部分実行し、画像編集の左側にある**筆アイコン（ペイント）**で編集できます。
   不透明度と硬さは1にします。
   透明度だけを塗る通常のinpaintマスクは色マップになりません。
   `RGB mask previews` を部分実行すると、LLLiteへ渡す画像と各色の抽出を生成前に確認できます。
6. 生成します。出力画像に加え、使用したRGB色マップも `output/Anima/regional_maps/` に保存します。

### PreviewBridgeの制約

記事作者はPreviewBridgeを独自修正していますが、その修正版コードは記事に公開されていません。
**この配布物は現行上流版のPreviewBridgeを使用し、非公開修正版の同一再現とはしていません。**

PreviewBridgeの編集内容は実行キャッシュと一時画像に依存します。
Pod再起動や入力画像・解像度変更でRGB編集が戻る場合があります。
保持したい色マップは `Save RGB map` のPNGを保存し、左のLoadImageへ読み直してください。
LoadImage側の画像編集で保存する方法、外部で作ったPNGを読み込む方法でも同じ推論経路を使えます。
画像の縦横比を大きく変える場合は形が伸びるので、色マップも新しい構図へ描き直します。

## 初期設定と比較

| 設定 | 値 |
| --- | --- |
| 生成サイズ | 1152×1536 |
| Turbo / Skin Texture | 0.6 / 0.45 |
| Sampler / scheduler | res_multistep / sgm_uniform |
| steps / CFG / denoise | 18 / 1 / 1 |
| LLLite strength / start / end | 0.6 / 0 / 0.65 |
| Global attention mask | 1.0 |
| 色抽出threshold | 10 |

これは普段のWAI-ANIMA設定へ寄せた比較用初期値で、記事作者の非公開設定を再現した数値ではありません。
CFG 1なので通常のnegativeは使用せず、共通conditioningをZeroOutしています。
Global maskを0にすると、白背景などに未充填部分ができPPMがエラーにするため、0より大きくしてください。
Global maskの値を下げると、色領域内の個別プロンプトの比率が上がります。

まず固定seed・同じプロンプトでLLLite強度0と0.6を比較します。
次に赤/青のプロンプトを交換して外見が領域とともに移るか確認します。
その後、肩寄せ・背中合わせ・抱き合いの順に色領域の形を変えます。
手や腕を相手の側へ伸ばす場合も、見えている部分をその人物の色で描きます。

**PPMは領域別LoRAローダーではありません。** 標準LoRAローダーへキャラLoRAを追加すると
重みはモデル全体に適用され、トリガーを地域プロンプトへ分けてもLoRAの完全隔離にはなりません。
髪・衣装の分離、接触部の自然さ、単体生成との質感一致は保証できません。
App 07のLoRA hooks版とは別方式として比較してください。

## 検証範囲

- JSON、配線型、循環、LLLite/PPMへの同一色マップ入力、サイズ連動、ノード配置、既存機能の回帰テスト。
- Dockerビルド時に実ComfyUI上で4つのノードパックをCPU読み込みし、色抽出とPreviewBridgeのRGB受け渡しを検査。
- ComfyUI 0.26.2のCPU環境でAnima用PPMの小さなcross-attentionを実計算し、領域別加重結果と既存ラッパーの保持を確認。
- フロントエンド1.54.8のデスクトップブラウザーで通常グラフの読み込み、PPMの動的入力のAPI出力、
  PreviewBridge上のRGB描画・保存・Python側への赤色の受け渡しを確認。
- このローカルUI検証環境にはWAI-ANIMA等の大規模モデルは置いていません。
  GPUでのWAI-ANIMA実生成・速度・VRAM・画質、およびiPhone実機の操作は別途確認が必要です。

CPUチェックはモデルを読み込まず、サーバーのポートも開きません。

```bash
python3 /opt/runpod-anima-image/scripts/check_regional_runtime.py
```
