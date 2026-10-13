# Anima NegPiP

CFG 1 + Turboのまま、**正プロンプト内の負の重み**で不要な要素を抑える実験用機能です。
通常のネガティブ欄を有効にする機能ではありません。追加モデルのダウンロードはありません。

## ワークフロー

- `anima_negpip_basic.json`: 通常ノード版の単体生成。
- `anima_negpip_latent_2pass.json`: 通常ノード版の一括生成・latent高解像度化。両パスに適用。
- `anima_lllite_regional_ppm.json`: 既存の通常ノード版に切り替えを追加。
- Apps 01〜07: 各アプリに共通のNegPiP切り替えを追加。インペイントの仕上げも含め全パスに適用。

通常ノード版の単体・一括はApps 01/02と同じ設定・配線です。App Modeは使用しません。
従来のワークフローは削除しません。全て初期値OFFで、既存のプロンプト・CFG・steps・
Turbo/Skinの強度・denoiseは変更していません。

## 使い方

1. `Anima NegPiP (ON/OFF)` の `enabled` をONにします。App Modeでは `NegPiP` をON。
2. **正プロンプト**へ、例えば次を追加します。

```text
(text:-0.5), (watermark:-0.5)
```

カンマは括弧の外へ置きます。重みはまず `-0.25` など弱めから、1〜2項目ずつ比較してください。
これは試験開始値で、画質を保証する推奨値ではありません。
従来の長いネガティブ一覧の自動変換・自動挿入は行いません。
CFG 1では通常ネガティブ欄は引き続き使用されません。
領域版では全体へ作用させたい語は共通の正プロンプト、特定領域はその領域の正プロンプトへ入力します。
LoRA漏れや衣装混同の完全な解消を保証するものではありません。

既存の手元ワークフローへ追加する場合は、MODELとCLIPの**両方**をノードへ通してください。

```text
UNETLoader -> NegPiP.MODEL -> Turbo / other LoRAs -> [LLLite -> AttentionCouplePPM] -> samplers
CLIPLoader -> NegPiP.CLIP  -> all positive/negative text encoders and regional character nodes
```

NegPiPはAttentionCouplePPMより前に置きます。共通MODELから派生する人物LoRA・
初回・高解像度化の全経路に届く位置へ入れます。キャラLoRAを全体へ追加する機能ではありません。

## 比較手順

1. seedを固定し、モデル、解像度、LoRA、sampler、steps、CFG、denoiseを同じにする。
2. 負の重みの語を入れずOFF/ONを比較する。まず互換性と質感を確認する。
3. ONのまま負の語を1つ追加し、`-0.25`、`-0.5`を比較する。
4. 一括版は初回プレビューと最終画像の両方を確認する。
5. 領域版は同じ色マップでAだけの指定、Bだけの指定を比較し、髪・服・接触部・背景への影響を確認する。

OFFで元の結果と比較する際は、正プロンプトに追加した負の重みの語も外してください。
OFFは入力のMODEL/CLIPをそのまま返しますが、負の重み記法まで削除するわけではありません。

## 導入と既存Pod

Actionsでビルド完了後の新しいコンテナイメージを使用します。
通常ノード版は `INSTALL_ANIMA_REGIONAL_GRAPH=1`（既定値）で配置され、`INSTALL_ANIMA_APPS=0`でも使えます。
単体・一括版の補助ノードには既存の `INSTALL_ANIMA_NODE=1` を使用します。
Appsだけを入れる構成でも、NegPiPノードと同梱PPMは配置されます。
編集済みの同梱ワークフローは上書きしません。新しいJSONを読み込むか、上記の配線でノードを追加してください。
既存Podを再起動するだけでは新しいコンテナイメージの取得は保証されません。

## 実装と検証範囲

[PPMのCLIPNegPip](https://github.com/pamparamm/ComfyUI-ppm/tree/6c6c360155cace9d7091306c1b8e26d9c7438620)
を使用します。Anima以外や未対応のtext encoderで黙って無効になることを防ぐチェックを追加しています。

ComfyUI 0.26.2のCosmos Attentionには、PPMが必要とする `attn2_patch` の呼び出しがありません。
そのため旧版に限り、対象MODELのcross-attentionへ互換処理を追加します。
biasなしV投影・Identity正規化を確認したうえで、PPMの符号マスクを投影後Vへ適用します。
新しいComfyUIの `compute_qkv` が `transformer_options` を受ける場合は標準hookへ任せます。
ComfyUI本体やPyTorchのバージョンは変更しません。OFFではこの互換処理も追加しません。

- 自動テスト: ON/OFF、未対応時のエラー、全MODEL/CLIP経路、両パス、JSON再生成、通常グラフの重なり、インストーラー。
- CPU実計算: 実Anima型・PPM・小さなランダム重みのAttentionで、符号反転、正の重みでの一致、
  PPM領域別符号、既存MODELラッパー保持、元のMODEL/CLIPを変更しないことを検査。
- CPUテストはDockerビルドにも含めます。実学習済みQwenやAnimaモデルは読み込みません。
- フロントエンド1.54.8で通常グラフ3種の読み込み、ONへの変更、実行用JSONへの反映、保存・再読込を確認。
  UI検証環境にモデル本体はないため、モデル不足の警告は残したまま配線・操作のみ検査しています。
- **WAI-ANIMA + Turbo/LLLiteでのGPU画像生成・抑制効果・画質・速度・VRAMは未検証です。**

```bash
python3 /opt/runpod-anima-image/scripts/check_regional_runtime.py
```
