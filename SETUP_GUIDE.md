# 粗大ごみ検索アプリ 全自動化セットアップガイド
## GitHub → Cloudflare Pages → Stripe → GAS 完全手順

> 対象：小宮山様（テラデザイン） / 作成：2026-05-26

---

## 全体フロー（完成形）

```
スポンサー申込 → GAS → Stripe決済 → GAS → 素材フォーム → GitHub更新 → 自動デプロイ
     ↑                                                              ↓
  sponsor.html                                          Cloudflare Pages（5分で公開）
```

---

## STEP 1：GitHub にリポジトリを作成してコードをアップロード

### 1-1. 新しいリポジトリを作成

1. ブラウザで [https://github.com](https://github.com) を開いてログイン
2. 右上の「＋」 → 「New repository」をクリック
3. 以下を入力：
   - **Repository name**：`sodaigomi-japan`
   - **Description**：`粗大ごみ処分料金かんたん検索`
   - **Public** を選択（Cloudflare Pages 無料プランで必要）
   - 「Create repository」をクリック

### 1-2. Git（ソースコード管理ツール）をインストール

1. [https://git-scm.com/download/win](https://git-scm.com/download/win) を開く
2. 「64-bit Git for Windows Setup」をダウンロード・インストール
3. インストール中はすべてデフォルト設定のまま「Next」

### 1-3. アプリフォルダをGitHubにアップロード

PowerShellを開いて以下のコマンドを順番に実行：

```powershell
# フォルダに移動
cd C:\Users\Terradesign\MyApps\sodaigomi-app

# Gitを初期化
git init

# GitHubアカウント情報を設定（1回だけ必要）
git config user.name "Terradesign"
git config user.email "terradesignik@gmail.com"

# 全ファイルを追加
git add .

# 最初のコミット（保存）
git commit -m "initial commit"

# メインブランチに設定
git branch -M main

# GitHubリポジトリと接続（YOUR_USERNAMEを自分のGitHubユーザー名に変更）
git remote add origin https://github.com/YOUR_USERNAME/sodaigomi-japan.git

# GitHubにアップロード
git push -u origin main
```

> ✅ GitHubを開いてリポジトリにファイルが見えたら成功

---

## STEP 2：Cloudflare Pages でデプロイ設定

### 2-1. Cloudflare アカウント作成（無料）

1. [https://dash.cloudflare.com/sign-up](https://dash.cloudflare.com/sign-up) でアカウント作成
2. メール認証を完了する

### 2-2. Pages プロジェクトを作成

1. Cloudflare ダッシュボード → 左メニュー「Workers & Pages」
2. 「Create application」→「Pages」→「Connect to Git」
3. 「Add account」からGitHubアカウントと連携
4. リポジトリ `sodaigomi-japan` を選択
5. 「Begin setup」をクリック

### 2-3. ビルド設定

以下のように設定：

| 項目 | 設定値 |
|------|--------|
| Project name | `sodaigomi-japan` |
| Production branch | `main` |
| Framework preset | `None` |
| Build command | （空欄のまま） |
| Build output directory | `/`（スラッシュ1つ） |

「Save and Deploy」をクリック → 数分後に公開完了！

### 2-4. カスタムドメインの設定（任意）

1. プロジェクト → 「Custom domains」→「Set up a custom domain」
2. 取得したドメイン名（例：`sodaigomi-japan.com`）を入力
3. Cloudflare でドメインを購入すれば自動設定される
   - Cloudflare ダッシュボード → 「Domain Registration」→「Register a domain」
   - `sodaigomi-japan.com` は年間 $10〜12 程度

### 2-5. Deploy Hook URL を取得（重要！）

自動更新のために必要なURLです。

1. プロジェクト → 「Settings」→「Builds & deployments」
2. 「Deploy hooks」セクションの「Add deploy hook」
3. Hook name：`gas-auto-deploy`
4. Branch：`main`
5. 「Save」→ **表示されたURLをコピーして控えておく**

> 例：`https://api.cloudflare.com/client/v4/pages/webhooks/deploy_hooks/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

---

## STEP 3：GitHub Personal Access Token を取得

GAS がコードを自動更新するために必要です。

1. GitHub → 右上アイコン → 「Settings」
2. 左下「Developer settings」→「Personal access tokens」→「Tokens (classic)」
3. 「Generate new token (classic)」
4. 設定：
   - **Note**：`sodaigomi-gas`
   - **Expiration**：`No expiration`（または1年）
   - **Scopes**：`repo` にチェック（全部チェックが入る）
5. 「Generate token」→ **表示されたトークンをコピーして控える**（一度しか表示されない！）

> 例：`ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx`

---

## STEP 4：Stripe Payment Links を作成

### 4-1. Stripe ダッシュボードで Payment Links を作成

[https://dashboard.stripe.com/payment-links](https://dashboard.stripe.com/payment-links) を開く

**作成する12本のリンク**（A/B/C × 1年/2年/3年/5年）：

| リンク名 | 金額 | 説明 |
|---------|------|------|
| A_1Y | ¥120,000 | Aランク（政令市・23区）1年 |
| A_2Y | ¥216,000 | Aランク 2年 |
| A_3Y | ¥306,000 | Aランク 3年 |
| A_5Y | ¥480,000 | Aランク 5年 |
| B_1Y | ¥60,000 | Bランク（人口20万以上）1年 |
| B_2Y | ¥108,000 | Bランク 2年 |
| B_3Y | ¥153,000 | Bランク 3年 |
| B_5Y | ¥240,000 | Bランク 5年 |
| C_1Y | ¥30,000 | Cランク（その他市区）1年 |
| C_2Y | ¥54,000 | Cランク 2年 |
| C_3Y | ¥76,500 | Cランク 3年 |
| C_5Y | ¥120,000 | Cランク 5年 |

各 Payment Link の作成方法：
1. 「Create payment link」
2. 商品名：例「粗大ごみ検索 Aランク 1年掲載」
3. 金額：上表の金額を入力
4. 「Collect additional information」→「Phone number」をオン
5. 作成後に表示される URL（`https://buy.stripe.com/xxxxx`）を控える

### 4-2. Stripe Webhook を設定

1. Stripe → 「Developers」→「Webhooks」→「Add endpoint」
2. Endpoint URL：`GASのウェブアプリURL`（STEP 5-4 で取得後に設定）
3. Events：`checkout.session.completed` を選択
4. 「Add endpoint」→ **Signing secret をコピー**

---

## STEP 5：GAS（Google Apps Script）を設定・デプロイ

### 5-1. Google スプレッドシートを作成

1. [https://sheets.new](https://sheets.new) で新しいスプレッドシートを作成
2. 名前：`粗大ごみ検索 スポンサー管理`
3. URLの `/d/` と `/edit` の間の部分をコピー（これがスプレッドシートID）

### 5-2. GAS にコードを貼り付け

1. スプレッドシートの「拡張機能」→「Apps Script」
2. 左側「ファイル」の「+」→「スクリプト」→ ファイル名：`gas_sponsor_manager_v3`
3. `gas_sponsor_manager_v3.js` の内容を全コピーして貼り付け
4. 同様に `gas_deploy_addon.js` の内容を末尾に追加

### 5-3. CONFIG の値を設定

`gas_sponsor_manager_v3.js` の `CONFIG` に以下を入力：

```javascript
// ★ 必須設定（あなたの実際の値に変更してください）
STRIPE_WEBHOOK_SECRET: 'whsec_xxxxx',  // ← STEP 4-2 で取得
CLOUDFLARE_URL: 'https://sodaigomi-japan.pages.dev',  // ← STEP 2 で取得

// ★ STEP 4-1 で取得した Stripe Payment Links の URL を入力
STRIPE_LINKS: {
  A_1Y: 'https://buy.stripe.com/xxxxx',
  A_2Y: 'https://buy.stripe.com/xxxxx',
  // ... 全12本を入力
},

// ★ gas_deploy_addon.js 用の設定（追加）
GITHUB_TOKEN: 'ghp_xxxxx',        // ← STEP 3 で取得
GITHUB_REPO: 'YOUR_USERNAME/sodaigomi-japan',  // ← ご自身のGitHubユーザー名/リポジトリ名
GITHUB_BRANCH: 'main',
CLOUDFLARE_DEPLOY_HOOK: 'https://api.cloudflare.com/client/v4/pages/webhooks/deploy_hooks/xxxxx',  // ← STEP 2-5 で取得
```

### 5-4. 初期セットアップを実行

1. `initSpreadsheet` を選択 → ▶️ 実行
2. `importCityMaster` を選択 → ▶️ 実行
3. `setupAllTriggers` を選択 → ▶️ 実行

### 5-5. ウェブアプリとして公開

1. 右上「デプロイ」→「新しいデプロイ」
2. 種類：「ウェブアプリ」
3. 「次のユーザーとして実行」：自分（terradesignik@gmail.com）
4. 「アクセスできるユーザー」：**全員**
5. 「デプロイ」→ **ウェブアプリURL をコピー**
6. このURL を Stripe Webhook の Endpoint URL に設定（STEP 4-2）

---

## STEP 6：素材収集 Google フォームを作成

### フォームの項目

1. 契約ID（短答式テキスト・必須）
2. 会社名・屋号（短答式テキスト・必須）
3. キャッチコピー（短答式テキスト・30字以内・必須）
4. 紹介文（段落・80字以内・必須）
5. 電話番号（短答式テキスト・必須）
6. 会社URL（短答式テキスト）
7. ロゴ画像URL（短答式テキスト・GoogleドライブのURLかhttps形式）

### 設定手順

1. [https://forms.new](https://forms.new) でフォーム作成
2. 上記7項目を追加
3. フォームの右上「⋮」→「スクリプトエディタ」
   または スプレッドシートの GAS に戻り、
   フォームと GAS を紐付け：
   フォームの送信トリガーを `onMaterialSubmit` に設定
4. フォームURL を CONFIG の `MATERIAL_FORM_URL` に設定

---

## STEP 7：動作確認チェックリスト

- [ ] GitHub: リポジトリにファイルがアップロードされている
- [ ] Cloudflare Pages: `sodaigomi-japan.pages.dev` でアプリが表示される
- [ ] GAS: `initSpreadsheet` 実行 → スプレッドシートにシートが自動作成された
- [ ] テスト申込: sponsor.html からテスト送信 → GAS からメールが届く
- [ ] Stripe テスト決済: テストモードで決済 → GAS Webhook が受信した
- [ ] 素材フォーム提出 → GitHub の `sponsors/` フォルダに JSON が追加された
- [ ] Cloudflare Pages が自動再デプロイされた
- [ ] アプリのその都市の検索結果にスポンサー情報が表示された

---

## コードの更新手順（将来）

新しい都市データを追加したり、index.html を修正したとき：

```powershell
cd C:\Users\Terradesign\MyApps\sodaigomi-app
git add .
git commit -m "都市データ追加：愛知県"
git push
```

→ Cloudflare Pages が自動でビルド・公開します（5〜10分）

---

## まとめ：何が自動化されるか

| 処理 | 自動化 | 手動 |
|------|--------|------|
| スポンサー申込受付 → 決済メール送付 | ✅ GAS | |
| Stripe決済確認 → 契約記録 | ✅ GAS Webhook | |
| 素材収集フォーム送付 | ✅ GAS | |
| スポンサーJSON更新 | ✅ GAS + GitHub API | |
| サイト再デプロイ | ✅ Cloudflare Deploy Hook | |
| 契約更新リマインド（6/3/1ヶ月前） | ✅ GAS 毎日実行 | |
| 週次レポートメール | ✅ GAS 毎週 | |
| 新都市データ追加 | | ✅ git push のみ |
| Stripe Payment Links 作成 | | ✅ 初回のみ手動 |

---

## 困ったときの連絡先

質問は Claude Code に「粗大ごみアプリの〇〇がうまくいかない」と伝えれば続きから対応できます。
