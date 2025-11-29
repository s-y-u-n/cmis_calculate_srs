# 指標実装概要

以下では、各種指標の実装概要と数学的定義を簡潔に示す。数式は Markdown レンダラー向けに `$...$`（インライン）および `$$...$$`（表示）で統一している。

## Shapley 値

モジュール: `contrib_metrics.indices.shapley`

- 想定: $N \le 12$（厳密計算は $2^{|N|}$ 列挙）
- 関数: `compute_shapley_exact(game: Game) -> dict[int, float]`、`compute_shapley_mc(game: Game, num_samples: int) -> dict[int, float]`

### 定義 (TU ゲーム)

プレイヤー集合を $N$、価値関数を $v:2^N\to\mathbb{R}$ とすると、プレイヤー $i\in N$ の Shapley 値 $\phi_i(v)$ は

$$
\phi_i(v)=\sum_{S\subseteq N\setminus\{i\}}\frac{|S|!\,(|N|-|S|-1)!}{|N|!}\bigl(v(S\cup\{i\})-v(S)\bigr)
$$

で定義される。実装では `game.players` と `game.values` を用い、全ての部分集合を列挙して上式を評価する。モンテカルロ版はランダム順列をサンプリングして近似する。

## Banzhaf 指標

モジュール: `contrib_metrics.indices.banzhaf`

- 関数: `compute_banzhaf(game: Game, normalize: bool = True) -> dict[int, float]`

### Banzhaf の定義

非正規化 Banzhaf 指標 $\beta_i(v)$ は

$$
\beta_i(v)=\sum_{S\subseteq N\setminus\{i\}}\bigl(v(S\cup\{i\})-v(S)\bigr)
$$

で定義される。`normalize=True` のときは

$$
\hat{\beta}_i(v)=\frac{\beta_i(v)}{\sum_{j\in N}|\beta_j(v)|}
$$

として正規化する。

## Ordinal 指標

モジュール: `contrib_metrics.indices.ordinal`

- 順序情報に基づく marginal や Banzhaf 風スコア、lex-cel (lexicographic choice by electoral layers) などを実装する。

### ordinal marginal

ランク関数を `rank(S)`（小さい値が好ましい）とすると、従来の差分定義は

$$
m_i^S:=\mathrm{rank}(S\cup\{i\})-\mathrm{rank}(S)
$$

である。

### 符号付き定義

比較の符号のみを扱う定義は以下の通り：

$$
m_i^{S}(\succsim)=\begin{cases}
  1 & \text{if } S\cup\{i\} \succ S\\
  -1& \text{if } S \succ S\cup\{i\}\\
  0 & \text{otherwise}
\end{cases}
$$

ここから各プレイヤーについて正負の出現数を数え、差分スコア $s_i$ を返す実装を行う。

### lex-cel

ランクの層ごとの出現頻度ベクトル $\theta_{\succsim}(i)$ を計算し、辞書式比較で lex-cel 関係を構成する。

## Synergy / Anasy

モジュール: `contrib_metrics.indices.synergy`

- 基本例: `synergy(S)=v(S)-\sum_{i\in S}v(\{i\})` など。拡張用の API (`SynergyCalculator`) を用意している。

## Interaction 指標

モジュール: `contrib_metrics.indices.interactions`

- 提供: Shapley Interaction Index、Banzhaf Interaction Index

### Shapley Interaction Index

プレイヤー集合 $N$、価値関数 $v:2^N\to\mathbb{R}$、任意の連立 $S\subseteq N$ に対して Shapley Interaction Index $I_v(S)$ は次で定義される（$n=|N|$）。

$$
I_v(S)=\sum_{T\subseteq N\setminus S}\frac{(n-|T|-|S|)!\,|T|!}{(n-|S|+1)!}\sum_{L\subseteq S}(-1)^{|S|-|L|}\,v(L\cup T)
$$

ここで内側の和は $S$ の部分集合に対する包含排除形の差分を表し、外側の係数は Shapley の順序統計に由来する重みである。実装は `game.players` と `game.values` を用い、指定された `subsets`（省略時は適当な既定集合）ごとに上式を評価して `dict[Coalition,float]` を返す。

### Banzhaf Interaction Index

Banzhaf 相互作用は次で定義される。

$$
I_v^{B}(S)=\frac{1}{2^{\,n-|S|}}\sum_{T\subseteq N\setminus S}\sum_{L\subseteq S}(-1)^{|S|-|L|}\,v(L\cup T)
$$

実装は上式の直接評価に基づく（選択的に `subsets` パラメータで評価対象を絞れる）。

## Group values

モジュール: `contrib_metrics.indices.group_values`

- 将来の group-value 系指標の雛形を用意している。現時点ではプレースホルダー実装のみ。

---

**注:** このファイルは表示用に数式デリミタを `$` / `$$` に統一している。必要があれば、レンダラーに合わせた追加のエスケープや改行（あるいは MathJax の設定）を調整する。
