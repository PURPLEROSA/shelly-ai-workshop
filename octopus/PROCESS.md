# OC-8: תמנון רובוטי בשלושה ממדים, בצבעי GENIRO

שחזור 1:1 של הבילד מהפוסט (Opus 5.5, "make the model"), בשפה העיצובית AIGOS.
פותחים את `octopus/index.html` בשרת מקומי. הוא לא רץ ישירות מ-file://, כי ה-importmap צריך שרת:

```bash
cd octopus && python3 -m http.server 8000
# http://localhost:8000
```

## התהליך מהפוסט, בשישה שלבים

1. **התמונה קובעת את הלוק.** כל עלה, עדשה וחוליה נבנים כקוד three.js. אין מודל מוכן ואין קובץ GLB.
2. **לולאת השוואה לפני אנימציה.** מרנדרים פריים סטטי אחד, מניחים אותו ליד תמונת הרפרנס ומתקנים את הפערים. עושים 3 סבבים כאלה, ורק אחריהם נוגעים בתנועה.
3. **הפס הראשון נראה כמו צעצוע.** החזרנו את הצפיפות: 202 חוליות ו-480 גלגלים בשמונה זרועות.
4. **כל זרוע היא draw call אחד** (BatchedMesh). המיקום שלה מחושב בכל פריים בהליכה על שרשרת הכיפופים (forward kinematics).
5. **כל 2–3 שניות משהו נפתח:** העדשה מתברגת החוצה, המעטפת נפתחת על ציר, המשאבה עולה ומסתובבת, והמקור נפתח.
6. **ב-0:16 הכול מתפרק** על פטיפון של 330° ומתחבר בחזרה לפני שהסיבוב נגמר. בסוף הלולאה התמנון יוצא מהפריים בכוח ההנעה הסילונית שלו.

## מה שונה כאן מהמקור

| | מקור | OC-8 |
|---|---|---|
| רקע | אפור-לבן בהיר | ‎#050505 עם זוהר סגול/כחול |
| גוף | קרמיקה לבנה עם אדום-כתום | קרמיקת פנינה עם iridescence, גרפיט, ונקודות אור הולוגרפיות |
| גלגלים | לבן עם אדום | גרדיאנט ההולוגרמה לאורך הזרוע |
| HUD | Mono על בהיר | Urbanist ו-DM Sans, כרטיסי זכוכית, תוויות סגולות |
| מותג | Pelagos OC-8 | GENIRO.AI · OC-8 |

## הפרומפט לשחזור (להדבקה)

```
Build a single-file three.js field simulation of a robotic octopus ("OC-8").
Style: [paste the AIGOS skill / attach reference image].
Rules:
- Every part is procedural three.js geometry. No external models.
- Before animating: render ONE still next to the reference, list the gaps, fix. Repeat 3 rounds.
- Density: 8 arms, 202 links total, 480 suction wheels (30 stations x 2 per arm).
- Each arm = ONE draw call (BatchedMesh), posed every frame by walking its chain of bends (FK).
- 25 s loop. Something opens every 2-3 s: lens unscrews, mantle hinges open, pump rises spinning, beak opens, arms wake.
- At 0:16 the whole body explodes on a 330° turntable and reassembles before the turn ends.
- Ends with a jet exit: the octopus leaves the frame on its own.
- HUD around it: jet pressure + sparkline, power, arm load, depth dial, assemblies (click to jump),
  display toggles (labels / exploded / jet wake / turntable), subsystems status, timeline scrubber.
```

## Controls

- גרירה מסובבת את המצלמה, וגלגלת עושה זום.
- רווח עוצר וממשיך.
- לחיצה על הטיימליין או על צ'יפ ב-Assemblies קופצת לשלב.
- Display: תוויות, פיצוץ קבוע, שובל סילון, פטיפון.
