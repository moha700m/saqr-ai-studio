# REPOSITORY COMPARISON

| البعد | Deep-Live-Cam 2.1.6 | beekamai fork | SAQR AI Studio 0.9 |
|---|---|---|---|
| الترخيص | AGPL-3.0 | AGPL-3.0 | AGPL-3.0 |
| أسطر Python | 5,607 | 10,947 | ~4,772 (محرك + سطح مكتب) |
| الواجهة | PySide6 | PySide6 (أغنى) | PySide6 + ويب React |
| الكشف | InsightFace buffalo_l | InsightFace + تعقّب | YuNet (MIT) + تعقّب IoU |
| المحاذاة | insightface norm_crop | + معايرة/هندسة رأس | Umeyama أصلي إلى قالب ArcFace |
| التبديل | inswapper_128 | inswapper + سجلات نماذج | ONNX model-agnostic (latent/dual) |
| التحسين | GFPGAN/GPEN | GFPGAN/GPEN/CodeFormer/RestoreFormer | GFPGAN-class (استيراد يدوي) |
| المزوّدات | CUDA/DirectML/CPU | + TensorRT/CUDA graph | CUDA/TRT/DML/ROCm/OpenVINO/CoreML/CPU مع فحص |
| اختيار الخلفية | يدوي/بيئي | يدوي | تلقائي + فحص جلسة + احتياط |
| الكاميرا | Tk/PySide معاينة | + تعقّب | خيط + طابور يُسقط الأقدم |
| الفيديو | FFmpeg | FFmpeg | FFmpeg pipe + دمج صوت + إلغاء |
| الجسر/API | لا | لا | FastAPI مقترن، Origin، جلسات |
| الويب | لا | لا | 12 صفحة RTL + كاميرا + MediaPipe |
| النماذج | تنزيل تلقائي من HF | مكتبة نماذج | كتالوج + SHA-256 + بوابة ترخيص |
| السحابة | لا | لا | BYO endpoint + موافقة صريحة (معطّل) |
| الاختبارات | 5 ملفات | 6 ملفات | 53 اختبار pytest |
| المثبّت | حزم جاهزة/سكربتات | سكربتات | PyInstaller + Inno Setup + postinstall |
| CI | محدود | غير واضح | 4 سير عمل (اختبار/مثبّت/أمان/نشر) |

## استنتاجات

- **الأداء**: لا يمكن مقارنة أرقامنا بأرقام المستودعين لاختلاف العتاد. ما نملكه:
  قياس كشف حقيقي على CPU، وزمن معالجة فيديو فعلي.
- **الجودة**: inswapper يبقى المعيار البصري؛ SAQR لا يدّعي أفضلية بصرية بدون
  أوزان حقيقية وGPU. الميزة في الهندسة: كشف عتاد، أمان الجسر، إدارة النماذج.
- **التراخيص**: المستودعان يعيدان توزيع inswapper؛ SAQR لا يفعل. هذا يقلل سهولة
  التثبيت لكنه يحمي المستخدم من ادّعاء حقوق لا يملكها.
