
# 手話タウン to Anki

このツールは [手話タウンハンドブック](https://handbook.sign.town/ja/feed?sl=JSL) の学習資料から Anki パッケージを生成します。

現在、JSLにのみ対応しています。
生成されるカードは、現在確認している数で延べ 1,290 枚です。

## 依存関係

- [uv](https://github.com/astral-sh/uv)

## インストール

uv 導入済みの環境で、以下のコマンドからインストールしてください。

```zsh
uv tool install git+https://github.com/mootah/signtown_to_anki
```

## 使い方

### ヘルプ

```zsh
signtown-to-anki --help
```

### 推奨

オプションを何も指定しなければ、推奨設定で実行されます。

```zsh
signtown-to-anki
```

### 動画をダウンロードしない

```zsh
signtown-to-anki --no-download
```

### 動画の変換を行わない

元動画（mp4）のサイズは 計2.2GB です。

```zsh
signtown-to-anki --no-conversion
```

### 変換・圧縮フォーマットを指定する

- アニメーション画像
    - `avif`（ 計96MB ）
    - `webp`（ 計447MB ）
- 動画
    - `mp4`（ 計104MB ）
    - `webm`（ 計303MB ）

から選択できます。
デフォルトでは`avif`です。

```zsh
signtown-to-anki --format webm
```

### テンプレートを選択する

- `jsl-ja`（日本手話→日本語）
- `ja-jsl`（日本語→日本手話）
- `all`（両方）

から選択できます。
デフォルトでは`jsl-ja`です

```zsh
signtown-to-anki --template ja-jsl
```

## 注意事項

- 圧縮・変換後のファイルサイズは実行環境によって異なります。
- Ankiの環境やバージョンによっては使用できないファイル形式が存在します。
- 当方は、学習資料の著作権および所有権を有していません。当ツールの利用は個人学習の範囲に限ることを想定しており、再配布や商用利用を行う場合は handbook.sign.town の利用規約や許諾を確認してください。
