/**
 * 粗大ごみ判定アプリ フィードバック自動処理
 * Google Apps Script — フォーム回答 → 同義語マスター自動追記
 *
 * 【設置場所】
 * フィードバック受信スプレッドシートの Apps Script に貼り付け
 *
 * 【トリガー設定】
 * onFeedbackSubmit → フォーム送信時
 * weeklyFeedbackReport → 毎週月曜 9:00
 */

const FB_CONFIG = {
  ADMIN_EMAIL: 'terradesignik@gmail.com',
  SHEET_FEEDBACK: 'フィードバック受信',
  SHEET_SYNONYM:  '同義語候補（要確認）',
  SHEET_DONE:     '対応済み',
  SYNONYM_MASTER_SHEET: '同義語マスター',  // synonym_master_v2 のシート名
};

// =====================================================
// フォーム送信時の自動処理
// =====================================================
function onFeedbackSubmit(e) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(FB_CONFIG.SHEET_FEEDBACK);
  if (!sheet) return;

  const lastRow = sheet.getLastRow();
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const data = sheet.getRange(lastRow, 1, 1, sheet.getLastColumn()).getValues()[0];

  const get = (col) => {
    const idx = headers.indexOf(col);
    return idx >= 0 ? (data[idx] || '') : '';
  };

  const type    = get('お問い合わせの種類を選んでください') || get('種別');
  const keyword = get('何を検索しましたか？入力した言葉をそのまま書いてください') || get('検索キーワード');
  const item    = get('本当は何を捨てたかったですか？') || get('探していた品目');
  const suggest = get('この品目をどんな言葉で検索する人が多いと思いますか？') || '';
  const city    = get('お住まいの市区町村（任意）') || '';
  const comment = get('その他、気づいたこと・ご要望があればご自由にどうぞ') || '';

  // タイムスタンプ追記
  sheet.getRange(lastRow, headers.length + 1).setValue(Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy/MM/dd HH:mm'));
  sheet.getRange(lastRow, headers.length + 2).setValue('未対応');

  // 同義語提案・品目未発見 → 候補シートに自動転記
  if (keyword && item && (type.includes('見つからなかった') || type.includes('同義語'))) {
    addToSynonymCandidate(keyword, item, suggest, city, lastRow);
  }

  // 管理者通知
  const urgentTypes = ['情報が間違っている', 'バグ'];
  const isUrgent = urgentTypes.some(t => type.includes(t));

  if (isUrgent || !keyword) {
    MailApp.sendEmail({
      to: FB_CONFIG.ADMIN_EMAIL,
      subject: `【${isUrgent ? '要確認' : 'フィードバック'}】粗大ごみアプリ: ${type.slice(0,20)}`,
      body: `新しいフィードバックが届きました。\n\n種別: ${type}\nキーワード: ${keyword}\n品目: ${item}\n地域: ${city}\nコメント: ${comment}\n\nスプレッドシートで確認してください。`
    });
  }
}

// =====================================================
// 同義語候補シートに追記
// =====================================================
function addToSynonymCandidate(keyword, item, suggest, city, sourceRow) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(FB_CONFIG.SHEET_SYNONYM);

  if (!sheet) {
    sheet = ss.insertSheet(FB_CONFIG.SHEET_SYNONYM);
    sheet.getRange(1, 1, 1, 8).setValues([[
      '受信日', '検索キーワード', '探していた品目', '提案同義語', '地域', '件数', 'ステータス', '元行番号'
    ]]).setFontWeight('bold');
    sheet.setFrozenRows(1);
  }

  const data = sheet.getDataRange().getValues();
  const headers = data[0];
  const keyIdx = headers.indexOf('検索キーワード');
  const itemIdx = headers.indexOf('探していた品目');
  const countIdx = headers.indexOf('件数');
  const statusIdx = headers.indexOf('ステータス');

  // 既存の同じキーワード+品目の組み合わせを探す
  for (let i = 1; i < data.length; i++) {
    if (data[i][keyIdx] === keyword && data[i][itemIdx] === item) {
      // 件数を増やす
      sheet.getRange(i + 1, countIdx + 1).setValue((parseInt(data[i][countIdx]) || 1) + 1);
      // 提案があれば追記
      if (suggest) {
        const existing = data[i][headers.indexOf('提案同義語')] || '';
        if (!existing.includes(suggest)) {
          sheet.getRange(i + 1, headers.indexOf('提案同義語') + 1).setValue(
            existing ? existing + '\n' + suggest : suggest
          );
        }
      }
      return;
    }
  }

  // 新規追加
  const today = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy/MM/dd');
  sheet.appendRow([today, keyword, item, suggest, city, 1, '未対応', sourceRow]);
}

// =====================================================
// 週次レポート（毎週月曜 9:00）
// =====================================================
function weeklyFeedbackReport() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(FB_CONFIG.SHEET_SYNONYM);
  if (!sheet) return;

  const data = sheet.getDataRange().getValues();
  if (data.length < 2) return;

  const headers = data[0];
  const statusIdx = headers.indexOf('ステータス');
  const keyIdx = headers.indexOf('検索キーワード');
  const itemIdx = headers.indexOf('探していた品目');
  const countIdx = headers.indexOf('件数');

  // 未対応で件数3件以上
  const priority = data.slice(1)
    .filter(r => r[statusIdx] === '未対応' && parseInt(r[countIdx]) >= 3)
    .sort((a, b) => parseInt(b[countIdx]) - parseInt(a[countIdx]))
    .map(r => `・「${r[keyIdx]}」→「${r[itemIdx]}」（${r[countIdx]}件）`);

  // 未対応全件
  const allPending = data.slice(1).filter(r => r[statusIdx] === '未対応');

  if (!allPending.length) return;

  const body = `今週の同義語フィードバック集計

未対応件数: ${allPending.length}件
${priority.length ? '\n【優先対応（3件以上）】\n' + priority.join('\n') : ''}

スプレッドシートで確認:
https://docs.google.com/spreadsheets/（URLを貼る）

---
同義語マスター更新手順:
1. 「同義語候補（要確認）」シートを確認
2. 正しいと判断したものを synonym_master_v2.csv に追加
3. index.html の SYNONYMS 辞書にも追記
4. ステータスを「対応済み」に変更`;

  MailApp.sendEmail({
    to: FB_CONFIG.ADMIN_EMAIL,
    subject: `【週次レポート】粗大ごみアプリ 同義語フィードバック ${allPending.length}件`,
    body
  });
}

// =====================================================
// 同義語マスターへの一括反映（手動実行）
// 「同義語候補（要確認）」→「同義語マスター」への移行
// =====================================================
function applyApprovedSynonyms() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const candidateSheet = ss.getSheetByName(FB_CONFIG.SHEET_SYNONYM);
  const masterSheet = ss.getSheetByName(FB_CONFIG.SYNONYM_MASTER_SHEET);

  if (!candidateSheet || !masterSheet) {
    Logger.log('シートが見つかりません');
    return;
  }

  const cData = candidateSheet.getDataRange().getValues();
  const cHeaders = cData[0];
  const statusIdx = cHeaders.indexOf('ステータス');
  const keyIdx = cHeaders.indexOf('検索キーワード');
  const itemIdx = cHeaders.indexOf('探していた品目');
  const suggestIdx = cHeaders.indexOf('提案同義語');

  let applied = 0;

  for (let i = 1; i < cData.length; i++) {
    const row = cData[i];
    if (row[statusIdx] !== '承認済み') continue;

    const keyword = row[keyIdx];
    const item = row[itemIdx];
    const suggestion = row[suggestIdx];

    // マスターシートの対象品目を検索して同義語列に追記
    const mData = masterSheet.getDataRange().getValues();
    const mHeaders = mData[0];
    const mItemIdx = mHeaders.indexOf('品目名（正式）');
    const mSynIdx = mHeaders.indexOf('同義語・別名・言い換え・崩し語・ブランド名（パイプ区切り）');

    for (let j = 1; j < mData.length; j++) {
      if (mData[j][mItemIdx] && mData[j][mItemIdx].includes(item)) {
        const existing = mData[j][mSynIdx] || '';
        const newSyns = [keyword, suggestion].filter(s => s && !existing.includes(s));
        if (newSyns.length) {
          const updated = existing + '|' + newSyns.join('|');
          masterSheet.getRange(j + 1, mSynIdx + 1).setValue(updated);
          applied++;
        }
        // ステータスを対応済みに
        candidateSheet.getRange(i + 1, statusIdx + 1).setValue('反映済み');
        break;
      }
    }
  }

  Logger.log(`${applied}件の同義語を反映しました`);
  showFinalReport(applied);
}

function showFinalReport(count) {
  MailApp.sendEmail({
    to: FB_CONFIG.ADMIN_EMAIL,
    subject: `【同義語反映完了】${count}件を同義語マスターに追加`,
    body: `同義語マスターへの反映が完了しました。\n反映件数: ${count}件\n\n次の手順:\n1. 同義語マスターシートをCSVエクスポート\n2. data/synonym_master_v2.csv を更新\n3. index.html の SYNONYMS 辞書に追記`
  });
}

// =====================================================
// 初期設定（初回1回だけ手動実行）
// =====================================================
function setupFeedbackTriggers() {
  ScriptApp.getProjectTriggers().forEach(t => {
    if (t.getHandlerFunction() === 'weeklyFeedbackReport' ||
        t.getHandlerFunction() === 'onFeedbackSubmit') {
      ScriptApp.deleteTrigger(t);
    }
  });

  // フォーム送信時トリガー
  ScriptApp.newTrigger('onFeedbackSubmit')
    .forSpreadsheet(SpreadsheetApp.getActiveSpreadsheet())
    .onFormSubmit()
    .create();

  // 週次レポート（月曜 9:00）
  ScriptApp.newTrigger('weeklyFeedbackReport')
    .timeBased()
    .onWeekDay(ScriptApp.WeekDay.MONDAY)
    .atHour(9)
    .create();

  Logger.log('フィードバックトリガーを設定しました');
}
