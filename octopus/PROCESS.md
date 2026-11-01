# OC-8: תמנון רובוטי בשלושה ממדים, בצבעי GENIRO

בנוי בשיטת **teardown** (הסקיל החינמי של Elvar, רישיון MIT, github.com/elvarofficial/teardown), בשפה העיצובית AIGOS.

```bash
cd octopus && python3 -m http.server 8765
# http://localhost:8765
```

הקובץ צריך שרת, כי ה-importmap לא נטען מ-file://. אין תלות ברשת חוץ מ-Google Fonts, ו-three.js צרוב בתיקייה `vendor/`.

---

## השיטה בקצרה: 6 חלקים בכל סימולטור

| חלק | מה זה | איך זה ממומש ב-OC-8 |
|---|---|---|
| **המכונה** | נבנית מקוד, בלי מודל מוכן | ראש, מעטפת על ציר, עדשה בהברגה, משאבה, מקור ו-8 זרועות. 202 חוליות ו-480 גלגלים |
| **המודל** | קלט אחד, וכל השאר פונקציה שלו | `tourState(t)`: זמן הלולאה (0–25 ש') קובע כל תנוחה. אין `Math.random` ואין state בין פריימים |
| **הפאנלים** | מספרים שנגזרים מהמודל | מ"מ של העדשה, מעלות הציר, סל"ד הרוטור, זווית הלסת, דחף, גרף לחץ ושרטוט עליון |
| **הכפתורים** | כפתור לכל תת-מערכת | Optics, Mantle, Pump, Beak, Arms, Explode, Jet, ומקשים 1–7 |
| **החלון** | הרצפה מראה את המודל עובד | טבעות, פטיפון עם מעלות, צל מגע ושובל סילון |
| **הסיור** | סמן שמפעיל את הדף לבד | לחיצה, גרירה, גלילה או מקש מעבירים לך שליטה. אחרי 25 ש' בלי מגע הסיור חוזר |

## 9 השלבים, ואיך כל אחד יושם

1. **התקנה:** `npx skills add elvarofficial/teardown -g -a claude-code`, ואז מריצים `/teardown`.
2. **רפרנס לפני הכול.** בלי רפרנס יוצא צעצוע גנרי. כאן הרפרנס היה הפריים מהפוסט.
3. **המודל קודם.** פונקציות טהורות של קלט אחד. כל חלק, פאנל ותווית קוראים מאותו מקור. יחידות: 1 יחידה = 100 מ"מ. העדשה זזה 50 מ"מ ב-2 סיבובים, הציר נפתח ל-66°, המשאבה עולה 60 מ"מ, הלסת נפתחת ל-34°.
4. **קונסולה סביב המכונה, ב-1600×900:** מספר ראשי גדול, גרפים חיים, שרטוט 2D מאותו מודל, כפתור לכל תת-מערכת, כפתורי מצלמה (Hero, Front, Side, Top, Inside), ותוויות עם קווים מובילים.
5. **הלוק:** פה בחרתי במכוון אחרת מהסקיל. הוא ממליץ על סטודיו בהיר, ואני הלכתי על AIGOS כהה כי זו השפה שלך. הכלל של "צבע הדגשה אחד" נשמר: רק החלק שעובד עכשיו מקבל תווית ומיקוד מצלמה.
6. **ביקורת כמו מבקר.** מרנדרים פריים סטילס בכל ביט וקוראים כל אחד. בודקים את התפר בין 24.95 ל-0 ומוודאים שאין קפיצה. מתקנים התנגשויות עם מספר, לא עם מצלמה.
7. **דף שנוהגים בו:** סיור עם סמן, מסירת שליטה, חזרה אחרי 25 ש', ומקש H להסתרת הפאנלים. מוסיפים חימום shaders לפני הפריים הראשון, ומדרגות איכות ל-GPU מובנה: pixel ratio 1, אחר כך בלי bloom ופאנלים ב-10 FPS.
8. **וידאו:** `node tools/record.mjs --fps 60 --size 1600x900 --dpr 1.2`. כל פריים מרונדר מ-`render(t)` ולא בהקלטת מסך, ולכן אף פריים לא נופל.
9. **אונליין:** ה-HTML שוקל כ-60KB, ו-three.js כ-680KB. Vercel או GitHub Pages מתאימים.

---

## פרומפט לשחזור על כל מכונה אחרת

```
/teardown Build [the machine] as an interactive 3D simulator. Reference attached: [image].
Style: [paste AIGOS skill] — dark #050505, pearl ceramic + graphite, holographic accents only on the working part.

Build it from code in real units: [list parts].
Before you draw anything, write the model as pure functions of one input: [loop time 0–25 s / stroke 0..1].
Use real numbers: [travel mm, angles, ratios]. Check them by hand and show me the check.
Every part, every panel and every label reads from that one model. Nothing is animated by hand.

Console at 1600×900: main live number top-left, live charts that move with the machine,
a 2D schematic redrawn from the same model, one button per subsystem, camera views as buttons,
callouts with thin leader lines. No number on screen is typed in.

Before you show me anything: render a still at every beat, scrub transitions at 0.2 s,
fix collisions with a number, never with the camera. Show me the stills.

Make it a page people drive: auto tour with a cursor that presses each button;
any input hands control over, 25 s of quiet hands it back. Warm shaders, add quality tiers.
```

## Controls

- גרירה מסובבת את המצלמה, וגלגלת עושה זום.
- רווח עוצר וממשיך. H מסתיר את הפאנלים. מקשים 1–7 מפעילים את ה-Assemblies.
- לחיצה על הטיימליין חוזרת לסיור מאותה נקודה.
