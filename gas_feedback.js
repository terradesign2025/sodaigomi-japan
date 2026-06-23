/**
 * 粗大ごみナビ GAS スクリプト
 * Google Apps Script に貼り付けて「ウェブアプリとしてデプロイ」してください。
 *
 * スプレッドシートのシートは自動作成されます。
 * デプロイ後のURLを app.js の FEEDBACK_GAS_URL に設定してください。
 *
 * デプロイ手順:
 *  1. Google スプレッドシートを新規作成して開く
 *  2. 拡張機能 → Apps Script → このコードを貼り付け
 *  3. デプロイ → 新しいデプロイ → ウェブアプリ
 *  4. 「次のユーザーとして実行」= 自分 / 「アクセスできるユーザー」= 全員
 *  5. デプロイ → URLをコピーして app.js の FEEDBACK_GAS_URL に貼り付け
 */

function doPost(e) {
  try {
    var params = JSON.parse(e.postData.contents);
    var action = params.action || 'unknown';
    var ss = SpreadsheetApp.getActiveSpreadsheet();

    if (action === 'feedback') {
      // ご意見箱
      var sheet = ss.getSheetByName('ご意見箱') || ss.insertSheet('ご意見箱');
      if (sheet.getLastRow() === 0) {
        sheet.appendRow(['受信日時', '都市ID', '都市名', '種別', 'メッセージ', '言語', 'UA']);
        sheet.getRange(1, 1, 1, 7).setFontWeight('bold').setBackground('#E8F5E9');
      }
      sheet.appendRow([
        new Date(),
        params.cityId || '',
        params.cityName || '',
        params.type || '',
        params.message || '',
        params.lang || 'ja',
        params.ua || ''
      ]);

    } else if (action === 'city_url') {
      // 都市URL投稿（既存機能）
      var urlSheet = ss.getSheetByName('都市URL提案') || ss.insertSheet('都市URL提案');
      if (urlSheet.getLastRow() === 0) {
        urlSheet.appendRow(['受信日時', '都市ID', '都市名', 'URL', '種別', '言語']);
        urlSheet.getRange(1, 1, 1, 6).setFontWeight('bold').setBackground('#E3F2FD');
      }
      urlSheet.appendRow([
        new Date(),
        params.cityId || '',
        params.cityName || '',
        params.url || '',
        params.type || '',
        params.lang || 'ja'
      ]);
    }

    return ContentService
      .createTextResponse(JSON.stringify({ ok: true }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService
      .createTextResponse(JSON.stringify({ ok: false, error: String(err) }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// テスト用（GAS エディタから手動実行）
function testFeedback() {
  var fakeEvent = {
    postData: {
      contents: JSON.stringify({
        action: 'feedback',
        cityId: '13113',
        cityName: '新宿区',
        type: 'bug',
        message: 'テスト送信です',
        lang: 'ja',
        ua: 'test-agent'
      })
    }
  };
  var result = doPost(fakeEvent);
  Logger.log(result.getContent());
}
