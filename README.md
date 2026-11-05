# SAQR AI Studio

بديل عملي لـ DeepLiveCam: محرك ONNX للكشف والتبديل، تطبيق سطح مكتب PySide6، واجهة ويب،
جسر محلي آمن، ومعالجة صور/فيديو — بافتراضات خصوصية صريحة.

> المستودع: https://github.com/moha700m/saqr-ai-studio
>
> **الحالة:** معاينة 0.9. كل الأرقام في `TEST_REPORT.md` مقيسة فعليًا داخل بيئة Linux CPU.
> ما لم يُختبر (Windows، GPU، كاميرا حقيقية، مثبّت موقّع) مذكور صراحة في `PROJECT_STATE.md`.

---

## ما الذي يعمل فعلًا

| المكوّن | الحالة |
|---|---|
| كشف العتاد (CPU/GPU/RAM/OS) على Linux وWindows وmacOS | يعمل، مع مصادر موثّقة لكل حقل |
| فحص مزوّدات ONNX بجلسة حقيقية + سلسلة احتياط | يعمل (CPU مُتحقق هنا) |
| مدير نماذج ببصمة SHA-256 وتراخيص وبوابة موافقة | يعمل؛ YuNet نُزّل وتحققت بصمته |
| كشف الوجوه YuNet + محاذاة Umeyama + تعقّب IoU | يعمل؛ قياس حقيقي 22.3ms @640×480 |
| تبديل ONNX (inswapper-style وdual-image) + أقنعة | الكود والاختبارات تعمل على نماذج اصطناعية؛ **الأوزان الحقيقية غير مضمّنة** |
| كاميرا مباشرة بطابور محدود يُسقط القديم | يعمل مع كاميرا وهمية في الاختبارات |
| معالجة صور وفيديو H.264 + دمج الصوت + إلغاء | يعمل؛ 50 إطارًا في 1.46s على CPU |
| جسر FastAPI محلي: اقتران، مصادقة، Origin، حدود | يعمل؛ 53 اختبارًا ناجحًا |
| واجهة ويب RTL متجاوبة (12 صفحة) | تُبنى بنجاح؛ 24 فحص صفحة بلا تجاوز عرض |
| تطبيق PySide6 | مكتوب بالكامل؛ لم يُشغّل في هذه البيئة (لا شاشة) |
| مثبّت Windows | سكربتات Inno Setup + PyInstaller جاهزة؛ **لم يُبنَ هنا** (لا Windows) |

---

## البدء السريع (Linux/macOS)

```bash
git clone https://github.com/moha700m/saqr-ai-studio.git && cd saqr-ai-studio
./scripts/bootstrap.sh

saqr models download yunet-2023mar
saqr doctor
saqr serve --pair          # يعرض رمز اقتران صالحًا 3 دقائق
```

ثم:

```bash
cd web && npm run dev      # http://localhost:5173
# أو افتح البناء المجمّع من نفس أصل المحرك:
cd web && npm run build && cd .. && saqr serve
```

## البدء السريع (Windows)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\pip install -e "engine[desktop,dev]"
.venv\Scripts\saqr models download yunet-2023mar
.venv\Scripts\python -m saqr_desktop
# أو بناء المثبّت:
powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1
```

---

## النماذج والتراخيص

- **YuNet** — MIT، يُنزّل تلقائيًا ويتحقق من SHA-256.
- **GFPGAN 1.4** — Apache-2.0، استيراد يدوي فقط.
- **inswapper_128** — ترخيص InsightFace **غير تجاري**. لا تنزّله SAQR ولا تعيد توزيعه.
  يتطلب تأكيدًا صريحًا: `saqr models import ./inswapper_128.onnx --kind swapper --accept-license`.

اقرأ `docs/MODEL_LICENSES.md` قبل أي استخدام تجاري. المحرك نفسه مرخّص AGPL-3.0.

---

## الهيكل

```
engine/      محرك Python: hardware, models, face, camera, media, api
desktop/     تطبيق PySide6
web/         React + Vite + TS (RTL)
installer/   PyInstaller spec + Inno Setup + postinstall
scripts/     bootstrap, build, assets, benchmark
tests/       51 اختبار pytest
docs/        المعمارية، البحث، التراخيص، الأمان
```

## الأوامر

```bash
saqr doctor [--json] [--verify-trt]
saqr models list|download|import|remove|verify
saqr serve [--pair] [--port 8765]
saqr benchmark --frames 60 --image portrait.jpg [--swap]
saqr process image|video IN OUT --source face.jpg
```

## الخصوصية باختصار

- المعالجة محلية افتراضيًا؛ لا رفع تلقائي، لا تسجيل تلقائي، لا كاميرا تلقائية.
- السحابة معطّلة ولا يوجد مزوّد مضمّن؛ تتطلب endpoint تملكه وموافقة لكل ملف.
- الجسر على `127.0.0.1` فقط، برمز لمرة واحدة وجلسات مُهشّرة.
- لا تُستخرج Embeddings ولا تُحفظ قاعدة هوية.

## التوثيق

`ARCHITECTURE.md` · `TECHNICAL_RESEARCH.md` · `REPOSITORY_COMPARISON.md` ·
`MODEL_LICENSES.md` · `SECURITY.md` · `PRIVACY.md` · `TEST_REPORT.md` · `PROJECT_STATE.md`

## الاستخدام المسؤول

استخدم وجوهًا تملك موافقتها. أشر إلى أن المخرجات مُولّدة. لا تنشئ مواد جنسية غير رضائية
أو انتحال هوية. القوانين تختلف بين الدول — المسؤولية عليك.
