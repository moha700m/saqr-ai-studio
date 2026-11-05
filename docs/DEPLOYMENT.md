# DEPLOYMENT

## الحالة الحالية

| الهدف | الحالة | الرابط |
|---|---|---|
| GitHub (عام) | منشور | https://github.com/moha700m/saqr-ai-studio |
| GitHub Pages (عرض ثابت) | **منشور** | https://moha700m.github.io/saqr-ai-studio/ |
| Cloudflare Pages | سير عمل جاهز، لا توكن | — |
| مثبّت Windows | إصدار `v0.9.0` | صفحة Releases |

## GitHub Pages (منشور)

البناء يُنشر إلى فرع `gh-pages` عبر `peaceiris/actions-gh-pages`، وGitHub Pages يخدمه
بـ «Deploy from a branch». تحقق آلي: 200 على 12 مسارًا × مقاسين، بلا تجاوز أو أخطاء JS.

### لماذا ليس Actions/artifact؟

`actions/deploy-pages` بقي `in_progress` أكثر من 7 دقائق لهذا الحساب. فرع `gh-pages`
عمل فورًا، لذا اعتمدناه. سير Cloudflare يبقى المسار الإنتاجي عند توفر الحساب.

الواجهة تعمل على HTTPS، لكن جسر `127.0.0.1` قد يُحظر من Safari بسبب mixed content.

- البناء يستخدم `base: './'` و`HashRouter` ليعمل تحت مسار `/saqr-ai-studio/`.
- سير العمل: `.github/workflows/pages.yml`.
- الموقع ثابت: واجهة + MediaPipe. لا يعالج وجوهًا بدون جسر سطح المكتب.
- الجسر من صفحة HTTPS إلى `http://127.0.0.1:8765`:
  - Chrome/Edge يسمحان بذلك كـ "potentially trustworthy origin".
  - Safari قد يحظر mixed content. الحل: افتح الواجهة من نفس أصل المحرك
    (`http://127.0.0.1:8765`) بعد تشغيل `saqr serve`.

## Cloudflare Pages

```bash
gh secret set CLOUDFLARE_API_TOKEN
gh secret set CLOUDFLARE_ACCOUNT_ID
```

ثم شغّل `Deploy web`. السير يبني ويرفع `web/dist`. بدون الأسرار ينجح البناء
ولا يحدث نشر (تحذير فقط)، وهذا مقصود لمنع نشر غير مقصود.

## المثبّت

- يُبنى على `windows-latest` عبر `.github/workflows/installer.yml`.
- عند دفع وسم `v*` يُرفع `SAQR-AI-Setup.exe` تلقائيًا إلى Releases.
- التوقيع غير مُهيأ. أضف شهادة Authenticode إلى `SignTool` في Inno Setup قبل التوزيع.

## ما لا يُنشر

- أوزان inswapper (ترخيص غير تجاري).
- أي مفاتيح أو رموز. الأسرار تمر عبر GitHub Secrets فقط.

## التحقق بعد النشر

```bash
curl -I https://moha700m.github.io/saqr-ai-studio/
# ثم افتح الصفحة على الهاتف وتأكد من:
# - ظهور الواجهة RTL.
# - طلب إذن الكاميرا يعمل عبر HTTPS.
# - شارة "المحرك غير متصل" عند عدم تشغيل الجسر.
```
