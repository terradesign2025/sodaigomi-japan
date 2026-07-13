import glob, re

CTA = '''
<!-- 相互リンク・バナー掲載のお願い -->
<div style="background:#F0FBF4;border:1px solid #34C759;border-radius:12px;padding:14px 16px;margin:20px 0;font-size:12px;color:#1C1C1E;line-height:1.6;">
  🤝 <strong>サイト運営者の方へ：</strong>リサイクルショップ・買取業者・出張買取業者様やブログ運営者様は、この記事や当サイトを紹介する無料の<a href="../partner.html" style="color:#28A745;font-weight:700;">紹介バナー</a>をご自由にお使いいただけます。
</div>

'''

files = sorted(glob.glob('blog/*.html'))
updated, skipped = 0, 0
for f in files:
    with open(f, encoding='utf-8') as fh:
        content = fh.read()
    if 'partner.html' in content:
        skipped += 1
        continue
    if '<footer>' not in content:
        print(f'[WARN] no <footer> in {f}')
        continue
    new_content = content.replace('<footer>', CTA + '<footer>', 1)
    with open(f, 'w', encoding='utf-8') as fh:
        fh.write(new_content)
    updated += 1

print(f'updated={updated} skipped(already has)={skipped} total={len(files)}')
