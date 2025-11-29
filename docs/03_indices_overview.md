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

有限集合 $N$ 上の coalitional ranking（全前順序）$\succsim\in\mathcal{R}(F(N))$ を考える。  
これが誘導する同値類（quotient ranking）を

$$
\Sigma_1 \succ \Sigma_2 \succ \cdots \succ \Sigma_\ell
$$

と書く（$\Sigma_1$ が最上位の層）。

各プレイヤー $i\in N$ について、層ごとの出現頻度ベクトルを

$$
i_k := \bigl|\{\, S \in \Sigma_k \mid i \in S \,\}\bigr|
\qquad (k = 1,\ldots,\ell),
$$

$$
\theta_{\succsim}(i) := (i_1,\ldots,i_\ell)
$$

と定義する。

このとき lex-cel 解（lexicographic choice by electoral layers）は

$$
R_{\mathrm{le}} : \mathcal{R}(F(N)) \to \mathcal{B}(N)
$$

として、すべての $i,j\in N$ について

$$
i\,R_{\mathrm{le}}(\succsim)\,j
\Longleftrightarrow
\theta_{\succsim}(i)\;\ge_{\mathrm{lex}}\;\theta_{\succsim}(j)
$$

と定義される（$\ge_{\mathrm{lex}}$ は高い層から順に比較する辞書式順序）。

- $I^{\mathrm{le}}_{\succsim}$ : $R_{\mathrm{le}}(\succsim)$ の対称部分（同値関係）
- $P^{\mathrm{le}}_{\succsim}$ : その非対称部分（厳密優越）

実装では、

- 全ての層 $\Sigma_k$ を rank 値から構成し、
- 各 $i$ について $\theta_{\succsim}(i)$ を計算したうえで、
- すべてのペア $(i,j)$ に対して辞書式比較を行い
  - 厳密優越ペア $(i,j)$ を集合 $P$ に
  - 同値ペア $\{i,j\}$ を集合 $I$ に

として `LexCelRelation`（`theta`, `P`, `I`）を構成している。

## Synergy / Anasy

モジュール: `contrib_metrics.indices.synergy`

- 基本例: `synergy(S)=v(S)-\sum_{i\in S}v(\{i\})` など。拡張用の API (`SynergyCalculator`) を用意している。

## Interaction 指標

モジュール: `contrib_metrics.indices.interactions`（cardinal）および  
`contrib_metrics.indices.ordinal`（ordinal group Banzhaf）

- Shapley Interaction Index
- Banzhaf Interaction Index
- Group Ordinal Banzhaf（序数版の相互作用）

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

### Group Ordinal Banzhaf

有限集合 $N$ 上の coalitional ranking $\succsim\in\mathcal{R}(F(N))$ を考える。
任意の連立 $T\subseteq N$ と $S\subseteq N\setminus T$ に対して、
Group Ordinal Marginal Contribution を

$$
  m_T^S(\succsim)
  :=
  \begin{cases}
    1 & \text{if } S \cup T \succ S,\\\\
   -1 & \text{if } S \succ S \cup T,\\\\
    0 & \text{otherwise},
  \end{cases}
$$

と定義する。

連立 $T$ の Group Ordinal Banzhaf スコアは

$$
  u_T^{+,\succsim}
  :=
  \bigl|\{\, S \subseteq N\setminus T \mid m_T^S(\succsim)=1 \,\}\bigr|,
  \qquad
  u_T^{-,\succsim}
  :=
  \bigl|\{\, S \subseteq N\setminus T \mid m_T^S(\succsim)=-1 \,\}\bigr|,
$$

$$
  s_T^{\succsim}
  :=
  u_T^{+,\succsim}-u_T^{-,\succsim}
$$

で与えられる。

Group Ordinal Banzhaf Relation は、全ての連立 $S,T\subseteq N$ に対して

$$
  S\ \hat{R}^{\succsim}_N\ T
  \Longleftrightarrow
  s_S^{\succsim} \ge s_T^{\succsim}
$$

と定義される。

実装では:

- `compute_group_ordinal_banzhaf_scores(game)` が $T\mapsto s_T^{\succsim}$ を返し、
- `coalitions.<format>` の `group_ordinal_banzhaf_score` 列として出力することで、
  連立レベルの ordinal な「相互作用」を SRS として利用できる。

### Group lex-cel

Group lex-cel は、連立 $T$ について「$T$ を含む上位連立の頻度ベクトル」を用いる序数的なグループ指標である。

先ほどと同じ coalitional ranking $\succsim\in\mathcal{R}(F(N))$ を考え、
対応する quotient ranking

$$
\Sigma_1 \succ \Sigma_2 \succ \cdots \succ \Sigma_\ell
$$

をとる。

任意の非空連立 $T\in F(N)$ と $k=1,\ldots,\ell$ について

$$
  T_k := \bigl|\{\, S \in \Sigma_k \mid T \subseteq S \,\}\bigr|,
  \qquad
  \Theta_{\succsim}(T) := (T_1,\ldots,T_\ell)
$$

を定義する。

Group lex-cel 解は

$$
  R^{\mathrm{grp}}_{\mathrm{le}} : \mathcal{R}(F(N)) \to \mathcal{B}(F(N))
$$

として、全ての非空 $T,U\in F(N)$ について

$$
  T\; R^{\mathrm{grp}}_{\mathrm{le}}(\succsim)\; U
  \Longleftrightarrow
  \Theta_{\succsim}(T)\;\ge_{\mathrm{lex}}\;\Theta_{\succsim}(U)
$$

と定義される（\(\ge_{\mathrm{lex}}\) は高い層から順に比較する辞書式順序）。

- $I^{\mathrm{grp,le}}_{\succsim}$ : $R^{\mathrm{grp}}_{\mathrm{le}}(\succsim)$ の対称部分
- $P^{\mathrm{grp,le}}_{\succsim}$ : その非対称部分

実装では:

- `compute_group_lex_cel(game)` が
  - 各連立 $T$ について $\Theta_{\succsim}(T)$ を
  - そこから誘導される lex-cel 関係（$P$, $I$）
  を `GroupLexCelRelation` として返し、
- `coalitions.<format>` の
  - `group_lexcel_theta` 列として頻度ベクトル（カンマ区切り）を
  - `group_lexcel_rank` 列として lex 次のグループランク（1 が最良）を
  出力することで、連立レベルの lex-cel 型 SRS を利用できる。

## Group values

モジュール: `contrib_metrics.indices.group_values`

- 将来の group-value 系指標の雛形を用意している。現時点ではプレースホルダー実装のみ。

## メタ評価（Swimmy / Synergy–Anasy）

上記のようなシナジー比較ルール（Shapley/Banzhaf interaction、Group Ordinal Banzhaf、Group lex-cel）が
望ましい性質（公理）をどの程度満たしているかを、事後的にチェックするメタ指標も提供している。

現在は Swimmy Axiom と Synergy–Anasy Distinction Axiom を対象としている。

### Swimmy Axiom

2 人連立のペア \((S,T)\) で前件を満たすものに対して、各ルール \(R^I\) について後件
\(T P^I_\succsim S\) がどれだけ成立するかを集計する。

- ルールごとに
  - `triggered_pairs`: Swimmy の前件を満たしたペア数
  - `satisfied_pairs`: さらに後件も満たしたペア数
  - `satisfaction_rate`: `satisfied_pairs / triggered_pairs`
- `run_manager` から `axioms_swimmy.csv` として出力され、シナジー比較ルールのメタ評価に利用できる。

### Synergy–Anasy Distinction

各 2 人連立 \(T=\{i,j\}\) のシナジーレベル \(\mathrm{syn}_\succeq(T)\in\{1,\ldots,6\}\) を
序数順位 \(\succeq\) から計算し（Definition: synergy level）、2 つの連立 \(T,U\) に対して
\(\mathrm{syn}_\succeq(T) < \mathrm{syn}_\succeq(U)\) ならば、interaction 比較ルール \(R^I\) の観点でも
常に \(T P^I_\succeq U\) が成り立っているかどうかをチェックする。

- ルールごとに
  - `triggered_pairs`: \(\mathrm{syn}_\succeq(T) < \mathrm{syn}_\succeq(U)\) となるペア数
  - `satisfied_pairs`: さらに \(T P^I_\succeq U\) も満たすペア数
  - `satisfaction_rate`: `satisfied_pairs / triggered_pairs`
- 結果は `axioms_sada.csv` として出力され、synergy/anasy の区別をどの程度守っているかを評価できる。

---

**注:** このファイルは表示用に数式デリミタを `$` / `$$` に統一している。必要があれば、レンダラーに合わせた追加のエスケープや改行（あるいは MathJax の設定）を調整する。
