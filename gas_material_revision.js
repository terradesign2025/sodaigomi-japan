/**
 * 粗大ごみ判定アプリ 全国版
 * 素材提出・修正ワークフロー管理スクリプト
 * 株式会社テラデザイン
 *
 * ── このファイルについて ──────────────────────────────────────────────
 * gas_sponsor_manager_v3.js と同一 GAS プロジェクトに追加するアドオンです。
 * CONFIG オブジェクトは gas_sponsor_manager_v3.js で定義済みのものを参照します。
 *
 * ── 素材提出フォーム（Googleフォーム）との接続方法 ────────────────────
 * 1. Googleフォームを新規作成し、以下の設問を追加する（設問タイトルを完全一致させること）
 *
 *    設問タイトル                  → onMaterialSubmitRevision() の引数へのマッピング
 *    -------------------------------------------------------------------
 *    「契約ID」                    → contractId  （例: SP2026-0001）
 *    「提出ラウンド」（プルダウン）  → round       （選択肢: 1回目 / 2回目 / 3回目）
 *    「会社名」                    → materialData.company
 *    「都市名」                    → materialData.city  ※「会社名」「都市名」は確認用
 *    「広告見出し（30字以内）」     → materialData.adHeadline
 *    「広告本文（80字以内）」       → materialData.adBody
 *    「電話番号」                  → materialData.phone
 *    「会社URL」                   → materialData.companyUrl
 *    「ロゴ画像URL（GoogleドライブURL可）」 → materialData.logoUrl
 *    「管理者へのメモ（任意）」     → materialData.adminNote
 *
 * 2. フォームの「回答」→「スプレッドシートにリンク」で本スプレッドシートに連携する
 * 3. GAS のトリガー設定（setupAllTriggers に追記）で「フォーム送信時」→ onMaterialSubmitRevision を紐付ける
 *    または、フォームのスクリプトエディタ側でトリガーを設定する
 *
 * ── 各関数の実行タイミング ─────────────────────────────────────────────
 * initMaterialSheets()           → 初回セットアップ時（手動1回）
 * onMaterialSubmitRevision()     → Googleフォーム送信時（自動）
 * requestRevision(contractId)    → 修正依頼時（管理者がスクリプトエディタから手動実行）
 * approveMaterial(contractId)    → 承認時（管理者がスクリプトエディタから手動実行）
 *
 * ── CONFIG への追記が必要な設定項目 ───────────────────────────────────
 * gas_sponsor_manager_v3.js の CONFIG オブジェクトに以下を追加してください：
 *
 *   MATERIAL_FORM_URL: 'https://forms.gle/XXXXXXXXXXXXXXXX',  // 素材提出フォームのURL
 *   SHEET_MATERIALS: '素材管理',
 *   SHEET_REVISION_LOG: '修正履歴',
 */

// ============================================================
// シート名定数（CONFIG に未追加の場合のフォールバック用）
// ============================================================
const SHEET_MATERIALS    = (typeof CONFIG !== 'undefined' && CONFIG.SHEET_MATERIALS)    ? CONFIG.SHEET_MATERIALS    : '素材管理';
const SHEET_REVISION_LOG = (typeof CONFIG !== 'undefined' && CONFIG.SHEET_REVISION_LOG) ? CONFIG.SHEET_REVISION_LOG : '修正履歴';

// 素材提出フォームURL（CONFIG に MATERIAL_FORM_URL が設定済みの場合はそちらを優先）
const MATERIAL_FORM_URL_ = (typeof CONFIG !== 'undefined' && CONFIG.MATERIAL_FORM_URL)
  ? CONFIG.MATERIAL_FORM_URL
  : 'https://forms.gle/（要設定）';

// ============================================================
// 1. initMaterialSheets()
//    「素材管理」「修正履歴」の2シートを初期化する
//    gas_sponsor_manager_v3.js の initSpreadsheet() 実行後に1回だけ手動実行すること
// ============================================================
function initMaterialSheets() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  // ── シート1: 素材管理 ───────────────────────────────────────────────
  // 1スポンサー1行で管理。ラウンドごとの入稿日を列で管理することで
  // 「今何ラウンド目か」「いつ提出があったか」を一目で確認できる設計
  const materialHeaders = [
    '契約ID',       // 例: SP2026-0001（契約管理シートと紐付け）
    '会社名',
    '都市',
    '現在のラウンド', // 数値: 1〜3
    '状態',          // 下記「状態マスタ」参照
    '入稿1回目日',
    '入稿2回目日',
    '入稿3回目日',
    '承認日',
    '公開日',
    '備考',
  ];
  // 状態マスタ（セルに手動入力 or onMaterialSubmitRevision / requestRevision / approveMaterial から自動更新）:
  //   素材未提出 → 審査中(R1) → 修正依頼(R1) → 審査中(R2) → 修正依頼(R2) → 審査中(R3)
  //   → 承認済み → 公開済み
  //   または: 差し戻し（3回目も修正不可の場合）

  let matSheet = ss.getSheetByName(SHEET_MATERIALS);
  if (!matSheet) {
    matSheet = ss.insertSheet(SHEET_MATERIALS);
  }
  if (matSheet.getRange('A1').getValue() === '') {
    matSheet.getRange(1, 1, 1, materialHeaders.length)
      .setValues([materialHeaders])
      .setFontWeight('bold')
      .setBackground('#d9ead3'); // 淡いグリーン
    matSheet.setFrozenRows(1);
    matSheet.setColumnWidth(1, 130);  // 契約ID
    matSheet.setColumnWidth(5, 160);  // 状態
  }

  // ── シート2: 修正履歴 ───────────────────────────────────────────────
  // 操作ログとして全アクションを時系列で記録する
  // 誰が・いつ・何をしたかを追跡できるようにする
  const revLogHeaders = [
    '記録日時',          // 例: 2026/05/25 10:30:00
    '契約ID',
    '会社名',
    '都市',
    'ラウンド',          // 数値: 1〜3
    'アクション',        // 「素材提出」「修正依頼」「承認」など
    '担当者メモ',        // requestRevision の adminNote など
    '送信メールの件名',  // 送信したメールの件名（追跡用）
  ];

  let revSheet = ss.getSheetByName(SHEET_REVISION_LOG);
  if (!revSheet) {
    revSheet = ss.insertSheet(SHEET_REVISION_LOG);
  }
  if (revSheet.getRange('A1').getValue() === '') {
    revSheet.getRange(1, 1, 1, revLogHeaders.length)
      .setValues([revLogHeaders])
      .setFontWeight('bold')
      .setBackground('#fce5cd'); // 淡いオレンジ
    revSheet.setFrozenRows(1);
    revSheet.setColumnWidth(1, 160);  // 記録日時
    revSheet.setColumnWidth(7, 250);  // 担当者メモ
    revSheet.setColumnWidth(8, 300);  // 送信メールの件名
  }

  Logger.log('素材管理・修正履歴シートの初期化が完了しました。');
  Logger.log('次のステップ: Googleフォームを作成し、onMaterialSubmitRevision のトリガーを設定してください。');
}

// ============================================================
// 2. onMaterialSubmitRevision(contractId, round, materialData)
//    素材提出時に Googleフォームの onFormSubmit トリガーから呼び出す
//
//    引数:
//      contractId  : 契約ID（例: SP2026-0001）
//      round       : 提出ラウンド（1〜3の数値）
//      materialData: {
//                     company     : 会社名（確認用）
//                     city        : 都市名（確認用）
//                     adHeadline  : 広告見出し（30字以内）
//                     adBody      : 広告本文（80字以内）
//                     phone       : 電話番号
//                     companyUrl  : 会社URL
//                     logoUrl     : ロゴ画像URL
//                     adminNote   : 管理者へのメモ（任意）
//                   }
//
//    Googleフォームのトリガーから直接呼び出す場合の例:
//      function onFormSubmitMaterial(e) {
//        const form = {};
//        e.response.getItemResponses().forEach(r => {
//          form[r.getItem().getTitle()] = r.getResponse();
//        });
//        const roundMap = { '1回目': 1, '2回目': 2, '3回目': 3 };
//        onMaterialSubmitRevision(
//          (form['契約ID'] || '').trim(),
//          roundMap[form['提出ラウンド']] || 1,
//          {
//            company    : form['会社名'] || '',
//            city       : form['都市名'] || '',
//            adHeadline : form['広告見出し（30字以内）'] || '',
//            adBody     : form['広告本文（80字以内）'] || '',
//            phone      : form['電話番号'] || '',
//            companyUrl : form['会社URL'] || '',
//            logoUrl    : form['ロゴ画像URL（GoogleドライブURL可）'] || '',
//            adminNote  : form['管理者へのメモ（任意）'] || '',
//          }
//        );
//      }
// ============================================================
function onMaterialSubmitRevision(contractId, round, materialData) {
  try {
    // ── 引数バリデーション ───────────────────────────────────────────
    if (!contractId || !contractId.trim()) {
      _notifyAdminError('素材提出', '契約IDが空です。フォームの「契約ID」設問を確認してください。', contractId);
      return;
    }
    if (!round || round < 1 || round > 3) {
      _notifyAdminError('素材提出', `ラウンド番号が不正です（受信値: ${round}）。1〜3の数値である必要があります。`, contractId);
      return;
    }

    const cid       = contractId.trim();
    const company   = (materialData.company   || '').trim();
    const city      = (materialData.city      || '').trim();
    const ts        = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy/MM/dd HH:mm:ss');
    const today     = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy/MM/dd');
    const newStatus = `審査中(R${round})`;

    // ── 「素材管理」シートを更新 ──────────────────────────────────────
    const ss       = SpreadsheetApp.getActiveSpreadsheet();
    const matSheet = ss.getSheetByName(SHEET_MATERIALS);
    if (!matSheet) {
      _notifyAdminError('素材提出', '「素材管理」シートが見つかりません。initMaterialSheets() を実行してください。', cid);
      return;
    }

    const matData  = matSheet.getDataRange().getValues();
    const mH       = matData[0];
    const mCol = {
      CID:    mH.indexOf('契約ID'),
      CO:     mH.indexOf('会社名'),
      CITY:   mH.indexOf('都市'),
      ROUND:  mH.indexOf('現在のラウンド'),
      STATUS: mH.indexOf('状態'),
      D1:     mH.indexOf('入稿1回目日'),
      D2:     mH.indexOf('入稿2回目日'),
      D3:     mH.indexOf('入稿3回目日'),
    };

    let targetRow = -1; // 見つかった行（1始まり）

    // 既存行を探す
    for (let i = 1; i < matData.length; i++) {
      if (String(matData[i][mCol.CID]).trim() === cid) {
        targetRow = i + 1; // シート実行番号
        break;
      }
    }

    if (targetRow < 0) {
      // 該当する契約IDが「素材管理」になければ新規追加
      // （契約登録と同時に「素材未提出」行を作っていない場合もあるため）
      const newRow = [
        cid, company, city,
        round,        // 現在のラウンド
        newStatus,    // 状態
        round === 1 ? today : '',
        round === 2 ? today : '',
        round === 3 ? today : '',
        '', '',       // 承認日・公開日
        '',           // 備考
      ];
      matSheet.appendRow(newRow);
      Logger.log(`素材管理: 新規行を追加しました（${cid}）`);
    } else {
      // 既存行を更新
      matSheet.getRange(targetRow, mCol.STATUS + 1).setValue(newStatus);
      matSheet.getRange(targetRow, mCol.ROUND  + 1).setValue(round);
      // 入稿日を記録（1回目〜3回目の対応列に書き込む）
      const dateCol = [mCol.D1, mCol.D2, mCol.D3][round - 1];
      if (dateCol >= 0) matSheet.getRange(targetRow, dateCol + 1).setValue(today);
      Logger.log(`素材管理: 既存行を更新しました（${cid} → ${newStatus}）`);
    }

    // ── 「修正履歴」シートに記録 ─────────────────────────────────────
    const mailSubjectAdmin = `【素材審査依頼 R${round}】${city} / ${company}`;
    _appendRevisionLog(ts, cid, company, city, round, '素材提出', materialData.adminNote || '', mailSubjectAdmin);

    // ── 管理者に審査依頼メールを送信 ─────────────────────────────────
    const ssUrl   = SpreadsheetApp.getActiveSpreadsheet().getUrl();
    const adminBody =
`──────────────────────────────────
スポンサー素材の審査依頼（ラウンド ${round}）
──────────────────────────────────
契約ID    : ${cid}
会社名    : ${company}
都市      : ${city}
提出日時  : ${ts}
──────────────────────────────────
■ 提出素材
──────────────────────────────────
広告見出し（30字以内）: ${materialData.adHeadline || '（未入力）'}
広告本文（80字以内）  : ${materialData.adBody     || '（未入力）'}
電話番号              : ${materialData.phone       || '（未入力）'}
会社URL               : ${materialData.companyUrl  || '（未入力）'}
ロゴ画像URL           : ${materialData.logoUrl     || '（未入力）'}
管理者へのメモ        : ${materialData.adminNote   || '（なし）'}
──────────────────────────────────
■ 審査後の操作
──────────────────────────────────
✅ 承認する場合  → approveMaterial("${cid}") をスクリプトエディタで実行
❌ 修正依頼の場合 → requestRevision("${cid}", "修正内容のメモ") をスクリプトエディタで実行

スプレッドシート（素材管理シート）:
${ssUrl}`;

    MailApp.sendEmail({
      to:      CONFIG.ADMIN_EMAIL,
      subject: mailSubjectAdmin,
      body:    adminBody,
      name:    CONFIG.FROM_NAME,
    });

    // ── スポンサーに受領確認メールを送信 ─────────────────────────────
    // 契約管理シートからメールアドレスを取得する
    const sponsorEmail = _getSponsorEmail(cid);
    if (sponsorEmail) {
      const mailSubjectSponsor = `【素材受領のご確認 R${round}】${city} スポンサー枠 [${cid}]`;
      const sponsorBody =
`${company} ご担当者様

このたびはご多忙のところ掲載素材をご提出いただきありがとうございます。
以下の内容で第${round}回目の素材を受領いたしました。

━━━━━━━━━━━━━━━━━━━━━━━
■ 受領内容（ラウンド ${round}）
━━━━━━━━━━━━━━━━━━━━━━━
契約番号    : ${cid}
掲載都市    : ${city}
広告見出し  : ${materialData.adHeadline || '（未入力）'}
広告本文    : ${materialData.adBody     || '（未入力）'}
電話番号    : ${materialData.phone      || '（未入力）'}
掲載URL     : ${materialData.companyUrl || '（未入力）'}
ロゴ画像URL : ${materialData.logoUrl    || '（未入力）'}
━━━━━━━━━━━━━━━━━━━━━━━

内容を確認後、修正依頼または承認のご連絡をいたします。
しばらくお待ちください。

なお、修正依頼がある場合は引き続き同じ素材提出フォームよりご対応ください。
（修正回数は最大3回まで承っております）

────────────────────────
${CONFIG.COMPANY_NAME}
Mail: ${CONFIG.CONTACT_EMAIL}
────────────────────────`;

      MailApp.sendEmail({
        to:      sponsorEmail,
        subject: mailSubjectSponsor,
        body:    sponsorBody,
        name:    CONFIG.FROM_NAME,
      });
    } else {
      // メールアドレスが取得できない場合は管理者に通知
      MailApp.sendEmail({
        to:      CONFIG.ADMIN_EMAIL,
        subject: `【要確認】スポンサー受領メール未送信 [${cid}]`,
        body:    `契約管理シートに ${cid} のメールアドレスが見つかりませんでした。\n手動でスポンサーに受領確認メールをお送りください。`,
      });
    }

    appendLog('素材提出受付', sponsorEmail || cid, `R${round} ${city} ${company} [${cid}]`);
    Logger.log(`onMaterialSubmitRevision 完了: ${cid} R${round}`);

  } catch (err) {
    _notifyAdminError('素材提出処理', err.toString(), contractId);
  }
}

// ============================================================
// 3. requestRevision(contractId, adminNote)
//    管理者が内容を確認後、スクリプトエディタから手動実行する修正依頼関数
//
//    引数:
//      contractId : 修正を依頼する契約ID（例: SP2026-0001）
//      adminNote  : スポンサーに伝える修正内容のメモ
//                   例: 'ロゴ画像が低解像度です。120×120px以上でご再提出ください。'
//
//    実行例（スクリプトエディタのコンソールから）:
//      requestRevision('SP2026-0001', 'ロゴ画像が低解像度です。120×120px以上でご再提出ください。')
// ============================================================
function requestRevision(contractId, adminNote) {
  try {
    if (!contractId || !contractId.trim()) {
      Logger.log('ERROR: contractId が空です。');
      return;
    }
    const cid = contractId.trim();

    // ── 「素材管理」シートで該当行を探す ─────────────────────────────
    const ss       = SpreadsheetApp.getActiveSpreadsheet();
    const matSheet = ss.getSheetByName(SHEET_MATERIALS);
    if (!matSheet) {
      _notifyAdminError('修正依頼', '「素材管理」シートが見つかりません。', cid);
      return;
    }

    const matData = matSheet.getDataRange().getValues();
    const mH      = matData[0];
    const mCol = {
      CID:    mH.indexOf('契約ID'),
      CO:     mH.indexOf('会社名'),
      CITY:   mH.indexOf('都市'),
      ROUND:  mH.indexOf('現在のラウンド'),
      STATUS: mH.indexOf('状態'),
    };

    let targetRow    = -1;
    let currentRound = 0;
    let company      = '';
    let city         = '';

    for (let i = 1; i < matData.length; i++) {
      if (String(matData[i][mCol.CID]).trim() === cid) {
        targetRow    = i + 1;
        currentRound = parseInt(matData[i][mCol.ROUND], 10) || 0;
        company      = matData[i][mCol.CO]   || '';
        city         = matData[i][mCol.CITY] || '';
        break;
      }
    }

    if (targetRow < 0) {
      Logger.log(`ERROR: 契約ID「${cid}」が素材管理シートに見つかりませんでした。`);
      MailApp.sendEmail({
        to:      CONFIG.ADMIN_EMAIL,
        subject: `【エラー】修正依頼失敗 [${cid}]`,
        body:    `素材管理シートに「${cid}」が見つかりませんでした。先に素材を提出させてください。`,
      });
      return;
    }

    // ── ラウンド制限チェック ──────────────────────────────────────────
    // 3回目は修正依頼不可→差し戻しのみ
    if (currentRound >= 3) {
      Logger.log(`INFO: ${cid} はラウンド3に到達しています。差し戻しを行います。`);
      _processDismissal(matSheet, targetRow, mCol, cid, company, city, adminNote);
      return;
    }

    // ── 状態を「修正依頼(R{現在のラウンド})」に更新 ───────────────────
    const newStatus = `修正依頼(R${currentRound})`;
    const ts        = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy/MM/dd HH:mm:ss');
    matSheet.getRange(targetRow, mCol.STATUS + 1).setValue(newStatus);

    // ── 「修正履歴」シートに記録 ─────────────────────────────────────
    const mailSubject = `【修正のお願い】${city} スポンサー掲載素材について`;
    _appendRevisionLog(ts, cid, company, city, currentRound, '修正依頼', adminNote || '', mailSubject);

    // ── スポンサーに修正依頼メールを送信 ─────────────────────────────
    const sponsorEmail = _getSponsorEmail(cid);
    if (!sponsorEmail) {
      _notifyAdminError('修正依頼', `${cid} のメールアドレスが取得できませんでした。手動でご連絡ください。`, cid);
    } else {
      const nextRound = currentRound + 1;
      const sponsorBody =
`${company} ご担当者様

いつも「${CONFIG.SITE_NAME}」のスポンサーとしてご支援いただきありがとうございます。

先日ご提出いただいた掲載素材（第${currentRound}回）を拝見しました。
誠に恐れ入りますが、以下の点について修正をお願いいたします。

━━━━━━━━━━━━━━━━━━━━━━━
■ 修正のお願い
━━━━━━━━━━━━━━━━━━━━━━━
${adminNote || '（担当者よりご連絡いたします）'}

━━━━━━━━━━━━━━━━━━━━━━━
■ 修正後の再提出先（第${nextRound}回目）
━━━━━━━━━━━━━━━━━━━━━━━
${MATERIAL_FORM_URL_}

フォームの「提出ラウンド」は「${nextRound}回目」をお選びください。
また「契約ID」欄には「${cid}」とご入力ください。

なお、修正回数は最大3回まで承っております。
3回の修正後も掲載基準を満たさない場合は、掲載をお断りする場合がございます。
あらかじめご了承ください。

ご不明な点がございましたら本メールへご返信ください。

────────────────────────
${CONFIG.COMPANY_NAME}
Mail: ${CONFIG.CONTACT_EMAIL}
────────────────────────`;

      MailApp.sendEmail({
        to:      sponsorEmail,
        subject: mailSubject,
        body:    sponsorBody,
        name:    CONFIG.FROM_NAME,
      });
    }

    // 管理者へも修正依頼した旨を記録メール
    MailApp.sendEmail({
      to:      CONFIG.ADMIN_EMAIL,
      subject: `【修正依頼送信済み R${currentRound}】${city} / ${company} [${cid}]`,
      body:    `スポンサーに修正依頼メールを送信しました。\n\n契約ID: ${cid}\n会社名: ${company}\n都市: ${city}\n修正内容メモ: ${adminNote || '（なし）'}\n\n第${currentRound + 1}回目の素材提出をお待ちください。`,
    });

    appendLog('修正依頼送信', sponsorEmail || cid, `R${currentRound} ${city} ${company} [${cid}]`);
    Logger.log(`requestRevision 完了: ${cid} → ${newStatus}`);

  } catch (err) {
    _notifyAdminError('修正依頼処理', err.toString(), contractId);
  }
}

// ============================================================
// 4. approveMaterial(contractId)
//    管理者がスクリプトエディタから手動実行する承認関数
//
//    引数:
//      contractId : 承認する契約ID（例: SP2026-0001）
//
//    実行例（スクリプトエディタのコンソールから）:
//      approveMaterial('SP2026-0001')
//
//    ※ 承認後は publishSponsor() を実行してJSONを更新・デプロイしてください
//       publishSponsor() は gas_deploy_addon.js に実装予定
// ============================================================
function approveMaterial(contractId) {
  try {
    if (!contractId || !contractId.trim()) {
      Logger.log('ERROR: contractId が空です。');
      return;
    }
    const cid = contractId.trim();

    // ── 「素材管理」シートで該当行を探す ─────────────────────────────
    const ss       = SpreadsheetApp.getActiveSpreadsheet();
    const matSheet = ss.getSheetByName(SHEET_MATERIALS);
    if (!matSheet) {
      _notifyAdminError('承認処理', '「素材管理」シートが見つかりません。', cid);
      return;
    }

    const matData = matSheet.getDataRange().getValues();
    const mH      = matData[0];
    const mCol = {
      CID:      mH.indexOf('契約ID'),
      CO:       mH.indexOf('会社名'),
      CITY:     mH.indexOf('都市'),
      ROUND:    mH.indexOf('現在のラウンド'),
      STATUS:   mH.indexOf('状態'),
      APPROVED: mH.indexOf('承認日'),
    };

    let targetRow    = -1;
    let currentRound = 0;
    let currentStatus = '';
    let company       = '';
    let city          = '';

    for (let i = 1; i < matData.length; i++) {
      if (String(matData[i][mCol.CID]).trim() === cid) {
        targetRow     = i + 1;
        currentRound  = parseInt(matData[i][mCol.ROUND], 10) || 0;
        currentStatus = String(matData[i][mCol.STATUS] || '');
        company       = matData[i][mCol.CO]   || '';
        city          = matData[i][mCol.CITY] || '';
        break;
      }
    }

    if (targetRow < 0) {
      Logger.log(`ERROR: 契約ID「${cid}」が素材管理シートに見つかりませんでした。`);
      MailApp.sendEmail({
        to:      CONFIG.ADMIN_EMAIL,
        subject: `【エラー】承認失敗 [${cid}]`,
        body:    `素材管理シートに「${cid}」が見つかりませんでした。`,
      });
      return;
    }

    // ── 状態チェック: 「審査中(R*)」のみ承認可能 ──────────────────────
    // 修正依頼中・素材未提出・差し戻し・承認済みは処理しない
    if (!currentStatus.startsWith('審査中')) {
      Logger.log(`INFO: ${cid} の現在の状態「${currentStatus}」は承認できません。審査中(R*)の状態のみ承認可能です。`);
      MailApp.sendEmail({
        to:      CONFIG.ADMIN_EMAIL,
        subject: `【要確認】承認スキップ [${cid}]`,
        body:    `「${cid}」の状態が「${currentStatus}」のため承認できませんでした。\n素材管理シートを確認してください。\n\n承認できるのは「審査中(R*)」の状態のみです。`,
      });
      return;
    }

    // ── 状態を「承認済み」に更新し、承認日を記録 ─────────────────────
    const today = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy/MM/dd');
    const ts    = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy/MM/dd HH:mm:ss');
    matSheet.getRange(targetRow, mCol.STATUS   + 1).setValue('承認済み');
    if (mCol.APPROVED >= 0) {
      matSheet.getRange(targetRow, mCol.APPROVED + 1).setValue(today);
    }

    // ── 「修正履歴」シートに記録 ─────────────────────────────────────
    const mailSubjectAdmin   = `【承認完了】${city} / ${company} [${cid}] → publishSponsor() を実行してください`;
    const mailSubjectSponsor = `【掲載内容確定のご連絡】${city} スポンサー枠 [${cid}]`;
    _appendRevisionLog(ts, cid, company, city, currentRound, '承認', '', mailSubjectAdmin);

    // ── 管理者メール: publishSponsor() の実行を促す ───────────────────
    // publishSponsor() は gas_deploy_addon.js に実装されている自動デプロイ関数
    const ssUrl = SpreadsheetApp.getActiveSpreadsheet().getUrl();
    MailApp.sendEmail({
      to:      CONFIG.ADMIN_EMAIL,
      subject: mailSubjectAdmin,
      body:
`━━━━━━━━━━━━━━━━━━━━━━━
【承認完了】素材を承認しました
━━━━━━━━━━━━━━━━━━━━━━━
契約ID    : ${cid}
会社名    : ${company}
都市      : ${city}
承認日    : ${today}
承認ラウンド: R${currentRound}
━━━━━━━━━━━━━━━━━━━━━━━

■ 次のアクション（必須）

スクリプトエディタで以下を実行して掲載JSONを更新・デプロイしてください:

  publishSponsor("${cid}")

※ publishSponsor() は gas_deploy_addon.js に実装されています。
  実行後、Cloudflare Pages への自動デプロイが走ります。

スプレッドシート（素材管理シート）:
${ssUrl}`,
    });

    // ── スポンサーへ承認通知メール ────────────────────────────────────
    // 「○営業日以内に公開」の目安を伝える（通常3営業日）
    const sponsorEmail = _getSponsorEmail(cid);
    if (sponsorEmail) {
      MailApp.sendEmail({
        to:      sponsorEmail,
        subject: mailSubjectSponsor,
        body:
`${company} ご担当者様

このたびはご丁寧に素材をご提出いただきありがとうございます。

提出いただいた掲載内容について審査が完了し、
掲載内容が確定いたしましたことをお知らせします。

━━━━━━━━━━━━━━━━━━━━━━━
■ 確定した掲載内容
━━━━━━━━━━━━━━━━━━━━━━━
契約番号  : ${cid}
掲載都市  : ${city}
承認日    : ${today}
━━━━━━━━━━━━━━━━━━━━━━━

3営業日以内に公開いたします。
公開後に改めてご報告のメールをお送りします。

掲載後の内容変更は契約期間内に1回まで承っております。
変更をご希望の場合は ${CONFIG.CONTACT_EMAIL} までご連絡ください。

今後ともどうぞよろしくお願いいたします。

────────────────────────
${CONFIG.COMPANY_NAME}
Mail: ${CONFIG.CONTACT_EMAIL}
────────────────────────`,
        name: CONFIG.FROM_NAME,
      });
    } else {
      _notifyAdminError('承認通知', `${cid} のメールアドレスが取得できませんでした。手動でスポンサーにご連絡ください。`, cid);
    }

    appendLog('素材承認', sponsorEmail || cid, `R${currentRound} ${city} ${company} [${cid}]`);
    Logger.log(`approveMaterial 完了: ${cid} → 承認済み`);

  } catch (err) {
    _notifyAdminError('承認処理', err.toString(), contractId);
  }
}

// ============================================================
// ── プライベート補助関数 ─────────────────────────────────────────────────
// ============================================================

/**
 * 差し戻し処理（ラウンド3でさらに修正依頼が来た場合）
 * requestRevision() の内部から呼ばれる
 */
function _processDismissal(matSheet, targetRow, mCol, cid, company, city, adminNote) {
  const ts    = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy/MM/dd HH:mm:ss');
  matSheet.getRange(targetRow, mCol.STATUS + 1).setValue('差し戻し');

  const mailSubject = `【差し戻し】${city} スポンサー掲載素材について [${cid}]`;
  _appendRevisionLog(ts, cid, company, city, 3, '差し戻し', adminNote || '', mailSubject);

  const sponsorEmail = _getSponsorEmail(cid);
  if (sponsorEmail) {
    MailApp.sendEmail({
      to:      sponsorEmail,
      subject: mailSubject,
      body:
`${company} ご担当者様

「${CONFIG.SITE_NAME}」をご利用いただきありがとうございます。

このたびご提出いただいた掲載素材について、
3回のラウンドを経た後も掲載基準を満たすことができなかったため、
誠に残念ながら今回の掲載を差し戻しとさせていただくことになりました。

━━━━━━━━━━━━━━━━━━━━━━━
■ 差し戻し理由
━━━━━━━━━━━━━━━━━━━━━━━
${adminNote || '（担当者よりご連絡いたします）'}
━━━━━━━━━━━━━━━━━━━━━━━

ご状況についてご不明な点がございましたら、
担当者より改めてご説明いたします。
お手数ですが ${CONFIG.CONTACT_EMAIL} までご連絡ください。

────────────────────────
${CONFIG.COMPANY_NAME}
Mail: ${CONFIG.CONTACT_EMAIL}
────────────────────────`,
      name: CONFIG.FROM_NAME,
    });
  }

  MailApp.sendEmail({
    to:      CONFIG.ADMIN_EMAIL,
    subject: `【差し戻し実施】${city} / ${company} [${cid}]`,
    body:    `R3で差し戻し処理を実行しました。\n契約ID: ${cid}\n理由メモ: ${adminNote || '（なし）'}`,
  });

  appendLog('差し戻し', sponsorEmail || cid, `R3 ${city} ${company} [${cid}]`);
  Logger.log(`_processDismissal 完了: ${cid} → 差し戻し`);
}

/**
 * 「修正履歴」シートに1行追記する
 *
 * @param {string} ts         - 記録日時（yyyy/MM/dd HH:mm:ss）
 * @param {string} cid        - 契約ID
 * @param {string} company    - 会社名
 * @param {string} city       - 都市名
 * @param {number} round      - ラウンド番号
 * @param {string} action     - アクション名（「素材提出」「修正依頼」「承認」「差し戻し」など）
 * @param {string} note       - 担当者メモ
 * @param {string} mailSubject - 送信したメールの件名
 */
function _appendRevisionLog(ts, cid, company, city, round, action, note, mailSubject) {
  try {
    const ss       = SpreadsheetApp.getActiveSpreadsheet();
    const revSheet = ss.getSheetByName(SHEET_REVISION_LOG);
    if (!revSheet) return;
    revSheet.appendRow([ts, cid, company, city, round, action, note || '', mailSubject || '']);
  } catch (e) {
    Logger.log(`_appendRevisionLog ERROR: ${e.toString()}`);
  }
}

/**
 * 契約管理シートからスポンサーのメールアドレスを取得する
 *
 * @param  {string} contractId - 契約ID
 * @return {string} メールアドレス（見つからない場合は空文字）
 */
function _getSponsorEmail(contractId) {
  try {
    const ss            = SpreadsheetApp.getActiveSpreadsheet();
    const contractSheet = ss.getSheetByName(CONFIG.SHEET_CONTRACTS);
    if (!contractSheet) return '';

    const data = contractSheet.getDataRange().getValues();
    const H    = data[0];
    const cCol = H.indexOf('契約ID');
    const eCol = H.indexOf('メール');
    if (cCol < 0 || eCol < 0) return '';

    for (let i = 1; i < data.length; i++) {
      if (String(data[i][cCol]).trim() === contractId.trim()) {
        return data[i][eCol] || '';
      }
    }
  } catch (e) {
    Logger.log(`_getSponsorEmail ERROR: ${e.toString()}`);
  }
  return '';
}

/**
 * エラー発生時に管理者へ通知メールを送信する
 *
 * @param {string} context    - エラーが発生した処理名（例: 「素材提出処理」）
 * @param {string} message    - エラーメッセージ
 * @param {string} contractId - 関係する契約ID（不明な場合は空文字可）
 */
function _notifyAdminError(context, message, contractId) {
  const cid = contractId || '（不明）';
  Logger.log(`ERROR [${context}] CID: ${cid} — ${message}`);
  try {
    MailApp.sendEmail({
      to:      CONFIG.ADMIN_EMAIL,
      subject: `【エラー】${context}失敗 [${cid}]`,
      body:    `処理中にエラーが発生しました。\n\n処理名: ${context}\n契約ID: ${cid}\nエラー内容:\n${message}`,
    });
  } catch (e) {
    Logger.log(`_notifyAdminError 送信失敗: ${e.toString()}`);
  }
}
