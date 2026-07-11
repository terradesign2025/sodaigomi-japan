# -*- coding: utf-8 -*-
"""
東京23区「粗大ごみ完全ガイド」ブログ記事の自動生成

cities/13_tokyo/{13101..13123}_v2.json から blog/{romaji}-sodaigomi-guide.html を生成する。
区ごとの料金・申込み先・持ち込み情報はすべて実データで差別化。
データ更新後は再実行: python gen_ward_guides.py
"""
import json, os, sys, html, re

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = 'https://sodaigomi-navi.com'
ROOT = os.path.dirname(os.path.abspath(__file__))
DATE_PUB = '2026-07-10'
DATE_JP = '2026年7月10日'

WARDS = [
    ('13101', 'chiyoda'), ('13102', 'chuo'), ('13103', 'minato'), ('13104', 'shinjuku'),
    ('13105', 'bunkyo'), ('13106', 'taito'), ('13107', 'sumida'), ('13108', 'koto'),
    ('13109', 'shinagawa'), ('13110', 'meguro'), ('13111', 'ota'), ('13112', 'setagaya'),
    ('13113', 'shibuya'), ('13114', 'nakano'), ('13115', 'suginami'), ('13116', 'toshima'),
    ('13117', 'kita'), ('13118', 'arakawa'), ('13119', 'itabashi'), ('13120', 'nerima'),
    ('13121', 'adachi'), ('13122', 'katsushika'), ('13123', 'edogawa'),
]

# 主要都市（政令指定都市＋八王子）。23区と同じテンプレートで生成する
MAJOR_CITIES = [
    ('27100', 'osaka'), ('14100', 'yokohama'), ('23100', 'nagoya'), ('01100', 'sapporo'),
    ('40130', 'fukuoka'), ('26100', 'kyoto'), ('11100', 'saitama'), ('13201', 'hachioji'),
    ('14130', 'kawasaki'), ('12100', 'chiba'), ('28100', 'kobe'), ('04100', 'sendai'),
    ('34100', 'hiroshima'), ('27140', 'sakai'), ('15100', 'niigata'), ('22100', 'shizuoka'),
    ('14150', 'sagamihara'), ('33100', 'okayama'), ('43100', 'kumamoto'),
    ('40100', 'kitakyushu'), ('22130', 'hamamatsu'),
]
ROMAJI = dict(WARDS) | dict(MAJOR_CITIES)

# よく検索される品目（この順で最大18件拾う）
POPULAR_KEYWORDS = [
    'ソファ', 'ベッド', 'マットレス', 'タンス', '布団', '自転車', 'テーブル', '椅子',
    '本棚', '食器棚', 'カーペット', '電子レンジ', 'ストーブ', '扇風機', '掃除機',
    'ベビーカー', 'こたつ', 'チャイルドシート', 'スーツケース', '物干し',
]

CSP_META = ("default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://www.googletagmanager.com https://www.google-analytics.com; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https://*.google-analytics.com https://*.analytics.google.com "
            "https://www.googletagmanager.com https://stats.g.doubleclick.net "
            "https://mreversegeocoder.gsi.go.jp https://zipcloud.ibsnet.co.jp "
            "https://api.web3forms.com https://script.google.com https://script.googleusercontent.com; "
            "base-uri 'self'; form-action 'self' https://api.web3forms.com; object-src 'none'")

CSS = '''<style>
:root {
  --g: #16a34a; --gd: #14532d; --gl: #dcfce7; --glm: #bbf7d0; --bg: #f0fdf4;
  --card: #fff; --text: #111827; --muted: #6b7280; --border: #e5e7eb;
  --navy: #1e3a5f; --sh: 0 2px 16px rgba(22,163,74,.10);
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", "Noto Sans JP", sans-serif; background: var(--bg); color: var(--text); line-height: 1.8; font-size: 16px; }
.top-bar { background: var(--card); border-bottom: 1px solid var(--border); padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 100; box-shadow: 0 1px 6px rgba(0,0,0,.05); }
.logo { display: flex; align-items: center; gap: 8px; text-decoration: none; }
.logo-ico { width: 36px; height: 36px; background: var(--gl); border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 20px; }
.logo-txt { font-size: 14px; font-weight: 800; color: var(--gd); }
.blog-link { font-size: 12px; color: var(--g); text-decoration: none; border: 1px solid var(--g); padding: 5px 12px; border-radius: 16px; font-weight: 600; }
.blog-link:hover { background: var(--gl); }
.article-hero { background: linear-gradient(145deg, #14532d 0%, #16a34a 60%, #22c55e 100%); color: #fff; padding: 52px 20px 48px; text-align: center; }
.article-category { display: inline-block; background: rgba(255,255,255,.2); border: 1px solid rgba(255,255,255,.35); border-radius: 20px; padding: 4px 14px; font-size: 11px; font-weight: 700; margin-bottom: 14px; letter-spacing: .04em; }
.article-hero h1 { font-size: clamp(20px, 4.5vw, 32px); font-weight: 900; line-height: 1.3; margin-bottom: 14px; }
.article-meta { font-size: 12px; opacity: .8; display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; }
.article-summary { display: inline-block; background: rgba(255,255,255,.15); border-radius: 8px; padding: 10px 20px; font-size: 14px; margin-top: 16px; max-width: 560px; line-height: 1.6; }
.main-wrap { max-width: 760px; margin: 0 auto; padding: 0 20px 60px; }
.breadcrumb { padding: 12px 0; font-size: 12px; color: var(--muted); display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.breadcrumb a { color: var(--g); text-decoration: none; }
.breadcrumb a:hover { text-decoration: underline; }
.toc { background: var(--gl); border: 1px solid var(--glm); border-radius: 12px; padding: 20px 24px; margin: 28px 0; }
.toc-title { font-size: 14px; font-weight: 800; color: var(--gd); margin-bottom: 12px; }
.toc ol { padding-left: 20px; }
.toc li { margin: 6px 0; font-size: 13px; }
.toc a { color: var(--g); text-decoration: none; font-weight: 600; }
.toc a:hover { text-decoration: underline; }
.article-body { margin-top: 8px; }
.article-body h2 { font-size: clamp(18px, 3.5vw, 22px); font-weight: 900; color: var(--navy); margin: 44px 0 16px; padding-bottom: 10px; border-bottom: 3px solid var(--g); line-height: 1.4; }
.article-body h3 { font-size: clamp(15px, 3vw, 18px); font-weight: 800; color: var(--gd); margin: 28px 0 12px; padding-left: 12px; border-left: 4px solid var(--g); line-height: 1.4; }
.article-body p { margin-bottom: 16px; color: var(--text); }
.article-body ul, .article-body ol { padding-left: 22px; margin-bottom: 16px; }
.article-body li { margin: 6px 0; }
.article-body a { color: var(--g); }
.definition-box { background: #fff; border: 2px solid var(--g); border-radius: 10px; padding: 18px 20px; margin: 24px 0; }
.definition-box .def-label { font-size: 11px; font-weight: 700; color: var(--g); letter-spacing: .06em; margin-bottom: 6px; }
.definition-box p { font-size: 15px; font-weight: 600; margin: 0; line-height: 1.7; }
.step-flow { margin: 24px 0; }
.step-item { display: flex; gap: 16px; align-items: flex-start; margin-bottom: 8px; position: relative; }
.step-item:not(:last-child)::after { content: ''; position: absolute; left: 20px; top: 44px; width: 2px; height: calc(100% + 8px - 44px + 8px); background: var(--glm); }
.step-num { width: 40px; height: 40px; background: var(--g); color: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: 900; flex-shrink: 0; position: relative; z-index: 1; }
.step-content { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; flex: 1; box-shadow: var(--sh); }
.step-content .step-title { font-size: 15px; font-weight: 800; color: var(--navy); margin-bottom: 6px; }
.step-content .step-desc { font-size: 13px; color: var(--muted); line-height: 1.6; margin: 0; }
.table-wrap { overflow-x: auto; margin: 20px 0; border-radius: 10px; box-shadow: var(--sh); }
table { width: 100%; border-collapse: collapse; background: var(--card); font-size: 14px; min-width: 460px; }
th { background: var(--gd); color: #fff; padding: 10px 14px; text-align: left; font-size: 13px; font-weight: 700; }
td { padding: 10px 14px; border-bottom: 1px solid var(--border); vertical-align: top; word-break: break-word; overflow-wrap: anywhere; }
td.fee { white-space: nowrap; font-weight: 700; color: var(--gd); }
tr:last-child td { border-bottom: none; }
tr:nth-child(even) td { background: var(--bg); }
.warning-box { background: #fef2f2; border: 1px solid #fca5a5; border-left: 4px solid #ef4444; border-radius: 10px; padding: 16px 18px; margin: 20px 0; font-size: 14px; }
.warning-box strong { color: #b91c1c; }
.note-box { background: #fffbeb; border: 1px solid #fcd34d; border-radius: 10px; padding: 16px 18px; margin: 20px 0; font-size: 14px; }
.note-box strong { color: #92400e; }
.faq-item { background: var(--card); border: 1px solid var(--border); border-radius: 12px; margin: 14px 0; overflow: hidden; box-shadow: var(--sh); }
.faq-q { background: var(--gl); padding: 14px 18px; font-size: 15px; font-weight: 700; color: var(--gd); display: flex; gap: 10px; align-items: flex-start; }
.faq-q::before { content: "Q"; background: var(--g); color: #fff; width: 22px; height: 22px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 900; flex-shrink: 0; margin-top: 1px; }
.faq-a { padding: 14px 18px; font-size: 14px; line-height: 1.7; display: flex; gap: 10px; align-items: flex-start; }
.faq-a::before { content: "A"; background: #f3f4f6; color: var(--navy); width: 22px; height: 22px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 900; flex-shrink: 0; margin-top: 1px; }
.cta-box { background: linear-gradient(135deg, #14532d 0%, #16a34a 100%); border-radius: 16px; padding: 32px 28px; text-align: center; margin: 44px 0 28px; color: #fff; }
.cta-box h3 { font-size: clamp(17px, 3.5vw, 22px); font-weight: 900; margin-bottom: 10px; color: #fff; border: none; padding: 0; }
.cta-box p { font-size: 14px; opacity: .9; margin-bottom: 20px; color: #fff; }
.btn-cta { display: inline-flex; align-items: center; gap: 8px; background: #fff; color: var(--gd); padding: 14px 32px; border-radius: 30px; font-size: 15px; font-weight: 800; text-decoration: none; box-shadow: 0 4px 16px rgba(0,0,0,.2); transition: all .15s; }
.btn-cta:hover { transform: translateY(-2px); box-shadow: 0 6px 24px rgba(0,0,0,.25); }
.ward-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); gap: 8px; margin: 16px 0; }
.ward-grid a { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 8px 10px; font-size: 13px; text-align: center; text-decoration: none; color: var(--text); }
.ward-grid a:hover { border-color: var(--g); color: var(--gd); }
.related-section { margin: 40px 0 0; padding: 28px 0; border-top: 1px solid var(--border); }
.related-title { font-size: 15px; font-weight: 800; color: var(--navy); margin-bottom: 16px; }
.related-card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px 18px; text-decoration: none; display: block; transition: box-shadow .15s; margin-bottom: 10px; }
.related-card:hover { box-shadow: var(--sh); }
.related-card .rc-tag { font-size: 11px; color: var(--g); font-weight: 700; margin-bottom: 4px; }
.related-card .rc-title { font-size: 14px; font-weight: 700; color: var(--text); }
footer { background: var(--gd); color: rgba(255,255,255,.7); text-align: center; padding: 24px 20px; font-size: 12px; }
footer a { color: var(--glm); text-decoration: none; }
footer a:hover { text-decoration: underline; }
@media (max-width: 600px) {
  .article-hero { padding: 40px 16px 36px; }
  .main-wrap { padding: 0 14px 48px; }
  .toc { padding: 16px 18px; }
  .cta-box { padding: 24px 18px; }
  .step-item:not(:last-child)::after { display: none; }
}
</style>'''

DISCLAIMER = '掲載している料金・申込方法は各自治体の公式情報をもとに作成していますが、改定等により実際と異なる場合があります。お申し込み前に必ず各自治体の公式情報をご確認ください。'


def esc(s):
    return html.escape(str(s), quote=True) if s is not None else ''


def fee_str(fee):
    if isinstance(fee, (int, float)):
        return '無料' if fee == 0 else f'{int(fee):,}円'
    return '—'


def has_fee(it):
    return isinstance(it.get('fee'), (int, float)) and it['fee'] >= 0


def load_ward(cid):
    import glob as _glob
    paths = _glob.glob(os.path.join(ROOT, 'cities', '*', f'{cid}_v2.json'))
    with open(paths[0], encoding='utf-8') as f:
        data = json.load(f)
    city = data.get('city') or {}
    items = data.get('items') or city.get('items') or []
    return {
        'id': city['id'], 'name': city['name'],
        'ver': city.get('dataVersion', ''),
        'rules': city.get('rules') or {},
        'items': items,
        'unc': data.get('uncollectible') or city.get('uncollectible') or [],
    }


def popular_items(items, limit=24):
    picked, used = [], set()
    for kw in POPULAR_KEYWORDS:
        for it in items:
            n = it.get('n', '')
            if kw in n and n not in used and has_fee(it):
                picked.append(it)
                used.add(n)
                break
        if len(picked) >= limit:
            break
    # キーワード一致が少ない都市は、残りを収録順で補完（表の情報量を確保）
    if len(picked) < limit:
        for it in items:
            n = it.get('n', '')
            if n not in used and has_fee(it):
                picked.append(it)
                used.add(n)
                if len(picked) >= limit:
                    break
    return picked


def uniform_fee_para(w, fmin, fmax):
    """均一料金制の都市向け解説（さいたま市等）"""
    if fmin is None or fmin != fmax:
        return ''
    name, items = w['name'], w['items']
    note = next((it.get('note') for it in items if it.get('note')), '')
    note_txt = f'対象の目安は「{esc(note)}」とされています。' if note else ''
    m = next((it.get('m') for it in items if it.get('m')), '')
    m_txt = f'出し方の区分は「{esc(m)}」です。' if m else ''
    return (f'<h3>{esc(name)}は品目によらない均一料金制です</h3>'
            f'<p>{esc(name)}の収録データでは、粗大ごみの手数料は品目にかかわらず1点{fee_str(fmin)}の均一料金になっています。'
            f'{note_txt}{m_txt}'
            f'「この家具はいくらだろう」と品目ごとに調べる必要がない、わかりやすい制度です。'
            f'ただし、サイズが基準に満たないものは通常ごみ、大きすぎるものは受付対象外となる場合があるため、'
            f'迷ったら申込み時に寸法を伝えて確認しましょう。</p>')


def base_plus_exception_para(w):
    """「一般◯円＋例外品目」型の料金体系解説（さいたま市等・収録品目が少ない都市向け）"""
    name, items = w['name'], w['items']
    if len(items) >= 20:
        return ''
    base = next((it for it in items if '一般' in it.get('n', '') and has_fee(it)), None)
    if not base:
        return ''
    exceptions = [it for it in items if has_fee(it) and it['fee'] != base['fee'] and it is not base]
    exc_txt = ''
    if exceptions:
        tops = sorted(exceptions, key=lambda x: -x['fee'])[:4]
        exc_txt = ('ただし、' + '、'.join(f'{esc(t["n"])}（{fee_str(t["fee"])}）' for t in tops) +
                   'など、処理に手間がかかる品目は個別の料金が設定されています。')
    note = base.get('note') or ''
    note_txt = f'対象の目安は「{esc(note)}」とされています。' if note else ''
    return (f'<h3>{esc(name)}の料金体系はシンプルです</h3>'
            f'<p>{esc(name)}の収録データでは、一般的な家具・家電などの粗大ごみは「{esc(base["n"])}」として'
            f'1点{fee_str(base["fee"])}に統一されています。{note_txt}'
            f'品目ごとに料金を調べる手間が少ないわかりやすい制度です。{exc_txt}'
            f'ご自身の品物がどちらに当たるか迷う場合は、申込み時に品目と寸法を伝えて確認しておくと、'
            f'処理券の買い間違いを防げます。</p>')


def fee_distribution_para(items, name):
    fees = [int(it['fee']) for it in items if has_fee(it)]
    if len(fees) < 5:
        return ''
    from collections import Counter
    mode_fee, mode_cnt = Counter(fees).most_common(1)[0]
    return (f'<p>収録データを集計すると、{esc(name)}の粗大ごみは全{len(fees)}品目のうち'
            f'最も多い手数料が{mode_fee:,}円（{mode_cnt}品目）で、最低{min(fees):,}円〜最高{max(fees):,}円の範囲に分布しています。'
            f'手数料は品物のサイズや種類で決まるため、申込み前に品目ごとの金額を確認しておくと、処理券の買い間違いを防げます。</p>')


def fee_range(items):
    fees = [int(it['fee']) for it in items if has_fee(it)]
    return (min(fees), max(fees)) if fees else (None, None)


def find_item(items, kw):
    for it in items:
        if kw in it.get('n', '') and has_fee(it):
            return it
    return None


def top_fee_items(items, pops, limit=10):
    """高額品目トップN（早見表と重複しないもの）"""
    used = {p.get('n') for p in pops}
    cand = [it for it in items
            if has_fee(it) and it.get('n') not in used]
    cand.sort(key=lambda x: (-x['fee'], x.get('n', '')))
    return cand[:limit]


def item_detail_paras(w):
    """ソファ・ベッド・布団の区別実データ解説（品目記事への内部リンクつき）"""
    items = w['items']
    name = w['name']
    paras = []
    sofa = find_item(items, 'ソファ')
    if sofa:
        paras.append(
            f'<h3>ソファを捨てる場合</h3>'
            f'<p>{esc(name)}では「{esc(sofa["n"])}」が{fee_str(sofa["fee"])}です。サイズ区分（1人掛けか2人掛け以上か）で料金が変わるため、申込み前に幅を測っておきましょう。'
            f'スプリング入りや電動リクライニングは扱いが変わる場合があります。全国の比較は<a href="sofa-disposal-guide.html">ソファの処分費用ガイド</a>で詳しく解説しています。</p>')
    bed = find_item(items, 'ベッド')
    mat = find_item(items, 'マットレス') or find_item(items, 'ベッドマット')
    if bed:
        mat_txt = f'マットレスは別品目で、「{esc(mat["n"])}」は{fee_str(mat["fee"])}です。' if mat else 'マットレスは別品目・別料金になる場合があります。'
        paras.append(
            f'<h3>ベッドを捨てる場合</h3>'
            f'<p>{esc(name)}では「{esc(bed["n"])}」が{fee_str(bed["fee"])}です。{mat_txt}'
            f'フレームとマットレスは2品目として申し込むのが基本です。詳しくは<a href="bed-mattress-disposal-guide.html">ベッド・マットレスの捨て方完全ガイド</a>をご覧ください。</p>')
    futon = find_item(items, '布団')
    if futon:
        paras.append(
            f'<h3>布団を捨てる場合</h3>'
            f'<p>{esc(name)}では「{esc(futon["n"])}」が{fee_str(futon["fee"])}です。紐でしばってまとめ、処理券が見えるように貼って出します。'
            f'毛布・こたつ布団の扱いは品目区分の確認をおすすめします。</p>')
    # ソファ・ベッド・布団が収録にない都市は、高額品目の解説で補完
    if len(paras) < 2:
        used_kw = {'ソファ', 'ベッド', '布団'}
        cand = sorted(
            [it for it in items if has_fee(it) and it['fee'] > 0
             and not any(k in it.get('n', '') for k in used_kw)],
            key=lambda x: -x['fee'])
        for it in cand[:3 - len(paras)]:
            paras.append(
                f'<h3>{esc(it["n"])}を捨てる場合</h3>'
                f'<p>{esc(name)}では「{esc(it["n"])}」が{fee_str(it["fee"])}です。大型で重さのある品物は搬出時のけがを防ぐため2人以上での運び出しをおすすめします。'
                f'サイズによって区分が変わる場合があるため、申込み時に寸法を伝えて金額を確定させておくと安心です。</p>')
    return ''.join(paras)


PRACTICAL_TIPS = '''
<h3>収集日に出し忘れた・回収されなかった場合</h3>
<p>出し忘れた場合は、受付センターに連絡して収集日を取り直すのが基本です。処理券は購入済みのものをそのまま使える場合が多いので、捨てずに保管しておきましょう。品物に「回収できません」の案内が貼られていた場合は、記載された理由（サイズ超過・対象外品目・券の金額不足など）を確認してから再申込みします。</p>
<h3>マンション・集合住宅の場合</h3>
<p>集合住宅では、建物指定の粗大ごみ置き場がある場合と、通常どおり自宅前・集積所に出す場合があります。管理規約や掲示板の案内を確認し、わからない場合は管理会社に問い合わせてから申し込むとスムーズです。</p>
<h3>引越しシーズンは早めの申込みを</h3>
<p>3〜4月や年末は申込みが集中し、収集日が通常より先になることがあります。退去日が決まっている場合は、遅くとも1か月前には品目の洗い出しと申込みを済ませておくと安心です。</p>'''


def build_faq(w, fmin, fmax):
    name, r, items = w['name'], w['rules'], w['items']
    qa = []
    sofa = find_item(items, 'ソファ')
    futon = find_item(items, '布団')
    ex = ''
    if sofa:
        ex += f'例えば{sofa["n"]}は{fee_str(sofa["fee"])}'
    if futon:
        ex += ('、' if ex else '例えば') + f'{futon["n"]}は{fee_str(futon["fee"])}'
    if ex:
        ex += 'です。'
    if fmin is not None:
        qa.append((f'{name}の粗大ごみはいくらかかりますか？',
                   f'品目により{fmin:,}円〜{fmax:,}円です（2026年5月時点の収録データ）。{ex}品目ごとの正確な料金は粗大ごみナビの検索アプリで確認できます。'))
    if r.get('applicationMethod'):
        qa.append((f'{name}の粗大ごみはどうやって申し込みますか？', r['applicationMethod']))
    if r.get('paymentMethod'):
        qa.append((f'{name}の粗大ごみ処理券はどこで買えますか？', r['paymentMethod']))
    if r.get('selfCarryIn'):
        qa.append((f'{name}では粗大ごみの持ち込み処分はできますか？', r['selfCarryIn']))
    qa.append((f'{name}では申し込みから収集まで何日かかりますか？',
               '時期にもよりますが、一般的に1〜2週間程度かかることが多いです。3〜4月の引越しシーズンは混み合うため、日程が決まったら早めの申込みをおすすめします。'))
    return qa[:5]


def ward_page(w, group, category='東京23区ガイド', grid_title='東京23区のほかの区のガイド'):
    cid, name = w['id'], w['name']
    r, items = w['rules'], w['items']
    romaji = ROMAJI[cid]
    slug = f'{romaji}-sodaigomi-guide'
    path = f'/blog/{slug}.html'
    n_items = len(items)
    fmin, fmax = fee_range(items)
    pops = popular_items(items)
    faq = build_faq(w, fmin, fmax)

    title = f'{name}の粗大ごみ完全ガイド｜申込み方法・料金・持ち込み【2026年7月版】'
    range_txt = f'{fmin:,}円〜{fmax:,}円' if fmin is not None else ''
    desc = f'{name}の粗大ごみの申込み方法・処理券の買い方・持ち込み処分・収集ルールを1ページに整理。品目別料金は{range_txt}（全{n_items}品目収録）。よく出る家具・家電の手数料早見表つきです。'

    # ---- JSON-LD ----
    ld_article = {
        "@context": "https://schema.org", "@type": "Article",
        "headline": title, "datePublished": DATE_PUB, "dateModified": DATE_PUB,
        "author": {"@type": "Organization", "name": "株式会社テラデザイン", "url": "https://terra-design.co.jp"},
        "publisher": {"@type": "Organization", "name": "株式会社テラデザイン"},
        "description": desc,
    }
    ld_breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "粗大ごみナビ", "item": BASE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": "ブログ", "item": BASE_URL + "/blog/"},
            {"@type": "ListItem", "position": 3, "name": f"{name}の粗大ごみ完全ガイド", "item": BASE_URL + path},
        ],
    }
    ld_faq = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in faq
        ],
    }
    ld_blocks = ''.join(
        f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n'
        for ld in [ld_article, ld_breadcrumb, ld_faq]
    )

    # ---- 基本情報テーブル ----
    info_rows = []
    for label, val in [
        ('粗大ごみの定義', r.get('definition')),
        ('申込み方法', r.get('applicationMethod')),
        ('電話番号', r.get('contact')),
        ('電話受付時間', r.get('hours')),
        ('ネット受付', r.get('internetHours')),
        ('支払い方法', r.get('paymentMethod')),
        ('出し方（収集）', r.get('collectionMethod')),
    ]:
        if val:
            info_rows.append(f'<tr><th>{esc(label)}</th><td>{esc(val)}</td></tr>')
    info_table = f'<div class="table-wrap"><table>{"".join(info_rows)}</table></div>' if info_rows else ''

    # ---- よく出る品目テーブル ----
    pop_rows = ''.join(
        f'<tr><td>{esc(p["n"])}</td><td class="fee">{fee_str(p.get("fee"))}</td></tr>'
        for p in pops
    )
    pop_table = f'<div class="table-wrap"><table><tr><th>品目</th><th>手数料</th></tr>{pop_rows}</table></div>'

    # ---- 高額品目テーブル ----
    tops = top_fee_items(items, pops)
    top_table = ''
    if tops:
        top_rows = ''.join(
            f'<tr><td>{esc(t["n"])}</td><td class="fee">{fee_str(t.get("fee"))}</td></tr>'
            for t in tops
        )
        top_table = f'''<h3>手数料が高めの大型品目</h3>
<p>搬出や解体の判断にも関わるため、大型品は事前に料金を確認しておきましょう。</p>
<div class="table-wrap"><table><tr><th>品目</th><th>手数料</th></tr>{top_rows}</table></div>'''

    # ---- 品目別詳細（ソファ・ベッド・布団） ----
    detail_html = item_detail_paras(w)
    if detail_html:
        detail_html = f'<h2 id="details">{esc(name)}の品目別の捨て方ポイント</h2>' + detail_html

    # ---- 持ち込み ----
    carry_html = ''
    if r.get('selfCarryIn'):
        carry_html = f'''<h2 id="carry">{esc(name)}で粗大ごみの持ち込み処分はできますか？</h2>
<p>{esc(r["selfCarryIn"])}</p>
<p class="note-box"><strong>持ち込みのポイント：</strong>事前予約や本人確認書類が必要な場合が多く、受け入れ日時も限られます。運搬手段を確保できる方は、収集より費用を抑えられる場合がある一方、準備の手間もあるため、品目数と照らして選ぶのがおすすめです。</p>'''

    # ---- 収集できないもの ----
    unc_html = ''
    unc_parts = []
    if w['unc']:
        rows = []
        for u in w['unc']:
            if isinstance(u, dict):
                rows.append(f'<tr><td>{esc(u.get("n",""))}</td><td>{esc(u.get("reason",""))}</td></tr>')
            else:
                rows.append(f'<tr><td colspan="2">{esc(u)}</td></tr>')
        unc_parts.append(f'<div class="table-wrap"><table><tr><th>品目</th><th>理由・処分先</th></tr>{"".join(rows)}</table></div>')
    if r.get('nonCollectibleNote'):
        unc_parts.append(f'<p>{esc(r["nonCollectibleNote"])}</p>')
    if unc_parts:
        unc_html = f'''<h2 id="cannot">{esc(name)}で収集できないもの</h2>
{''.join(unc_parts)}
<p>冷蔵庫・テレビ・洗濯機・エアコンなどの家電リサイクル法対象品の正しい処分方法は、<a href="refrigerator-disposal-guide.html">冷蔵庫の処分ガイド</a>で詳しく解説しています。</p>'''

    # ---- 同グループの他都市リンク ----
    other_links = ''.join(
        f'<a href="{ROMAJI[oid]}-sodaigomi-guide.html">{esc(oname)}</a>'
        for oid, oname in group if oid != cid
    )

    # ---- FAQ ----
    faq_html = ''.join(
        f'<div class="faq-item"><div class="faq-q">{esc(q)}</div><div class="faq-a">{esc(a)}</div></div>'
        for q, a in faq
    )

    ver_note = f'※ 掲載内容は{esc(w["ver"])}時点の収録データに基づきます。' if w['ver'] else ''
    net_txt = 'インターネット受付は24時間利用できるため、日中に電話ができない方はネット申込みが便利です。' if r.get('internetHours') else '受付時間内の申込みが必要なため、余裕を持って手続きを進めましょう。'

    body_html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta http-equiv="Content-Security-Policy" content="{CSP_META}">
<meta name="referrer" content="strict-origin-when-cross-origin">
<title>{esc(title)}｜粗大ごみナビ</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{BASE_URL}{path}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="article">
<meta property="og:url" content="{BASE_URL}{path}">
<meta property="og:site_name" content="粗大ごみナビ">
<meta property="og:image" content="{BASE_URL}/ogp.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{BASE_URL}/ogp.png">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-4KRRV4LLLH"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-4KRRV4LLLH');</script>
{ld_blocks}{CSS}
</head>
<body>

<header class="top-bar">
  <a href="../index.html" class="logo">
    <div class="logo-ico">♻️</div>
    <span class="logo-txt">粗大ごみナビ</span>
  </a>
  <a href="index.html" class="blog-link">← ブログ一覧</a>
</header>

<div class="article-hero">
  <div class="article-category">{esc(category)}</div>
  <h1>{esc(name)}の粗大ごみ完全ガイド<br>【申込み方法・料金・持ち込み】</h1>
  <div class="article-meta">
    <span>📅 {DATE_JP}</span>
    <span>✍️ テラデザイン編集部</span>
    <span>📖 読了8分</span>
  </div>
  <div class="article-summary">
    {esc(name)}の粗大ごみの申込み先・処理券の買い方・持ち込み処分・収集できないものを、この1ページに整理しました。よく出る品目の手数料早見表つきです。
  </div>
</div>

<div class="main-wrap">

  <nav class="breadcrumb">
    <a href="../index.html">TOP</a>
    <span>›</span>
    <a href="index.html">ブログ</a>
    <span>›</span>
    <span>{esc(name)}の粗大ごみ完全ガイド</span>
  </nav>

  <nav class="toc">
    <div class="toc-title">📋 この記事の目次</div>
    <ol>
      <li><a href="#basic">{esc(name)}の粗大ごみ 申込み先と基本ルール</a></li>
      <li><a href="#steps">申込みから収集までの4ステップ</a></li>
      <li><a href="#fees">よく出る品目の手数料早見表</a></li>
      {'<li><a href="#details">品目別の捨て方ポイント</a></li>' if detail_html else ''}
      {'<li><a href="#carry">持ち込み処分はできますか？</a></li>' if carry_html else ''}
      {'<li><a href="#cannot">収集できないもの</a></li>' if unc_html else ''}
      <li><a href="#tips">知っておきたい実務ポイント</a></li>
      <li><a href="#faq">よくある質問</a></li>
    </ol>
  </nav>

  <article class="article-body">

    <h2 id="basic">{esc(name)}の粗大ごみ 申込み先と基本ルール</h2>

    <div class="definition-box">
      <div class="def-label">まとめ</div>
      <p>{esc(name)}の粗大ごみは事前申込み制です。手数料は品目により{range_txt}（全{n_items}品目収録・2026年5月時点）。申込みから収集まで日数がかかるため、処分が決まったら早めに手続きしましょう。</p>
    </div>

    {info_table}

    <p>{net_txt}申込みの前に品目ごとの手数料を確認しておくと、処理券の購入が一度で済みます。{esc(name)}の全{n_items}品目の料金は<a href="/city/{cid}.html">{esc(name)}の品目別料金一覧</a>でも確認できます。</p>

    <h2 id="steps">申込みから収集までの4ステップ</h2>

    <div class="step-flow">
      <div class="step-item">
        <div class="step-num">1</div>
        <div class="step-content">
          <div class="step-title">品目と手数料を確認する</div>
          <p class="step-desc">捨てたい品目のサイズを測り、手数料を確認します。検索アプリなら{esc(name)}の品目を選ぶだけで料金と合計金額がわかります。</p>
        </div>
      </div>
      <div class="step-item">
        <div class="step-num">2</div>
        <div class="step-content">
          <div class="step-title">収集を申し込む</div>
          <p class="step-desc">{esc((r.get('applicationMethod') or '電話またはインターネット') )}。品目・個数・収集場所を伝え、収集日と必要な手数料額を確認します。</p>
        </div>
      </div>
      <div class="step-item">
        <div class="step-num">3</div>
        <div class="step-content">
          <div class="step-title">処理券を購入して貼る</div>
          <p class="step-desc">{esc((r.get('paymentMethod') or '指定の販売店で処理券を購入し、品物に貼付します'))}</p>
        </div>
      </div>
      <div class="step-item">
        <div class="step-num">4</div>
        <div class="step-content">
          <div class="step-title">収集日の朝、指定場所に出す</div>
          <p class="step-desc">{esc((r.get('collectionMethod') or '収集日当日の朝、指定された場所へ出します。'))}</p>
        </div>
      </div>
    </div>

    <div class="cta-box">
      <h3>{esc(name)}の料金を検索・合計する</h3>
      <p>全{n_items}品目の手数料と申込み先を無料で確認。複数品目の合計金額もその場で計算できます。</p>
      <a href="/?city={cid}" class="btn-cta">♻️ {esc(name)}の料金を無料で調べる</a>
    </div>

    <h2 id="fees">{esc(name)}でよく出る品目の手数料早見表</h2>

    <p>引越しや買い替えでよく処分される品目の手数料をまとめました（2026年5月時点の収録データ）。</p>

    {pop_table}

    <p class="note-box">{ver_note}同じ品目でもサイズにより手数料が変わる場合があります。掲載のない品目や正確な区分は<a href="/?city={cid}">検索アプリ</a>でご確認ください。</p>

    {fee_distribution_para(items, name)}

    {uniform_fee_para(w, fmin, fmax)}

    {base_plus_exception_para(w)}

    {top_table}

    {detail_html}

    {carry_html}

    {unc_html}

    <h2 id="tips">知っておきたい実務ポイント</h2>
    {PRACTICAL_TIPS}

    <h2 id="faq">よくある質問（{esc(name)}の粗大ごみ）</h2>

    {faq_html}

    <p style="font-size:12px;color:var(--muted);margin-top:20px;">{DISCLAIMER}</p>

    <div class="cta-box">
      <h3>捨てたい品目の料金をまとめてチェック</h3>
      <p>ソファ・ベッド・自転車…{esc(name)}の粗大ごみ料金を、まとめて検索・合計できます。</p>
      <a href="/?city={cid}" class="btn-cta">📱 {esc(name)}の料金を検索する</a>
    </div>

    <h2>{esc(grid_title)}</h2>
    <div class="ward-grid">{other_links}</div>

    <div class="related-section">
      <div class="related-title">📚 関連記事</div>
      <a href="sodaigomi-complete-guide.html" class="related-card">
        <div class="rc-tag">出し方・手順ガイド</div>
        <div class="rc-title">粗大ごみを正しく捨てる方法【2026年最新版・完全ガイド】</div>
      </a>
      <a href="sodaigomi-save-money-guide.html" class="related-card">
        <div class="rc-tag">料金・節約</div>
        <div class="rc-title">粗大ごみを安く処分する5つの方法｜自己搬入で半額になる自治体も</div>
      </a>
      <a href="sofa-disposal-guide.html" class="related-card">
        <div class="rc-tag">品目別ガイド</div>
        <div class="rc-title">ソファの処分費用はいくら？主要12都市の粗大ごみ料金比較</div>
      </a>
    </div>

  </article>
</div>

<footer>
  <p>© 2026 粗大ごみナビ | Powered by 株式会社テラデザイン</p>
  <p style="margin-top:6px;"><a href="../index.html">料金検索アプリ</a> | <a href="../area/">対応エリア一覧</a> | <a href="index.html">ブログ一覧</a> | <a href="../disclaimer.html">免責事項</a></p>
</footer>

</body>
</html>'''
    return slug, body_html


def visible_chars(src):
    body = re.sub(r'<script.*?</script>|<style.*?</style>', '', src, flags=re.S)
    text = re.sub(r'<[^>]+>', '', body)
    return len(re.sub(r'\s+', '', text))


def main():
    results = []
    for cid, _ in WARDS:
        w = load_ward(cid)
        slug, html_out = ward_page(w, ALL_NAMES)
        with open(os.path.join(ROOT, 'blog', f'{slug}.html'), 'w', encoding='utf-8') as f:
            f.write(html_out)
        results.append((slug, w['name'], visible_chars(html_out)))
    for cid, _ in MAJOR_CITIES:
        w = load_ward(cid)
        slug, html_out = ward_page(w, MAJOR_NAMES, '都市別ガイド', '主要都市の粗大ごみガイド')
        with open(os.path.join(ROOT, 'blog', f'{slug}.html'), 'w', encoding='utf-8') as f:
            f.write(html_out)
        results.append((slug, w['name'], visible_chars(html_out)))
    for slug, name, chars in results:
        print(f'  {slug}: {name} {chars}字')
    short = [r for r in results if r[2] < 3500]
    print(f'\n{len(results)} pages generated. under 3500 chars: {len(short)}')
    for s in short:
        print('  SHORT:', s)


# 他都市リンク用の名前一覧（実行時に先読み）
ALL_NAMES = []
MAJOR_NAMES = []

if __name__ == '__main__':
    ALL_NAMES = [(cid, load_ward(cid)['name']) for cid, _ in WARDS]
    MAJOR_NAMES = [(cid, load_ward(cid)['name']) for cid, _ in MAJOR_CITIES]
    main()
