# GitHub Actions Authoring Skill

Skill名は **`github-actions-agent-skills`** です。Security、Correctness and Reliability、Maintainability、Execution Efficiencyの順に優先します。

## インストールと利用

指定されたソース配置は `github-actions-authoring/` です。一方、Agent Skills仕様はインストール先のディレクトリ名とfrontmatterの `name` の一致を要求します。そのため、利用するエージェントのSkillディレクトリへ **`github-actions-agent-skills` という名前でコピー**してください。ソースフォルダをそのまま登録せず、インストール先で名前を一致させます。

Codexでの例（リポジトリのルートで実行、既存のインストール先は上書きしません）:

```bash
target="${CODEX_HOME:-$HOME/.codex}/skills/github-actions-agent-skills"
test ! -e "$target" && mkdir -p "$(dirname "$target")" && cp -R github-actions-authoring "$target"
```

エージェントに次のように依頼します。

```text
$github-actions-agent-skills を使って、このリポジトリにNode.jsのCIを追加してください。
既存WorkflowとComposite Actionも調査し、安全に共通化できる重複を確認してください。
```

通常は `SKILL.md` と該当する参照文書だけを読みます。`tests/` は開発時専用で、Skill利用時に読み込む必要はありません。検証補助スクリプト以外にPythonの依存関係はありません。

## 検証補助スクリプト

Python 3.10以上とPyYAMLが必要です。YAMLを独自パースせず、安全なパーサーを利用するための依存です。対象リポジトリのコード、Action、シェルコマンドは実行しません。読み取り専用です。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r github-actions-authoring/scripts/requirements.txt
.venv/bin/python github-actions-authoring/scripts/inspect_actions.py /path/to/repository --format json
.venv/bin/python github-actions-authoring/scripts/inspect_actions.py /path/to/repository --strict-review
```

- `error`: 構文・構造・独自規約の違反。終了コード1。
- `review`: 意味的な判断や外部情報の確認が必要。通常は終了コード0、`--strict-review` 指定時は1。
- 終了コード2: 引数・環境の問題（依存未導入など）。
- `duplicates`: 2ステップ以上の連続列候補。完全一致と、`with` / `env` のスカラー値だけ異なる候補を区別します。後者も意味的同等性の証明ではありません。
- `manual_checks`: 常に残る確認項目。出力が空でも「安全」「動作互換」とは断定しません。

階層、ローカル参照（`./` およびGitHub.comの `$/`）、循環、最大深さ、メタデータ、shell、inputs条件分岐の疑い、主要なWorkflow規約を検査します。`./` のcheckout到達性、外部Action内部、間接的な入力依存、任意のシェル分岐、動的Runner、lockfileの有効性は完全には判定できません。lockfileが存在しても依存確認を自動免除しません。詳細は [validation.md](references/validation.md) を参照してください。

## 開発時のテスト

```bash
.venv/bin/python -m unittest discover -s github-actions-authoring/tests -v
```

Fixtureは `tests/fixtures/` のデータから一時リポジトリへ展開されます。不正・危険な例も含み、実際のWorkflowとして登録・実行しません。重複の全組合せ、共通化後の再スキャン、5階層、違反グラフ、入力分岐、outputs、slimの選択例を検査します。`actionlint` と `shellcheck` があれば、有効なFixtureへ追加検証を行い、未導入時はskipとして表示します。

`actionlint` はComposite Actionの完全なメタデータ検証を代替しません。テスト合格は、実GitHub実行・Secretの非漏洩・意味的互換性の保証ではありません。

開発環境ではactionlint v1.7.12、ShellCheck 0.11.0を使用しました。actionlintは公式の新しい `$/` ローカル参照構文を拒否したため、その互換性検査はskipとして記録します。同構文を含むFixtureも独自のパス・依存グラフ検査とShellCheckの対象です。既存構文のWorkflow検証は成功しています。

## 設計と資料

実装規則は英語の [SKILL.md](SKILL.md) と8つの参照文書にあります。公式仕様と、このSkill独自の5階層・inputs規約を区別しています。重複排除はエージェントが意味と互換性を確認して実施し、スクリプトは自動変更しません。

調査基準日: **2026-10-24（日本時間）**。`ubuntu-slim` のツールや制約は設計時に再確認します。Workflow dependency lockfileは公式資料上public previewかつGitHub Enterprise Cloud向けです。対象環境の対応状況を確認し、利用可能なら公式CLIで生成・検証し、未対応なら実在を確認した完全なSHAで固定します。

参考実装は比較調査のみ行い、本文・コードを転載していません。資料URL、確認事項、参考実装との設計上の差は [maintainability.md](references/maintainability.md) に記録しています。
