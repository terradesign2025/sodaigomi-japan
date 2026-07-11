# -*- coding: utf-8 -*-
import json, os, sys

# force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

uncollectible = [
    {"n":"エアコン","k":["特"],"reason":"家電リサイクル法対象","tags":["エアコン"],"en":"Air Conditioner"},
    {"n":"テレビ","k":["特"],"reason":"家電リサイクル法対象","tags":["テレビ"],"en":"Television"},
    {"n":"冷蔵庫・冷凍庫","k":["特"],"reason":"家電リサイクル法対象","tags":["冷蔵庫"],"en":"Refrigerator"},
    {"n":"洗濯機・衣類乾燥機","k":["特"],"reason":"家電リサイクル法対象","tags":["洗濯機"],"en":"Washing Machine"},
    {"n":"パソコン・ノートPC","k":["特"],"reason":"PCリサイクル法対象","tags":["パソコン"],"en":"Computer"},
    {"n":"バイク・原付","k":["特"],"reason":"二輪車リサイクル対象","tags":["バイク"],"en":"Motorcycle"},
    {"n":"タイヤ（車用）","k":["特"],"reason":"産廃扱い","tags":["タイヤ"],"en":"Car Tires"},
    {"n":"消火器","k":["特"],"reason":"専門業者処分","tags":["消火器"],"en":"Fire Extinguisher"},
    {"n":"ピアノ（アコースティック）","k":["特"],"reason":"重量超過","tags":["ピアノ"],"en":"Acoustic Piano"}
]

def std_items():
    return [
        {"n":"タンス（木製・小）","k":["た"],"fee":500,"m":"収集/持込","tags":["タンス","家具"],"en":"Small Wooden Chest"},
        {"n":"タンス（木製・大）","k":["た"],"fee":1000,"m":"収集/持込","tags":["タンス","家具"],"en":"Large Wooden Chest"},
        {"n":"食器棚","k":["し"],"fee":1000,"m":"収集/持込","tags":["食器棚","家具"],"en":"Cupboard"},
        {"n":"本棚","k":["ほ"],"fee":500,"m":"収集/持込","tags":["本棚","家具"],"en":"Bookshelf"},
        {"n":"ソファー（1人掛け）","k":["そ"],"fee":500,"m":"収集/持込","tags":["ソファー","家具"],"en":"Single Sofa"},
        {"n":"ソファー（2〜3人掛け）","k":["そ"],"fee":1000,"m":"収集/持込","tags":["ソファー","家具"],"en":"2-3 Seat Sofa"},
        {"n":"ベッド（シングル）フレームのみ","k":["べ"],"fee":500,"m":"収集/持込","tags":["ベッド","家具"],"en":"Single Bed Frame"},
        {"n":"ベッド（ダブル）フレームのみ","k":["べ"],"fee":1000,"m":"収集/持込","tags":["ベッド","家具"],"en":"Double Bed Frame"},
        {"n":"マットレス（スプリング入り）","k":["ま"],"fee":1000,"m":"収集/持込","tags":["マットレス","寝具"],"en":"Spring Mattress"},
        {"n":"マットレス（スプリングなし）","k":["ま"],"fee":500,"m":"収集/持込","tags":["マットレス","寝具"],"en":"Non-Spring Mattress"},
        {"n":"布団","k":["ふ"],"fee":200,"m":"収集/持込","tags":["布団","寝具"],"en":"Futon"},
        {"n":"こたつ","k":["こ"],"fee":300,"m":"収集/持込","tags":["こたつ","家電"],"en":"Kotatsu"},
        {"n":"テーブル（小）","k":["て"],"fee":300,"m":"収集/持込","tags":["テーブル","家具"],"en":"Small Table"},
        {"n":"テーブル（大）","k":["て"],"fee":500,"m":"収集/持込","tags":["テーブル","家具"],"en":"Large Table"},
        {"n":"椅子","k":["い"],"fee":200,"m":"収集/持込","tags":["椅子","家具"],"en":"Chair"},
        {"n":"自転車","k":["じ"],"fee":500,"m":"収集/持込","tags":["自転車"],"en":"Bicycle"},
        {"n":"電子レンジ","k":["て"],"fee":300,"m":"収集/持込","tags":["電子レンジ","家電"],"en":"Microwave Oven"},
        {"n":"ガスコンロ","k":["か"],"fee":300,"m":"収集/持込","tags":["ガスコンロ","調理家電"],"en":"Gas Stove"},
        {"n":"扇風機","k":["せ"],"fee":200,"m":"収集/持込","tags":["扇風機","家電"],"en":"Electric Fan"},
        {"n":"掃除機","k":["そ"],"fee":200,"m":"収集/持込","tags":["掃除機","家電"],"en":"Vacuum Cleaner"},
        {"n":"石油ファンヒーター","k":["せ"],"fee":300,"m":"収集/持込","tags":["ヒーター","暖房"],"en":"Oil Fan Heater"},
        {"n":"石油ストーブ","k":["せ"],"fee":300,"m":"収集/持込","tags":["ストーブ","暖房"],"en":"Kerosene Stove"},
        {"n":"カーペット・じゅうたん","k":["か"],"fee":300,"m":"収集/持込","tags":["カーペット"],"en":"Carpet/Rug"},
        {"n":"物干し台","k":["も"],"fee":300,"m":"収集/持込","tags":["物干し台","屋外用品"],"en":"Clothes Drying Stand"},
        {"n":"物干し竿","k":["も"],"fee":200,"m":"収集/持込","tags":["物干し竿","屋外用品"],"en":"Clothes Drying Pole"},
        {"n":"ベビーカー","k":["べ"],"fee":300,"m":"収集/持込","tags":["ベビーカー","育児用品"],"en":"Baby Stroller"},
        {"n":"チャイルドシート","k":["ち"],"fee":300,"m":"収集/持込","tags":["チャイルドシート","育児用品"],"en":"Child Seat"},
        {"n":"三輪車","k":["さ"],"fee":200,"m":"収集/持込","tags":["三輪車","玩具"],"en":"Tricycle"},
        {"n":"ミシン","k":["み"],"fee":300,"m":"収集/持込","tags":["ミシン","家電"],"en":"Sewing Machine"},
        {"n":"ガス給湯器","k":["か"],"fee":1000,"m":"持込","tags":["給湯器"],"en":"Gas Water Heater"},
        {"n":"電気温水器","k":["で"],"fee":1000,"m":"持込","tags":["電気温水器","給湯"],"en":"Electric Water Heater"},
        {"n":"畳","k":["た"],"fee":300,"m":"収集/持込","tags":["畳"],"en":"Tatami Mat"},
        {"n":"鏡台・ドレッサー","k":["か"],"fee":500,"m":"収集/持込","tags":["鏡台","家具"],"en":"Dressing Table"},
        {"n":"スチールラック","k":["す"],"fee":300,"m":"収集/持込","tags":["スチールラック","家具"],"en":"Steel Rack"},
        {"n":"プリンター","k":["ふ"],"fee":300,"m":"収集/持込","tags":["プリンター","OA機器"],"en":"Printer"},
        {"n":"テレビ台","k":["て"],"fee":300,"m":"収集/持込","tags":["テレビ台","家具"],"en":"TV Stand"},
        {"n":"サイドボード","k":["さ"],"fee":1000,"m":"収集/持込","tags":["サイドボード","家具"],"en":"Sideboard"},
        {"n":"草刈り機","k":["く"],"fee":500,"m":"収集/持込","tags":["草刈り機","農機具"],"en":"Lawn Mower"},
        {"n":"物置（スチール製）","k":["も"],"fee":2000,"m":"持込","tags":["物置","屋外用品"],"en":"Steel Storage Shed"},
        {"n":"灯油タンク","k":["と"],"fee":200,"m":"収集/持込","tags":["灯油タンク"],"en":"Kerosene Tank"},
        {"n":"スノーダンプ・雪かき","k":["す"],"fee":200,"m":"収集/持込","tags":["雪かき","除雪"],"en":"Snow Shovel/Snow Pusher"},
        {"n":"そり（雪用）","k":["そ"],"fee":200,"m":"収集/持込","tags":["そり","雪"],"en":"Snow Sled"},
        {"n":"スキー板・スノーボード","k":["す"],"fee":200,"m":"収集/持込","tags":["スキー","スノーボード"],"en":"Skis/Snowboard"}
    ]

cities = [
    {"id":"15206","name":"新発田市","pref":"新潟県","rank":"C","dir":"15_niigata","tel":"0254-22-9172","url":"https://www.city.shibata.lg.jp/"},
    {"id":"15210","name":"十日町市","pref":"新潟県","rank":"C","dir":"15_niigata","tel":"025-757-3704","url":"https://www.city.tokamachi.niigata.jp/"},
    {"id":"15211","name":"見附市","pref":"新潟県","rank":"C","dir":"15_niigata","tel":"0258-62-1700","url":"https://www.city.mitsuke.niigata.jp/"},
    {"id":"15212","name":"村上市","pref":"新潟県","rank":"C","dir":"15_niigata","tel":"0254-53-2111","url":"https://www.city.murakami.niigata.jp/","note2":"要確認"},
    {"id":"15213","name":"燕市","pref":"新潟県","rank":"C","dir":"15_niigata","tel":"0256-62-5537","url":"https://www.city.tsubame.niigata.jp/life/8/1/21338.html","method":"電話申込後粗大ごみシール購入・貼付。環境センター土曜9:00〜12:00受付あり"},
    {"id":"15216","name":"糸魚川市","pref":"新潟県","rank":"C","dir":"15_niigata","tel":"025-552-1511","url":"https://www.city.itoigawa.lg.jp/"},
    {"id":"15222","name":"上越市","pref":"新潟県","rank":"B","dir":"15_niigata","tel":"025-526-5111","url":"https://www.city.joetsu.niigata.jp/"},
    {"id":"15225","name":"魚沼市","pref":"新潟県","rank":"C","dir":"15_niigata","tel":"025-792-9900","url":"https://www.city.uonuma.lg.jp/page/2050.html","method":"電話(025-792-9900)・FAX・電子申請・メール(haikibutsu@city.uonuma.lg.jp)で前日午後5時まで申込。大物・中物・小物・6号袋の区分あり"},
    {"id":"15226","name":"南魚沼市","pref":"新潟県","rank":"C","dir":"15_niigata","tel":"025-773-6810","url":"https://www.city.minamiuonuma.lg.jp/","note2":"要確認"},
    {"id":"20203","name":"上田市","pref":"長野県","rank":"C","dir":"20_nagano","tel":"0268-22-0666","url":"https://www.city.ueda.nagano.jp/soshiki/haiki/2512.html","method":"清掃センター持込のみ（戸別収集なし）。上田クリーンセンター8:30〜11:45・13:00〜16:00、丸子クリーンセンター9:00〜11:30・13:00〜16:00（土日祝休）","note":"重量制：20kg以下400円、超過分10kgごと200円加算"},
    {"id":"20204","name":"岡谷市","pref":"長野県","rank":"C","dir":"20_nagano","tel":"0266-23-4811","url":"https://www.city.okaya.lg.jp/"},
    {"id":"20205","name":"飯田市","pref":"長野県","rank":"C","dir":"20_nagano","tel":"0265-22-4511","url":"https://www.city.iida.nagano.jp/","note2":"要確認"},
    {"id":"20206","name":"諏訪市","pref":"長野県","rank":"C","dir":"20_nagano","tel":"0266-52-4141","url":"https://www.city.suwa.lg.jp/"},
    {"id":"20209","name":"伊那市","pref":"長野県","rank":"C","dir":"20_nagano","tel":"0265-72-2111","url":"https://www.city.ina.nagano.jp/","note2":"要確認"},
    {"id":"20211","name":"中野市","pref":"長野県","rank":"C","dir":"20_nagano","tel":"0269-22-2111","url":"https://www.city.nakano.nagano.jp/","method":"不燃性粗大ごみは年1回指定会場で回収（事前申込不要・受付9:00〜11:30）。可燃性粗大ごみは随時受付。品目：自転車・ストーブ・ファンヒーター・電子レンジ等"},
    {"id":"20214","name":"茅野市","pref":"長野県","rank":"C","dir":"20_nagano","tel":"0266-72-2101","url":"https://www.city.chino.lg.jp/"},
    {"id":"20215","name":"塩尻市","pref":"長野県","rank":"C","dir":"20_nagano","tel":"0263-54-3000","url":"https://www.city.shiojiri.nagano.jp/","note2":"要確認"},
    {"id":"20217","name":"佐久市","pref":"長野県","rank":"C","dir":"20_nagano","tel":"0267-62-2111","url":"https://www.city.saku.nagano.jp/"},
    {"id":"20220","name":"安曇野市","pref":"長野県","rank":"C","dir":"20_nagano","tel":"0263-71-2000","url":"https://www.city.azumino.nagano.jp/","note2":"要確認"},
    {"id":"19201","name":"甲府市","pref":"山梨県","rank":"B","dir":"19_yamanashi","tel":"055-237-5300","url":"https://www.city.kofu.yamanashi.jp/kurashi/gomi/sodaigomi/"},
    {"id":"19202","name":"富士吉田市","pref":"山梨県","rank":"C","dir":"19_yamanashi","tel":"0555-22-1111","url":"https://www.city.fujiyoshida.yamanashi.jp/","note2":"要確認"},
    {"id":"19204","name":"都留市","pref":"山梨県","rank":"C","dir":"19_yamanashi","tel":"0554-43-1111","url":"https://www.city.tsuru.yamanashi.jp/","note2":"要確認"},
    {"id":"19205","name":"山梨市","pref":"山梨県","rank":"C","dir":"19_yamanashi","tel":"0553-22-1111","url":"https://www.city.yamanashi.yamanashi.jp/","note2":"要確認"},
    {"id":"19208","name":"南アルプス市","pref":"山梨県","rank":"C","dir":"19_yamanashi","tel":"055-282-6097","url":"https://www.city.minami-alps.yamanashi.jp/","note":"有料別途品目あり：タイヤ300円・マッサージチェア1000円・刈払機500円・大型楽器1500円・温水器3000円・金属製浴槽1000円・スプリングマットレス/ソファー3000円"},
    {"id":"19209","name":"北杜市","pref":"山梨県","rank":"C","dir":"19_yamanashi","tel":"0551-42-1111","url":"https://www.city.hokuto.yamanashi.jp/","note2":"要確認"},
    {"id":"19210","name":"甲斐市","pref":"山梨県","rank":"C","dir":"19_yamanashi","tel":"055-278-1706","url":"https://www.city.kai.yamanashi.jp/","method":"地区ごとに収集日・時間が異なる（竜王地区・敷島地区・双葉地区）。環境森林課：055-278-1706"},
    {"id":"19211","name":"笛吹市","pref":"山梨県","rank":"C","dir":"19_yamanashi","tel":"055-262-4111","url":"https://www.city.fuefuki.yamanashi.jp/","note2":"要確認"},
    {"id":"19213","name":"甲州市","pref":"山梨県","rank":"C","dir":"19_yamanashi","tel":"0553-32-2111","url":"https://www.city.koshu.yamanashi.jp/","note2":"要確認"},
    {"id":"19214","name":"中央市","pref":"山梨県","rank":"C","dir":"19_yamanashi","tel":"055-274-1111","url":"https://www.city.chuo.yamanashi.jp/","note2":"要確認"},
    {"id":"16202","name":"高岡市","pref":"富山県","rank":"C","dir":"16_toyama","tel":"0766-20-1261","url":"https://www.city.takaoka.toyama.jp/"},
    {"id":"16204","name":"魚津市","pref":"富山県","rank":"C","dir":"16_toyama","tel":"0765-23-1025","url":"https://www.city.uozu.toyama.jp/","note2":"要確認"},
    {"id":"16207","name":"黒部市","pref":"富山県","rank":"C","dir":"16_toyama","tel":"0765-54-2111","url":"https://www.city.kurobe.toyama.jp/","note2":"要確認"},
    {"id":"16208","name":"砺波市","pref":"富山県","rank":"C","dir":"16_toyama","tel":"0763-33-1372","url":"https://www.city.tonami.toyama.jp/"},
    {"id":"16210","name":"南砺市","pref":"富山県","rank":"C","dir":"16_toyama","tel":"0763-23-2003","url":"https://www.city.nanto.toyama.jp/"},
    {"id":"16211","name":"射水市","pref":"富山県","rank":"C","dir":"16_toyama","tel":"0766-51-6624","url":"https://www.city.imizu.toyama.jp/"},
    {"id":"17203","name":"小松市","pref":"石川県","rank":"C","dir":"17_ishikawa","tel":"0761-20-0404","url":"https://www.city.komatsu.lg.jp/soshiki/1021/gomi_risaikuru/4/2043.html","method":"電話予約必須（エコロジーパーク：0761-41-1600）。月〜金8:30〜17:00受付。土日祝は収集なし","note":"150cm未満500円・150cm以上1000円。スプリング入り品目+500円加算"},
    {"id":"17206","name":"加賀市","pref":"石川県","rank":"C","dir":"17_ishikawa","tel":"0761-72-7899","url":"https://www.city.kaga.ishikawa.jp/","note2":"要確認"},
    {"id":"17211","name":"白山市","pref":"石川県","rank":"C","dir":"17_ishikawa","tel":"076-274-9524","url":"https://www.city.hakusan.ishikawa.jp/","note2":"要確認"},
    {"id":"17212","name":"能美市","pref":"石川県","rank":"C","dir":"17_ishikawa","tel":"0761-58-2217","url":"https://sodai-sys.jp/nomi/users/","method":"インターネット申込(https://sodai-sys.jp/nomi/users/)または電話・来庁。月〜金8:30〜17:15受付","note":"大型ごみ1000円（ベッド・除湿器等）・中型ごみ500円（自転車・カラーボックス等）。戸別収集日：根上地区第1・3金、寺井地区第1・3木、辰口地区第1・3水"},
    {"id":"17213","name":"野々市市","pref":"石川県","rank":"C","dir":"17_ishikawa","tel":"076-227-6059","url":"https://www.city.nonoichi.lg.jp/","note2":"要確認"},
    {"id":"18202","name":"敦賀市","pref":"福井県","rank":"C","dir":"18_fukui","tel":"0770-21-1111","url":"https://www.city.tsuruga.lg.jp/","note2":"要確認"},
    {"id":"18205","name":"大野市","pref":"福井県","rank":"C","dir":"18_fukui","tel":"0779-64-4828","url":"https://www.city.ono.fukui.jp/","method":"持込のみ（ビュークリーンおくえつへ）または許可業者への依頼。環境・水循環課：0779-64-4828","note":"ビュークリーンおくえつ（0779-66-6690）へ直接持込可"},
    {"id":"18207","name":"鯖江市","pref":"福井県","rank":"C","dir":"18_fukui","tel":"0778-53-2228","url":"https://www.city.sabae.fukui.jp/","method":"許可を受けた専門業者（9社）へ依頼（市による個別戸別収集なし）。環境政策課：0778-53-2228","note":"料金は業者により異なる。専門業者への直接依頼"},
    {"id":"18209","name":"越前市","pref":"福井県","rank":"C","dir":"18_fukui","tel":"0778-22-5342","url":"https://www.city.echizen.lg.jp/office/kankyounourin/051/gomirecycle/sodai.html","method":"町内収集（年1回・区長に問合）または清掃センター持込（平日8:30〜16:30）。環境政策課：0778-22-5342","note":"重量制：10kgあたり60円（別途処理料あり）"},
    {"id":"18210","name":"坂井市","pref":"福井県","rank":"C","dir":"18_fukui","tel":"0776-50-3011","url":"https://www.city.sakai.fukui.jp/","note2":"要確認"}
]

base_dir = "C:/Users/Terradesign/MyApps/sodaigomi-app/cities"

for c in cities:
    cid = c["id"]
    cdir = c["dir"]
    items = std_items()
    method = c.get("method", "事前に電話申込後、粗大ごみ処理券を購入して品目に貼付。収集日当日に玄関先・指定場所へ出す")
    if cid == "18207":
        carry = "許可業者への依頼（市クリーンセンターへの一般持込は不可）"
    elif cid == "18205":
        carry = "可（ビュークリーンおくえつ：0779-66-6690）"
    elif cid == "20203":
        carry = "可（上田クリーンセンター：0268-22-0666、丸子クリーンセンター）"
    else:
        carry = "可（各市清掃センター・環境センター）"

    note2 = c.get("note2", "")
    definition = "日常生活から排出される大型ごみ（通常のごみ袋に入らないもの）"
    if note2 == "要確認":
        definition = "日常生活から排出される大型ごみ（通常のごみ袋に入らないもの）※料金等は公式サイトで要確認"

    rules = {
        "definition": definition,
        "contact": c["tel"] + "（" + c["name"] + "環境担当課）",
        "hours": "月曜日〜金曜日 午前8時30分〜午後5時15分（祝日・年末年始除く）",
        "websiteUrl": c["url"],
        "applicationMethod": method,
        "paymentMethod": "粗大ごみ処理券（スーパー・コンビニ等で購入）または窓口払い",
        "collectionMethod": "戸別収集または清掃センター持込（市によって異なる）",
        "selfCarryIn": carry,
        "nonCollectibleNote": "家電4品目（エアコン・テレビ・冷蔵庫・洗濯機）・パソコン・バイク・タイヤ・消火器・ピアノは収集不可"
    }
    if c.get("note"):
        rules["note"] = c["note"]

    data = {
        "city": {"id": cid, "name": c["name"], "prefecture": c["pref"], "rank": c["rank"], "dataVersion": "2026-05", "rules": rules},
        "items": items,
        "uncollectible": uncollectible
    }

    filepath = os.path.join(base_dir, cdir, cid + "_v2.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"OK: {cid} {c['name']}")

print("Done!")