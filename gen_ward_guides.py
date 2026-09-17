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
# 2026-09-14: Codexレビュー（_internal/codex_review_2026-09-14.md）を受けたテンプレ修正で再生成
DATE_MOD = '2026-09-14'
DATE_MOD_JP = '2026年9月14日'
EDITION = '2026年9月版'

# ブログ掲載時だけ差し替える文言（元データは変更しない）
# 13121 足立区: 持込先の民間事業者名はBLOG_RULES「他社実名禁止」に合わせて伏せる
BLOG_TEXT_OVERRIDES = {
    '13121': {
        'selfCarryIn': '事前申込制で持込可能・料金無料。区民のみ利用可。年度内20個まで。持込先は区が指定する2か所（区の公式案内でご確認ください）。本人確認書類必須',
    },
    # 以下は 2026-09-14 に各自治体の公式サイトで確認した内容（根拠: _internal/fix_evidence/00_evidence_base.md F節）
    '14100': {  # 横浜市: 受付は月〜土（祝日含む）17:00まで。持込先は自己搬入ヤード（清掃工場ではない）
        'hours': '月〜土（祝日含む）8:30〜17:00（日曜・年末年始12/31〜1/3除く）',
        'selfCarryIn': '市内4か所の自己搬入ヤードへ持込可（事前に粗大ごみ受付センターへ申込み・本人確認書類必要）。受付は9:00〜12:00・13:00〜16:00、日曜・年末年始休み。1日20個まで（栄ストックヤードの簡易申込みは10個まで）',
    },
    '14130': {  # 川崎市: 家庭の粗大ごみは処理施設へ直接持ち込めない
        'selfCarryIn': '川崎市では家庭ごみ・粗大ごみを処理施設へ直接持ち込むことはできません（戸別収集のみ）。引越し等で一時的に多量に出る場合は、市の許可業者が有料で収集する「一時多量ごみ制度」があります',
    },
    '14150': {  # 相模原市: 直接搬入は予約不要・重量制
        'selfCarryIn': '北部粗大ごみ受入施設・南部粗大ごみ受入施設・津久井クリーンセンターへ直接搬入可（予約不要）。月〜土 9:00〜16:00（12/31〜1/3除く）。手数料は10kgにつき240円（10kg未満の端数は10kgとして計算）、スプリング付きベッドマットレスは1個につき2,900円加算。粗大ごみ搬入申請書が必要',
    },
    '26100': {  # 京都市: 持込先はクリーンセンター、前日までに要予約、100kgまで1,500円
        'selfCarryIn': '南部クリーンセンター・東北部クリーンセンターへ持込可。搬入前日までにインターネットまたは電話で要予約。搬入は月〜金（祝日含む）と第2・第4土曜の9:00〜16:30。手数料は100kgまで1,500円、100kgを超える分は10kgごとに200円加算。本人のごみに限り、自動車での搬入・身分証の提示が必要',
    },
    '28100': {  # 神戸市: 手数料は300/600/900/1,200円（一部3,000円）の区分。納付券の券種数はデータ未確認のため書かない
        'paymentMethod': '大型ごみ処理手数料納付券（シール券）をコンビニ・スーパー等で購入し、必要額分を組み合わせて品目に貼付。手数料は品目により300円・600円・900円・1,200円（一部3,000円）',
    },
    '40130': {  # 福岡市: 自己搬入は要予約（搬入希望時刻の30分前まで）
        'selfCarryIn': '市の処理施設への自己搬入可。事前予約が必要（搬入日の2週間前から搬入希望時刻の30分前まで。インターネット24時間または自己搬入ごみ事前受付センター 092-433-8234 月〜土 8:30〜16:00）。手数料は10kgまでごとに140円',
    },
    '22100': {  # 静岡市: 自己搬入の手数料はデータ未確認のため記載しない
        'selfCarryIn': '西ケ谷清掃工場・沼上清掃工場・清水ごみ受付センターへ家庭ごみの持ち込み可。受付は月〜金（祝日含む）8:30〜12:00・13:00〜16:00、土曜（祝日含む）8:30〜12:00。手数料・予約の要否は市の公式案内でご確認ください',
    },
    '13112': {  # 世田谷区: 持込先は船橋粗大ごみ中継所（清掃事務所は処理券の販売窓口）
        'selfCarryIn': '船橋粗大ごみ中継所（世田谷区船橋7-21-15）へ持込可。事前に粗大ごみ受付センターへ申込みが必要（申込みなしの持込不可）。土曜・日曜のうち申込時に指定された日の9:00〜12:00・13:00〜15:30。1世帯あたり1日1回・1回10個まで。手数料は収集の半額程度',
    },
}

# 収集不可データの理由文のうち、法律名・分類が不正確なものを表示時に置き換える
# （根拠: 家庭用PCの回収は「資源有効利用促進法」に基づくメーカー回収。「PCリサイクル法」という法律は存在しない／
#   家庭から出るタイヤは産業廃棄物ではなく、多くの自治体が「処理困難物」として収集対象外にしている）
REASON_FIX = [
    ('PCリサイクル法対象', '資源有効利用促進法に基づくメーカー回収の対象（PCリサイクルマーク）。市区の粗大ごみでは収集不可'),
    ('産廃扱い', '処理困難物のため市区では収集不可。購入店・専門業者へ'),
    ('二輪車リサイクル対象（電動自転車含む）', '二輪車リサイクル対象（フル電動自転車を含む。電動アシスト自転車は粗大ごみとして出せます）'),
]

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


def is_uncollectible(it):
    """収集不可として登録されている行（fee=0 でも料金ではない）"""
    m = it.get('m') or ''
    n = it.get('n') or ''
    return ('不可' in m) or ('収集不可' in n)


def is_special_free(it):
    """通常収集とは別制度の無料引取（例: 足立区の自転車移送所引取）"""
    return it.get('fee') == 0 and ('引取' in (it.get('m') or ''))


def collectible(it):
    return has_fee(it) and not is_uncollectible(it)


def priced_items(items):
    """料金レンジ・収録品目数の集計対象。収集不可は除外し、有料都市では別制度の0円も除外する"""
    col = [it for it in items if collectible(it)]
    if any(it['fee'] > 0 for it in col):
        col = [it for it in col if it['fee'] > 0 or not is_special_free(it)]
    return col


def asof(w):
    """データ確認時点（dataVersion '2026-05' → '2026年5月時点'）"""
    v = (w.get('ver') or '').strip()
    m = re.match(r'(\d{4})-(\d{1,2})', v)
    return f'{m.group(1)}年{int(m.group(2))}月時点' if m else '2026年5月時点'


def load_ward(cid):
    import glob as _glob
    paths = _glob.glob(os.path.join(ROOT, 'cities', '*', f'{cid}_v2.json'))
    with open(paths[0], encoding='utf-8') as f:
        data = json.load(f)
    city = data.get('city') or {}
    items = data.get('items') or city.get('items') or []
    rules = dict(city.get('rules') or {})
    rules.update(BLOG_TEXT_OVERRIDES.get(cid, {}))
    # 明らかな表記ミスの表示時修正（元データは変更しない）
    for k, v in list(rules.items()):
        if isinstance(v, str):
            rules[k] = v.replace('building解体材', '建物の解体材')
    return {
        'id': city['id'], 'name': city['name'],
        'ver': city.get('dataVersion', ''),
        'rules': rules,
        'items': items,
        'unc': data.get('uncollectible') or city.get('uncollectible') or [],
    }


# 品目名の部分一致だけで選ぶと「いす（ソファー以外）」「布団乾燥機」を拾ってしまうため、
# キーワードごとに除外語・優先語を持たせて選ぶ（Codexレビュー2026-09-14の指摘）
COMMON_EXCLUDE = ['カバー', '乾燥機', '干し']
KW_RULES = {
    'ソファ': {'exclude': ['ベッド', 'マッサージ'], 'prefer': ['ソファ', '応接']},
    'ベッド': {'exclude': ['ソファ', 'ウォーター', 'サマー', 'エア', '脚付', '折りたたみ', '折畳', 'ベビー', '乳児',
                           '介護', 'ガード', 'はしご', 'マット', 'セット', '二段', 'パイプ', 'ロフト', '電動', 'ヘッド', '部分'],
              'prefer': ['シングル', 'ベッド本体', 'ベッド枠', 'ベッド（', 'ベッド']},
    'マットレス': {'exclude': ['脚付', 'エア', 'ウォーター', '布団用', 'ベッド（', 'ベビー'], 'prefer': ['マットレス', 'ベッドマット']},
    'ベッドマット': {'exclude': ['脚付', 'エア', 'ウォーター'], 'prefer': ['ベッドマット']},
    'マット': {'exclude': ['脚付', 'エア', 'ウォーター', '布団', 'ベッド（', 'ベビー', 'バス', '玄関', 'ヨガ', 'フロア', 'キッチン', 'ジョイント', '珪藻土', '電気', 'ホット'],
             'prefer': ['スプリングマット', 'ベッドマット', 'マット']},
    '布団': {'exclude': ['座布団', 'こたつ', '袋', 'マットレス（', '用マット'], 'prefer': ['布団', 'ふとん', '掛布団', '敷布団']},
    'ふとん': {'exclude': ['座', 'こたつ', '袋'], 'prefer': ['ふとん']},
    '椅子': {'exclude': ['ソファ', '座椅子', 'マッサージ', 'チャイルド', 'ベビー', '車椅子'], 'prefer': ['椅子', 'いす']},
    'テーブル': {'exclude': ['サイド', 'こたつ', 'ちゃぶ'], 'prefer': ['テーブル']},
    '応接': {'exclude': ['テーブル', 'セット'], 'prefer': ['応接', 'ソファ', 'いす（応接', '椅子（応接']},
}


def _excluded_by_paren(n, kw):
    """「いす（ソファー以外）」「シングルベッド（マットレス除く）」のように、
    括弧内で kw 自体が除外されている品目は、その kw の候補にしない"""
    return bool(re.search(r'[（(][^）)]*' + re.escape(kw) + r'[^）)]*(以外|除く|除)[^）)]*[）)]', n))


def find_items(items, kw, limit=3):
    """kw に該当する品目を、除外語を外し優先語順に並べて返す（収集不可・別制度は含めない）"""
    rule = KW_RULES.get(kw, {})
    excl = COMMON_EXCLUDE + rule.get('exclude', [])
    prefer = rule.get('prefer', [kw])
    cand = []
    for idx, it in enumerate(items):
        n = it.get('n', '')
        if kw not in n or not collectible(it) or is_special_free(it):
            continue
        # 除外語は括弧の外だけで判定する（「ベッド（マットレス除く）」を「マット」で落とさない）
        n_out = re.sub(r'[（(][^）)]*[）)]', '', n)
        if any(x in n_out for x in excl) or _excluded_by_paren(n, kw):
            continue
        rank = next((i for i, p in enumerate(prefer) if n.startswith(p)), len(prefer))
        cand.append((rank, idx, it))
    cand.sort(key=lambda x: (x[0], x[1]))
    return [c[2] for c in cand[:limit]]


def find_item(items, kw):
    r = find_items(items, kw, 1)
    return r[0] if r else None


def popular_items(items, limit=24):
    picked, used = [], set()
    for kw in POPULAR_KEYWORDS:
        for it in find_items(items, kw, 3):
            if it.get('n') not in used:
                picked.append(it)
                used.add(it.get('n'))
                break
        if len(picked) >= limit:
            break
    # キーワード一致が少ない都市は、残りを収録順で補完（表の情報量を確保）
    if len(picked) < limit:
        for it in items:
            n = it.get('n', '')
            if n not in used and collectible(it) and not is_special_free(it):
                picked.append(it)
                used.add(n)
                if len(picked) >= limit:
                    break
    return picked


def item_note(it):
    """表の備考欄: 元データの note（切断条件・数量条件など）と、無料引取などの区分"""
    parts = []
    if it.get('note'):
        parts.append(str(it['note']))
    m = it.get('m') or ''
    if '無料' in m and it.get('fee', 0) == 0:
        parts.append(m)
    return '／'.join(parts)


def fee_table(rows):
    has_note = any(item_note(r) for r in rows)
    head = '<tr><th>品目</th><th>手数料</th>' + ('<th>備考</th>' if has_note else '') + '</tr>'
    body = ''.join(
        f'<tr><td>{esc(r["n"])}</td><td class="fee">{fee_str(r.get("fee"))}</td>'
        + (f'<td>{esc(item_note(r))}</td>' if has_note else '') + '</tr>'
        for r in rows
    )
    return f'<div class="table-wrap"><table>{head}{body}</table></div>'


def uniform_fee_para(w, fmin, fmax):
    """均一料金制・無料収集の都市向け解説（さいたま市・静岡市等）
    ※ 個別品目の note（「要解体」等）を市全体の対象基準として流用しない（Codex指摘）"""
    if fmin is None or fmin != fmax:
        return ''
    name, items = w['name'], w['items']
    if fmin == 0:
        notes = sorted({str(it['note']) for it in items if it.get('note')})
        note_txt = ('一部の品目には「' + '」「'.join(esc(n) for n in notes[:3]) + '」などの出し方の条件が付いています（早見表の備考欄参照）。'
                    if notes else '')
        return (f'<h3>{esc(name)}の粗大ごみ収集は手数料がかかりません</h3>'
                f'<p>{esc(name)}の収録データ（{asof(w)}）では、対象品目の戸別収集はすべて無料（手数料なし）です。'
                f'処理券の購入や貼付は不要ですが、事前の申込みは必要です。{note_txt}'
                f'サイズが基準に満たないものは通常ごみ、対象外の品目は別の処分方法になるため、迷ったら申込み時に品目と寸法を伝えて確認しましょう。</p>')
    return (f'<h3>{esc(name)}は品目によらない均一料金制です</h3>'
            f'<p>{esc(name)}の収録データ（{asof(w)}）では、粗大ごみの手数料は品目にかかわらず1点{fee_str(fmin)}の均一料金になっています。'
            f'「この家具はいくらだろう」と品目ごとに調べる必要がない、わかりやすい制度です。'
            f'ただし、サイズが基準に満たないものは通常ごみ、大きすぎるものは受付対象外となる場合があるため、'
            f'迷ったら申込み時に寸法を伝えて確認しましょう。</p>')


def base_plus_exception_para(w):
    """「一般◯円＋例外品目」型の料金体系解説（さいたま市等・収録品目が少ない都市向け）"""
    name, items = w['name'], w['items']
    if len(items) >= 20:
        return ''
    base = next((it for it in items if '一般' in it.get('n', '') and collectible(it)), None)
    if not base:
        return ''
    exceptions = [it for it in items if collectible(it) and it['fee'] != base['fee'] and it is not base]
    exc_txt = ''
    if exceptions:
        tops = sorted(exceptions, key=lambda x: -x['fee'])[:4]
        exc_txt = ('ただし、' + '、'.join(f'{esc(t["n"])}（{fee_str(t["fee"])}{"・" + esc(t["note"]) if t.get("note") else ""}）' for t in tops) +
                   'など、処理に手間がかかる品目は個別の料金が設定されています（1個・1本あたりなど課金単位は備考欄をご確認ください）。')
    note = base.get('note') or ''
    note_txt = f'一般料金の対象は「{esc(note)}」とされています。' if note else ''
    return (f'<h3>{esc(name)}の料金体系はシンプルです</h3>'
            f'<p>{esc(name)}の収録データ（{asof(w)}）では、一般的な家具・家電などの粗大ごみは「{esc(base["n"])}」として'
            f'1点{fee_str(base["fee"])}に統一されています。{note_txt}'
            f'品目ごとに料金を調べる手間が少ないわかりやすい制度です。{exc_txt}'
            f'なお、この記事の「収録{len(priced_items(items))}品目」は当サイトに登録している料金区分の数で、市が受け付ける品目の総数ではありません。'
            f'ご自身の品物がどちらに当たるか迷う場合は、申込み時に品目と寸法を伝えて確認しておくと、'
            f'処理券の買い間違いを防げます。</p>')


def fee_distribution_para(items, name, w=None):
    fees = [int(it['fee']) for it in priced_items(items)]
    if len(fees) < 5 or min(fees) == max(fees):
        return ''
    from collections import Counter
    mode_fee, mode_cnt = Counter(fees).most_common(1)[0]
    when = f'（{asof(w)}）' if w else ''
    return (f'<p>収録データ{when}を集計すると、{esc(name)}の粗大ごみは収録{len(fees)}品目のうち'
            f'最も多い手数料が{mode_fee:,}円（{mode_cnt}品目）で、最低{min(fees):,}円〜最高{max(fees):,}円の範囲に分布しています。'
            f'手数料は品物のサイズや種類で決まるため、申込み前に品目ごとの金額を確認しておくと、処理券の買い間違いを防げます。</p>')


def fee_range(items):
    fees = [int(it['fee']) for it in priced_items(items)]
    return (min(fees), max(fees)) if fees else (None, None)


def top_fee_items(items, pops, limit=10):
    """高額品目トップN（早見表と重複しないもの）"""
    used = {p.get('n') for p in pops}
    cand = [it for it in items
            if collectible(it) and not is_special_free(it) and it.get('n') not in used]
    cand.sort(key=lambda x: (-x['fee'], x.get('n', '')))
    return cand[:limit]


def _list_items(its):
    return '、'.join(f'「{esc(it["n"])}」{fee_str(it["fee"])}' for it in its)


def item_detail_paras(w):
    """ソファ・ベッド・布団の区別実データ解説（品目記事への内部リンクつき）
    2026-09-14: 品目の誤選択・固定文の断定（「1人掛けか2人掛け以上か」「2品目として申し込むのが基本」）を修正"""
    items = w['items']
    name = w['name']
    cid = w['id']
    when = asof(w)
    paras = []
    sofas = find_items(items, 'ソファ', 3)
    for it in find_items(items, '応接', 3):  # 「応接用いす」名義でソファを登録している都市（相模原・神戸など）
        if it not in sofas and len(sofas) < 3:
            sofas.append(it)
    if sofas:
        paras.append(
            f'<h3>ソファを捨てる場合</h3>'
            f'<p>{esc(name)}では{_list_items(sofas)}です（{when}）。'
            f'料金の区分（人数・最長辺の寸法・材質など）は自治体ごとに異なるため、申込み前に寸法を測り、どの区分に当たるかを確認しておきましょう。'
            f'スプリング入りや電動リクライニングは扱いが変わる場合があります。全国の比較は<a href="sofa-disposal-guide.html">ソファの処分費用ガイド</a>で詳しく解説しています。</p>')
    beds = find_items(items, 'ベッド', 2)
    mats = find_items(items, 'マットレス', 2) or find_items(items, 'ベッドマット', 2) or find_items(items, 'マット', 2)
    bedset = next((it for it in items if 'セット' in it.get('n', '') and 'ベッド' in it.get('n', '') and collectible(it)), None)
    if beds:
        mat_txt = f'マットレスは{_list_items(mats)}です。' if mats else 'マットレスは別品目・別料金になる場合があります。'
        set_txt = f'「{esc(bedset["n"])}」{fee_str(bedset["fee"])}のようにセット料金の区分もあるため、該当する場合はそちらで申し込みます。' if bedset else ''
        paras.append(
            f'<h3>ベッドを捨てる場合</h3>'
            f'<p>{esc(name)}では{_list_items(beds)}です（{when}）。{mat_txt}'
            f'ベッド本体とマットレスが別品目になっている場合は、それぞれ申し込みます。{set_txt}'
            f'脚付きマットレスやソファーベッドなどの一体型は1品目として扱われることが多いため、申込み時に確認してください。'
            f'詳しくは<a href="bed-mattress-disposal-guide.html">ベッド・マットレスの捨て方完全ガイド</a>をご覧ください。</p>')
    futons = find_items(items, '布団', 2) or find_items(items, 'ふとん', 2)
    if futons:
        paras.append(
            f'<h3>布団を捨てる場合</h3>'
            f'<p>{esc(name)}では{_list_items(futons)}です（{when}）。'
            f'枚数の数え方（1枚単位・2枚まで等）や、毛布・座布団・こたつ布団の区分は自治体で異なるため、申込み時に枚数と種類を伝えて確認しましょう。'
            f'紐でしばってまとめるなど出し方の指定がある場合は、上記の「出し方（収集）」に従ってください。</p>')
    # ソファ・ベッド・布団が収録にない都市は、高額品目の解説で補完
    if len(paras) < 2:
        used_kw = {'ソファ', 'ベッド', '布団'}
        cand = sorted(
            [it for it in priced_items(items) if it['fee'] > 0
             and not any(k in it.get('n', '') for k in used_kw)],
            key=lambda x: -x['fee'])
        for it in cand[:3 - len(paras)]:
            note_txt = f'出し方の条件は「{esc(it["note"])}」です。' if it.get('note') else ''
            paras.append(
                f'<h3>{esc(it["n"])}を捨てる場合</h3>'
                f'<p>{esc(name)}では「{esc(it["n"])}」が{fee_str(it["fee"])}です（{when}）。{note_txt}大型で重さのある品物は搬出時のけがを防ぐため2人以上での運び出しをおすすめします。'
                f'サイズによって区分が変わる場合があるため、申込み時に寸法を伝えて金額を確定させておくと安心です。</p>')
    if paras:
        paras.append(f'<p>ここに挙げた以外の品目は<a href="/city/{cid}.html">{esc(name)}の品目別料金一覧</a>で確認できます。</p>')
    return ''.join(paras)


PRACTICAL_TIPS = '''
<h3>収集日に出し忘れた・回収されなかった場合</h3>
<p>出し忘れた場合は、受付センターに連絡して収集日を取り直すのが基本です。処理券は購入済みのものをそのまま使える場合が多いので、捨てずに保管しておきましょう。品物に「回収できません」の案内が貼られていた場合は、記載された理由（サイズ超過・対象外品目・券の金額不足など）を確認してから再申込みします。</p>
<h3>マンション・集合住宅の場合</h3>
<p>集合住宅では、建物指定の粗大ごみ置き場がある場合と、通常どおり自宅前・集積所に出す場合があります。管理規約や掲示板の案内を確認し、わからない場合は管理会社に問い合わせてから申し込むとスムーズです。</p>
<h3>引越しシーズンは早めの申込みを</h3>
<p>3〜4月や年末は申込みが集中し、収集日が通常より先になることがあります。退去日が決まっている場合は、遅くとも1か月前には品目の洗い出しと申込みを済ませておくと安心です。</p>'''


def net_status(r):
    """ネット受付の有無と24時間かどうかを、受付手段の文言から判定する
    （internetHours が空でないだけで24時間と断定しない。「電話・FAXのみ受付」等は否定扱い）"""
    ih = r.get('internetHours') or ''
    am = r.get('applicationMethod') or ''
    negative = bool(re.search(r'のみ受付|のみ|不可|なし|受け付けていません', ih))
    src = ih + ' ' + am
    has_net = (not negative) and bool(re.search(r'インターネット|ネット|Web|WEB|オンライン|電子申請|チャット|LINE', src))
    h24 = has_net and ('24時間' in src)
    return has_net, h24


def carry_status(r):
    sc = r.get('selfCarryIn') or ''
    if not sc:
        return None, sc
    no_carry = bool(re.search(r'制度なし|できません|不可|廃止|収集のみ', sc)) and not re.search(r'持込可|持ち込み可|搬入可|持込み可|持込先', sc)
    return (not no_carry), sc


def build_faq(w, fmin, fmax):
    name, r, items = w['name'], w['rules'], w['items']
    when = asof(w)
    qa = []
    sofa = find_item(items, 'ソファ') or find_item(items, '応接')
    futon = find_item(items, '布団') or find_item(items, 'ふとん')
    ex = ''
    if sofa:
        ex += f'例えば{sofa["n"]}は{fee_str(sofa["fee"])}'
    if futon:
        ex += ('、' if ex else '例えば') + f'{futon["n"]}は{fee_str(futon["fee"])}'
    if ex:
        ex += 'です。'
    free_city = fmin == 0 and fmax == 0
    if free_city:
        qa.append((f'{name}の粗大ごみはいくらかかりますか？',
                   f'収録データ（{when}）では、対象品目の戸別収集は無料（手数料なし）です。ただし事前の申込みは必要で、対象外の品目や自己搬入の料金は別途かかる場合があります。品目ごとの扱いは粗大ごみナビの検索アプリで確認できます。'))
    elif fmin is not None:
        qa.append((f'{name}の粗大ごみはいくらかかりますか？',
                   f'品目により{fmin:,}円〜{fmax:,}円です（{when}の収録データ）。{ex}品目ごとの正確な料金は粗大ごみナビの検索アプリで確認できます。'))
    if r.get('applicationMethod'):
        qa.append((f'{name}の粗大ごみはどうやって申し込みますか？', r['applicationMethod']))
    if r.get('paymentMethod'):
        if free_city:
            qa.append((f'{name}の粗大ごみに手数料はかかりますか？', r['paymentMethod']))
        else:
            qa.append((f'{name}の粗大ごみの手数料はどう支払いますか？', r['paymentMethod']))
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
    priced = priced_items(items)
    n_items = len(priced)
    n_unc = sum(1 for it in items if has_fee(it) and is_uncollectible(it))
    fmin, fmax = fee_range(items)
    free_city = fmin == 0 and fmax == 0
    when = asof(w)
    pops = popular_items(items)
    faq = build_faq(w, fmin, fmax)
    has_net, h24 = net_status(r)
    can_carry, carry_txt = carry_status(r)
    pm = r.get('paymentMethod') or ''
    cashless = bool(re.search(r'オンライン決済|キャッシュレス|クレジット|決済', pm))

    title = f'{name}の粗大ごみ完全ガイド｜申込み方法・料金・持ち込み【{EDITION}】'
    if free_city:
        range_txt = '無料（手数料なし）'
    else:
        range_txt = f'{fmin:,}円〜{fmax:,}円' if fmin is not None else ''
    carry_word = '持ち込み処分・' if r.get('selfCarryIn') else ''
    pay_word = '手数料の支払い方法・' if free_city else '処理券の買い方・'
    desc = (f'{name}の粗大ごみの申込み方法・{pay_word}{carry_word}収集ルールを1ページに整理。'
            f'品目別料金は{range_txt}（収録{n_items}品目・{when}）。よく出る家具・家電の手数料早見表つきです。')

    # ---- JSON-LD ----
    ld_article = {
        "@context": "https://schema.org", "@type": "Article",
        "headline": title, "datePublished": DATE_PUB, "dateModified": DATE_MOD,
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
        ('インターネット受付', r.get('internetHours')),
        ('支払い方法', r.get('paymentMethod')),
        ('出し方（収集）', r.get('collectionMethod')),
    ]:
        if val:
            info_rows.append(f'<tr><th>{esc(label)}</th><td>{esc(val)}</td></tr>')
    info_table = f'<div class="table-wrap"><table>{"".join(info_rows)}</table></div>' if info_rows else ''

    # ---- よく出る品目テーブル（備考欄つき） ----
    pop_table = fee_table(pops)

    # ---- 高額品目テーブル（無料都市では意味がないため省略） ----
    tops = [] if free_city else top_fee_items(items, pops)
    top_table = ''
    if tops:
        top_table = f'''<h3>手数料が高めの大型品目</h3>
<p>搬出や解体の判断にも関わるため、大型品は事前に料金を確認しておきましょう（{when}）。</p>
{fee_table(tops)}'''

    # ---- 品目別詳細（ソファ・ベッド・布団） ----
    detail_html = item_detail_paras(w)
    if detail_html:
        detail_html = f'<h2 id="details">{esc(name)}の品目別の捨て方ポイント</h2>' + detail_html

    # ---- 持ち込み ----
    carry_html = ''
    if r.get('selfCarryIn'):
        if can_carry:
            same_txt = f'{esc(name)}では収集と同額のため、費用面の差はありません。' if '同額' in carry_txt else ''
            pre_txt = ('受け入れ日時が限られるため、上記の受付時間を確認してから運びましょう。' if '予約不要' in carry_txt
                       else '事前予約や本人確認書類が必要な場合が多く、受け入れ日時も限られます。')
            tip = (f'<p class="note-box"><strong>持ち込みのポイント：</strong>{pre_txt}'
                   f'料金は自治体により「収集と同額」「収集の半額」「重量制」などさまざまです。{same_txt}'
                   f'運搬手段と品目数を踏まえて、収集と持ち込みのどちらが合うか選びましょう。</p>')
        else:
            tip = f'<p>{esc(name)}では通常の粗大ごみは戸別収集で出します。持ち込みを前提にした準備は不要です。</p>'
        carry_html = f'''<h2 id="carry">{esc(name)}で粗大ごみの持ち込み処分はできますか？</h2>
<p>{esc(carry_txt)}</p>
{tip}'''

    # ---- 収集できないもの・別の手続きが必要なもの ----
    unc_html = ''
    unc_parts = []
    if w['unc']:
        rows = []
        for u in w['unc']:
            if isinstance(u, dict):
                reason = str(u.get('reason', ''))
                for old, new in REASON_FIX:
                    reason = reason.replace(old, new)
                rows.append(f'<tr><td>{esc(u.get("n",""))}</td><td>{esc(reason)}</td></tr>')
            else:
                rows.append(f'<tr><td colspan="2">{esc(u)}</td></tr>')
        unc_parts.append(f'<div class="table-wrap"><table><tr><th>品目</th><th>理由・処分先</th></tr>{"".join(rows)}</table></div>')
    if r.get('nonCollectibleNote'):
        unc_parts.append(f'<p>{esc(r["nonCollectibleNote"])}</p>')
    if unc_parts:
        unc_html = f'''<h2 id="cannot">{esc(name)}で収集できないもの・別の手続きが必要なもの</h2>
<p>通常の粗大ごみとして出せないものと、家電リサイクル法の対象品目のように別の手続き・別料金で引き取られるものをまとめました。</p>
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

    ver_note = f'※ 掲載内容は{when}の収録データに基づきます。' if w['ver'] else ''
    if h24:
        net_txt = 'インターネット受付は24時間利用できるため、日中に電話ができない方はネット申込みが便利です。'
    elif has_net:
        net_txt = 'インターネット受付もあります。受付時間は上記の基本情報をご確認ください。'
    else:
        net_txt = '電話など受付時間内の申込みが必要なため、余裕を持って手続きを進めましょう。'
    if free_city:
        prep_txt = '申込みの前に品目ごとの対象・出し方を確認しておくと手続きがスムーズです。'
        summary_fee = f'手数料はかかりません（収録{n_items}品目・{when}）'
        step3_title = '手数料の支払いは不要です（無料収集）'
        step3_desc = pm or '手数料はかかりません。申込み時に案内された方法で出します。'
    else:
        prep_txt = '申込みの前に品目ごとの手数料を確認しておくと、処理券の購入が一度で済みます。' if not cashless else '申込みの前に品目ごとの手数料を確認しておくと、支払いがスムーズです。'
        summary_fee = f'手数料は品目により{range_txt}（収録{n_items}品目・{when}）'
        step3_title = '手数料を支払う（処理券の購入またはオンライン決済）' if cashless else '処理券（シール）を購入して貼る'
        step3_desc = pm or '指定の販売店で処理券を購入し、品物に貼付します'
    unc_note = f'このほか収集不可として登録されている品目が{n_unc}件あります（下記「収集できないもの」参照）。' if n_unc else ''

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
    <span>📅 {DATE_JP}公開／{DATE_MOD_JP}更新</span>
    <span>✍️ テラデザイン編集部</span>
    <span>📖 読了8分</span>
  </div>
  <div class="article-summary">
    {esc(name)}の粗大ごみの申込み先・{pay_word}{carry_word}収集できないものを、この1ページに整理しました。よく出る品目の手数料早見表つきです。
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
      <p>{esc(name)}の粗大ごみは事前申込み制です。{summary_fee}。申込みから収集まで日数がかかるため、処分が決まったら早めに手続きしましょう。</p>
    </div>

    {info_table}

    <p>{net_txt}{prep_txt}{esc(name)}の収録{n_items}品目の料金は<a href="/city/{cid}.html">{esc(name)}の品目別料金一覧</a>でも確認できます。{unc_note}</p>

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
          <div class="step-title">{esc(step3_title)}</div>
          <p class="step-desc">{esc(step3_desc)}</p>
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
      <p>収録{n_items}品目の手数料を無料で確認。複数品目の合計金額もその場で計算できます。</p>
      <a href="/?city={cid}" class="btn-cta">♻️ {esc(name)}の料金を無料で調べる</a>
    </div>

    <h2 id="fees">{esc(name)}でよく出る品目の手数料早見表</h2>

    <p>引越しや買い替えでよく処分される品目の手数料をまとめました（{when}の収録データ）。備考欄がある品目は、切断・解体・数量などの条件付きです。</p>

    {pop_table}

    <p class="note-box">{ver_note}同じ品目でもサイズにより手数料が変わる場合があります。掲載のない品目や正確な区分は<a href="/?city={cid}">検索アプリ</a>または<a href="/city/{cid}.html">{esc(name)}の品目別料金一覧</a>でご確認ください。</p>

    {fee_distribution_para(items, name, w)}

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
