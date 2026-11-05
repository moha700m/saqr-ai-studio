# TECHNICAL RESEARCH — Deep-Live-Cam ومشتقاته

تاريخ البحث: 2026-11-05. المنهج: استنساخ سطحي (`--depth 1`) للمستودعين وقراءة الكود
والاعتماديات والتراخيص. لم يُنسخ أي كود إلى SAQR؛ الأفكار أُعيد تنفيذها من الصفر.

## المستودعات المدروسة

| المستودع | HEAD | الحجم | الترخيص |
|---|---|---|---|
| `hacksider/Deep-Live-Cam` | `0bae1a5` | 5,607 سطر Python | AGPL-3.0 |
| `beekamai/DeepLiveCam` (fork) | HEAD عند الاستنساخ | 10,947 سطر Python | AGPL-3.0 |

## Deep-Live-Cam 2.1.6

### البنية

- `modules/ui.py` — 1,730 سطرًا، واجهة **PySide6** (وليس Tkinter؛ بقايا `tkinter_fix.py` تاريخية).
- `modules/core.py` — تنسيق المعالجة لكل إطار/صورة/فيديو.
- `modules/face_analyser.py` — `insightface.app.FaceAnalysis(name='buffalo_l')` مع
  `allowed_modules=['detection','recognition','landmark_2d_106']`، وحجم كشف قابل للتغيير
  يعيد تهيئة المحلل لأن InsightFace يثبّت شكل الإدخال عند `prepare()`.
- `modules/processors/frame/` — سجل معالجات مسموح: `face_swapper`, `face_enhancer`,
  `face_enhancer_gpen256`, `face_enhancer_gpen512`؛ كل معالج يلتزم بواجهة
  `pre_check/pre_start/process_frame/process_image/process_video`.
- `modules/video_capture.py`, `modules/capturer.py` — التقاط الكاميرا والمعاينة.
- `modules/gpu_processing.py` — عمليات CUDA/GPU للنسخ والتحجيم والمزج.
- `modules/onnx_optimize.py` (555 سطرًا) — تحسين/تفريز ONNX وTensorRT.
- `modules/model_downloader.py` — تنزيل من HuggingFace `hacksider/deep-live-cam`؛
  يسرد `inswapper_128.onnx` بحجم 554,253,681 بايت ونسخة fp16 بحجم 277,680,638 بايت.

### تبديل الوجه والمزج

`face_swapper.py` يستخدم inswapper ثم:

- قناع بيضاوي مُموّه في فضاء الوجه المحاذى، مخزّن مؤقتًا حسب الحجم لتقليل الاهتزاز.
- مزج Poisson (`cv2.seamlessClone`) بقناع مشتق من تحويل affine نفسه، لا من نقاط
  مستقلة، لتقليل "wobble" الناتج عن اهتزاز المعالم.
- تخزين نتيجة الإطار السابق واستخدامها في الاستيفاء (interpolation) لتثبيت الحركة.
- تحسين اختياري بـ GFPGAN/GPEN بنسب مختلفة.

### الاعتماديات

`onnxruntime-gpu==1.26.0` (غير macOS)، `insightface==0.7.3`, `opencv-python==4.14`,
`PySide6>=6.7`, `opennsfw2` لفحص المحتوى، `keras`/`protobuf`. التثبيت يدير CUDA
بشكل ضمني عبر حزم onnxruntime-gpu، وهو مصدر شائع لأعطال "provider not found".

### الاختبارات

خمسة ملفات: تحميل/تحليل الوجه، خريطة الوجوه والاحتياط، فحص SSL عند التنزيل،
معاينة الواجهة، والأدوات. لا اختبارات لواجهة API ولا لتعدد المصادر.

### ملاحظات ترخيص

- التطبيق AGPL-3.0.
- **إعادة توزيع أوزان inswapper على HuggingFace لا تمنح المستخدم حقًا تجاريًا**؛
  ترخيص InsightFace للنماذج بحثي غير تجاري. هذه نقطة حرجة لأي منتج تجاري.

## Fork: beekamai/DeepLiveCam

أكبر (~ضعف الحجم) ويضيف:

| الملف | الفكرة |
|---|---|
| `modules/providers.py` | TensorRT كمزوّد اختياري مع بناء engine وذاكرة تخزين مؤقت |
| `modules/cuda_graph.py` | إعادة تشغيل CUDA graph لتقليل overhead لكل إطار |
| `modules/face_tracker.py` (475 سطرًا) | تعقّب مستقر عبر الإطارات |
| `modules/calibration.py` (551 سطرًا) | معايرة/ضبط هندسي |
| `modules/head_geometry.py`, `reprojection.py` | هندسة الرأس وإعادة الإسقاط |
| `modules/face_occluder.py`, `face_reveal.py` | إخفاء/كشف مناطق الوجه |
| `modules/enhancer_registry.py`, `swapper_registry.py` | سجلات نماذج قابلة للتبديل |
| `modules/ui.py` | 3,039 سطرًا، واجهة أغنى |

docstring الخاص بـ `providers.py` يذكر قياسات على RTX 5060 Ti: TensorRT أسرع
2–3.5× من CUDA graph (inswapper 19ms → 5.4ms، GPEN-256 8.5→3.2). هذه **أرقام مؤلف
المستودع**، لم تُتحقق منها هنا لعدم وجود GPU.

## ما تبنّيناه

1. **فصل الطبقات**: hardware / models / face / camera / media / api — بدل ملفات مترابطة.
2. **التحقق الفعلي من المزوّد** قبل الاختيار، وسلسلة احتياط دائمة.
3. **قناع مشتق من التحويل** (كما في DLC) لأنه يقلل الاهتزاز فعليًا.
4. **مقاييس لكل إطار** بدل إخفائها.
5. **بوابة ترخيص** قبل أي تحميل/استيراد لنموذج مقيّد.
6. **جسر محلي مُصادق** بدل تعريض API مفتوح.

## ما تجنّبناه

- `insightface` كاعتماد إجباري: يجرّ onnxruntime خاصًا وتراخيص نماذج، ويصعّب التغليف.
- نسخ كود AGPL: كل ملف في SAQR مكتوب أصليًا.
- ادّعاء أن TensorRT "سيعمل" دون فحص: عندنا لا يُختار إلا بعد نجاح جلسة.
- تنزيل inswapper تلقائيًا: الترخيص يمنع ذلك في منتج يُوزّع.

## أرقام من هذه البيئة (ليست أرقام GPU)

| القياس | القيمة | السياق |
|---|---|---|
| كشف YuNet 640×480 | 22.3ms متوسط، p95 22.9ms | Neoverse-N1، نواتان، CPU فقط |
| معالجة 50 إطارًا 640×480 + ترميز H.264 | 1.46s (≈34 FPS) | نفس البيئة، بلا تبديل |
| كشف صورة 512×512 | 24.8ms، وجه واحد بثقة 0.909 | lena.jpg من عينات OpenCV |

لا توجد أرقام تبديل حقيقية لأن أوزان inswapper غير متاحة في البيئة (ترخيص + حجم).
