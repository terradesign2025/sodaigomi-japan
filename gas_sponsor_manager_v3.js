/**
 * 粗大ごみ判定アプリ 全国版
 * Google Apps Script v3 — スポンサー完全自動化スクリプト
 * 株式会社テラデザイン
 *
 * 【機能一覧】
 * A. Googleフォーム申込 → 自動受付メール + 決済リンク送付
 * B. Stripe決済完了 → 契約登録 + 完了メール (doPost webhook)
 * C. 6ヶ月前・3ヶ月前・1ヶ月前リマインド + 満了通知（毎日9:00）
 * D. 月次URLスクレイピング（全国自治体ページ変更チェック）
 * E. 週次レポート（満了予定一覧）
 * F. 初期セットアップ（シート自動作成 + 設定シート初期化）
 * G. 都市マスタ一括インポート（関東172都市 + 大阪33都市）
 *
 * 【初期設定手順】
 * 1. CONFIG の値を書き換える（STRIPE_WEBHOOK_SECRET 等）
 * 2. initSpreadsheet() を1回手動実行
 * 3. importCityMaster() を1回手動実行（都市マスタに全データを書き込む）
 * 4. setupAllTriggers() を1回手動実行
 * 5. GASをウェブアプリとして「全員がアクセス可能」で公開
 *    → 発行されたURLをStripeダッシュボードのWebhookエンドポイントに登録
 */

// ============================================================
// 設定（必ず書き換えてください）
// ============================================================
const CONFIG = {
  ADMIN_EMAIL: 'terradesignik@gmail.com',
  FROM_NAME: '全国粗大ごみ判定アプリ',
  COMPANY_NAME: '株式会社テラデザイン',
  SITE_NAME: '全国粗大ごみ判定アプリ',
  CONTACT_EMAIL: 'info@terra-design.co.jp',
  APPLY_FORM_URL: 'https://terra-design.co.jp/sponsor/apply/',
  RENEW_URL: 'https://terra-design.co.jp/sponsor/renew/',
  STRIPE_WEBHOOK_SECRET: '', // Stripeダッシュボードで確認したWebhookシークレットを入力

  CLOUDFLARE_URL: 'https://sodaigomi-japan.com', // デプロイ後に更新
  SHEET_SETTINGS: '設定',

  // Stripe Payment Link URL（Stripeダッシュボードで作成後に入力）
  // ランクA：政令市・東京23区（月¥10,000）
  // ランクB：人口20万以上（月¥5,000）
  // ランクC：その他市区町村（月¥2,500）
  STRIPE_LINKS: {
    A_1Y: 'https://buy.stripe.com/XXXXX', // Aランク 1年 ¥120,000
    A_2Y: 'https://buy.stripe.com/XXXXX', // Aランク 2年 ¥216,000
    A_3Y: 'https://buy.stripe.com/XXXXX', // Aランク 3年 ¥306,000
    A_5Y: 'https://buy.stripe.com/XXXXX', // Aランク 5年 ¥480,000
    B_1Y: 'https://buy.stripe.com/XXXXX', // Bランク 1年 ¥60,000
    B_2Y: 'https://buy.stripe.com/XXXXX', // Bランク 2年 ¥108,000
    B_3Y: 'https://buy.stripe.com/XXXXX', // Bランク 3年 ¥153,000
    B_5Y: 'https://buy.stripe.com/XXXXX', // Bランク 5年 ¥240,000
    C_1Y: 'https://buy.stripe.com/XXXXX', // Cランク 1年 ¥30,000
    C_2Y: 'https://buy.stripe.com/XXXXX', // Cランク 2年 ¥54,000
    C_3Y: 'https://buy.stripe.com/XXXXX', // Cランク 3年 ¥76,500
    C_5Y: 'https://buy.stripe.com/XXXXX', // Cランク 5年 ¥120,000
  },

  SHEET_CONTRACTS: '契約管理',
  SHEET_CITIES: '都市マスタ',
  SHEET_INQUIRY: '申込履歴',
  SHEET_LOG: '送信ログ',
  SHEET_CONTRIBUTIONS: '市民投稿',  // 市民からのURL提供を記録

  // IFTTT Webhook 設定（Google Home通知用）
  IFTTT_WEBHOOK_KEY: '',              // IFTTTダッシュボードで取得した Webhook Key
  IFTTT_EVENT_CONTRACT: 'sodaigomi_contract',  // 契約成立時のIFTTTイベント名
  IFTTT_EVENT_MATERIAL: 'sodaigomi_material',  // 素材入稿完了時のIFTTTイベント名

  // ── GitHub API 設定（スポンサーJSON 自動更新用）────────────────────────
  // 設定方法: GitHub > Settings > Developer settings > Personal access tokens (classic)
  //           「Generate new token」→ repo スコープにチェック → コピー
  GITHUB_TOKEN: 'ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',

  // 設定方法: 'GitHubユーザー名/リポジトリ名' の形式
  //           例: 'terradesign/sodaigomi-japan'
  GITHUB_REPO: 'YOUR_GITHUB_USERNAME/sodaigomi-japan',

  // リポジトリのブランチ名（通常 main）
  GITHUB_BRANCH: 'main',

  // ── Cloudflare Pages 自動デプロイ設定 ──────────────────────────────────
  // 設定方法: Cloudflare ダッシュボード > Pages > sodaigomi-japan > Settings
  //           > Builds & deployments > Deploy hooks > 「Add deploy hook」
  //           Hook名: gas-auto-deploy / Branch: main → 作成 → URLをコピー
  CLOUDFLARE_DEPLOY_HOOK: 'https://api.cloudflare.com/client/v4/pages/webhooks/deploy_hooks/3eb0cce2-551f-4f77-be73-4f716f5fe60d',
};

// ============================================================
// 料金テーブル（正式料金）
// A: 政令市・東京23区  月¥10,000
// B: 人口20万以上      月¥5,000
// C: その他市区町村    月¥2,500
// 2年=10%OFF / 3年=15%OFF / 5年=20%OFF
// ============================================================
const PRICE_TABLE = {
  A: { base: 10000, y1: 120000, y2: 216000, y3: 306000, y5: 480000 }, // 政令市・東京23区
  B: { base: 5000,  y1: 60000,  y2: 108000, y3: 153000, y5: 240000 }, // 人口20万以上
  C: { base: 2500,  y1: 30000,  y2: 54000,  y3: 76500,  y5: 120000 }, // その他市区町村
};

// ============================================================
// A. Googleフォーム申込受信 → 自動受付 + 決済リンク送付
// ============================================================
function onFormSubmit(e) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(CONFIG.SHEET_INQUIRY);
  const lastRow = sheet.getLastRow();
  const data = sheet.getRange(lastRow, 1, 1, sheet.getLastColumn()).getValues()[0];
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];

  const get = (colName) => {
    const idx = headers.indexOf(colName);
    return idx >= 0 ? (data[idx] || '') : '';
  };

  const inquiryId = `SP${new Date().getFullYear()}-${String(lastRow).padStart(4, '0')}`;
  const timestamp = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy/MM/dd HH:mm:ss');
  sheet.getRange(lastRow, 1).setValue(inquiryId);

  const companyName = get('会社名・屋号');
  const contactName = get('担当者名');
  const email = get('メールアドレス');
  const prefecture = get('希望都道府県');
  const city = get('希望都市');
  const rank = get('ランク') || 'C';
  const period = get('希望契約期間') || '1年';
  const industry = get('業種');
  const url = get('会社URL');

  // 料金と決済リンクを選択
  const prices = PRICE_TABLE[rank] || PRICE_TABLE.C;
  const periodKey = period.replace('年', 'Y');
  const paymentUrl = CONFIG.STRIPE_LINKS[`${rank}_${periodKey}`] || CONFIG.STRIPE_LINKS.C_1Y;

  const body = `${companyName} ${contactName} 様

このたびは「${CONFIG.SITE_NAME}」のスポンサー枠への
お申し込みをありがとうございます。

━━━━━━━━━━━━━━━━━━━━━━━
■ 受付内容
━━━━━━━━━━━━━━━━━━━━━━━
受付番号:    ${inquiryId}
受付日時:    ${timestamp}
都市:        ${prefecture} ${city}
業種:        ${industry}
契約期間:    ${period}
ご担当者:    ${contactName}
━━━━━━━━━━━━━━━━━━━━━━━

■ ご契約金額
${period}契約:  ¥${prices[`y${period.replace('年','')}`].toLocaleString()}（税込）

━━━━━━━━━━━━━━━━━━━━━━━
■ お支払いはこちらから（クレジットカード）
━━━━━━━━━━━━━━━━━━━━━━━

${paymentUrl}

※ お支払い完了後、24時間以内に掲載準備の
  ご案内メールをお送りします。

※ お支払いに進む前に、下記の利用規約を
  必ずご確認ください。
  https://terra-design.co.jp/sponsor/terms/

━━━━━━━━━━━━━━━━━━━━━━━
■ 掲載内容のご準備（お支払い後にご提出）
━━━━━━━━━━━━━━━━━━━━━━━
・会社ロゴ（PNG/JPG、120×120px推奨）
・広告見出し（30字以内）
・広告本文（80字以内）
・掲載先URL（https://〜）

ご不明点は本メールへの返信または
${CONFIG.CONTACT_EMAIL} までお気軽にどうぞ。

────────────────────────
${CONFIG.COMPANY_NAME}
Mail: ${CONFIG.CONTACT_EMAIL}
────────────────────────`;

  MailApp.sendEmail({
    to: email,
    subject: `【お申込受付・お支払いリンクのご案内】${city} スポンサー枠 / ${CONFIG.SITE_NAME}`,
    body: body,
    name: CONFIG.FROM_NAME
  });

  // 管理者通知
  MailApp.sendEmail({
    to: CONFIG.ADMIN_EMAIL,
    subject: `【新規申込】${prefecture}${city} / ${companyName} [${inquiryId}]`,
    body: `申込受付:\n${prefecture}${city} | ${companyName} | ${contactName} | ${email}\n期間:${period} | 金額:¥${(prices[`y${period.replace('年','')}`]||0).toLocaleString()}\n受付番号:${inquiryId}`
  });

  appendLog('申込受付', email, `${prefecture}${city} ${companyName} [${inquiryId}]`);
}

// ============================================================
// B. Stripe Webhook受信 → 契約登録 + 完了メール
//    GASをウェブアプリとして公開してStripeのWebhookに登録する
//    StripeのPayment Linkには以下のmetadataを設定してください:
//    cityId, cityName, prefecture, rank, period, companyName, contactName, email
// ============================================================
function doPost(e) {
  try {
    const payload = JSON.parse(e.postData.contents);

    // 市民投稿（アプリからのURL提供）
    if (payload.action === 'submitCityUrl') {
      return handleCityUrlSubmission(payload);
    }

    // checkout.session.completed イベントのみ処理する
    if (payload.type !== 'checkout.session.completed') {
      return ContentService.createTextOutput('ok');
    }

    const session = payload.data.object;
    const metadata = session.metadata || {};

    const cityId = metadata.cityId || '';
    const cityName = metadata.cityName || '';
    const prefecture = metadata.prefecture || '';
    const rank = metadata.rank || 'C';
    const period = parseInt(metadata.period || '1', 10);
    const companyName = metadata.companyName || session.customer_details?.name || '未設定';
    const contactName = metadata.contactName || '';
    const email = session.customer_details?.email || metadata.email || '';
    const amountPaid = session.amount_total / 100; // 円換算

    // 契約管理シートに登録
    const contractId = registerContract({
      cityId, cityName, prefecture, rank, period,
      companyName, contactName, email, amountPaid
    });

    // 完了メール送信
    sendContractCompletionEmail({ contractId, cityName, prefecture, period, companyName, contactName, email, amountPaid });

    // Google Home通知（IFTTT経由）
    notifyGoogleHome(
      CONFIG.IFTTT_EVENT_CONTRACT,
      `${prefecture}${cityName}の${companyName}からスポンサー契約が入りました。金額は${amountPaid}円です。`,
      `${prefecture}${cityName} / ${companyName}`,
      String(amountPaid)
    );

    return ContentService.createTextOutput('ok');
  } catch (err) {
    console.error('doPost error:', err);
    MailApp.sendEmail(CONFIG.ADMIN_EMAIL, '【エラー】Stripe Webhook処理失敗', err.toString());
    return ContentService.createTextOutput('error');
  }
}

// ============================================================
// B-1b. 市民URL投稿受信（アプリの「準備中」画面からの送信）
// ============================================================
function handleCityUrlSubmission(payload) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(CONFIG.SHEET_CONTRIBUTIONS);
  if (!sheet) {
    return ContentService.createTextOutput(JSON.stringify({status:'error',msg:'シートなし'}))
      .setMimeType(ContentService.MimeType.JSON);
  }

  const ts = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy/MM/dd HH:mm:ss');
  const cityId     = payload.cityId     || '';
  const cityName   = payload.cityName   || '';
  const prefecture = payload.prefecture || '';
  const url        = payload.submittedUrl || '';
  const email      = payload.email      || '';

  // シートに記録
  sheet.appendRow([ts, cityId, prefecture, cityName, url, email, '未確認', '']);

  // 管理者メール通知
  MailApp.sendEmail({
    to: CONFIG.ADMIN_EMAIL,
    subject: `【市民投稿・URL提供】${prefecture}${cityName}`,
    body: `市民からURLが提供されました。\n\n都市: ${prefecture}${cityName}（ID: ${cityId}）\nURL: ${url}\n投稿者メール: ${email || 'なし'}\n受信日時: ${ts}\n\n---\nスプレッドシートの「市民投稿」シートで確認してください。`,
    name: CONFIG.FROM_NAME
  });

  // Google Home通知（設定済みの場合のみ）
  notifyGoogleHome(
    CONFIG.IFTTT_EVENT_MATERIAL,
    `${prefecture}${cityName}のURLが市民から提供されました`,
    cityName,
    url
  );

  appendLog('市民投稿', email || '匿名', `${prefecture}${cityName} URL: ${url}`);

  return ContentService.createTextOutput(JSON.stringify({status:'ok'}))
    .setMimeType(ContentService.MimeType.JSON);
}

function registerContract(data) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(CONFIG.SHEET_CONTRACTS);
  const lastRow = sheet.getLastRow();
  const contractId = `SP${new Date().getFullYear()}-${String(lastRow).padStart(4, '0')}`;

  const startDate = new Date();
  const endDate = new Date(startDate);
  endDate.setFullYear(endDate.getFullYear() + data.period);

  const fmt = (d) => Utilities.formatDate(d, 'Asia/Tokyo', 'yyyy/MM/dd');
  const remind180 = new Date(endDate.getTime() - 180 * 24 * 60 * 60 * 1000);
  const remind90  = new Date(endDate.getTime() - 90  * 24 * 60 * 60 * 1000);
  const remind30  = new Date(endDate.getTime() - 30  * 24 * 60 * 60 * 1000);

  sheet.appendRow([
    contractId, data.prefecture, data.cityId, data.cityName, data.rank,
    data.companyName, data.contactName, data.email, '', '', // 電話・業種は入稿フォームから取得
    fmt(startDate), `${data.period}年`, fmt(endDate), data.amountPaid,
    '入金済', '', '', '', '', 'PR', false, '公開準備中',
    fmt(remind180), fmt(remind90), fmt(remind30),
    false, false, false, false, ''
  ]);

  // 都市マスタのスポンサー状況を更新
  updateCityStatus(data.cityId, '契約中', contractId, fmt(endDate));

  appendLog('契約登録', data.email, `${data.cityName} ${contractId}`);
  return contractId;
}

function sendContractCompletionEmail(d) {
  const body = `${d.companyName} ${d.contactName} 様

お支払いが完了しました。ありがとうございます！

━━━━━━━━━━━━━━━━━━━━━━━
■ ご契約内容
━━━━━━━━━━━━━━━━━━━━━━━
契約番号:    ${d.contractId}
掲載都市:    ${d.prefecture} ${d.cityName}
契約期間:    ${d.period}年
お支払金額:  ¥${d.amountPaid.toLocaleString()}
━━━━━━━━━━━━━━━━━━━━━━━

■ 次のステップ：掲載素材のご提出

以下のフォームから掲載素材をご提出ください。
確認後、3営業日以内に公開いたします。

素材入稿フォーム:
https://terra-design.co.jp/sponsor/submit/?id=${d.contractId}

【ご提出いただくもの】
・会社ロゴ（PNG/JPG、推奨120×120px、最大2MB）
・広告見出し（30字以内）
・広告本文（80字以内）
・クリック先URL（https://〜）

※ 素材未提出の場合は仮テキストで公開されます
━━━━━━━━━━━━━━━━━━━━━━━

ご不明点は ${CONFIG.CONTACT_EMAIL} までどうぞ。

────────────────────────
${CONFIG.COMPANY_NAME}
────────────────────────`;

  MailApp.sendEmail({
    to: d.email,
    subject: `【契約完了・素材入稿のご案内】${d.cityName} スポンサー枠`,
    body: body,
    name: CONFIG.FROM_NAME
  });

  MailApp.sendEmail({
    to: CONFIG.ADMIN_EMAIL,
    subject: `【契約完了・要素材確認】${d.cityName} / ${d.companyName} [${d.contractId}]`,
    body: `決済完了\n${d.prefecture}${d.cityName} | ${d.companyName} | ${d.email}\n金額:¥${d.amountPaid.toLocaleString()} | 期間:${d.period}年 | ID:${d.contractId}`
  });
}

// ============================================================
// B-2. Google Home通知（IFTTT Webhook経由）
//      CONFIG.IFTTT_WEBHOOK_KEY が空の場合はスキップ
//      value1: アナウンス本文 / value2: 都市・会社名 / value3: 金額等
// ============================================================
function notifyGoogleHome(eventName, value1, value2, value3) {
  if (!CONFIG.IFTTT_WEBHOOK_KEY) return; // キー未設定時はスキップ

  const url = `https://maker.ifttt.com/trigger/${eventName}/with/key/${CONFIG.IFTTT_WEBHOOK_KEY}`;
  const payload = JSON.stringify({ value1: value1 || '', value2: value2 || '', value3: value3 || '' });

  try {
    UrlFetchApp.fetch(url, {
      method: 'post',
      contentType: 'application/json',
      payload: payload,
      muteHttpExceptions: true,
    });
    appendLog('Google Home通知', eventName, value2 || value1);
  } catch (err) {
    MailApp.sendEmail(
      CONFIG.ADMIN_EMAIL,
      '【エラー】Google Home通知失敗',
      `イベント: ${eventName}\n内容: ${value1}\nエラー: ${err.toString()}`
    );
  }
}

// ============================================================
// B-3. 素材入稿フォーム受信 → シート更新・通知
//      Googleフォームの「フォーム送信時」トリガーに紐付ける
//      受信フィールド: 契約ID / 広告見出し / 広告本文 / 会社URL / ロゴURL / 店舗写真URL
// ============================================================
function onMaterialSubmit(e) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const contractSheet = ss.getSheetByName(CONFIG.SHEET_CONTRACTS);
    const data = contractSheet.getDataRange().getValues();
    const H = data[0];

    // フォーム回答をフィールド名→値のマップに変換
    const responses = e.response.getItemResponses();
    const form = {};
    responses.forEach(r => { form[r.getItem().getTitle()] = r.getResponse(); });

    const contractId   = (form['契約ID']         || '').toString().trim();
    const adHeadline   = (form['広告見出し（30字以内）'] || form['広告見出し'] || '').toString().trim();
    const adBody       = (form['広告本文（80字以内）']   || form['広告本文']  || '').toString().trim();
    const companyUrl   = (form['会社URL']          || '').toString().trim();
    const logoUrl      = (form['ロゴURL']           || '').toString().trim();
    const photoUrl     = (form['店舗写真URL']        || '').toString().trim();

    if (!contractId) {
      MailApp.sendEmail(CONFIG.ADMIN_EMAIL, '【エラー】素材入稿：契約IDが空', JSON.stringify(form));
      return;
    }

    // 列インデックスを取得
    const c = {
      ID:       H.indexOf('契約ID'),
      PREF:     H.indexOf('都道府県'),
      CITY:     H.indexOf('都市名'),
      COMPANY:  H.indexOf('会社名'),
      CONTACT:  H.indexOf('担当者名'),
      EMAIL:    H.indexOf('メール'),
      STATUS:   H.indexOf('ステータス'),
      LOGO_URL: H.indexOf('広告ロゴURL'),
      HEADLINE: H.indexOf('広告見出し'),
      AD_BODY:  H.indexOf('広告本文'),
      AD_URL:   H.indexOf('広告URL'),
      MAT_DATE: H.indexOf('素材入稿日'),
      PHOTO:    H.indexOf('店舗写真URL'),
      MAT_CHK:  H.indexOf('素材確認済'),
    };

    // 該当契約行を検索して更新
    let found = false;
    for (let i = 1; i < data.length; i++) {
      if (String(data[i][c.ID]).trim() !== contractId) continue;

      const today = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy/MM/dd');
      const row = i + 1; // シートの実行番号（1始まり）

      // 素材情報を更新
      if (c.LOGO_URL >= 0) contractSheet.getRange(row, c.LOGO_URL + 1).setValue(logoUrl);
      if (c.HEADLINE >= 0) contractSheet.getRange(row, c.HEADLINE + 1).setValue(adHeadline);
      if (c.AD_BODY  >= 0) contractSheet.getRange(row, c.AD_BODY  + 1).setValue(adBody);
      if (c.AD_URL   >= 0) contractSheet.getRange(row, c.AD_URL   + 1).setValue(companyUrl);
      if (c.MAT_DATE >= 0) contractSheet.getRange(row, c.MAT_DATE + 1).setValue(today);
      if (c.PHOTO    >= 0) contractSheet.getRange(row, c.PHOTO    + 1).setValue(photoUrl);
      if (c.MAT_CHK  >= 0) contractSheet.getRange(row, c.MAT_CHK  + 1).setValue(false); // 確認待ち

      // ステータスを「入金済」→「公開準備中」に更新
      if (c.STATUS >= 0 && data[i][c.STATUS] === '入金済') {
        contractSheet.getRange(row, c.STATUS + 1).setValue('公開準備中');
      }

      const cityName    = data[i][c.CITY]    || '';
      const prefecture  = data[i][c.PREF]    || '';
      const companyName = data[i][c.COMPANY] || '';
      const contactName = data[i][c.CONTACT] || '';
      const email       = data[i][c.EMAIL]   || '';

      // 管理者メール通知
      MailApp.sendEmail({
        to: CONFIG.ADMIN_EMAIL,
        subject: `【素材入稿】${prefecture}${cityName} / ${companyName} [${contractId}]`,
        body: `素材入稿を受け付けました。内容を確認して「素材確認済」列をTRUEにしてください。\n\n` +
              `契約ID:    ${contractId}\n` +
              `都市:      ${prefecture}${cityName}\n` +
              `会社名:    ${companyName}\n` +
              `広告見出し: ${adHeadline}\n` +
              `広告本文:  ${adBody}\n` +
              `会社URL:   ${companyUrl}\n` +
              `ロゴURL:   ${logoUrl}\n` +
              `店舗写真:  ${photoUrl}\n` +
              `入稿日:    ${today}`,
      });

      // 申込者への受領確認メール
      if (email) {
        MailApp.sendEmail({
          to: email,
          subject: `【素材受領のご確認】${cityName} スポンサー枠 [${contractId}]`,
          body: `${companyName} ${contactName} 様\n\n` +
                `掲載素材を受け付けました。ありがとうございます。\n\n` +
                `━━━━━━━━━━━━━━━━━━━━━━━\n` +
                `■ 受領内容\n` +
                `━━━━━━━━━━━━━━━━━━━━━━━\n` +
                `契約番号:   ${contractId}\n` +
                `掲載都市:   ${prefecture}${cityName}\n` +
                `広告見出し: ${adHeadline}\n` +
                `広告本文:   ${adBody}\n` +
                `掲載URL:    ${companyUrl}\n` +
                `━━━━━━━━━━━━━━━━━━━━━━━\n\n` +
                `内容確認後、3営業日以内に公開いたします。\n` +
                `修正が必要な場合は本メールへご返信ください。\n\n` +
                `────────────────────────\n` +
                `${CONFIG.COMPANY_NAME}\n` +
                `Mail: ${CONFIG.CONTACT_EMAIL}\n` +
                `────────────────────────`,
          name: CONFIG.FROM_NAME,
        });
      }

      // Google Home通知（IFTTT経由）
      notifyGoogleHome(
        CONFIG.IFTTT_EVENT_MATERIAL,
        `${prefecture}${cityName}の素材が入稿されました。確認してください。`,
        `${prefecture}${cityName} / ${companyName}`,
        contractId
      );

      appendLog('素材入稿受付', email, `${cityName} ${companyName} [${contractId}]`);
      found = true;
      break;
    }

    if (!found) {
      MailApp.sendEmail(
        CONFIG.ADMIN_EMAIL,
        `【エラー】素材入稿：契約ID不一致 [${contractId}]`,
        `契約管理シートに一致するIDが見つかりませんでした。\nフォーム回答: ${JSON.stringify(form)}`
      );
    }

  } catch (err) {
    MailApp.sendEmail(CONFIG.ADMIN_EMAIL, '【エラー】素材入稿処理失敗', err.toString());
  }
}

// ============================================================
// C. リマインドメール（毎日9:00 自動実行）
// ============================================================
function sendReminders() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(CONFIG.SHEET_CONTRACTS);
  const data = sheet.getDataRange().getValues();
  const H = data[0]; // ヘッダー行

  // カラムインデックスを取得
  const c = {
    ID: H.indexOf('契約ID'),
    PREF: H.indexOf('都道府県'),
    CITY: H.indexOf('都市名'),
    RANK: H.indexOf('ランク'),
    COMPANY: H.indexOf('会社名'),
    CONTACT: H.indexOf('担当者名'),
    EMAIL: H.indexOf('メール'),
    PERIOD: H.indexOf('契約期間'),
    END: H.indexOf('契約終了日'),
    STATUS: H.indexOf('ステータス'),
    NOTIF_180: H.indexOf('6ヶ月前通知済'),
    NOTIF_90: H.indexOf('3ヶ月前通知済'),
    NOTIF_30: H.indexOf('1ヶ月前通知済'),
    NOTIF_EXP: H.indexOf('満了通知済'),
  };

  const today = new Date(); today.setHours(0,0,0,0);

  for (let i = 1; i < data.length; i++) {
    const r = data[i];
    const status = r[c.STATUS];
    if (status !== '公開中' && status !== '公開準備中') continue;

    const endDate = new Date(r[c.END]); endDate.setHours(0,0,0,0);
    const daysLeft = Math.round((endDate - today) / 86400000);
    const rank = r[c.RANK] || 'C';
    const prices = PRICE_TABLE[rank] || PRICE_TABLE.C;

    const ctx = {
      contractId: r[c.ID],
      pref: r[c.PREF],
      city: r[c.CITY],
      company: r[c.COMPANY],
      contact: r[c.CONTACT],
      email: r[c.EMAIL],
      period: r[c.PERIOD],
      endDate: Utilities.formatDate(endDate, 'Asia/Tokyo', 'yyyy年M月d日'),
      daysLeft,
      prices,
    };

    // 6ヶ月前（180日）リマインド
    if (daysLeft <= 180 && daysLeft > 150 && !r[c.NOTIF_180]) {
      sendReminderMail(ctx, '6ヶ月');
      sheet.getRange(i+1, c.NOTIF_180+1).setValue(true);
    }
    // 3ヶ月前（90日）リマインド
    if (daysLeft <= 90 && daysLeft > 60 && !r[c.NOTIF_90]) {
      sendReminderMail(ctx, '3ヶ月');
      sheet.getRange(i+1, c.NOTIF_90+1).setValue(true);
    }
    // 1ヶ月前（30日）リマインド
    if (daysLeft <= 30 && daysLeft > 0 && !r[c.NOTIF_30]) {
      sendReminderMail(ctx, '1ヶ月');
      sheet.getRange(i+1, c.NOTIF_30+1).setValue(true);
    }
    // 満了当日：ステータスを「満了」に変更 + 都市マスタを「空き」に戻す
    if (daysLeft <= 0 && !r[c.NOTIF_EXP]) {
      sendExpiryMail(ctx);
      sheet.getRange(i+1, c.STATUS+1).setValue('満了');
      sheet.getRange(i+1, c.NOTIF_EXP+1).setValue(true);
      updateCityStatus(r[H.indexOf('都市ID')] || '', '空き', '', '');
    }
  }

  // 月曜日のみ週次レポートを送信
  if (today.getDay() === 1) {
    sendWeeklyReport(data, c, today);
  }
}

function sendReminderMail(ctx, periodLabel) {
  const p = ctx.prices;
  const body = `${ctx.company} ${ctx.contact} 様

いつも「${CONFIG.SITE_NAME}」をご利用いただきありがとうございます。

${ctx.city}のスポンサー枠が ${ctx.endDate} に満了となります。
（残り約${periodLabel}・${ctx.daysLeft}日）

引き続きご掲載をご希望の場合は、下記から更新手続きをお願いいたします。

━━━━━━━━━━━━━━━━━━━━━━━
■ 更新プラン（${ctx.city}）
━━━━━━━━━━━━━━━━━━━━━━━
1年プラン:  ¥${p.y1.toLocaleString()}（月額 ¥${p.base.toLocaleString()}）
2年プラン:  ¥${p.y2.toLocaleString()}（10%OFF）
3年プラン:  ¥${p.y3.toLocaleString()}（15%OFF）
5年プラン:  ¥${p.y5.toLocaleString()}（20%OFF）
━━━━━━━━━━━━━━━━━━━━━━━

更新フォーム: ${CONFIG.RENEW_URL}?id=${ctx.contractId}

※ 満了後は自動的に掲載が停止されます
━━━━━━━━━━━━━━━━━━━━━━━

────────────────────────
${CONFIG.COMPANY_NAME}
Mail: ${CONFIG.CONTACT_EMAIL}
────────────────────────`;

  MailApp.sendEmail({
    to: ctx.email,
    subject: `【契約更新のご案内】${ctx.city} スポンサー枠 残り${periodLabel}（${ctx.daysLeft}日）`,
    body, name: CONFIG.FROM_NAME
  });
  appendLog(`${periodLabel}前リマインド`, ctx.email, `${ctx.city} [${ctx.contractId}]`);
}

function sendExpiryMail(ctx) {
  const body = `${ctx.company} ${ctx.contact} 様

${ctx.city}のスポンサー枠の契約が本日満了となりました。
誠にありがとうございました。

掲載は本日をもって停止いたします。

引き続きのご掲載をご希望の場合は、
下記から新規お申し込みください。

申込フォーム: ${CONFIG.APPLY_FORM_URL}

────────────────────────
${CONFIG.COMPANY_NAME}
Mail: ${CONFIG.CONTACT_EMAIL}
────────────────────────`;

  MailApp.sendEmail({
    to: ctx.email,
    subject: `【掲載終了】${ctx.city} スポンサー枠の契約が満了しました`,
    body, name: CONFIG.FROM_NAME
  });

  MailApp.sendEmail({
    to: CONFIG.ADMIN_EMAIL,
    subject: `【要対応・掲載停止】${ctx.city} / ${ctx.company} [${ctx.contractId}]`,
    body: `契約満了・掲載停止。JSONファイルの削除・空き枠表示に切り替えてください。\n都市:${ctx.pref}${ctx.city} | 会社:${ctx.company} | ID:${ctx.contractId}`
  });

  appendLog('満了通知', ctx.email, `${ctx.city} 掲載停止 [${ctx.contractId}]`);
}

function sendWeeklyReport(data, c, today) {
  const H = data[0];
  const upcoming = [];
  const next180 = new Date(today.getTime() + 180 * 86400000);

  // 満了6ヶ月以内の公開中スポンサーをリストアップ
  for (let i = 1; i < data.length; i++) {
    const r = data[i];
    if (r[c.STATUS] !== '公開中') continue;
    const endDate = new Date(r[c.END]);
    if (endDate <= next180) {
      const days = Math.round((endDate - today) / 86400000);
      upcoming.push(`・${r[c.PREF]}${r[c.CITY]}（${r[c.COMPANY]}）残${days}日 [${r[c.ID]}]`);
    }
  }

  // 素材未入稿のアクティブスポンサーをリストアップ
  // 条件：ステータスが「公開準備中」かつ「素材入稿日」列が空
  const MAT_DATE_COL = H.indexOf('素材入稿日');
  const noMaterial = [];
  for (let i = 1; i < data.length; i++) {
    const r = data[i];
    if (r[c.STATUS] !== '公開準備中') continue;
    const matDate = MAT_DATE_COL >= 0 ? r[MAT_DATE_COL] : '';
    if (!matDate || matDate === '') {
      noMaterial.push(`・${r[c.PREF]}${r[c.CITY]}（${r[c.COMPANY]}）[${r[c.ID]}]`);
    }
  }

  if (!upcoming.length && !noMaterial.length) return;

  let body = '';
  if (upcoming.length) {
    body += `【更新営業が必要なスポンサー一覧】\n\n${upcoming.join('\n')}\n\n`;
  }
  if (noMaterial.length) {
    body += `【素材未入稿スポンサー一覧（要フォロー）】\n` +
            `※ステータスが「公開準備中」で素材入稿日が未記入の契約\n\n${noMaterial.join('\n')}`;
  }

  MailApp.sendEmail({
    to: CONFIG.ADMIN_EMAIL,
    subject: `【週次レポート】満了予定${upcoming.length}件・素材未入稿${noMaterial.length}件`,
    body: body.trim(),
  });
}

// ============================================================
// D. 月次URLスクレイピング（都市マスタのURL変更チェック）
//    毎月1日 2:00 に自動実行
//    1件約1.2秒 × 280件 = 336秒（5.6分）。
//    815市区は3〜4回に分割して実行する想定。
// ============================================================
function monthlyUrlCheck() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(CONFIG.SHEET_CITIES);
  const data = sheet.getDataRange().getValues();
  const H = data[0];

  const COL_URL  = H.indexOf('粗大ごみページURL');
  const COL_DATE = H.indexOf('最終アクセス日');
  const COL_CHG  = H.indexOf('前回からの変更点');
  const COL_CITY = H.indexOf('市区町村名');
  const COL_PREF = H.indexOf('都道府県名');

  const props = PropertiesService.getScriptProperties();
  const today = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy-MM-dd');

  const startRow = 1;
  const BATCH = 280; // GAS 6分制限に収まる安全な件数
  const endRow = Math.min(startRow + BATCH - 1, data.length - 1);

  const errors = [], changed = [];

  for (let i = startRow; i <= endRow; i++) {
    const row = data[i];
    const url = row[COL_URL];
    if (!url || !url.startsWith('http')) continue;

    try {
      const res = UrlFetchApp.fetch(url, { muteHttpExceptions: true, followRedirects: true });
      const code = res.getResponseCode();
      const body = res.getContentText('UTF-8').substring(0, 3000);
      const hash = Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, body)
                     .map(b => (b+256).toString(16).slice(-2)).join('');
      const prevHash = props.getProperty(`h_${i}`) || '';

      let note = '';
      if (code === 404)      note = '404エラー：URL変更の可能性あり';
      else if (code !== 200) note = `HTTP ${code}`;
      else if (prevHash && prevHash !== hash) note = 'ページ内容変更を検出';

      sheet.getRange(i+1, COL_DATE+1).setValue(today);
      if (note) {
        const prev = sheet.getRange(i+1, COL_CHG+1).getValue();
        sheet.getRange(i+1, COL_CHG+1).setValue(`[${today}] ${note}${prev ? '\n' + prev : ''}`);
        (code !== 200 ? errors : changed).push(`${row[COL_PREF]}${row[COL_CITY]}: ${note}`);
      }
      props.setProperty(`h_${i}`, hash);

    } catch(err) {
      errors.push(`${row[COL_PREF]}${row[COL_CITY]}: ${err.message}`);
    }
    Utilities.sleep(300);
  }

  if (endRow >= data.length - 1) {
    // 全件完了
    props.deleteProperty('scrape_row');
    const body = `月次スクレイピング完了\n\nエラー${errors.length}件・変更検出${changed.length}件\n\n${
      errors.length ? '【要URLの修正】\n' + errors.join('\n') + '\n\n' : ''}${
      changed.length ? '【内容変更あり（データ要確認）】\n' + changed.join('\n') : ''}`;
    MailApp.sendEmail({ to: CONFIG.ADMIN_EMAIL, subject: `【スクレイピング完了】エラー${errors.length}件・変更${changed.length}件`, body });
  } else {
    props.setProperty('scrape_row', String(endRow + 1));
  }
}

// ============================================================
// E. ユーティリティ
// ============================================================
function updateCityStatus(cityId, status, contractId, endDate) {
  if (!cityId) return;
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(CONFIG.SHEET_CITIES);
  const data = sheet.getDataRange().getValues();
  const H = data[0];
  const COL_ID = H.indexOf('都市ID');
  const COL_ST = H.indexOf('スポンサー状況');
  const COL_CID = H.indexOf('スポンサー契約ID');
  const COL_END = H.indexOf('契約終了日');

  for (let i = 1; i < data.length; i++) {
    if (String(data[i][COL_ID]) === String(cityId)) {
      sheet.getRange(i+1, COL_ST+1).setValue(status);
      if (contractId) sheet.getRange(i+1, COL_CID+1).setValue(contractId);
      if (endDate)    sheet.getRange(i+1, COL_END+1).setValue(endDate);
      break;
    }
  }
}

function appendLog(type, to, detail) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(CONFIG.SHEET_LOG);
  const ts = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy/MM/dd HH:mm:ss');
  sheet.appendRow([ts, type, to, detail]);
}

// ============================================================
// F. 初期セットアップ（初回1回だけ手動実行）
//    全シートを自動作成し、設定シートに初期値を書き込む
// ============================================================
function initSpreadsheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const defs = {
    '申込履歴': ['受付番号','受付日時','会社名・屋号','担当者名','メールアドレス','電話番号','希望都道府県','希望都市','希望契約期間','業種','会社URL','備考'],
    '契約管理': ['契約ID','都道府県','都市ID','都市名','ランク','会社名','担当者名','メール','電話','業種','契約開始日','契約期間','契約終了日','契約金額','支払状況','広告ロゴURL','広告見出し','広告本文','広告URL','PRタグ','featured','ステータス','6ヶ月前通知日','3ヶ月前通知日','1ヶ月前通知日','6ヶ月前通知済','3ヶ月前通知済','1ヶ月前通知済','満了通知済','備考','素材入稿日','店舗写真URL','素材確認済'],
    '都市マスタ': ['都市ID','都道府県コード','都道府県名','市区町村名','人口目安','ランク','粗大ごみページURL','最終アクセス日','前回からの変更点','データ収集状況','スポンサー状況','スポンサー契約ID','契約終了日','備考'],
    '送信ログ': ['送信日時','種別','宛先','内容'],
    '市民投稿': ['受信日時','都市ID','都道府県','都市名','投稿URL','投稿者メール','確認状況','備考'],
    '設定': ['項目名', '値', '備考'],
  };

  Object.entries(defs).forEach(([name, headers]) => {
    let sh = ss.getSheetByName(name) || ss.insertSheet(name);
    if (sh.getRange('A1').getValue() === '') {
      sh.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight('bold');
      sh.setFrozenRows(1);
    }
  });

  // 設定シートに初期データを書き込む
  const settingsSheet = ss.getSheetByName(CONFIG.SHEET_SETTINGS);
  if (settingsSheet.getLastRow() <= 1) {
    const initialSettings = [
      ['アプリURL',               'https://sodaigomi-japan.com',              'Cloudflare Pages公開後に更新'],
      ['スポンサー申込フォームURL', 'https://terra-design.co.jp/sponsor/apply/',  'WordPress設置後に更新'],
      ['素材入稿フォームURL',       'https://terra-design.co.jp/sponsor/submit/', 'Googleフォーム設置後に更新'],
      ['更新フォームURL',           'https://terra-design.co.jp/sponsor/renew/',  'WordPress設置後に更新'],
      ['管理者メール',              'terradesignik@gmail.com',                  '変更不要'],
      ['Stripe Webhook Secret',   '（要設定）',                                 'Stripeダッシュボードから取得'],
    ];
    settingsSheet.getRange(2, 1, initialSettings.length, 3).setValues(initialSettings);
  }

  Logger.log('初期セットアップ完了！シート: 申込履歴 / 契約管理 / 都市マスタ / 送信ログ / 設定');
}

// ============================================================
// G. 都市マスタ一括インポート
//    関東172都市 + 大阪33都市 = 合計205都市を一括書き込む
//    initSpreadsheet() 実行後に1回だけ手動実行すること
// ============================================================
function importCityMaster() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(CONFIG.SHEET_CITIES);

  if (!sheet) {
    Logger.log('ERROR: 都市マスタシートが見つかりません。先に initSpreadsheet() を実行してください。');
    return;
  }

  // 既存データ（ヘッダー以外）を削除してからインポート
  const lastRow = sheet.getLastRow();
  if (lastRow > 1) {
    sheet.deleteRows(2, lastRow - 1);
  }

  // 列順: [都市ID, 都道府県コード, 都道府県名, 市区町村名, 人口目安, ランク,
  //        粗大ごみページURL, 最終アクセス日, 前回からの変更点, データ収集状況,
  //        スポンサー状況, スポンサー契約ID, 契約終了日, 備考]
  // dataReady:true → 'v2あり' / false → '未収集'

  const rows = [
    // ==================== 関東（172都市）====================
    // --- 東京都 23区 ---
    ['13101','13','東京都','千代田区',67000,'A','https://www.city.chiyoda.lg.jp/koho/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['13102','13','東京都','中央区',170000,'A','https://www.city.chuo.lg.jp/kurasi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['13103','13','東京都','港区',263000,'A','https://www.city.minato.tokyo.jp/gomi-recycle/sodaigomi/','','','v2あり','空き','','',''],
    ['13104','13','東京都','新宿区',346000,'A','https://www.city.shinjuku.lg.jp/seikatsu/gomi04_000005.html','','','v2あり','空き','','',''],
    ['13105','13','東京都','文京区',235000,'A','https://www.city.bunkyo.lg.jp/toshikankyo/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['13106','13','東京都','台東区',209000,'A','https://www.city.taito.lg.jp/gomi_recycle/sodaigomi/','','','v2あり','空き','','',''],
    ['13107','13','東京都','墨田区',275000,'A','https://www.city.sumida.lg.jp/kurashi_guide/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['13108','13','東京都','江東区',524000,'A','https://www.city.koto.lg.jp/390001/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['13109','13','東京都','品川区',415000,'A','https://www.city.shinagawa.tokyo.jp/PC/kankyo/kankyo-gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['13110','13','東京都','目黒区',286000,'A','https://www.city.meguro.tokyo.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['13111','13','東京都','大田区',739000,'A','https://www.city.ota.tokyo.jp/seikatsu/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['13112','13','東京都','世田谷区',920000,'A','https://www.city.setagaya.lg.jp/mokuji/kurashi/002/004/d00138882.html','','','v2あり','空き','','',''],
    ['13113','13','東京都','渋谷区',232000,'A','https://www.city.shibuya.tokyo.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['13114','13','東京都','中野区',340000,'A','https://www.city.tokyo-nakano.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['13115','13','東京都','杉並区',579000,'A','https://www.city.suginami.tokyo.jp/guide/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['13116','13','東京都','豊島区',295000,'A','https://www.city.toshima.lg.jp/171/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['13117','13','東京都','北区',354000,'A','https://www.city.kita.tokyo.jp/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['13118','13','東京都','荒川区',216000,'A','https://www.city.arakawa.tokyo.jp/a038/kankyo/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['13119','13','東京都','板橋区',574000,'A','https://www.city.itabashi.tokyo.jp/kurashi/gomi_recycle/sodaigomi/','','','v2あり','空き','','',''],
    ['13120','13','東京都','練馬区',741000,'A','https://www.city.nerima.tokyo.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['13121','13','東京都','足立区',692000,'A','https://www.city.adachi.tokyo.jp/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['13122','13','東京都','葛飾区',458000,'A','https://www.city.katsushika.lg.jp/kurashi/1000058/1003839/1003845.html','','','v2あり','空き','','',''],
    ['13123','13','東京都','江戸川区',698000,'A','https://www.city.edogawa.tokyo.jp/e004/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    // --- 東京都 市部・町村 ---
    ['13201','13','東京都','八王子市',563000,'B','https://www.city.hachioji.tokyo.jp/kurashi/gomi/kateigomi/sodaigomi/','','','v2あり','空き','','',''],
    ['13202','13','東京都','立川市',185000,'C','https://www.city.tachikawa.lg.jp/shiminseikatsu/gomi/','','','v2あり','空き','','',''],
    ['13203','13','東京都','武蔵野市',149000,'C','https://www.city.musashino.lg.jp/kurashi_guide/gomi_recycle/','','','v2あり','空き','','',''],
    ['13204','13','東京都','三鷹市',195000,'C','https://www.city.mitaka.lg.jp/c_service/cat0029/','','','v2あり','空き','','',''],
    ['13205','13','東京都','青梅市',132000,'C','https://www.city.ome.tokyo.jp/soshiki/23/','','','v2あり','空き','','',''],
    ['13206','13','東京都','府中市',265000,'B','https://www.city.fuchu.tokyo.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['13207','13','東京都','昭島市',114000,'C','https://www.city.akishima.lg.jp/s032/010/020/010/','','','v2あり','空き','','',''],
    ['13208','13','東京都','調布市',240000,'B','https://www.city.chofu.lg.jp/kurashi/gomi/','','','v2あり','空き','','',''],
    ['13209','13','東京都','町田市',433000,'B','https://www.city.machida.tokyo.jp/kurashi/kankyo/gomishigen/sodaigomi/','','','v2あり','空き','','',''],
    ['13210','13','東京都','小金井市',122000,'C','https://www.city.koganei.lg.jp/smph/kurashi/gomi/','','','v2あり','空き','','',''],
    ['13211','13','東京都','小平市',196000,'C','https://www.city.kodaira.tokyo.jp/kurashi/002/002148.html','','','v2あり','空き','','',''],
    ['13212','13','東京都','日野市',186000,'C','https://www.city.hino.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['13213','13','東京都','東村山市',152000,'C','https://www.city.higashimurayama.tokyo.jp/kurashi/gomi/','','','v2あり','空き','','',''],
    ['13214','13','東京都','国分寺市',128000,'C','https://www.city.kokubunji.tokyo.jp/kurashi/2/7/','','','v2あり','空き','','',''],
    ['13215','13','東京都','国立市',78000,'C','https://www.city.kunitachi.tokyo.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['13218','13','東京都','福生市',58000,'C','https://www.city.fussa.tokyo.jp/life/garbege/sodaigomi/','','','v2あり','空き','','',''],
    ['13219','13','東京都','狛江市',85000,'C','https://www.city.komae.tokyo.jp/index.cfm/40,3617','','','v2あり','空き','','',''],
    ['13220','13','東京都','東大和市',85000,'C','https://www.city.higashiyamato.lg.jp/kurashi/gomishigen/sodaigomi/','','','v2あり','空き','','',''],
    ['13221','13','東京都','清瀬市',76000,'C','https://www.city.kiyose.lg.jp/kurashi/gomi/','','','v2あり','空き','','',''],
    ['13222','13','東京都','東久留米市',119000,'C','https://www.city.higashikurume.lg.jp/kurashi/gomi/','','','v2あり','空き','','',''],
    ['13223','13','東京都','武蔵村山市',72000,'C','https://www.city.musashimurayama.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['13224','13','東京都','多摩市',149000,'C','https://www.city.tama.tokyo.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['13225','13','東京都','稲城市',93000,'C','https://www.city.inagi.tokyo.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['13227','13','東京都','羽村市',57000,'C','https://www.city.hamura.tokyo.jp/0000001283.html','','','v2あり','空き','','',''],
    ['13228','13','東京都','あきる野市',81000,'C','https://www.city.akiruno.tokyo.jp/category/3-3-0-0-0-0-0-0-0-0.html','','','v2あり','空き','','',''],
    ['13229','13','東京都','西東京市',204000,'C','https://www.city.nishitokyo.lg.jp/kurasi/gomi_recycle/sodaigomi/','','','v2あり','空き','','',''],
    ['13303','13','東京都','瑞穂町',33000,'C','https://www.town.mizuho.tokyo.jp/kurashi/005/006/p000630.html','','','v2あり','空き','','',''],
    ['13305','13','東京都','日の出町',17000,'C','https://www.town.hinode.tokyo.jp/category/1-4-2-0-0-0-0-0-0-0.html','','','v2あり','空き','','',''],
    ['13307','13','東京都','檜原村',2200,'C','https://www.vill.hinohara.tokyo.jp/0000001092.html','','','v2あり','空き','','',''],
    ['13308','13','東京都','奥多摩町',5300,'C','https://www.town.okutama.tokyo.jp/gyosei/2/seikatsu_kankyo/gomi_recycle/1/1642.html','','','v2あり','空き','','',''],
    // --- 神奈川県 ---
    ['14100','14','神奈川県','横浜市',3778000,'A','https://www.city.yokohama.lg.jp/kurashi/machizukuri-kankyo/gomi-recycle/sodaigomi/','','','v2あり','空き','','',''],
    ['14130','14','神奈川県','川崎市',1536000,'A','https://www.city.kawasaki.jp/300/category/57-2-0-0-0-0-0-0-0-0.html','','','v2あり','空き','','',''],
    ['14150','14','神奈川県','相模原市',724000,'A','https://www.city.sagamihara.kanagawa.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['14201','14','神奈川県','横須賀市',401000,'B','https://www.city.yokosuka.kanagawa.jp/1810/sodaigomi/','','','v2あり','空き','','',''],
    ['14203','14','神奈川県','平塚市',263000,'B','https://www.city.hiratsuka.kanagawa.jp/kankyo/category/52-12-0-0-0-0-0-0-0-0.html','','','v2あり','空き','','',''],
    ['14204','14','神奈川県','鎌倉市',173000,'C','https://www.city.kamakura.kanagawa.jp/gomi/sodaigomi.html','','','v2あり','空き','','',''],
    ['14205','14','神奈川県','藤沢市',436000,'B','https://www.city.fujisawa.kanagawa.jp/kankyou/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['14206','14','神奈川県','小田原市',189000,'C','https://www.city.odawara.kanagawa.jp/public/kankyou/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['14207','14','神奈川県','茅ヶ崎市',244000,'B','https://www.city.chigasaki.kanagawa.jp/kankyo/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['14208','14','神奈川県','逗子市',59000,'C','https://www.city.zushi.kanagawa.jp/div/kankyouseisaku/gomi/','','','v2あり','空き','','',''],
    ['14210','14','神奈川県','厚木市',224000,'B','https://www.city.atsugi.kanagawa.jp/kurashi/kankyou/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['14211','14','神奈川県','大和市',241000,'B','https://www.city.yamato.kanagawa.jp/kankyo-gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['14212','14','神奈川県','伊勢原市',101000,'C','https://www.city.isehara.kanagawa.jp/docs/2013091900015/','','','v2あり','空き','','',''],
    ['14213','14','神奈川県','海老名市',136000,'C','https://www.city.ebina.kanagawa.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['14214','14','神奈川県','座間市',132000,'C','https://www.city.zama.kanagawa.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['14215','14','神奈川県','南足柄市',44000,'C','https://www.city.minamiashigara.kanagawa.jp/kankyou/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['14216','14','神奈川県','綾瀬市',84000,'C','https://www.city.ayase.kanagawa.jp/kurashi_guide/gomi/sodaigomi/','','','v2あり','空き','','',''],
    // --- 埼玉県 ---
    ['11100','11','埼玉県','さいたま市',1340000,'A','https://www.city.saitama.lg.jp/006/011/002/sodaigomi/','','','v2あり','空き','','',''],
    ['11201','11','埼玉県','川越市',354000,'B','https://www.city.kawagoe.saitama.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11202','11','埼玉県','熊谷市',193000,'C','https://www.city.kumagaya.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11203','11','埼玉県','川口市',601000,'B','https://www.city.kawaguchi.lg.jp/kurashi/19/120/2/2/','','','v2あり','空き','','',''],
    ['11204','11','埼玉県','行田市',80000,'C','https://www.city.gyoda.lg.jp/kurashi/gomi/sodaigomi.html','','','v2あり','空き','','',''],
    ['11206','11','埼玉県','秩父市',63000,'C','https://www.city.chichibu.lg.jp/1660.html','','','v2あり','空き','','',''],
    ['11207','11','埼玉県','所沢市',344000,'B','https://www.city.tokorozawa.saitama.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11208','11','埼玉県','飯能市',80000,'C','https://www.city.hanno.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11209','11','埼玉県','加須市',113000,'C','https://www.city.kazo.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11210','11','埼玉県','本庄市',78000,'C','https://www.city.honjo.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11211','11','埼玉県','東松山市',90000,'C','https://www.city.higashimatsuyama.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11213','11','埼玉県','春日部市',230000,'B','https://www.city.kasukabe.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11214','11','埼玉県','狭山市',152000,'C','https://www.city.sayama.saitama.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11215','11','埼玉県','羽生市',55000,'C','https://www.city.hanyu.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11216','11','埼玉県','鴻巣市',117000,'C','https://www.city.kounosu.saitama.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11217','11','埼玉県','深谷市',143000,'C','https://www.city.fukaya.saitama.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11218','11','埼玉県','上尾市',225000,'B','https://www.city.ageo.lg.jp/page/pageind.html','','','v2あり','空き','','',''],
    ['11220','11','埼玉県','草加市',249000,'B','https://www.city.soka.saitama.jp/cont/s1400/sodaigomi/','','','v2あり','空き','','',''],
    ['11221','11','埼玉県','越谷市',341000,'B','https://www.city.koshigaya.saitama.jp/kurashi_guide/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11222','11','埼玉県','蕨市',73000,'C','https://www.city.warabi.saitama.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11223','11','埼玉県','戸田市',139000,'C','https://www.city.toda.saitama.jp/0000015219.html','','','v2あり','空き','','',''],
    ['11224','11','埼玉県','入間市',148000,'C','https://www.city.iruma.saitama.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11226','11','埼玉県','朝霞市',141000,'C','https://www.city.asaka.lg.jp/site/kurashigu/sodaigomi.html','','','v2あり','空き','','',''],
    ['11227','11','埼玉県','志木市',78000,'C','https://www.city.shiki.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11228','11','埼玉県','和光市',82000,'C','https://www.city.wako.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11229','11','埼玉県','新座市',164000,'C','https://www.city.niiza.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11230','11','埼玉県','桶川市',74000,'C','https://www.city.okegawa.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11231','11','埼玉県','久喜市',154000,'C','https://www.city.kuki.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11232','11','埼玉県','北本市',68000,'C','https://www.city.kitamoto.saitama.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11233','11','埼玉県','八潮市',93000,'C','https://www.city.yashio.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11234','11','埼玉県','富士見市',115000,'C','https://www.city.fujimi.saitama.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11236','11','埼玉県','三郷市',141000,'C','https://www.city.misato.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11237','11','埼玉県','蓮田市',62000,'C','https://www.city.hasuda.saitama.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11238','11','埼玉県','坂戸市',101000,'C','https://www.city.sakado.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11239','11','埼玉県','幸手市',50000,'C','https://www.city.satte.saitama.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11240','11','埼玉県','鶴ヶ島市',70000,'C','https://www.city.tsurugashima.saitama.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11241','11','埼玉県','日高市',57000,'C','https://www.city.hidaka.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11242','11','埼玉県','吉川市',72000,'C','https://www.city.yoshikawa.saitama.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11244','11','埼玉県','ふじみ野市',115000,'C','https://www.city.fujimino.saitama.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['11245','11','埼玉県','白岡市',52000,'C','https://www.city.shiraoka.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    // --- 千葉県 ---
    ['12100','12','千葉県','千葉市',980000,'A','https://www.city.chiba.jp/kankyo/haikibutsu/sodaigomi/','','','v2あり','空き','','',''],
    ['12202','12','千葉県','銚子市',59000,'C','https://www.city.choshi.chiba.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['12203','12','千葉県','市川市',495000,'B','https://www.city.ichikawa.lg.jp/env01/1111000002.html','','','v2あり','空き','','',''],
    ['12204','12','千葉県','船橋市',644000,'B','https://www.city.funabashi.lg.jp/machi/gomi/002/p009786.html','','','v2あり','空き','','',''],
    ['12205','12','千葉県','館山市',45000,'C','https://www.city.tateyama.chiba.jp/kankyoubu/page100008.html','','','v2あり','空き','','',''],
    ['12206','12','千葉県','木更津市',137000,'C','https://www.city.kisarazu.lg.jp/kurashi/kankyou/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['12207','12','千葉県','松戸市',498000,'B','https://www.city.matsudo.chiba.jp/kurasi/gomi_houki/sodaigomi/','','','v2あり','空き','','',''],
    ['12208','12','千葉県','野田市',154000,'C','https://www.city.noda.chiba.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['12210','12','千葉県','茂原市',90000,'C','https://www.city.mobara.chiba.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['12211','12','千葉県','成田市',132000,'C','https://www.city.narita.chiba.jp/kanky/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['12212','12','千葉県','佐倉市',174000,'C','https://www.city.sakura.lg.jp/soshiki/kankyo/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['12214','12','千葉県','習志野市',175000,'C','https://www.city.narashino.lg.jp/joho/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['12215','12','千葉県','柏市',431000,'B','https://www.city.kashiwa.lg.jp/kankyou/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['12217','12','千葉県','市原市',272000,'B','https://www.city.ichihara.chiba.jp/kurasi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['12218','12','千葉県','流山市',208000,'C','https://www.city.nagareyama.chiba.jp/section/kankyo-kanri/sodaigomi.html','','','v2あり','空き','','',''],
    ['12219','12','千葉県','八千代市',199000,'C','https://www.city.yachiyo.chiba.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['12220','12','千葉県','我孫子市',131000,'C','https://www.city.abiko.chiba.jp/kankyou/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['12222','12','千葉県','鎌ヶ谷市',108000,'C','https://www.city.kamagaya.chiba.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['12224','12','千葉県','君津市',86000,'C','https://www.city.kimitsu.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['12225','12','千葉県','富津市',48000,'C','https://www.city.futtsu.lg.jp/kankyou/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['12226','12','千葉県','浦安市',165000,'C','https://www.city.urayasu.lg.jp/municipal/waste/large/','','','v2あり','空き','','',''],
    ['12228','12','千葉県','四街道市',93000,'C','https://www.city.yotsukaido.chiba.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['12231','12','千葉県','袖ケ浦市',63000,'C','https://www.city.sodegaura.lg.jp/kankyou/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['12233','12','千葉県','印西市',106000,'C','https://www.city.inzai.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['12234','12','千葉県','白井市',62000,'C','https://www.city.shiroi.chiba.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    // --- 茨城県 ---
    ['08201','08','茨城県','水戸市',271000,'B','https://www.city.mito.lg.jp/page/001500.html','','','v2あり','空き','','',''],
    ['08202','08','茨城県','日立市',186000,'C','https://www.city.hitachi.lg.jp/gomi_kankyou/cat50002/p027948.html','','','v2あり','空き','','',''],
    ['08203','08','茨城県','土浦市',142000,'C','https://www.city.tsuchiura.lg.jp/page/page000379.html','','','v2あり','空き','','',''],
    ['08204','08','茨城県','古河市',145000,'C','https://www.city.ibaraki-koga.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['08205','08','茨城県','石岡市',72000,'C','https://www.city.ishioka.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['08207','08','茨城県','結城市',52000,'C','https://www.city.yuki.ibaraki.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['08210','08','茨城県','龍ケ崎市',78000,'C','https://www.city.ryugasaki.ibaraki.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['08215','08','茨城県','取手市',105000,'C','https://www.city.toride.ibaraki.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['08217','08','茨城県','牛久市',83000,'C','https://www.city.ushiku.ibaraki.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['08218','08','茨城県','つくば市',241000,'B','https://www.city.tsukuba.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['08220','08','茨城県','ひたちなか市',157000,'C','https://www.city.hitachinaka.ibaraki.jp/kankyou/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['08221','08','茨城県','鹿嶋市',68000,'C','https://www.city.kashima.ibaraki.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['08222','08','茨城県','潮来市',28000,'C','https://www.city.itako.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['08224','08','茨城県','守谷市',68000,'C','https://www.city.moriya.ibaraki.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['08232','08','茨城県','筑西市',102000,'C','https://www.city.chikusei.ibaraki.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    // --- 栃木県 ---
    ['09201','09','栃木県','宇都宮市',524000,'B','https://www.city.utsunomiya.tochigi.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['09202','09','栃木県','足利市',149000,'C','https://www.city.ashikaga.tochigi.jp/kankyou/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['09203','09','栃木県','栃木市',158000,'C','https://www.city.tochigi.lg.jp/site/gomi/sodaigomi.html','','','v2あり','空き','','',''],
    ['09204','09','栃木県','佐野市',118000,'C','https://www.city.sano.tochigi.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['09205','09','栃木県','鹿沼市',99000,'C','https://www.city.kanuma.tochigi.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['09206','09','栃木県','日光市',82000,'C','https://www.city.nikko.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['09208','09','栃木県','小山市',169000,'B','https://www.city.oyama.tochigi.jp/kankyou/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['09209','09','栃木県','真岡市',80000,'C','https://www.city.moka.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['09210','09','栃木県','大田原市',72000,'C','https://www.city.ohtawara.tochigi.jp/kankyou/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['09212','09','栃木県','那須塩原市',116000,'C','https://www.city.nasushiobara.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['09214','09','栃木県','下野市',60000,'C','https://www.city.shimotsuke.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    // --- 群馬県 ---
    ['10201','10','群馬県','前橋市',336000,'B','https://www.city.maebashi.gunma.jp/kurashi/1/4/2/index.html','','','v2あり','空き','','',''],
    ['10202','10','群馬県','高崎市',371000,'B','https://www.city.takasaki.gunma.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['10203','10','群馬県','桐生市',110000,'C','https://www.city.kiryu.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['10204','10','群馬県','伊勢崎市',214000,'C','https://www.city.isesaki.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['10205','10','群馬県','太田市',223000,'B','https://www.city.ota.gunma.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['10206','10','群馬県','沼田市',53000,'C','https://www.city.numata.gunma.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['10207','10','群馬県','館林市',76000,'C','https://www.city.tatebayashi.gunma.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['10208','10','群馬県','渋川市',78000,'C','https://www.city.shibukawa.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['10209','10','群馬県','藤岡市',65000,'C','https://www.city.fujioka.gunma.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['10210','10','群馬県','富岡市',48000,'C','https://www.city.tomioka.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['10212','10','群馬県','みどり市',50000,'C','https://www.city.midori.gunma.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],

    // ==================== 大阪（33都市）====================
    ['27100','27','大阪府','大阪市',2752000,'A','https://www.city.osaka.lg.jp/kankyo/page/0000006476.html','','','v2あり','空き','','',''],
    ['27140','27','大阪府','堺市',820000,'A','https://www.city.sakai.lg.jp/kurashi/gomi/sodaigomi/','','','v2あり','空き','','',''],
    ['27201','27','大阪府','岸和田市',185000,'C','https://www.city.kishiwada.osaka.jp/soshiki/170/dasikata.html','','','v2あり','空き','','',''],
    ['27202','27','大阪府','豊中市',404000,'B','https://www.city.toyonaka.osaka.jp/kurashi/gomi_risaikuru_bika/bunbetsu_dashikata/sodaigomi_dashikata.html','','','v2あり','空き','','',''],
    ['27203','27','大阪府','池田市',103000,'C','https://www.city.ikeda.osaka.jp/soshiki/19/1011.html','','','v2あり','空き','','',''],
    ['27204','27','大阪府','吹田市',384000,'B','https://www.city.suita.osaka.jp/home/soshiki/div-kankyogesuidokyoku/kankyohozen/gomi/gomi_data/sodaigomi.html','','','v2あり','空き','','',''],
    ['27205','27','大阪府','泉大津市',76000,'C','https://www.city.izumiotsu.lg.jp/soshiki/4/384.html','','','v2あり','空き','','',''],
    ['27206','27','大阪府','高槻市',346000,'B','https://www.city.takatsuki.osaka.jp/soshiki/42/sodaigomi.html','','','v2あり','空き','','',''],
    ['27207','27','大阪府','貝塚市',89000,'C','https://www.city.kaizuka.lg.jp/kakuka/shiminseikatsu/haiki/menu/gomi/sodaigomi.html','','','v2あり','空き','','',''],
    ['27208','27','大阪府','守口市',141000,'C','https://www.city.moriguchi.osaka.jp/kakukanoannai/kankyougesuidoubu/haikibututaisakuka/gomirecycle/gominodashikatashushunitsuite/1750.html','','','v2あり','空き','','',''],
    ['27209','27','大阪府','枚方市',393000,'B','https://www.city.hirakata.osaka.jp/0000002820.html','','','v2あり','空き','','',''],
    ['27210','27','大阪府','茨木市',286000,'B','https://www.city.ibaraki.osaka.jp/kikou/sangyo/kankyoj/menu/sodaigomi.html','','','v2あり','空き','','',''],
    ['27211','27','大阪府','八尾市',265000,'B','https://www.city.yao.osaka.jp/kurashi_tetsuzuki/gomi_recycle/1003102/1003135/1003137.html','','','v2あり','空き','','',''],
    ['27212','27','大阪府','泉佐野市',100000,'C','https://www.city.izumisano.lg.jp/kakuka/seikatsu/kankyo/menu/gomi/gomi_katei/1438582381136.html','','','v2あり','空き','','',''],
    ['27213','27','大阪府','富田林市',110000,'C','https://www.city.tondabayashi.lg.jp/soshiki/17/1995.html','','','v2あり','空き','','',''],
    ['27214','27','大阪府','寝屋川市',229000,'B','https://www.city.neyagawa.osaka.jp/organization_list/kankyo/kankyoujigyou/moti/1590626319945.html','','','v2あり','空き','','',''],
    ['27215','27','大阪府','河内長野市',102000,'C','https://www.city.kawachinagano.lg.jp/soshiki/15/1829.html','','','v2あり','空き','','',''],
    ['27216','27','大阪府','松原市',118000,'C','https://www.city.matsubara.lg.jp/docs/page2804.html','','','v2あり','空き','','',''],
    ['27217','27','大阪府','大東市',119000,'C','https://www.city.daito.lg.jp/soshiki/17/39298.html','','','v2あり','空き','','',''],
    ['27218','27','大阪府','和泉市',183000,'B','https://www.city.osaka-izumi.lg.jp/kurasitetu/gomi_recycle/sodaigomi/1317281357111.html','','','v2あり','空き','','',''],
    ['27219','27','大阪府','箕面市',133000,'C','https://www.city.minoh.lg.jp/seibi/02_howto/03how_to_oogatagomi.html','','','v2あり','空き','','',''],
    ['27220','27','大阪府','柏原市',70000,'C','https://www.city.kashiwara.osaka.jp/bunya/gomi_recycle/','','','v2あり','空き','','',''],
    ['27221','27','大阪府','羽曳野市',111000,'C','https://www.city.habikino.lg.jp/soshiki/shiminjinken/kankyouhozen/seikan_eisei_gomi/index.html','','','v2あり','空き','','',''],
    ['27222','27','大阪府','門真市',121000,'C','https://www.city.kadoma.osaka.jp/kurashi/gomi/9/5/22407.html','','','v2あり','空き','','',''],
    ['27223','27','大阪府','摂津市',85000,'C','https://www.city.settsu.osaka.jp/kurashi/kankyou/gomi/dashikata/index.html','','','v2あり','空き','','',''],
    ['27224','27','大阪府','高石市',57000,'C','https://www.city.takaishi.lg.jp/kakuka/doboku/seikatu_kankyou_ka/gomi/gomi_syuusyuu.html','','','v2あり','空き','','',''],
    ['27225','27','大阪府','藤井寺市',64000,'C','https://www.city.fujiidera.lg.jp/soshiki/shiminseikatsu/kankyoeisei/gomi_shinyo/gomidashi/1387339564836.html','','','v2あり','空き','','',''],
    ['27227','27','大阪府','東大阪市',495000,'A','https://www.city.higashiosaka.lg.jp/soshiki/38/sodaigomi.html','','','v2あり','空き','','',''],
    ['27228','27','大阪府','泉南市',60000,'C','https://www.city.sennan.lg.jp/kakuka/shiminseikatu/seiso/zenpan/gomi/gominobumbetsutodashikata/10527.html','','','v2あり','空き','','',''],
    ['27229','27','大阪府','四條畷市',56000,'C','https://www.city.shijonawate.lg.jp/soshiki/16/15071.html','','','v2あり','空き','','',''],
    ['27230','27','大阪府','交野市',77000,'C','https://www.city.katano.osaka.jp/docs/2022112200039/','','','v2あり','空き','','',''],
    ['27231','27','大阪府','大阪狭山市',58000,'C','https://www.city.osakasayama.osaka.jp/sosiki/siminseikatsubu/seikatsukankyogurupu/1/gomi/5/3/1411355157445.html','','','v2あり','空き','','',''],
    ['27232','27','大阪府','阪南市',53000,'C','https://www.city.hannan.lg.jp/kakuka/shimin/shigen1/bunbetu/1526609414614.html','','','v2あり','空き','','',''],
  ];

  // 一括書き込み（appendRow より setValues の方が高速）
  sheet.getRange(2, 1, rows.length, rows[0].length).setValues(rows);

  // 統計を集計してログ出力
  const kantoCount = rows.filter(r => ['08','09','10','11','12','13','14'].includes(String(r[1]))).length;
  const osakaCount = rows.filter(r => String(r[1]) === '27').length;

  Logger.log(`都市マスタインポート完了！`);
  Logger.log(`  関東: ${kantoCount}都市`);
  Logger.log(`  大阪: ${osakaCount}都市`);
  Logger.log(`  合計: ${rows.length}都市`);
}

// ============================================================
// H. トリガー一括設定（初回1回だけ手動実行）
//    既存トリガーをすべて削除してから再設定する
// ============================================================
function setupAllTriggers() {
  // 既存のトリガーをすべて削除する
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));

  // 毎日9:00 — リマインドメール送信（契約満了通知・更新案内）
  ScriptApp.newTrigger('sendReminders')
    .timeBased()
    .everyDays(1)
    .atHour(9)
    .create();

  // 毎月1日 2:00 — 全国自治体ページのURLスクレイピング
  // ※ 1回あたり最大280件処理。815市区全件は複数回に分割実行する想定
  ScriptApp.newTrigger('monthlyUrlCheck')
    .timeBased()
    .onMonthDay(1)
    .atHour(2)
    .create();

  // スポンサー申込フォーム連携トリガー
  // ※ 申込フォームをスプレッドシートに接続した後、下記コメントアウトを外して再実行すること
  // ScriptApp.newTrigger('onFormSubmit')
  //   .forSpreadsheet(SpreadsheetApp.getActiveSpreadsheet())
  //   .onFormSubmit()
  //   .create();

  // 素材入稿フォーム連携トリガー
  // ※ 素材入稿用Googleフォームのスクリプトエディタでフォーム送信トリガーとして設定すること
  //   （スプレッドシート側ではなくフォーム側のトリガーとして登録する）
  // ScriptApp.newTrigger('onMaterialSubmit')
  //   .forForm(FormApp.openByUrl('YOUR_MATERIAL_FORM_URL'))
  //   .onFormSubmit()
  //   .create();

  Logger.log('トリガー設定完了！');
  Logger.log('  - sendReminders: 毎日 9:00');
  Logger.log('  - monthlyUrlCheck: 毎月1日 2:00');
  Logger.log('  ※ 申込フォーム連携は onFormSubmit のコメントアウトを外して再実行してください');
  Logger.log('  ※ 素材入稿フォーム連携は onMaterialSubmit のコメントアウトを外し、フォームURLを設定して再実行してください');
}
