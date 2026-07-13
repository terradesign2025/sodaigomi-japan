# -*- coding: utf-8 -*-
"""
SEO用 静的ページ生成スクリプト（粗大ごみナビ）

cities/*/​*_v2.json から以下を生成する:
  - city/{cityId}.html   … 市区別ランディングページ（全品目の料金表つき）
  - area/{prefCode}.html … 都道府県別の対応市区インデックス
  - area/index.html      … 全国の対応エリア一覧
  - sitemap.xml          … 上記を含めて全面再生成

データ更新後は毎回このスクリプトを再実行すること:
  python gen_seo_pages.py
"""
import json, os, sys, glob, html, re

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = 'https://sodaigomi-navi.com'
SITE_NAME = '粗大ごみナビ'
GA_ID = 'G-4KRRV4LLLH'
ROOT = os.path.dirname(os.path.abspath(__file__))

PREF_NAMES = {
    '01':'北海道','02':'青森県','03':'岩手県','04':'宮城県','05':'秋田県','06':'山形県','07':'福島県',
    '08':'茨城県','09':'栃木県','10':'群馬県','11':'埼玉県','12':'千葉県','13':'東京都','14':'神奈川県',
    '15':'新潟県','16':'富山県','17':'石川県','18':'福井県','19':'山梨県','20':'長野県',
    '21':'岐阜県','22':'静岡県','23':'愛知県','24':'三重県',
    '25':'滋賀県','26':'京都府','27':'大阪府','28':'兵庫県','29':'奈良県','30':'和歌山県',
    '31':'鳥取県','32':'島根県','33':'岡山県','34':'広島県','35':'山口県',
    '36':'徳島県','37':'香川県','38':'愛媛県','39':'高知県',
    '40':'福岡県','41':'佐賀県','42':'長崎県','43':'熊本県','44':'大分県','45':'宮崎県','46':'鹿児島県','47':'沖縄県',
}
REGIONS = [
    ('北海道・東北', ['01','02','03','04','05','06','07']),
    ('関東', ['08','09','10','11','12','13','14']),
    ('中部', ['15','16','17','18','19','20','21','22','23']),
    ('近畿', ['24','25','26','27','28','29','30']),
    ('中国', ['31','32','33','34','35']),
    ('四国', ['36','37','38','39']),
    ('九州・沖縄', ['40','41','42','43','44','45','46','47']),
]
# 区市ガイドのブログ記事があるcityId → blog/{slug}-sodaigomi-guide.html
BLOG_GUIDE_MAP = {
    '13121':'adachi','13118':'arakawa','13105':'bunkyo','12100':'chiba','13101':'chiyoda',
    '13102':'chuo','13123':'edogawa','40130':'fukuoka','13201':'hachioji','22130':'hamamatsu',
    '34100':'hiroshima','13119':'itabashi','13122':'katsushika','14130':'kawasaki','13117':'kita',
    '40100':'kitakyushu','28100':'kobe','13108':'koto','43100':'kumamoto','26100':'kyoto',
    '13110':'meguro','13103':'minato','23100':'nagoya','13114':'nakano','13120':'nerima',
    '15100':'niigata','33100':'okayama','27100':'osaka','13111':'ota','14150':'sagamihara',
    '11100':'saitama','27140':'sakai','01100':'sapporo','04100':'sendai','13112':'setagaya',
    '13113':'shibuya','13109':'shinagawa','13104':'shinjuku','22100':'shizuoka','13115':'suginami',
    '13107':'sumida','13106':'taito','13116':'toshima','14100':'yokohama',
}

GOJUON = ['あ','か','さ','た','な','は','ま','や','ら','わ','特']
POPULAR_KEYWORDS = [
    'ソファ','ベッド','マットレス','タンス','布団','自転車','テーブル','椅子',
    '本棚','食器棚','カーペット','電子レンジ','ストーブ','扇風機','掃除機','ベビーカー',
]

def esc(s):
    return html.escape(str(s), quote=True) if s is not None else ''

def fee_str(fee):
    if isinstance(fee, (int, float)) and fee > 0:
        return f'{int(fee):,}円'
    if isinstance(fee, str) and fee.strip():
        return esc(fee)
    return '—'

def kana_order(item):
    k = item.get('k') or ['']
    key = k[0] if k else ''
    try:
        gi = GOJUON.index(key)
    except ValueError:
        gi = len(GOJUON)
    return (gi, item.get('n', ''))

# GitHub PagesはHTTPレスポンスヘッダーを設定できないため、CSPはmetaタグで配信する
# （frame-ancestors等ヘッダー専用ディレクティブは_headersに残置＝Cloudflare移行時に有効化）
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

def head_common(title, desc, canonical_path, og_type='website'):
    url = BASE_URL + canonical_path
    return f'''<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta http-equiv="Content-Security-Policy" content="{CSP_META}">
<meta name="referrer" content="strict-origin-when-cross-origin">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="{og_type}">
<meta property="og:url" content="{url}">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:image" content="{BASE_URL}/ogp.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{BASE_URL}/ogp.png">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{GA_ID}');</script>'''

CSS = '''<style>
:root{--p:#34C759;--pd:#28A745;--pl:#F0FBF4;--bg:#F4F6FB;--card:#fff;--t1:#1C1C1E;--t2:#636366;--t3:#8E8E93;--b:#E5E5EA;--sh:0 2px 12px rgba(0,0,0,.06);--r:14px}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans","Noto Sans JP",sans-serif;background:var(--bg);color:var(--t1);line-height:1.7;font-size:15px}
.wrap{max-width:720px;margin:0 auto;padding:0 16px 40px}
header.site{background:var(--p);padding:12px 16px}
header.site a{color:#fff;font-weight:800;font-size:16px;text-decoration:none}
.crumb{font-size:12px;color:var(--t3);padding:12px 0;overflow-x:auto;white-space:nowrap}
.crumb a{color:var(--t2);text-decoration:none}
.crumb a:hover{color:var(--p)}
h1{font-size:21px;line-height:1.4;margin:6px 0 10px}
h2{font-size:17px;margin:28px 0 10px;padding-left:10px;border-left:4px solid var(--p)}
.lead{color:var(--t2);font-size:14px;margin-bottom:14px}
.note{font-size:12px;color:var(--t3);margin-top:8px}
.cta{display:block;background:var(--p);color:#fff;text-align:center;font-weight:700;padding:14px;border-radius:12px;text-decoration:none;margin:16px 0;box-shadow:var(--sh)}
.cta:hover{background:var(--pd)}
.card{background:var(--card);border-radius:var(--r);box-shadow:var(--sh);padding:16px;margin-bottom:14px}
table{width:100%;border-collapse:collapse;background:var(--card);border-radius:var(--r);overflow:hidden;box-shadow:var(--sh);font-size:14px}
th,td{padding:9px 12px;border-bottom:1px solid var(--b);text-align:left;vertical-align:top;word-break:break-word;overflow-wrap:anywhere}
th{background:var(--pl);font-size:13px;white-space:nowrap}
td.fee{white-space:nowrap;font-weight:700;color:var(--pd)}
tr:last-child td{border-bottom:none}
.item-note{display:block;font-size:11px;color:var(--t3);font-weight:400}
details{background:var(--card);border-radius:var(--r);box-shadow:var(--sh);padding:12px 16px;margin-bottom:10px}
summary{font-weight:700;cursor:pointer;font-size:14px}
details p{margin-top:8px;font-size:14px;color:var(--t2)}
.links{display:flex;flex-wrap:wrap;gap:8px}
.links a{background:var(--card);border:1px solid var(--b);border-radius:20px;padding:6px 14px;font-size:13px;color:var(--t1);text-decoration:none}
.links a:hover{border-color:var(--p);color:var(--pd)}
.pref-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}
.pref-grid a{background:var(--card);border-radius:10px;padding:10px 12px;font-size:14px;text-decoration:none;color:var(--t1);box-shadow:var(--sh)}
.pref-grid a:hover{color:var(--pd)}
.pref-grid .cnt{font-size:11px;color:var(--t3);display:block}
.pref-grid .soon{background:#EEE;color:var(--t3);border-radius:10px;padding:10px 12px;font-size:14px}
footer.site{margin-top:36px;padding-top:18px;border-top:1px solid var(--b);font-size:12px;color:var(--t3)}
footer.site nav{display:flex;flex-wrap:wrap;gap:6px 14px;margin-bottom:10px}
footer.site a{color:var(--t2);text-decoration:none}
footer.site a:hover{color:var(--p)}
.disclaimer{background:var(--card);border-radius:var(--r);padding:12px 14px;font-size:11px;color:var(--t3);line-height:1.8;margin-bottom:14px}
.blog-link{display:block;background:var(--pl);color:var(--pd);text-align:center;font-weight:700;padding:12px;border-radius:12px;text-decoration:none;margin:16px 0;font-size:14px}
.blog-link:hover{background:var(--p);color:#fff}
.pr-list{padding:4px 0}
.pr-item{padding:12px 16px;border-bottom:1px solid var(--b)}
.pr-item:last-child{border-bottom:none}
.pr-item a{color:var(--t1);font-weight:700;font-size:14px;text-decoration:none}
.pr-item a:hover{color:var(--pd)}
.pr-item span{color:var(--t1);font-weight:700;font-size:14px}
.pr-meta{font-size:12px;color:var(--t3);margin-top:2px}
</style>'''

FOOTER_DISCLAIMER = '掲載している料金・申込方法は各自治体の公式情報をもとに作成していますが、改定等により実際と異なる場合があります。お申し込み前に必ず各自治体の公式情報をご確認ください。'

def site_footer():
    return f'''<footer class="site">
<div class="disclaimer">{FOOTER_DISCLAIMER}</div>
<nav>
<a href="/">料金検索アプリ</a>
<a href="/area/">対応エリア一覧</a>
<a href="/blog/">お役立ち記事</a>
<a href="/sponsor.html">掲載パートナー募集</a>
<a href="/privacy.html">プライバシーポリシー</a>
<a href="/disclaimer.html">免責事項</a>
</nav>
<div>© 2026 株式会社テラデザイン</div>
</footer>'''

def load_cities():
    cities = []
    for path in sorted(glob.glob(os.path.join(ROOT, 'cities', '*', '*_v2.json'))):
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f'  [skip] parse error: {path}: {e}')
            continue
        city = data.get('city') or {}
        # items はトップレベル or city 内蔵の2形式がある（app.js normalizeCityData と同等）
        items = data.get('items') or city.get('items') or []
        if not city.get('id') or not city.get('name') or not items:
            print(f'  [skip] missing city/items: {path}')
            continue
        cities.append({
            'id': city['id'],
            'name': city['name'],
            'pref_code': city['id'][:2],
            'pref': city.get('prefecture') or PREF_NAMES.get(city['id'][:2], ''),
            'dataVersion': city.get('dataVersion', ''),
            'rules': city.get('rules') or {},
            'items': items,
            'uncollectible': data.get('uncollectible') or city.get('uncollectible') or [],
        })
    # 同一IDの重複は最初のものを採用
    seen, uniq = set(), []
    for c in cities:
        if c['id'] in seen:
            continue
        seen.add(c['id'])
        uniq.append(c)
    return uniq

def popular_items(items):
    picked, used = [], set()
    for kw in POPULAR_KEYWORDS:
        for it in items:
            name = it.get('n', '')
            if kw in name and name not in used and isinstance(it.get('fee'), (int, float)) and it['fee'] > 0:
                picked.append(it)
                used.add(name)
                break
        if len(picked) >= 12:
            break
    return picked

def load_pr_listings(cid):
    path = os.path.join(ROOT, 'pr', f'{cid}.json')
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return []
    if data.get('sponsored'):
        return [data['sponsored']]
    return data.get('listings') or []

def pr_section_html(cid, name):
    listings = load_pr_listings(cid)
    if not listings:
        return ''
    items = ''.join(
        f'''<div class="pr-item"><a href="{esc(b['url'])}" target="_blank" rel="noopener">{esc(b['name'])}</a>
<div class="pr-meta">{esc(b.get('category',''))}{f" ・ {esc(b['note'])}" if b.get('note') else ''}{f" ・ {esc(b['address'])}" if b.get('address') else ''}</div></div>'''
        if b.get('url') else
        f'''<div class="pr-item"><span>{esc(b['name'])}</span>
<div class="pr-meta">{esc(b.get('category',''))}{f" ・ {esc(b['note'])}" if b.get('note') else ''}{f" ・ {esc(b['address'])}" if b.get('address') else ''}</div></div>'''
        for b in listings
    )
    return f'''<h2>{esc(name)}の地元リサイクルショップ・不用品買取店</h2>
<div class="card pr-list">{items}</div>'''

def blog_link_html(cid, name):
    slug = BLOG_GUIDE_MAP.get(cid)
    if not slug:
        return ''
    return f'''<a class="blog-link" href="/blog/{slug}-sodaigomi-guide.html">📖 {esc(name)}の粗大ごみ完全ガイド記事を読む →</a>'''

def fee_range(items):
    fees = [it['fee'] for it in items if isinstance(it.get('fee'), (int, float)) and it['fee'] > 0]
    if not fees:
        return None, None
    return int(min(fees)), int(max(fees))

def build_faq(c, fmin, fmax):
    r = c['rules']
    qa = []
    if fmin is not None:
        example = ''
        pops = popular_items(c['items'])[:2]
        if pops:
            example = '例えば' + '、'.join(f"{p['n']}は{fee_str(p['fee'])}" for p in pops) + 'です。'
        qa.append((f"{c['name']}の粗大ごみ処分はいくらかかりますか？",
                   f"品目により{fmin:,}円〜{fmax:,}円です。{example}最新の料金は{c['name']}の公式サイトでご確認ください。"))
    if r.get('applicationMethod'):
        qa.append((f"{c['name']}の粗大ごみはどうやって申し込みますか？", r['applicationMethod']))
    if r.get('selfCarryIn'):
        qa.append((f"{c['name']}では粗大ごみの持ち込み処分はできますか？", r['selfCarryIn']))
    if r.get('paymentMethod'):
        qa.append((f"{c['name']}の粗大ごみ処理券はどこで買えますか？", r['paymentMethod']))
    return qa[:4]

def city_page(c, pref_cities):
    cid, name, pref = c['id'], c['name'], c['pref']
    r = c['rules']
    items = sorted(c['items'], key=kana_order)
    n_items = len(items)
    fmin, fmax = fee_range(items)
    ver = c['dataVersion']

    title = f'{name}の粗大ごみ処分料金一覧・出し方・申込み方法｜{SITE_NAME}'
    range_txt = f'{fmin:,}円〜{fmax:,}円' if fmin is not None else ''
    desc = f'{pref}{name}の粗大ごみ処分料金を品目別に掲載（全{n_items}品目{"・" + range_txt if range_txt else ""}）。申込み先・処理券の購入方法・持ち込み可否・出し方のルールをまとめています。'
    path = f'/city/{cid}.html'

    faq = build_faq(c, fmin, fmax)

    # JSON-LD
    breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": SITE_NAME, "item": BASE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": pref, "item": f"{BASE_URL}/area/{c['pref_code']}.html"},
            {"@type": "ListItem", "position": 3, "name": name, "item": BASE_URL + path},
        ],
    }
    webpage = {
        "@context": "https://schema.org", "@type": "WebPage",
        "name": title, "description": desc, "url": BASE_URL + path,
        "inLanguage": "ja", "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": BASE_URL + "/"},
        "publisher": {"@type": "Organization", "name": "株式会社テラデザイン"},
    }
    faq_ld = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in faq
        ],
    } if faq else None

    ld_blocks = ''.join(
        f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n'
        for ld in [breadcrumb, webpage] + ([faq_ld] if faq_ld else [])
    )

    # 基本情報テーブル
    info_rows = []
    info_fields = [
        ('粗大ごみの定義', r.get('definition')),
        ('申込み方法', r.get('applicationMethod')),
        ('電話番号', r.get('contact')),
        ('受付時間', r.get('hours')),
        ('ネット受付', r.get('internetHours')),
        ('支払い方法', r.get('paymentMethod')),
        ('出し方（収集）', r.get('collectionMethod')),
        ('持ち込み処分', r.get('selfCarryIn')),
        ('料金の仕組み', r.get('pointSystemNote')),
    ]
    for label, val in info_fields:
        if val:
            info_rows.append(f'<tr><th>{esc(label)}</th><td>{esc(val)}</td></tr>')
    if r.get('websiteUrl'):
        info_rows.append(f'<tr><th>公式サイト</th><td><a href="{esc(r["websiteUrl"])}" target="_blank" rel="noopener">{esc(name)}の粗大ごみページ ↗</a></td></tr>')
    info_table = f'<table>{"".join(info_rows)}</table>' if info_rows else ''

    # 人気品目
    pops = popular_items(items)
    pop_html = ''
    if pops:
        rows = ''.join(
            f'<tr><td>{esc(p["n"])}</td><td class="fee">{fee_str(p.get("fee"))}</td></tr>'
            for p in pops
        )
        pop_html = f'''<h2>{esc(name)}でよく検索される品目の手数料</h2>
<table><tr><th>品目</th><th>手数料</th></tr>{rows}</table>'''

    # 全品目テーブル
    all_rows = []
    for it in items:
        note = f'<span class="item-note">{esc(it["note"])}</span>' if it.get('note') else ''
        m = esc(it.get('m', ''))
        all_rows.append(f'<tr><td>{esc(it.get("n",""))}{note}</td><td class="fee">{fee_str(it.get("fee"))}</td><td>{m}</td></tr>')
    all_table = f'''<table><tr><th>品目</th><th>手数料</th><th>出し方</th></tr>{"".join(all_rows)}</table>'''

    # 収集できないもの
    unc_html = ''
    unc_parts = []
    if c['uncollectible']:
        # dict形式（{n, reason}）と文字列形式の両方に対応
        unc_rows = []
        for u in c['uncollectible']:
            if isinstance(u, dict):
                unc_rows.append(f'<tr><td>{esc(u.get("n",""))}</td><td>{esc(u.get("reason",""))}</td></tr>')
            else:
                unc_rows.append(f'<tr><td colspan="2">{esc(u)}</td></tr>')
        unc_parts.append(f'<table><tr><th>品目</th><th>理由・処分方法</th></tr>{"".join(unc_rows)}</table>')
    if r.get('nonCollectibleNote'):
        unc_parts.append(f'<p class="note">{esc(r["nonCollectibleNote"])}</p>')
    if unc_parts:
        unc_html = f'<h2>{esc(name)}で収集できないもの</h2>' + ''.join(unc_parts)

    # FAQ
    faq_html = ''
    if faq:
        blocks = ''.join(
            f'<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>'
            for q, a in faq
        )
        faq_html = f'<h2>よくある質問（{esc(name)}の粗大ごみ）</h2>{blocks}'

    # 同一都道府県の内部リンク
    others = [x for x in pref_cities if x['id'] != cid][:12]
    rel_html = ''
    if others:
        links = ''.join(f'<a href="/city/{x["id"]}.html">{esc(x["name"])}</a>' for x in others)
        rel_html = f'''<h2>{esc(pref)}のほかの市区を調べる</h2>
<div class="links">{links}<a href="/area/{c['pref_code']}.html"><strong>{esc(pref)}の対応市区一覧 →</strong></a></div>'''

    ver_note = f'※ 掲載内容は{esc(ver)}時点の情報です。' if ver else ''
    lead_app = r.get('applicationMethod', '')
    lead_app_short = (lead_app[:40] + '…') if len(lead_app) > 40 else lead_app
    blog_link = blog_link_html(cid, name)
    pr_html = pr_section_html(cid, name)

    return f'''<!DOCTYPE html>
<html lang="ja">
<head>
{head_common(title, desc, path, 'article')}
{ld_blocks}{CSS}
</head>
<body>
<header class="site"><a href="/">🗑️ {SITE_NAME}</a></header>
<div class="wrap">
<nav class="crumb"><a href="/">トップ</a> › <a href="/area/{c['pref_code']}.html">{esc(pref)}</a> › {esc(name)}</nav>
<h1>{esc(pref)}{esc(name)}の粗大ごみ処分料金・出し方</h1>
<p class="lead">{esc(name)}の粗大ごみ処分手数料を全{n_items}品目掲載しています。{f'手数料は品目により{range_txt}です。' if range_txt else ''}{f'申込みは{esc(lead_app_short)}。' if lead_app_short else ''}{ver_note}</p>
<a class="cta" href="/?city={cid}">🔍 品目を検索して料金を合計する（無料アプリ）</a>
{blog_link}
<h2>{esc(name)}の粗大ごみ 申込み・出し方の基本情報</h2>
{info_table}
{pop_html}
<h2>{esc(name)}の粗大ごみ処分手数料 全品目一覧（{n_items}品目）</h2>
{all_table}
<p class="note">{FOOTER_DISCLAIMER}</p>
{unc_html}
{faq_html}
{pr_html}
<a class="cta" href="/?city={cid}">📱 {esc(name)}の料金をアプリで検索する</a>
{rel_html}
{site_footer()}
</div>
</body>
</html>'''

def area_page(pref_code, pref_name, pref_cities):
    n = len(pref_cities)
    title = f'{pref_name}の粗大ごみ処分料金一覧（{n}市区対応）｜{SITE_NAME}'
    desc = f'{pref_name}の粗大ごみ処分料金・申込み方法・出し方を市区町村別に無料で調べられます。対応{n}市区。品目別の手数料一覧と申込み先をまとめています。'
    path = f'/area/{pref_code}.html'

    breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": SITE_NAME, "item": BASE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": "対応エリア一覧", "item": BASE_URL + "/area/"},
            {"@type": "ListItem", "position": 3, "name": pref_name, "item": BASE_URL + path},
        ],
    }
    itemlist = {
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": title, "description": desc, "url": BASE_URL + path, "inLanguage": "ja",
        "publisher": {"@type": "Organization", "name": "株式会社テラデザイン"},
    }
    ld_blocks = ''.join(
        f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n'
        for ld in [breadcrumb, itemlist]
    )
    links = ''.join(
        f'<a href="/city/{c["id"]}.html">{esc(c["name"])}<span class="cnt">{len(c["items"])}品目掲載</span></a>'
        for c in pref_cities
    )
    return f'''<!DOCTYPE html>
<html lang="ja">
<head>
{head_common(title, desc, path)}
{ld_blocks}{CSS}
</head>
<body>
<header class="site"><a href="/">🗑️ {SITE_NAME}</a></header>
<div class="wrap">
<nav class="crumb"><a href="/">トップ</a> › <a href="/area/">対応エリア一覧</a> › {esc(pref_name)}</nav>
<h1>{esc(pref_name)}の粗大ごみ処分料金・出し方（{n}市区対応）</h1>
<p class="lead">{esc(pref_name)}で粗大ごみの処分料金・申込み方法を調べられる市区の一覧です。市区名を選ぶと、品目別の手数料一覧と申込み先を確認できます。</p>
<a class="cta" href="/">🔍 アプリで品目を検索する（無料）</a>
<h2>{esc(pref_name)}の対応市区一覧</h2>
<div class="pref-grid">{links}</div>
<p class="note">未対応の市区町村は順次追加しています。</p>
{site_footer()}
</div>
</body>
</html>'''

def area_index(by_pref):
    total = sum(len(v) for v in by_pref.values())
    title = f'全国の対応エリア一覧（{total}市区）｜{SITE_NAME}'
    desc = f'{SITE_NAME}が対応する全国{total}市区の一覧です。都道府県を選ぶと、市区町村別の粗大ごみ処分料金・申込み方法を確認できます。'
    path = '/area/'

    breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": SITE_NAME, "item": BASE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": "対応エリア一覧", "item": BASE_URL + path},
        ],
    }
    ld_blocks = f'<script type="application/ld+json">{json.dumps(breadcrumb, ensure_ascii=False)}</script>\n'

    sections = []
    for region_name, codes in REGIONS:
        cells = []
        for code in codes:
            pname = PREF_NAMES[code]
            cities = by_pref.get(code)
            if cities:
                cells.append(f'<a href="/area/{code}.html">{esc(pname)}<span class="cnt">{len(cities)}市区</span></a>')
            else:
                cells.append(f'<span class="soon">{esc(pname)}<span class="cnt">準備中</span></span>')
        sections.append(f'<h2>{esc(region_name)}</h2><div class="pref-grid">{"".join(cells)}</div>')

    return f'''<!DOCTYPE html>
<html lang="ja">
<head>
{head_common(title, desc, path)}
{ld_blocks}{CSS}
</head>
<body>
<header class="site"><a href="/">🗑️ {SITE_NAME}</a></header>
<div class="wrap">
<nav class="crumb"><a href="/">トップ</a> › 対応エリア一覧</nav>
<h1>全国の対応エリア一覧（{total}市区）</h1>
<p class="lead">都道府県を選ぶと、対応している市区町村の粗大ごみ処分料金・申込み方法・出し方を確認できます。815市区への拡大を進めています。</p>
<a class="cta" href="/">🔍 アプリで品目を検索する（無料）</a>
{''.join(sections)}
{site_footer()}
</div>
</body>
</html>'''

def lastmod_of(ver):
    m = re.fullmatch(r'(\d{4})-(\d{2})', ver or '')
    return f'{m.group(1)}-{m.group(2)}-01' if m else None

def gen_sitemap(cities, pref_codes):
    entries = [
        ('/', 'weekly', '1.0', None),
        ('/lp.html', 'monthly', '0.8', None),
        ('/sponsor.html', 'monthly', '0.6', None),
        ('/blog/', 'weekly', '0.9', None),
        ('/area/', 'weekly', '0.8', None),
    ]
    # ブログ記事は blog/*.html を自動検出（index.html除く）
    for path in sorted(glob.glob(os.path.join(ROOT, 'blog', '*.html'))):
        fname = os.path.basename(path)
        if fname == 'index.html':
            continue
        entries.append((f'/blog/{fname}', 'monthly', '0.8', None))
    for code in sorted(pref_codes):
        entries.append((f'/area/{code}.html', 'monthly', '0.7', None))
    for c in cities:
        entries.append((f'/city/{c["id"]}.html', 'monthly', '0.7', lastmod_of(c['dataVersion'])))

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, freq, prio, lastmod in entries:
        lines.append('  <url>')
        lines.append(f'    <loc>{BASE_URL}{loc}</loc>')
        if lastmod:
            lines.append(f'    <lastmod>{lastmod}</lastmod>')
        lines.append(f'    <changefreq>{freq}</changefreq>')
        lines.append(f'    <priority>{prio}</priority>')
        lines.append('  </url>')
    lines.append('</urlset>')
    return '\n'.join(lines) + '\n'

def main():
    print('Loading city data...')
    cities = load_cities()
    print(f'  {len(cities)} cities loaded')

    by_pref = {}
    for c in cities:
        by_pref.setdefault(c['pref_code'], []).append(c)
    for v in by_pref.values():
        v.sort(key=lambda x: x['id'])

    os.makedirs(os.path.join(ROOT, 'city'), exist_ok=True)
    os.makedirs(os.path.join(ROOT, 'area'), exist_ok=True)

    n_city = 0
    for c in cities:
        html_out = city_page(c, by_pref[c['pref_code']])
        with open(os.path.join(ROOT, 'city', f'{c["id"]}.html'), 'w', encoding='utf-8') as f:
            f.write(html_out)
        n_city += 1
    print(f'  city/  : {n_city} pages')

    for code, pcs in sorted(by_pref.items()):
        with open(os.path.join(ROOT, 'area', f'{code}.html'), 'w', encoding='utf-8') as f:
            f.write(area_page(code, PREF_NAMES[code], pcs))
    print(f'  area/  : {len(by_pref)} prefecture pages')

    with open(os.path.join(ROOT, 'area', 'index.html'), 'w', encoding='utf-8') as f:
        f.write(area_index(by_pref))
    print('  area/index.html generated')

    with open(os.path.join(ROOT, 'sitemap.xml'), 'w', encoding='utf-8') as f:
        f.write(gen_sitemap(cities, by_pref.keys()))
    print(f'  sitemap.xml regenerated ({7 + len(by_pref) + n_city} URLs)')

if __name__ == '__main__':
    main()
