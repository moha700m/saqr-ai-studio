# MODEL LICENSES

SAQR لا يضمّن أوزانًا. هذا الجدول هو المرجع الوحيد لما يمكن تنزيله أو استيراده.

| النموذج | النوع | الترخيص | تجاري | إعادة توزيع | طريقة التثبيت | SHA-256 |
|---|---|---|---|---|---|---|
| YuNet 2023mar | detector | MIT (Shiqi Yu / OpenCV Zoo) | نعم | نعم مع إشعار | تنزيل آلي | `8f2383e4…52fa4` |
| GFPGAN v1.4 | enhancer | Apache-2.0 (Tencent ARC) | نعم | نعم مع إشعار | استيراد يدوي | غير مثبّت |
| inswapper_128 | swapper | InsightFace Model License — **بحثي غير تجاري** | **لا** | **لا** | استيراد يدوي + موافقة | غير مثبّت |

## التفاصيل

### YuNet
- المصدر: https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet
- الملف: `face_detection_yunet_2023mar.onnx`، 232,589 بايت.
- البصمة المقيسة: `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`.
- يُستخدم للكشف ونقاط المحاذاة الخمس. لا قيود تجارية.

### GFPGAN v1.4
- المصدر: https://github.com/TencentARC/GFPGAN (Apache-2.0).
- SAQR لا توزّع الأوزان. صدّر ONNX بنفسك أو نزّله من مصدر تثق به، ثم:
  `saqr models import GFPGANv1.4.onnx --kind enhancer`
- المدير يتحقق أن الرسم 4D ويقرأ حجم الإدخال تلقائيًا.

### inswapper_128
- المصدر: https://github.com/deepinsight/insightface
- الترخيص: "available for non-commercial research purposes only".
- **لا يوجد رابط تنزيل في SAQR، ولا nُعيد توزيعه.** بوابة `requires_acceptance`
  تمنع الاستيراد حتى تؤكد قراءتك للترخيص.
- للاستخدام التجاري: استخدم نموذج تبديل مرخّصًا تجاريًا. المحرك يقبل أي رسم
  ONNX يطابق أحد التوقيعين المدعومين (latent أو dual-image).

## الترخيص التجاري — كيف تتحقق

1. اقرأ ترخيص النموذج نفسه، لا ترخيص المستودع الذي نزّلته.
2. وجود النموذج على HuggingFace لا يعني إذنًا تجاريًا.
3. إذا كان منتجك تجاريًا، استبدل inswapper بنموذج مرخّص أو درّب نموذجك.
4. راجع `saqr models list` — عمود `commercial` يعكس تقييمنا، وليس استشارة قانونية.

## بصمات وتحقّق

- التنزيل الآلي يتحقق من SHA-256 قبل النقل النهائي.
- الاستيراد اليدوي يحسب البصمة ويسجلها، ويمكن إعادة التحقق:
  `saqr models verify <id>`.
- أي تعديل على الملف بعد التثبيت يظهر كفشل تحقق.
