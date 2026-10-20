/* 粗大ごみナビ 共通計測スクリプト
 * GA4 のカスタムイベントを送る。キーイベント（コンバージョン）の対象は次の3つ：
 *   shop_click        … 紹介ページの店舗サイトへのクリック（スポンサー営業の実績数値になる）
 *   sponsor_cta_click … スポンサー募集ページへの誘導クリック
 *   generate_lead     … スポンサー申込フォームの送信完了（sponsor.html 側から送信）
 * Microsoft Clarity は CLARITY_ID を設定すると有効になる（空のままなら何もしない）。
 */
(function () {
  'use strict';

  var CLARITY_ID = 'yvqjanpxog'; // 例: 'abcd1234ef'（Clarity のプロジェクトIDを貼る）

  function pageType() {
    var p = location.pathname;
    if (p === '/' || p === '/index.html') return 'top';
    if (p.indexOf('/blog/') === 0) return p === '/blog/' || p === '/blog/index.html' ? 'blog_index' : 'blog';
    if (p.indexOf('/city/') === 0) return 'city';
    if (p.indexOf('/area/') === 0) return 'area';
    if (p.indexOf('sponsor') > -1) return 'sponsor';
    if (p.indexOf('partner') > -1) return 'partner';
    return 'other';
  }

  function cityId() {
    var m = location.pathname.match(/\/city\/(\d+)\.html/);
    return m ? m[1] : '';
  }

  function send(name, params) {
    if (typeof window.gtag !== 'function') return;
    params = params || {};
    params.page_type = pageType();
    params.transport_type = 'beacon';
    try { window.gtag('event', name, params); } catch (e) {}
  }
  window.sodaiTrack = send;

  document.addEventListener('click', function (e) {
    var a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
    if (!a) return;
    var href = a.getAttribute('href') || '';

    if (href.indexOf('tel:') === 0) {
      send('tel_click', { link_url: href });
      return;
    }

    if (href.indexOf('sponsor.html') > -1) {
      var loc = a.closest('footer') ? 'footer' : (a.closest('.pr-list') ? 'shop_list' : 'body');
      send('sponsor_cta_click', { cta_location: loc, city_id: cityId() });
      return;
    }

    if (/^https?:\/\//.test(href) && a.hostname && a.hostname !== location.hostname) {
      var isShop = !!a.closest('.pr-item, .pr-list, [data-shop], .sp-card, .nb-card');
      send(isShop ? 'shop_click' : 'outbound_click', {
        link_domain: a.hostname,
        link_url: href,
        link_text: (a.textContent || '').trim().slice(0, 60),
        city_id: cityId()
      });
    }
  }, true);

  // Microsoft Clarity（ヒートマップ・録画）
  if (CLARITY_ID) {
    (function (c, l, a, r, i, t, y) {
      c[a] = c[a] || function () { (c[a].q = c[a].q || []).push(arguments); };
      t = l.createElement(r); t.async = 1; t.src = 'https://www.clarity.ms/tag/' + i;
      y = l.getElementsByTagName(r)[0]; y.parentNode.insertBefore(t, y);
    })(window, document, 'clarity', 'script', CLARITY_ID);
  }
})();
