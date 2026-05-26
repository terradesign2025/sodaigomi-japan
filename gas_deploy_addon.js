/**
 * gas_deploy_addon.js
 * gas_sponsor_manager_v3.js に追加する Deploy Hook + GitHub API 関数群
 *
 * ─────────────────────────────────────────────
 * 【導入手順】
 * ① このファイルの内容をすべて gas_sponsor_manager_v3.js の末尾に貼り付ける
 * ② 既存の CONFIG オブジェクトに下記の4項目を追加する（値を必ず書き換えること）
 *
 *   const CONFIG = {
 *     // ... 既存の設定 ...
 *
 *     // ── GitHub API 設定（スポンサーJSON自動更新用） ────────────────
 *     // 設定方法: GitHub > Settings > Developer settings > Personal access tokens
 *     //           「repo」スコープにチェックを入れてトークンを発行する
 *     GITHUB_TOKEN: 'ghp_xxxxxxxxxxxxxxxxxxxx',
 *
 *     // 設定方法: 'ユーザー名またはOrg名/リポジトリ名' の形式で記述する
 *     //           例: 'terradesign/sodaigomi-japan'
 *     GITHUB_REPO: 'username/sodaigomi-japan',
 *
 *     // 設定方法: 通常は 'main'。master ブランチの場合は 'master' に変更する
 *     GITHUB_BRANCH: 'main',
 *
 *     // ── Cloudflare Pages 設定（自動再デプロイ用） ────────────────
 *     // 設定方法: Cloudflare Dashboard > Pages > プロジェクト名 > Settings
 *     //           > Builds & deployments > Deploy hooks > フックを作成してURLをコピー
 *     CLOUDFLARE_DEPLOY_HOOK: 'https://api.cloudflare.com/client/v4/pages/webhooks/deploy_hooks/3eb0cce2-551f-4f77-be73-4f716f5fe60d',
 *   };
 *
 * ③ onMaterialSubmit() 内で素材確認後に publishSponsor() を呼ぶ方法（例）:
 *
 *   // ---- onMaterialSubmit() の appendLog(...) の直後に追加 ----
 *   // 素材確認が完了したら手動で publishSponsor を呼ぶ（自動公開の場合は下記を有効化）
 *   // const sponsorData = buildSponsorData(cityId, contractId, adHeadline, adBody, companyUrl, logoUrl, rank, cityName, prefecture);
 *   // publishSponsor(cityId, sponsorData);
 *
 * ─────────────────────────────────────────────
 */

// ============================================================
// 1. updateSponsorJson(cityId, sponsorData)
//    GitHub Contents API を使って sponsors/{cityId}.json を作成・更新する
//    ・既存ファイルがある場合は sha を取得してから PUT する（必須）
//    ・既存ファイルと内容が同一の場合は PUT をスキップする（deploy hook は後続で叩く）
//    ・エラー時は管理者メールで通知する
// ============================================================

/**
 * GitHub に sponsors/{cityId}.json を作成または更新する
 *
 * @param {string} cityId       都市ID（例: '13101'）
 * @param {Object} sponsorData  スポンサー情報オブジェクト
 *   {
 *     cityId:      string  // '13101'
 *     company:     string  // '会社名'
 *     tagline:     string  // キャッチコピー（30字以内）
 *     description: string  // 説明文（80字以内）
 *     phone:       string  // '0120-xxx-xxx'
 *     url:         string  // 'https://example.com'
 *     logoUrl:     string  // 'https://example.com/logo.png'
 *     rank:        string  // 'A' | 'B' | 'C'
 *     updatedAt:   string  // 'YYYY-MM-DD'
 *   }
 * @returns {boolean} 成功 true / 失敗 false
 */
function updateSponsorJson(cityId, sponsorData) {
  const token  = CONFIG.GITHUB_TOKEN;
  const repo   = CONFIG.GITHUB_REPO;
  const branch = CONFIG.GITHUB_BRANCH || 'main';
  const path   = `sponsors/${cityId}.json`;
  const apiUrl = `https://api.github.com/repos/${repo}/contents/${path}`;

  // 設定値のバリデーション
  if (!token || token.indexOf('ghp_xxxx') >= 0) {
    MailApp.sendEmail(
      CONFIG.ADMIN_EMAIL,
      '【設定エラー】GitHub Token が未設定です',
      'CONFIG.GITHUB_TOKEN を設定してください。\ngas_deploy_addon.js の導入手順を確認してください。'
    );
    return false;
  }
  if (!repo || repo === 'username/sodaigomi-japan') {
    MailApp.sendEmail(
      CONFIG.ADMIN_EMAIL,
      '【設定エラー】GitHub リポジトリが未設定です',
      'CONFIG.GITHUB_REPO を設定してください。\ngas_deploy_addon.js の導入手順を確認してください。'
    );
    return false;
  }

  const headers = {
    'Authorization': `token ${token}`,
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'GAS-SodaigomiApp/1.0',
  };

  // ── STEP 1: 既存ファイルの sha と内容を取得 ──────────────────────
  let existingSha     = null;
  let existingContent = null;

  try {
    const getRes = UrlFetchApp.fetch(apiUrl, {
      method: 'get',
      headers: headers,
      muteHttpExceptions: true,
    });

    const getCode = getRes.getResponseCode();

    if (getCode === 200) {
      const getJson = JSON.parse(getRes.getContentText());
      existingSha = getJson.sha;
      // Base64 デコードして現在の内容を取得
      const decoded = Utilities.newBlob(
        Utilities.base64Decode(getJson.content.replace(/\n/g, ''))
      ).getDataAsString('UTF-8');
      existingContent = decoded;

    } else if (getCode === 404) {
      // ファイルなし → 新規作成
      existingSha = null;

    } else {
      // 予期しないエラー
      throw new Error(`GitHub GET ${getCode}: ${getRes.getContentText().substring(0, 300)}`);
    }

  } catch (err) {
    MailApp.sendEmail(
      CONFIG.ADMIN_EMAIL,
      `【エラー】GitHub ファイル取得失敗 (${cityId})`,
      `都市ID: ${cityId}\nエラー内容: ${err.toString()}\n\nAPIエンドポイント: ${apiUrl}`
    );
    return false;
  }

  // ── STEP 2: 既存内容と新しいデータを比較 ─────────────────────────
  const newContentStr = JSON.stringify(sponsorData, null, 2);

  if (existingContent !== null) {
    // 整形後の JSON を比較（空白差異を吸収するためパースして再 stringify）
    try {
      const existingObj = JSON.parse(existingContent);
      const newObj      = JSON.parse(newContentStr);
      // updatedAt 以外のキーで比較（updatedAt は常に変わるため除外しない → 完全比較）
      if (JSON.stringify(existingObj) === JSON.stringify(newObj)) {
        Logger.log(`[updateSponsorJson] ${cityId}: 内容が同一のためスキップ（deploy hook は実行する）`);
        return true; // スキップ成功 → 呼び出し元で deploy hook を叩く
      }
    } catch (e) {
      // パース失敗時は内容が変わったとみなして上書きする
      Logger.log(`[updateSponsorJson] ${cityId}: 既存ファイルのパース失敗 → 強制上書き`);
    }
  }

  // ── STEP 3: Base64 エンコードして PUT ────────────────────────────
  const encodedContent = Utilities.base64Encode(newContentStr, Utilities.Charset.UTF_8);

  const putBody = {
    message: `スポンサー情報更新: ${cityId} (${sponsorData.company || ''})`,
    content: encodedContent,
    branch:  branch,
  };
  if (existingSha) {
    putBody.sha = existingSha; // 既存ファイルを更新する場合は sha が必須
  }

  try {
    const putRes = UrlFetchApp.fetch(apiUrl, {
      method: 'put',
      headers: Object.assign({ 'Content-Type': 'application/json' }, headers),
      payload: JSON.stringify(putBody),
      muteHttpExceptions: true,
    });

    const putCode = putRes.getResponseCode();

    if (putCode === 200 || putCode === 201) {
      Logger.log(`[updateSponsorJson] ${cityId}: ${existingSha ? '更新' : '新規作成'}成功 (HTTP ${putCode})`);
      return true;

    } else {
      throw new Error(`GitHub PUT ${putCode}: ${putRes.getContentText().substring(0, 500)}`);
    }

  } catch (err) {
    MailApp.sendEmail(
      CONFIG.ADMIN_EMAIL,
      `【エラー】GitHub ファイル書き込み失敗 (${cityId})`,
      `都市ID: ${cityId}\n会社名: ${sponsorData.company || '不明'}\n` +
      `エラー内容: ${err.toString()}\n\n` +
      `※ GitHub Personal Access Token の "repo" スコープが有効か確認してください。\n` +
      `APIエンドポイント: ${apiUrl}`
    );
    return false;
  }
}


// ============================================================
// 2. callDeployHook()
//    Cloudflare Pages の Deploy Hook に POST してビルドをトリガーする
//    ・成功時: Logger.log にのみ記録（メール不要）
//    ・失敗時: 管理者メールでデプロイ失敗を通知する
// ============================================================

/**
 * Cloudflare Pages の Deploy Hook を叩いて再デプロイをトリガーする
 *
 * @returns {boolean} 成功 true / 失敗 false
 */
function callDeployHook() {
  const hookUrl = CONFIG.CLOUDFLARE_DEPLOY_HOOK;

  // 設定値のバリデーション
  if (!hookUrl || hookUrl.indexOf('xxxx') >= 0) {
    Logger.log('[callDeployHook] CLOUDFLARE_DEPLOY_HOOK が未設定のためスキップ');
    return false;
  }

  try {
    const res = UrlFetchApp.fetch(hookUrl, {
      method: 'post',
      // Deploy Hook は body 不要。Content-Length: 0 で POST する
      payload: '',
      muteHttpExceptions: true,
    });

    const code = res.getResponseCode();
    const body = res.getContentText().substring(0, 200);

    // Cloudflare は成功時に 200 または 201 を返す
    if (code === 200 || code === 201) {
      Logger.log(`[callDeployHook] デプロイトリガー成功 (HTTP ${code})`);
      return true;

    } else {
      throw new Error(`HTTP ${code}: ${body}`);
    }

  } catch (err) {
    MailApp.sendEmail(
      CONFIG.ADMIN_EMAIL,
      '【エラー】Cloudflare Pages デプロイ失敗',
      `Deploy Hook への POST が失敗しました。\n\n` +
      `エラー内容: ${err.toString()}\n\n` +
      `Hook URL: ${hookUrl}\n\n` +
      `Cloudflare Dashboard で Deploy Hook が有効か確認してください。\n` +
      `Pages > プロジェクト名 > Settings > Builds & deployments > Deploy hooks`
    );
    return false;
  }
}


// ============================================================
// 3. publishSponsor(cityId, sponsorData)
//    スポンサー情報の公開を一気通貫で行うメイン関数
//    ① GitHub に sponsors/{cityId}.json を作成・更新
//    ② 3秒待機（GitHub API → Cloudflare の伝播待ち）
//    ③ Cloudflare Pages Deploy Hook を叩いて再デプロイ
//    ④ 管理者に公開完了メールを送信
//
//  【onMaterialSubmit() からの呼び出し方（素材確認後に自動公開する場合）】
//
//    // ---- onMaterialSubmit() 内の appendLog(...) の直後に追加 ----
//    if (found) {
//      // 素材データが揃った時点で即時公開する場合:
//      const sponsorData = buildSponsorData(
//        cityId, contractId, adHeadline, adBody,
//        companyUrl, logoUrl, rank, cityName, prefecture
//      );
//      publishSponsor(cityId, sponsorData);
//    }
//
//    ※ 素材確認後に手動で公開する場合はスクリプトエディタから
//      publishSponsor('13101', { cityId:'13101', company:'○○株式会社', ... })
//      を直接実行してください。
// ============================================================

/**
 * スポンサー情報を GitHub に書き込み、Cloudflare Pages を再デプロイして公開する
 *
 * @param {string} cityId       都市ID（例: '13101'）
 * @param {Object} sponsorData  スポンサー情報オブジェクト（updateSponsorJson と同形式）
 */
function publishSponsor(cityId, sponsorData) {
  const cityName = sponsorData.cityName || cityId;

  Logger.log(`[publishSponsor] 開始: ${cityId} (${sponsorData.company || ''})`);

  // ① GitHub に JSON を書き込む
  const jsonOk = updateSponsorJson(cityId, sponsorData);
  if (!jsonOk) {
    // updateSponsorJson 内でエラーメールを送信済みのため、ここでは終了するのみ
    Logger.log(`[publishSponsor] ${cityId}: GitHub 書き込み失敗 → 処理中断`);
    return;
  }

  // ② 3秒待機（GitHub API の処理完了を待つ安全マージン）
  Utilities.sleep(3000);

  // ③ Cloudflare Pages Deploy Hook でビルドをトリガー
  const deployOk = callDeployHook();

  // ④ 管理者に完了通知メール（deploy hook の成否も含めて報告）
  const now = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy/MM/dd HH:mm:ss');
  const deployStatus = deployOk
    ? 'デプロイ完了（通常3〜5分でサイトに反映されます）'
    : 'デプロイの呼び出しに失敗しました。Cloudflare Dashboard を確認してください。';

  MailApp.sendEmail({
    to: CONFIG.ADMIN_EMAIL,
    subject: `【スポンサー公開】${cityName} / ${sponsorData.company || ''}`,
    body:
      `${cityName}のスポンサー情報を公開しました。\n\n` +
      `━━━━━━━━━━━━━━━━━━━━━━━\n` +
      `■ 公開内容\n` +
      `━━━━━━━━━━━━━━━━━━━━━━━\n` +
      `都市ID:      ${cityId}\n` +
      `会社名:      ${sponsorData.company || ''}\n` +
      `キャッチ:    ${sponsorData.tagline || ''}\n` +
      `説明文:      ${sponsorData.description || ''}\n` +
      `電話番号:    ${sponsorData.phone || ''}\n` +
      `掲載URL:     ${sponsorData.url || ''}\n` +
      `ロゴURL:     ${sponsorData.logoUrl || ''}\n` +
      `ランク:      ${sponsorData.rank || ''}\n` +
      `更新日:      ${sponsorData.updatedAt || ''}\n` +
      `━━━━━━━━━━━━━━━━━━━━━━━\n\n` +
      `GitHub: sponsors/${cityId}.json を更新しました\n` +
      `デプロイ: ${deployStatus}\n\n` +
      `実行日時: ${now}\n\n` +
      `────────────────────────\n` +
      `${CONFIG.COMPANY_NAME}\n` +
      `────────────────────────`,
    name: CONFIG.FROM_NAME,
  });

  Logger.log(`[publishSponsor] ${cityId}: 公開完了 (GitHub OK / Deploy ${deployOk ? 'OK' : 'NG'})`);
}


// ============================================================
// 4. buildSponsorData(...)  ヘルパー関数
//    onMaterialSubmit() の変数から sponsorData オブジェクトを組み立てる
//    publishSponsor() に渡す際に使用する
// ============================================================

/**
 * onMaterialSubmit() の各変数から publishSponsor() 用の sponsorData を組み立てる
 *
 * @param {string} cityId      都市ID
 * @param {string} contractId  契約ID（ログ用）
 * @param {string} adHeadline  広告見出し（30字以内）
 * @param {string} adBody      広告本文（80字以内）
 * @param {string} companyUrl  会社URL
 * @param {string} logoUrl     ロゴURL
 * @param {string} rank        ランク（'A' | 'B' | 'C'）
 * @param {string} cityName    都市名（管理者メールの件名に使用）
 * @param {string} prefecture  都道府県名（管理者メールの件名に使用）
 * @param {string} company     会社名
 * @param {string} phone       電話番号（省略可）
 * @returns {Object} sponsorData
 */
function buildSponsorData(cityId, contractId, adHeadline, adBody, companyUrl, logoUrl, rank, cityName, prefecture, company, phone) {
  const today = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy-MM-dd');
  return {
    cityId:      cityId,
    cityName:    cityName     || '',   // publishSponsor の件名生成に使用（JSONには含めても可）
    prefecture:  prefecture   || '',   // 同上
    contractId:  contractId   || '',   // 管理用（任意）
    company:     company      || '',
    tagline:     adHeadline   || '',
    description: adBody       || '',
    phone:       phone        || '',
    url:         companyUrl   || '',
    logoUrl:     logoUrl      || '',
    rank:        rank         || 'C',
    updatedAt:   today,
  };
}


// ============================================================
// 5. テスト用関数（スクリプトエディタから手動実行して動作確認する）
//    本番運用時は不要。確認後に削除してもよい。
// ============================================================

/**
 * updateSponsorJson の動作確認用テスト関数
 * スクリプトエディタから testUpdateSponsorJson() を直接実行する
 */
function testUpdateSponsorJson() {
  const testData = {
    cityId:      '99999',         // テスト用の都市ID（本番には存在しない値を使う）
    company:     'テスト株式会社',
    tagline:     '地域No.1の信頼と実績',
    description: '創業30年。地域の皆さまに寄り添うサービスを提供しています。',
    phone:       '0120-000-000',
    url:         'https://example.com',
    logoUrl:     'https://example.com/logo.png',
    rank:        'C',
    updatedAt:   '2026-05-26',
  };

  Logger.log('[TEST] updateSponsorJson を実行します...');
  const result = updateSponsorJson('99999', testData);
  Logger.log(`[TEST] 結果: ${result ? '成功' : '失敗'}`);
}

/**
 * callDeployHook の動作確認用テスト関数
 * スクリプトエディタから testCallDeployHook() を直接実行する
 * ※ 実行するとサイトの再ビルドが走るため注意
 */
function testCallDeployHook() {
  Logger.log('[TEST] callDeployHook を実行します...');
  const result = callDeployHook();
  Logger.log(`[TEST] 結果: ${result ? '成功' : '失敗'}`);
}
