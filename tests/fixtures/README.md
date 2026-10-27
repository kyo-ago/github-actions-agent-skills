# テスト用リポジトリFixture

`repositories.json` の各ケースは `files`（リポジトリ相対パスからYAML等の本文への対応）、期待する `errors` / `reviews` のコード集合、`duplicates`（候補の有無）、`lint`（追加の構文・シェル検証対象）を持ちます。`self_reference_lint` のあるケースは新しい `$/` 構文の互換性検査を別途行います。

本番用のAction SHAは含めていません。可変参照の例は検証の弱点を確認するための不正例です。`actions.lock` のダミー内容も公式lockfileとして使わないでください。

`recursive-before` → `recursive-middle` → `recursive-after` は、既存Compositeの再利用・共通部分の切り出し・残った重複の解消・再スキャンの段階です。テストはこれらの明示的な変更を一時ディレクトリに適用します。意味的同等性を推論して自動変換する実装ではありません。

`data-condition-exception` の `note` は5条件の評価例です。コメントや記録があっても機械判定で安全と認定せず、reviewを残すことを確認します。

Fixtureのコマンドは実行しません。`lint: true` のWorkflowはactionlint、Bashのインライン処理はCompositeを含めてShellCheckに渡します。`$/` を使うケースもShellCheckおよびactionlint互換性検査へ渡します。開発環境のactionlint v1.7.12は `$/` をref欠落として拒否しました。この特定の未対応診断だけの場合は互換性テストをskipとして明示し、それ以外の診断は失敗にします。独自検証では参照先とグラフを確認します。実GitHub上の動作は別途必要です。
