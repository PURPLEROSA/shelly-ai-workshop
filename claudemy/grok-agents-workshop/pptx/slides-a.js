// פתיחה · 01 יסודות · 02 מי אני · 03 תפקיד ועיצוב · הפסקה
const L = require('./lib');
const { C, H, B, X0, X1, CW, t, en, chrome, head, card, box, hline, icon, tile, pill, numPill, checks, btn, arrow, prompt, tip, crop, photo, robot, rr } = L;
const IMG = 'assets/img/';
const TILES = [C.tPink, C.tMint, C.tButter, C.tBlue, C.tLilac];

module.exports = async (ctx) => {
  const { slide, section } = ctx;

  // divider used by both files
  ctx.divider = async (sec, n, title, sub, enLabel, img, o = {}) => {
    const s = slide(o.blue ? 'DIVIDER_BLUE' : 'DIVIDER', sec, o.notes);
    chrome(s, null);
    t(s, n, 6.2, 0.95, 6.38, 2.1, { fontFace: H, fontSize: o.numSize || 150, color: C.purple });
    t(s, title, 5.6, 3.05, 6.98, 1.2, { fontFace: H, fontSize: o.titleSize || 64 });
    t(s, sub, 6.2, 4.35, 6.38, 1.1, { fontSize: 20, lineSpacingMultiple: 1.25 });
    en(s, enLabel, 6.2, 5.6, 6.38, 0.35, { align: 'right', fontSize: 12, bold: true, charSpacing: 3, color: C.purple });
    const p = await crop(img, 4.1 / 5.2, 'div-' + require('path').basename(img, require('path').extname(img)) + '.jpg', o.gravity);
    photo(s, p, 1.15, 1.05, 4.1, 5.2, o.rot || -3, o.blue ? C.pink : C.blue);
    if (o.robot) robot(s, o.robot, 0.55, 5.35, 1.35);
    return s;
  };

  // ───────────── פתיחה
  section('פתיחה');
  {
    const s = slide('DIVIDER_BLUE', 'פתיחה', "0–5 · פתיחה. בצ'אט: המקצוע שלכם ומשימה אחת שהייתם מעבירים לסוכן.");
    chrome(s, 'AGENTS FROM ZERO · LIVE ON ZOOM');
    pill(s, 'סדנה חיה בזום · שני ערבים', 8.88, 1.2, 3.7, { fill: C.pink, line: null });
    t(s, 'סוכנים מאפס', 5.4, 1.8, 7.18, 1.15, { fontFace: H, fontSize: 66 });
    t(s, 'עם Grok Bot.', 5.4, 2.95, 7.18, 1.0, { fontFace: H, fontSize: 50, color: C.purple });
    t(s, 'בונים צוות קטן של בוטים עם תפקיד ברור, שעובד בשבילכם גם כשהלפטופ סגור. בלי קוד, בלייב, עם שבוע של ליווי.',
      6.0, 4.08, 6.58, 0.95, { fontSize: 17, lineSpacingMultiple: 1.3 });
    t(s, [{ text: 'עם ', options: {} }, { text: 'שלי אור גיסר', options: { bold: true } }, { text: ' · Head of AI בגיתם BBDO · מרצה בטכניון', options: {} }],
      5.6, 5.05, 6.98, 0.35, { fontSize: 13, color: C.muted });
    btn(s, 'הסוכן מכין. אתם מחליטים.', 7.88, 5.55, 4.7);
    t(s, 'יום שני, 2.11 · 20:00–22:00 בזום · מפגש המשך 9.11', 5.6, 6.32, 6.98, 0.35, { fontSize: 14, bold: true });
    const cov = await crop(IMG + 'shelly-disco-agents.jpg', 4.7 / 4.1, 'cover-south.jpg', 'south');
    photo(s, cov, 0.9, 1.75, 4.7, 4.1, -3);
    robot(s, 'home', 0.4, 1.0, 1.25);
  }
  {
    const s = slide('PAPER', 'פתיחה', 'ההבטחה. לא צריך רקע טכני. בסוף הערב כל אחד מקים סוכן משלו, בלייב.');
    chrome(s, 'TONIGHT · WHAT YOU GET');
    head(s, 'עם מה יוצאים?', 'עם סוכן ', 'שכבר עובד.');
    const items = [
      ['קובץ "מי אני"', '3 אבנים, ערך מול מתחרים, והקול שלכם.'],
      ['סקיל ראשון', 'משימה שעשיתם פעמיים, שמורה כמתכון.'],
      ['כרטיס תפקיד', 'תפקיד, כללים ומשפט הרשאה, מוכנים להדבקה.'],
      ['מפת "איפה שומרים מה"', 'הוראות, זיכרון, סקילים, שגרות ודרייב.'],
      ['סוכן שעובד', 'מוקם בלייב, עם משימה ראשונה וקו סיום.'],
      ['שקט נפשי', 'שום דבר שעולה כסף, נשלח או מתפרסם לא רץ בלי אישור.'],
    ];
    items.forEach(([h, p], i) => {
      const col = i % 2, row = Math.floor(i / 2);
      const w = 5.6, x = col === 0 ? X1 - w : X0, y = 2.55 + row * 1.38;
      hline(s, x, y, w);
      rr(s, x + w - 0.46, y + 0.25, 0.46, 0.46, C.pink, null, 0.23);
      t(s, '✓', x + w - 0.46, y + 0.25, 0.46, 0.46, { align: 'center', valign: 'middle', bold: true, fontSize: 16 });
      t(s, h, x, y + 0.2, w - 0.7, 0.5, { fontFace: H, fontSize: 22 });
      t(s, p, x, y + 0.72, w - 0.7, 0.55, { fontSize: 14 });
    });
  }
  {
    const s = slide('BLUE', 'פתיחה', 'שני מפגשים חיים ושבוע של ליווי ביניהם.');
    chrome(s, 'THE PROGRAM');
    head(s, 'שני מפגשים חיים ושבוע של ליווי', 'התוכנית');
    const sess = (x, fill, k, dur, date, when, h3, list) => {
      const w = 4.9, y = 2.45, h = 4.3;
      box(s, x, y, w, h, fill);
      t(s, k, x + 0.3, y + 0.25, w - 0.6, 0.3, { fontSize: 11, bold: true });
      t(s, dur, x + 0.3, y + 0.25, 1.5, 0.3, { fontSize: 11, align: 'left' });
      hline(s, x + 0.3, y + 0.68, w - 0.6, C.rose, 0.5);
      en(s, [{ text: '2026  ', options: { fontSize: 13, bold: false } }, { text: date, options: {} }], x + 0.3, y + 0.8, w - 0.6, 0.85,
        { align: 'right', fontSize: 50, bold: true });
      t(s, when, x + 0.3, y + 1.62, w - 0.6, 0.3, { fontSize: 11 });
      t(s, h3, x + 0.3, y + 2.0, w - 0.6, 0.85, { fontFace: H, fontSize: 24, lineSpacingMultiple: 1.0 });
      checks(s, list, x + 0.3, y + 2.88, w - 0.6, 1.35, { size: 13, gap: 4 });
    };
    sess(X1 - 4.9, C.paper, 'מפגש 01 · בונים יחד', 'שעתיים', '02.11', 'יום שני · 20:00 עד 22:00 · בזום', 'הסוכן הראשון שלכם מתחיל לעבוד.',
      ['מגדירים 3 מטרות ומשימה ראשונה', 'בונים קובץ "מי אני" ובוק מותג', 'כרטיס תפקיד ומשפט הרשאה', 'סוכן תוכן, ביו ופוסט ראשון']);
    sess(X0, C.pink, 'מפגש 02 · מדייקים יחד', 'שעה', '09.11', 'יום שני · 20:00 עד 21:00 · בזום', 'עושים את זה עוד יותר שלכם.',
      ['עוברים על מה שעבד, ופותרים תקלות', 'סקילים ושגרות', 'צוות עם ראש מטה', 'אתרים ודיוור במייל']);
    arrow(s, 5.65, 3.0, 2.03, 0.6);
    t(s, 'שבוע לנסות', 5.65, 3.75, 2.03, 0.45, { align: 'center', fontFace: H, fontSize: 20 });
    t(s, 'נותנים משימות, אוספים תוצאות ומביאים שאלות.', 5.85, 4.25, 1.63, 0.9, { align: 'center', fontSize: 12 });
    arrow(s, 5.65, 5.2, 2.03, 0.6);
  }
  {
    const s = slide('PAPER', 'פתיחה', 'ציר הזמן של ערב 1. 120 דקות.');
    chrome(s, 'TONIGHT · 120 MIN');
    head(s, 'ערב 1 · 2.11', 'הערב, ', 'דקה אחרי דקה');
    const rows = [
      ['0–5', 'פתיחה', 'המשימה שהייתם מעבירים לסוכן'],
      ['5–20', 'יסודות', 'מה זה Grok Bot, איפה הוא שומר מה, ומה מותר לו'],
      ['20–45', 'מי אני', '3 אבנים, ערך מול מתחרים, והקול שלכם'],
      ['45–65', 'תפקיד ועיצוב', 'כרטיס תפקיד, משפט הרשאה, ובוק מותג'],
      ['65–70', 'הפסקה', 'חמש דקות'],
      ['70–92', 'סושיאל ובטיחות', 'אינסטגרם, הסיפור שלי, והכספת'],
      ['92–105', 'עוד סוכנים', 'לידים, דיוור, לקוחות, וצוות'],
      ['105–120', 'מקימים בלייב', '15 דקות, וסוכן שעובד'],
    ];
    const x = 4.35, w = X1 - x;
    rows.forEach(([tm, h, p], i) => {
      const y = 2.42 + i * 0.53;
      hline(s, x, y, w, i === 0 ? C.ink : C.line, i === 0 ? 0.75 : 0.5);
      rr(s, X1 - 1.05, y + 0.1, 1.05, 0.33, i === 4 ? C.pink : C.white, C.ink, 0.16);
      en(s, tm, X1 - 1.05, y + 0.1, 1.05, 0.33, { align: 'center', valign: 'middle', fontSize: 11 });
      t(s, h, X1 - 3.4, y + 0.06, 2.2, 0.42, { fontFace: H, fontSize: 18, valign: 'middle' });
      t(s, p, x, y + 0.06, w - 3.55, 0.42, { fontSize: 14, valign: 'middle' });
    });
    card(s, X0, 2.42, 3.25, 4.2);
    robot(s, 'content', X0 + 0.82, 2.62, 1.6);
    t(s, 'שלוש אבנים.', X0 + 0.25, 4.35, 2.75, 0.5, { fontFace: H, fontSize: 24, align: 'center' });
    t(s, 'שעתיים. סוכן אחד שעובד.', X0 + 0.25, 4.9, 2.75, 0.4, { fontSize: 14, align: 'center' });
    pill(s, 'ערב 2: 9.11', X0 + 0.7, 5.7, 1.85, { fill: C.pink, line: null });
  }

  // ───────────── 01 יסודות
  section('01 יסודות');
  await ctx.divider('01 יסודות', '01', 'יסודות', 'מה זה Grok Bot, איפה הוא שומר מה, ומה מותר לו.', 'THE BASICS', IMG + 'scene-computer.jpg',
    { notes: '5–20 · יסודות. חייב להיות בהתחלה. בלי הבסיס, כל השאר נשמע כמו קסם.' });
  {
    const s = slide('BLUE', '01 יסודות', "למה בוט ולא רק צ'אט. שלוש סיבות, ומתי לא צריך בוט בכלל.");
    chrome(s, 'WHY A BOT');
    head(s, 'למה בכלל בוט?', "צ'אט מחכה. ", 'בוט כבר עבד.');
    const cols = [
      ['01', 'עובד כשאתם לא', 'שגרות רצות לפי שעה או אירוע, גם כשהלפטופ סגור.', 'תדריך בוקר מחכה ב-06:00'],
      ['02', 'זוכר אתכם', 'הוראות, זיכרון וקבצים. לא מסבירים מחדש כל בוקר.', 'כותב בקול שלכם'],
      ['03', 'עושה, לא רק עונה', 'יש לו מחשב, דפדפן וחיבורים. גולש, מסדר ומכין טיוטות.', 'טבלת לידים מסודרת'],
    ];
    const w = 3.61;
    cols.forEach(([n, h, p, lab], i) => {
      const x = X1 - w - i * (w + 0.5), y = 2.5;
      hline(s, x, y, w);
      numPill(s, n, x + w - 0.62, y + 0.25);
      t(s, h, x, y + 0.75, w, 0.55, { fontFace: H, fontSize: 26 });
      t(s, p, x, y + 1.35, w, 0.8, { fontSize: 15 });
      const lw = 0.4 + lab.length * 0.105;
      rr(s, x + w - lw, y + 2.25, lw, 0.36, C.pink, null, 0.02);
      t(s, lab, x + w - lw, y + 2.25, lw, 0.36, { align: 'center', valign: 'middle', fontSize: 12 });
    });
    card(s, X1 - 5.67, 5.45, 5.67, 1.25);
    t(s, 'מתי בוט?', X1 - 5.42, 5.6, 5.2, 0.4, { fontFace: H, fontSize: 19 });
    t(s, 'משימה שחוזרת · צריכה זיכרון · יכולה לרוץ בלי שתשבו מול המסך', X1 - 5.42, 6.02, 5.2, 0.55, { fontSize: 14 });
    card(s, X0, 5.45, 5.67, 1.25, C.paper);
    t(s, "מתי מספיק צ'אט?", X0 + 0.25, 5.6, 5.2, 0.4, { fontFace: H, fontSize: 19 });
    t(s, 'שאלה חד-פעמית, רעיון לפוסט, תמונה אחת', X0 + 0.25, 6.02, 5.2, 0.55, { fontSize: 14 });
  }
  {
    const s = slide('PAPER', '01 יסודות', 'למה דווקא Grok Bot. מחשב משלו בענן = עובד כשהלפטופ סגור. ספריות מוכנות = לא מתחילים מאפס.');
    chrome(s, 'WHY GROK BOT');
    head(s, 'שש סיבות', 'למה דווקא ', 'Grok Bot?');
    const cards = [
      ['cloud', 'מחשב משלו בענן', 'עובד גם כשהלפטופ סגור'],
      ['users', 'צוות באפליקציה אחת', 'תפקיד, זיכרון, שגרות ואישורים'],
      ['globe', 'מחובר לעכשיו', 'רשת ו-X בזמן אמת, עם מקורות'],
      ['sparkles', 'מנוי אחד', "צ'אט, תמונות, וידאו, קול ובוטים"],
      ['smartphone', 'מחשב וטלפון', 'אותם בוטים, אותה שיחה'],
      ['store', 'לא מתחילים מאפס', 'אלפי בוטים וסקילים מוכנים'],
    ];
    const w = 3.71, h = 1.95;
    cards.forEach(([ic, h3, p], i) => {
      const col = i % 3, row = Math.floor(i / 3);
      const x = X1 - w - col * (w + 0.35), y = 2.5 + row * (h + 0.3);
      card(s, x, y, w, h);
      tile(s, ic, x + w - 0.85, y + 0.28, 0.58, TILES[i % 5]);
      t(s, h3, x + 0.3, y + 0.95, w - 0.6, 0.45, { fontFace: H, fontSize: 20 });
      t(s, p, x + 0.3, y + 1.4, w - 0.6, 0.4, { fontSize: 14 });
    });
  }
  {
    const s = slide('BLUE', '01 יסודות', 'Grok עונה ומחכה. Grok Bot מקבל תפקיד, עובד לבד, ועוצר לאישור.');
    chrome(s, 'GROK VS GROK BOT');
    head(s, "צ'אט מול בוט", 'Grok עונה. ', 'Grok Bot עושה.');
    const half = (x, fill, lab, h3, p) => {
      box(s, x, 2.45, 5.67, 1.75, fill);
      en(s, lab, x + 0.3, 2.62, 5.07, 0.3, { align: 'right', fontSize: 11, bold: true, charSpacing: 2 });
      t(s, h3, x + 0.3, 2.92, 5.07, 0.5, { fontFace: H, fontSize: 26 });
      t(s, p, x + 0.3, 3.45, 5.07, 0.65, { fontSize: 14 });
    };
    half(X1 - 5.67, C.paper, 'GROK', "צ'אט: עונה ומחכה", 'אתם שואלים, הוא עונה, ומחכה. חיפוש, תמונות, וידאו וקול.');
    half(X0, C.pink, 'GROK BOT', 'בוט: עובד לבד', 'מקבל תפקיד, עובד לבד בענן, ועוצר לפני כל פעולה חשובה.');
    const nodes = ['תפקיד וכללים', 'עובד לבד בענן', 'מכין טיוטה', 'אתם מאשרים'];
    nodes.forEach((n, i) => {
      const w = 2.45, x = X1 - w - i * (w + 0.6), y = 4.65;
      box(s, x, y, w, 1.0, i === 3 ? C.pink : C.white);
      t(s, n, x + 0.15, y, w - 0.3, 1.0, { align: 'center', valign: 'middle', fontFace: H, fontSize: 19 });
      if (i < 3) arrow(s, x - 0.6, y + 0.25, 0.6, 0.5);
    });
    t(s, 'הוא מכין. אתם מאשרים.', X0, 6.0, CW, 0.55, { fontFace: H, fontSize: 24, color: C.purple });
  }
  {
    const s = slide('PAPER', '01 יסודות', "מסלולים (אומת 16.10, לבדוק שוב ביום הסדנה). The X Subscription מאז 12.10. מכסה שבועית משותפת. SpaceX רכשה את Cursor באוגוסט 2026, ו-Grok Bot רץ על התשתית שלה. 'איחוד חשבונות': לא לוחצים.");
    chrome(s, 'PLANS · CURSOR');
    head(s, 'The X Subscription', 'מה צריך כדי ', 'להתחיל');
    const tiers = [['PLUS', '$8', "צ'אט בלבד, בלי בוט"], ['PREMIUM', '$30', 'מכאן יש Grok Bot. מספיק לסדנה'], ['SUPER', '$100', 'יותר מכסה'], ['ULTRA', '$200', 'הכי הרבה מכסה']];
    tiers.forEach(([n, p, d], i) => {
      const w = 2.7, x = X1 - w - i * (w + 0.34), y = 2.45, hi = i === 1;
      if (hi) box(s, x, y, w, 2.35, C.pink); else card(s, x, y, w, 2.35);
      en(s, n, x + 0.25, y + 0.25, w - 0.5, 0.3, { align: 'right', fontSize: 12, bold: true, charSpacing: 2 });
      en(s, p, x + 0.25, y + 0.6, w - 0.5, 0.8, { align: 'right', fontSize: 44, bold: true });
      t(s, d, x + 0.25, y + 1.45, w - 0.5, 0.75, { fontSize: 14 });
    });
    const info = [['gauge', 'מכסה שבועית אחת', "משותפת לצ'אט, תמונות, קול ובוטים"], ['id-card', 'נכנסים עם חשבון Cursor', 'Grok Bot רץ על התשתית שלה. "איחוד חשבונות" לא נדרש']];
    info.forEach(([ic, h3, p], i) => {
      const w = 5.67, x = X1 - w - i * (w + 0.49), y = 5.1;
      card(s, x, y, w, 1.15);
      tile(s, ic, x + w - 0.85, y + 0.29, 0.56, i ? C.tMint : C.tButter);
      t(s, h3, x + 0.25, y + 0.17, w - 1.25, 0.42, { fontFace: H, fontSize: 18 });
      t(s, p, x + 0.25, y + 0.58, w - 1.25, 0.45, { fontSize: 13 });
    });
    t(s, 'מחירים מ-16.10. בודקים שוב ב-x.ai ביום הסדנה.', X0, 6.42, CW, 0.3, { fontSize: 12, color: C.muted });
  }
  {
    const s = slide('BLUE', '01 יסודות', "מחשב לינוקס בענן: מחשב אמיתי. אחד לכל החשבון, לא לכל בוט. כתובת זרה: אינסטגרם עלול לחשוד. Added = הותקן, לא מחובר: Authenticate.");
    chrome(s, 'THE GROK COMPUTER · LINUX');
    head(s, 'מחשב, לא צ\'אט', 'לבוטים יש ', 'מחשב משלהם');
    const p = await crop(IMG + 'scene-computer.jpg', 3.3 / 4.2, 'computer-frame.jpg');
    photo(s, p, 1.0, 2.45, 3.3, 4.2, 2.5);
    const chips = [['LINUX בענן', 1.6], ['משותף לכל הבוטים', 2.15], ['דפדפן · קבצים · טרמינל', 2.6]];
    let cx = X1;
    chips.forEach(([c, w]) => { cx -= w; pill(s, c, cx, 2.45, w, { size: 12, h: 0.4 }); cx -= 0.12; });
    const rows = [
      ['1', 'אינטרנט', 'גולש וממלא טפסים כמו אדם. כתובת זרה: אתרים עלולים לחשוד.'],
      ['2', 'החיבורים שלכם', 'Gmail, Calendar, Canva. סטטוס Added = עוד לא מחובר: לוחצים Authenticate.'],
      ['3', 'המחשב שלכם', 'הרשאה נפרדת: Ask every time, או Never allow.'],
    ];
    const x = 5.05, w = X1 - x;
    rows.forEach(([n, h, d], i) => {
      const y = 3.05 + i * 0.88;
      hline(s, x, y, w);
      t(s, n, X1 - 0.45, y + 0.12, 0.45, 0.6, { fontFace: H, fontSize: 26, color: C.purple });
      t(s, h, X1 - 2.85, y + 0.17, 2.3, 0.5, { fontFace: H, fontSize: 19 });
      t(s, d, x, y + 0.17, w - 3.0, 0.65, { fontSize: 14 });
    });
    tip(s, x, 5.75, w, 0.98, 'טיפ', 'מתחברים בעצמכם בדפדפן של הבוט (Take over). סיסמה לא נכנסת לצ\'אט.');
  }
  {
    const s = slide('PAPER', '01 יסודות', 'מה יש בכל שיחה עם בוט. להראות על המסך שלי.');
    chrome(s, 'INSIDE EVERY CHAT');
    head(s, 'שש פינות בכל שיחה', 'מה יש לכם ', 'בכל שיחה');
    const items = [
      ['message-circle', 'מדברים כמו עם עובד', 'כותבים, מכתיבים או בקול'],
      ['check', 'כרטיס אישור', 'Allow once · Always allow · Deny'],
      ['eye', 'רואים מה הוא עושה', 'Take over לסיסמה או לקוד'],
      ['calendar-clock', 'לשונית Details', 'השגרות שלו: מתי הוא רץ לבד'],
      ['brain', '"מה אתה זוכר עליי?"', 'אין מסך זיכרון. שואלים אותו'],
      ['bell', 'התראות', 'כשסיים, או כשצריך אתכם'],
    ];
    items.forEach(([ic, h, p], i) => {
      const col = i % 2, row = Math.floor(i / 2);
      const w = 5.6, x = col === 0 ? X1 - w : X0, y = 2.5 + row * 1.4;
      hline(s, x, y, w);
      tile(s, ic, x + w - 0.62, y + 0.3, 0.62, TILES[i % 5]);
      t(s, h, x, y + 0.25, w - 0.85, 0.45, { fontFace: H, fontSize: 21 });
      t(s, p, x, y + 0.72, w - 0.85, 0.45, { fontSize: 14 });
    });
  }
  {
    const s = slide('BLUE', '01 יסודות', "איפה הבוט שומר מה. מהעבודה שלי באפליקציה. המשל: משרד. נוהל על הקיר, פנקס, לוח מודעות משותף, ספר מתכונים, יומן, מחשב משרדי, כספת, ארון תיקיות.");
    chrome(s, 'WHERE IT REMEMBERS');
    head(s, 'כל מידע במקום שלו', 'איפה הבוט ', 'שומר מה');
    const cards = [
      ['notebook-pen', 'הוראות', 'תפקיד וכללים. רואה בכל הודעה'],
      ['brain', 'זיכרון הבוט', 'עובדות שלמד. נשאר אחרי ניקוי'],
      ['users', 'זיכרון משותף', 'שם וסגנון. כל הבוטים רואים'],
      ['book-open', 'סקילים', 'מתכון למשימה. כל בוט יכול'],
      ['calendar-clock', 'שגרות', 'רצות לבד. בלשונית Details'],
      ['monitor', 'המחשב', 'קבצים והתחברויות. משותף לכולם'],
      ['vault', 'כספת', 'סיסמאות, כרטיסים, פרטי קשר'],
      ['folder-open', 'דרייב ו-Library', 'קבצים, דפים ותבניות'],
    ];
    const w = 2.73, h = 1.75;
    cards.forEach(([ic, h3, p], i) => {
      const col = i % 4, row = Math.floor(i / 4);
      const x = X1 - w - col * (w + 0.3), y = 2.42 + row * (h + 0.22);
      card(s, x, y, w, h);
      tile(s, ic, x + w - 0.75, y + 0.22, 0.5, TILES[i % 5]);
      t(s, h3, x + 0.22, y + 0.82, w - 0.44, 0.4, { fontFace: H, fontSize: 18 });
      t(s, p, x + 0.22, y + 1.2, w - 0.44, 0.5, { fontSize: 13 });
    });
    rr(s, X1 - 7.4, 6.3, 7.4, 0.45, C.pink, null, 0.04);
    t(s, 'כללים בהוראות · עובדות בזיכרון · קבצים בדרייב', X1 - 7.4, 6.3, 7.4, 0.45, { align: 'center', valign: 'middle', bold: true, fontSize: 15 });
  }
  {
    const s = slide('PAPER', '01 יסודות', "רגע קהל: 'איפה שמים אף פעם לא שולחים בלי אישור? הוראות או זיכרון?' תשובה: הוראות.");
    chrome(s, 'MEMORY · 3 COMMANDS');
    head(s, 'אין מסך זיכרון. מדברים איתו.', 'שלוש פקודות ', 'לזיכרון');
    const q = [['"תזכור ש..."', 'שומר עובדה, גם אחרי שמנקים את הצ\'אט'], ['"מה אתה זוכר עליי?"', 'ככה בודקים מה נשמר'], ['"תשכח ש..."', 'מוחק משהו שנשמר לא נכון']];
    q.forEach(([h, p], i) => {
      const w = 3.71, x = X1 - w - i * (w + 0.35), y = 2.5;
      rr(s, x, y, w, 2.35, i === 1 ? C.tLilac : C.white, i === 1 ? 'D8C8E3' : C.line, 0.22);
      t(s, '“', x + 0.3, y + 0.05, w - 0.6, 0.7, { fontFace: 'Georgia', fontSize: 48, color: C.purple, rtlMode: false, align: 'right' });
      t(s, h, x + 0.3, y + 0.8, w - 0.6, 0.55, { fontFace: H, fontSize: 22 });
      t(s, p, x + 0.3, y + 1.4, w - 0.6, 0.7, { fontSize: 14 });
    });
    tip(s, X0, 5.2, CW, 1.35, 'חשוב', 'כלל כמו "אף פעם לא שולחים בלי אישור" שייך [להוראות], לא לזיכרון. שם הבוט רואה אותו בכל הודעה.', { fill: C.blue });
    t(s, 'שאלה לקהל: הוראות או זיכרון?', X0, 6.62, CW, 0.3, { fontSize: 12, color: C.muted });
  }
  {
    const s = slide('BLUE', '01 יסודות', "הסדר: קודם ידני ומתקנים, אחר כך סקיל, ורק אז שגרה. Teach a task: מקליטים את עצמכם בדפדפן של הבוט, עד 10 דקות. דמו 3 דק'.");
    chrome(s, 'SKILLS · ROUTINES · TEACH A TASK');
    head(s, 'ידני ← סקיל ← שגרה', 'איך משימה הופכת ', 'לחוזרת');
    const st = [[C.paper, 'MANUAL', 'ידני', 'עושים בצ\'אט, ומתקנים עד שזה טוב'], [C.white, 'SKILL', 'סקיל', '"שמור את מה שעשינו כסקיל בשם..."'], [C.pink, 'ROUTINE', 'שגרה', 'רץ לבד לפי שעה או אירוע. Test run קודם']];
    st.forEach(([f, e, h, p], i) => {
      const w = 3.4, x = X1 - w - i * (w + 0.81), y = 2.45;
      box(s, x, y, w, 1.95, f);
      en(s, e, x + 0.3, y + 0.22, w - 0.6, 0.3, { align: 'right', fontSize: 11, bold: true, charSpacing: 2 });
      t(s, h, x + 0.3, y + 0.52, w - 0.6, 0.6, { fontFace: H, fontSize: 30 });
      t(s, p, x + 0.3, y + 1.18, w - 0.6, 0.7, { fontSize: 14 });
      if (i < 2) arrow(s, x - 0.81, y + 0.72, 0.81, 0.5);
    });
    card(s, X1 - 6.9, 4.75, 6.9, 1.95);
    tile(s, 'video', X1 - 0.95, 5.0, 0.62, C.tLilac);
    t(s, 'Teach a task: מראים פעם אחת', X1 - 6.65, 4.95, 5.5, 0.5, { fontFace: H, fontSize: 21 });
    t(s, 'מקליטים את עצמכם בדפדפן של הבוט, עד 10 דקות, והוא הופך את זה לסקיל.', X1 - 6.65, 5.5, 5.5, 0.9, { fontSize: 14 });
    tip(s, X0, 4.75, 4.6, 1.95, 'טיפ', 'עשיתם משהו פעמיים? זה סקיל. עבד שבוע בלי תיקונים? זו שגרה.');
  }
  {
    const s = slide('PAPER', '01 יסודות', "הבוט עובד מהר ובביטחון, ולפעמים טועה. ג'וניור מעולה, לא מנכ\"ל.");
    chrome(s, 'CAN · WAITS · NEVER');
    head(s, 'שלוש רמות', 'מה מותר לו, ', 'ומה לא');
    const cols = [
      [C.white, C.ink, 'check', C.tMint, 'לבד', ['קורא, חוקר וגולש', 'מסכם ומנסח טיוטות', 'מכין קבצים', 'רץ לפי שעה']],
      [C.pink, C.ink, 'hand', C.white, 'מחכה לאישור', ['שולח ומפרסם', 'מגיב וקונה', 'משלם ומוחק', 'משתמש בכלי מחובר']],
      [C.ink, C.white, 'ban', C.pink, 'לא נותנים לו', ['חשבון בנק', 'פרטי ילדים', "סיסמה בצ'אט", 'מחשב עם חשבונות רגישים']],
    ];
    cols.forEach(([f, col, ic, tb, h, list], i) => {
      const w = 3.71, x = X1 - w - i * (w + 0.35), y = 2.45;
      if (i === 0) card(s, x, y, w, 3.25); else box(s, x, y, w, 3.25, f);
      tile(s, ic, x + w - 0.88, y + 0.28, 0.58, tb);
      t(s, h, x + 0.3, y + 0.32, w - 1.3, 0.5, { fontFace: H, fontSize: 24, color: col });
      t(s, list.map((it, k) => ({ text: it, options: { breakLine: k < list.length - 1 } })), x + 0.3, y + 1.15, w - 0.6, 1.95,
        { fontSize: 15, color: col, paraSpaceAfter: 6, lineSpacingMultiple: 1.25 });
    });
    t(s, [{ text: 'העיקרון: ', options: {} }, { text: 'הסוכן מכין, אתם מחליטים.', options: { color: C.purple } }], X1 - 8, 5.98, 8, 0.6, { fontFace: H, fontSize: 26 });
    t(s, "ג'וניור מעולה, לא מנכ\"ל", X0, 6.08, 3.6, 0.4, { fontSize: 14, color: C.muted, align: 'left' });
  }
  {
    const s = slide('BLUE', '01 יסודות', 'שתי שכבות. משפט בהוראות יכול לפספס, כלל Ask first תמיד עוצר. Settings > General > Custom Rules, מתחת למתג Auto Review.');
    chrome(s, 'LIMITS · TWO LAYERS');
    head(s, 'רך + קשיח', 'שום דבר שעולה כסף ', 'לא רץ לבד');
    prompt(s, X1 - 5.75, 2.42, 5.75, 2.5, 'שכבה 1 · שורה בהוראות של כל בוט', 'אף פעם אל תפרסם, תשלח, תמחק או תקנה בלי אישור מפורש שלי.', { size: 16 });
    prompt(s, X0, 2.42, 5.75, 2.5, 'שכבה 2 · Settings › General › Custom Rules', 'Ask first before anything that costs money or credits, and before using any connected app.', { size: 15, ltr: true });
    const hab = [['hand', 'לא לוחצים Always allow על כסף'], ['credit-card', 'שבוע ראשון בלי כרטיס בכספת'], ['gauge', 'On-demand כבוי, או תקרה חודשית']];
    hab.forEach(([ic, p], i) => {
      const w = 3.71, x = X1 - w - i * (w + 0.35), y = 5.25;
      card(s, x, y, w, 1.4, C.paper, null);
      tile(s, ic, x + w - 0.85, y + 0.4, 0.58, TILES[i]);
      t(s, p, x + 0.25, y + 0.25, w - 1.25, 0.9, { fontSize: 15, bold: true, valign: 'middle' });
    });
  }

  // ───────────── 02 מי אני
  section('02 מי אני');
  await ctx.divider('02 מי אני', '02', 'מי אני', 'קודם מחליטים מה חשוב. אחר כך מלמדים את הסוכן.', '3 BIG STONES', IMG + 'shelly-portrait-blue.jpg',
    { blue: true, notes: '20–45 · מי אני. סוכן בלי כיוון מייצר עוד ועוד תוכן שלא מקדם אתכם.' });
  {
    const s = slide('PAPER', '02 מי אני', "דף עבודה, 8 דקות כתיבה. הסוכן לא מציע מחירים ללקוחות. 'האבנים הן שלכם. הסוכן רק שומר שלא תתפזרו.'");
    chrome(s, '3 BIG STONES');
    head(s, '20–35', 'האבנים שלכם. ', 'הסוכן שומר עליהן.');
    const rows = [['01', '3 אבנים גדולות', 'מה שלא נשען עליהן, הסוכן לא עושה'], ['02', 'חזון ומקצוע', 'מה אני עושה, ולמי'], ['03', 'ערך מול מתחרים', '3 דברים שאצלי טובים יותר'], ['04', 'מחירון', 'הקשר בלבד. לא מציע מחירים']];
    const x = 6.75, w = X1 - x;
    rows.forEach(([n, h, p], i) => {
      const y = 2.45 + i * 1.03;
      hline(s, x, y, w);
      numPill(s, n, X1 - 0.62, y + 0.2);
      t(s, h, x, y + 0.12, w - 0.85, 0.45, { fontFace: H, fontSize: 21 });
      t(s, p, x, y + 0.56, w - 0.85, 0.4, { fontSize: 14 });
    });
    prompt(s, X0, 2.45, 5.65, 4.15, 'פרומפט · מתחרים', "תמצא 5 מתחרים שלי ב[תחום + אזור]. טבלה: מה מוכרים, מחיר אם יש, טון, מה חזק ומה חסר. קישור לכל נתון. בסוף, 3 ניסוחים ל\"רק אצלי תקבלו...\". מה שאין לו מקור: 'לא אומת'.", { size: 15 });
  }
  {
    const s = slide('BLUE', '02 מי אני', "4 דרכים, ובוחרים מה שנוח. אחרי כל דרך: 'תגיד לי במילים שלך מה הבנת עליי'. דמו 4 דק'.");
    chrome(s, 'TEACH IT ABOUT YOU');
    head(s, '35–45', '4 דרכים ללמד ', 'מי אתם');
    const ways = [['mic-vocal', 'לדבר', 'שיחה קולית'], ['type', 'להכתיב', 'טקסט ארוך'], ['copy', 'להדביק', 'דף 3 האבנים'], ['search', 'לסרוק', 'מה כתוב עליכם ברשת']];
    ways.forEach(([ic, h, p], i) => {
      const w = 2.73, x = X1 - w - i * (w + 0.3), y = 2.45;
      card(s, x, y, w, 2.2);
      tile(s, ic, x + w - 1.0, y + 0.3, 0.72, TILES[i]);
      t(s, h, x + 0.25, y + 1.15, w - 0.5, 0.5, { fontFace: H, fontSize: 24 });
      t(s, p, x + 0.25, y + 1.65, w - 0.5, 0.4, { fontSize: 14 });
    });
    prompt(s, X0 + 1.6, 4.95, CW - 1.6, 1.75, 'קובץ "מי אני" חי · כלל קבוע להוראות', 'כל פעם שאני מתקנת אותך, תעדכן את "מי אני" ותגיד לי מה שינית.', { size: 16 });
    robot(s, 'content', X0 - 0.05, 5.15, 1.45);
  }
  {
    const s = slide('PINK', '02 מי אני', "תרגיל 1 · 8 דק'. עוזר ההוראה (1 לכל 12) עובר בין החדרים.");
    chrome(s, 'EXERCISE 01 · 8 MIN');
    head(s, 'תרגיל 01 · 8 דקות', 'תכתבו את ', '3 האבנים');
    card(s, X0, 2.45, 3.6, 3.5, C.white, C.ink);
    en(s, "8'", X0, 2.75, 3.6, 2.0, { align: 'center', fontSize: 120, bold: true, color: C.purple });
    t(s, 'דקות כתיבה', X0, 4.85, 3.6, 0.5, { align: 'center', fontSize: 16, bold: true });
    const steps = ['3 עמודי תווך: על מה הכל נשען', 'חזון ומקצוע: מה אתם עושים, ולמי', '3 דברים שאצלכם טובים יותר', 'מדביקים לבוט: "מה הבנת עליי?"', 'מתקנים פרט אחד'];
    const x = 4.95, w = X1 - x;
    steps.forEach((p, i) => {
      const y = 2.45 + i * 0.7;
      hline(s, x, y, w);
      t(s, String(i + 1), X1 - 0.5, y + 0.08, 0.5, 0.55, { fontFace: H, fontSize: 24, color: C.purple });
      t(s, p, x, y + 0.14, w - 0.7, 0.45, { fontSize: 16 });
    });
    btn(s, 'התוצר: קובץ "מי אני" ראשון', X1 - 4.7, 6.08, 4.7);
  }

  // ───────────── 03 תפקיד ועיצוב
  section('03 תפקיד ועיצוב');
  await ctx.divider('03 תפקיד ועיצוב', '03', 'תפקיד ועיצוב', 'איך בונים בוט, מה כותבים לו, ואיך הוא לומד את העיצוב שלכם.', 'ROLE CARD · BRAND · DESIGN SKILL', IMG + 'scene-design.jpg',
    { notes: '45–65 · כרטיס תפקיד ועיצוב.' });
  {
    const s = slide('PAPER', '03 תפקיד ועיצוב', 'איך בונים בוט: New chat > Create new agent > Bot actions > Edit Profile. בוט אחד = תפקיד אחד.');
    chrome(s, 'HOW TO BUILD A BOT');
    head(s, '45–55', 'איך בונים בוט ', 'ב-4 צעדים');
    const st = [['1', 'בוט חדש', 'New chat › Create new agent'], ['2', 'שם ותפקיד', 'Bot actions › Edit Profile'], ['3', 'הוראות', 'כרטיס תפקיד + משפט הרשאה'], ['4', 'משימה אמיתית', 'עם קו סיום ברור']];
    st.forEach(([n, h, p], i) => {
      const w = 2.45, x = X1 - w - i * (w + 0.6), y = 2.5;
      box(s, x, y, w, 2.1, i === 3 ? C.pink : C.white);
      t(s, n, x + 0.25, y + 0.15, w - 0.5, 0.65, { fontFace: H, fontSize: 34, color: C.purple });
      t(s, h, x + 0.25, y + 0.82, w - 0.5, 0.45, { fontFace: H, fontSize: 20 });
      t(s, p, x + 0.25, y + 1.3, w - 0.5, 0.65, { fontSize: 13, rtlMode: i > 1, align: 'right' });
      if (i < 3) arrow(s, x - 0.6, y + 0.8, 0.6, 0.5);
    });
    tip(s, X1 - 6.2, 5.0, 6.2, 1.6, 'טיפ', 'בוט אחד = תפקיד אחד. מוסיפים בוט רק כשיש תפקיד מומחה יציב.');
    card(s, X0 + 1.5, 5.0, 4.0, 1.6);
    t(s, 'קיצור דרך', X0 + 1.75, 5.15, 3.5, 0.42, { fontFace: H, fontSize: 18, color: C.purple });
    t(s, 'dr eggbot שואל כמה שאלות ובונה את הבוט בשבילכם. פרק 05.', X0 + 1.75, 5.6, 3.5, 0.9, { fontSize: 14 });
    robot(s, 'clients', X0 - 0.1, 5.1, 1.4);
  }
  {
    const s = slide('BLUE', '03 תפקיד ועיצוב', "הדוגמה: סוכן סושיאל לסטודיו פילאטיס שכונתי (עסק בדיוני). לא מבטיח תוצאות רפואיות.");
    chrome(s, 'ROLE CARD · 8 FIELDS');
    head(s, 'דוגמה: סטודיו פילאטיס שכונתי', 'כרטיס תפקיד: ', '8 שדות');
    const f = [['תפקיד', 'מנהל הסושיאל של הסטודיו'], ['מי האדם', 'בעלת סטודיו, 12 שנות ניסיון'], ['מטרות', '20 פניות בחודש'], ['3 אבנים', 'קבוצות קטנות · גב · קהילה'], ['מה עושים', '5 פוסטים בשבוע · טיוטת בוקר'], ['סגנון', 'חם, ישיר, בלי "גוף מושלם"'], ['כללים', 'לא מפרסם · לא מבטיח · לא מציע מחיר'], ['כשאין נתונים', 'אומר מה חסר. לא מנחש']];
    const w = 2.73, h = 1.95;
    f.forEach(([lab, ex], i) => {
      const col = i % 4, row = Math.floor(i / 4);
      const x = X1 - w - col * (w + 0.3), y = 2.45 + row * (h + 0.25);
      card(s, x, y, w, h, i === 6 ? C.pink : C.white, i === 6 ? null : C.line);
      t(s, String(i + 1).padStart(2, '0'), x + 0.22, y + 0.15, w - 0.44, 0.45, { fontFace: H, fontSize: 20, color: C.purple });
      t(s, lab, x + 0.22, y + 0.6, w - 0.44, 0.42, { fontFace: H, fontSize: 19 });
      t(s, ex, x + 0.22, y + 1.05, w - 0.44, 0.8, { fontSize: 14 });
    });
  }
  {
    const s = slide('PAPER', '03 תפקיד ועיצוב', 'שני משפטים שנכנסים לכל כרטיס. להעתיק כמו שזה.');
    chrome(s, 'WHAT YOU WRITE');
    head(s, 'להעתיק כמו שזה', 'שני משפטים ', 'לכל בוט');
    prompt(s, X0, 2.42, CW, 2.1, 'הרשאה · לכל בוט', 'אף פעם אל תפרסם, תשלח, תמחק או תקנה בלי אישור מפורש שלי. לפני פעולה כזו תראה לי רשימה ממוספרת ותחכה. אם אתר דורש התחברות, עצור ותעביר את השלב אליי.', { size: 16 });
    prompt(s, X0, 4.75, CW, 1.85, 'כלל סושיאל · לכל בוט סושיאל', 'ברשתות החברתיות אתה רק קורא ומציע. אתה לא לוחץ לייק, לא מגיב, לא שולח הודעה ולא מפרסם.', { size: 16 });
  }
  {
    const s = slide('BLUE', '03 תפקיד ועיצוב', "5 דרכים, ומספיקה אחת. Canva דרך תוסף (תבניות מותג רק ב-Enterprise). סוגרים: 'שמור את כל כללי העיצוב כסקיל בשם העיצוב שלי'.");
    chrome(s, 'TEACH IT YOUR DESIGN');
    head(s, '55–65', 'ללמד את הסוכן ', 'את העיצוב שלכם');
    card(s, X1 - 6.1, 2.42, 6.1, 4.3);
    t(s, "צ'קליסט בוק מותג", X1 - 5.85, 2.6, 5.6, 0.45, { fontFace: H, fontSize: 21 });
    checks(s, ['לוגו בהיר וכהה', '2–3 צבעים עם קודים', '2 גופנים', 'סגנון תמונות', '3–5 דוגמאות "ככה כן"', '2 דוגמאות "ככה לא"', 'טון בשלוש מילים', '4:5 לפיד, 9:16 לסטורי'],
      X1 - 5.85, 3.15, 5.6, 3.45, { size: 15, gap: 5 });
    const side = [['images', 'מצרפים מה שיש', 'קרוסלה שאוהבים · 3–5 עיצובים · Canva'], ['book-open', 'שומרים כסקיל', '"שמור את כל כללי העיצוב כסקיל בשם \'העיצוב שלי\'"']];
    side.forEach(([ic, h, p], i) => {
      const x = X0, w = 5.35, y = 2.42 + i * 1.5;
      card(s, x, y, w, 1.35);
      tile(s, ic, x + w - 0.85, y + 0.3, 0.58, TILES[i + 2]);
      t(s, h, x + 0.25, y + 0.18, w - 1.25, 0.42, { fontFace: H, fontSize: 19 });
      t(s, p, x + 0.25, y + 0.62, w - 1.25, 0.65, { fontSize: 14 });
    });
    tip(s, X0, 5.42, 5.35, 1.3, 'טיפ', 'טקסט בעברית מוסיפים בעיצוב, לא בתוך תמונה שנוצרה.');
  }
  {
    const s = slide('PAPER', '03 תפקיד ועיצוב', "מצגות ועיצובים, שלב 1. טיפ מהשטח: המחשב של הבוט עלה אצלי ריק והקבצים נעלמו. עובדים בתיקיית workspace, תוצר סופי מצורף לשיחה, עיצוב מאושר עותק ל-Drive. מחשב נתקע: Recover, אחר כך Update. Reset רק כמוצא אחרון.");
    chrome(s, 'PRESENTATIONS & DESIGNS · PHASE 1');
    head(s, 'מצגות ועיצובים', 'מהבוק ', 'לתוצר');
    const nodes = [['בוק מותג', 'הצבעים, הגופנים והדוגמאות'], ['סקיל "העיצוב שלי"', 'הכללים, שמורים'], ['תוצר', 'מצגת · קרוסלה · דף נחיתה'], ['אתם מאשרים', 'ועותק לדרייב']];
    nodes.forEach(([h, p], i) => {
      const w = 2.45, x = X1 - w - i * (w + 0.6), y = 2.45;
      box(s, x, y, w, 1.25, i === 3 ? C.pink : C.white);
      t(s, h, x + 0.2, y + 0.15, w - 0.4, 0.45, { fontFace: H, fontSize: 18, align: 'center' });
      t(s, p, x + 0.2, y + 0.65, w - 0.4, 0.5, { fontSize: 13, align: 'center' });
      if (i < 3) arrow(s, x - 0.6, y + 0.38, 0.6, 0.5);
    });
    prompt(s, X0, 4.0, 6.75, 2.7, 'פרומפט · מצגת', "תבנה מצגת של 10 שקפים על [נושא] לפי הסקיל 'העיצוב שלי'. כותרת גדולה ותרשים אחד בכל שקף. תראה לי לפני שאתה ממשיך.", { size: 16 });
    tip(s, 7.85, 4.0, X1 - 7.85, 2.7, 'מהשטח', 'המחשב של הבוט הוא שולחן עבודה, לא ארכיון. אישרתם עיצוב? עותק לדרייב. נתקע? Recover ואז Update. Reset רק כמוצא אחרון.');
  }
  {
    const s = slide('BLUE', '03 תפקיד ועיצוב', "חדש: סקיל שלומד מצגת או עיצוב שכבר יש לכם, ומייצר לבד. מעלים דוגמאות, הבוט מנתח ובונה תבנית + SKILL.md, ריצת בדיקה, ותיקונים שנכנסים לסקיל.");
    chrome(s, 'DESIGN SKILL THAT LEARNS');
    head(s, 'מצגת או עיצוב שכבר יש לכם ← סקיל שמייצר לבד', 'סקיל שלומד ', 'עיצוב קיים');
    const st = [['01', 'מעלים דוגמאות', '3–5 שקפים או עיצובים: PPTX, PDF או צילומי מסך'], ['02', 'הבוט מנתח', 'צבעים, גופנים, גריד, סוגי שקפים וטון'], ['03', 'בונה סקיל', 'SKILL.md, תבנית ודוגמאות'], ['04', 'ריצת בדיקה', 'תוכן חדש, אותו עיצוב'], ['05', 'מתקנים', '"תעדכן את הסקיל עם התיקון"']];
    st.forEach(([n, h, p], i) => {
      const w = 2.1, x = X1 - w - i * (w + 0.33), y = 2.45;
      box(s, x, y, w, 1.95, i === 4 ? C.pink : C.white);
      en(s, n, x + 0.2, y + 0.15, w - 0.4, 0.42, { align: 'right', fontFace: H, fontSize: 20, color: C.purple });
      t(s, h, x + 0.2, y + 0.58, w - 0.4, 0.42, { fontFace: H, fontSize: 17 });
      t(s, p, x + 0.2, y + 1.0, w - 0.4, 0.88, { fontSize: 12.5 });
      if (i < 4) arrow(s, x - 0.33, y + 0.72, 0.33, 0.5);
    });
    prompt(s, X0, 4.7, CW, 2.0, 'פרומפט · לבנות את הסקיל', "מצורפות [3 מצגות] שלי. תנתח את מערכת העיצוב: צבעים עם קודים, גופנים, גריד וסוגי שקפים. תכתוב סקיל בשם [המצגת שלי] עם תבנית ודוגמאות, ותבנה מצגת בדיקה על [נושא]. תראה לי לפני ששומרים.", { size: 15 });
  }
  {
    const s = slide('PAPER', '03 תפקיד ועיצוב', 'הלולאה: כל תיקון שלכם נכנס לסקיל, והגרסה הבאה כבר יודעת. מהשטח: המצגת הזו נבנתה ככה, מהאתר של הסדנה.');
    chrome(s, 'THE LEARNING LOOP');
    head(s, 'כל תיקון נשמר', 'ככה הסקיל ', 'לומד לבד');
    const loop = [[3.95, 2.5, 'מייצר', 'מצגת חדשה לפי הסקיל', C.white], [0.75, 2.5, 'אתם מתקנים', '"הכותרת גדולה מדי"', C.white], [0.75, 4.6, '"תעדכן את הסקיל"', 'התיקון נכנס לכללים', C.pink], [3.95, 4.6, 'גרסה הבאה', 'כבר יודעת', C.tLilac]];
    loop.forEach(([x, y, h, p, f]) => {
      card(s, x, y, 2.4, 1.3, f, f === C.white ? C.line : null);
      t(s, h, x + 0.15, y + 0.2, 2.1, 0.45, { fontFace: H, fontSize: 18, align: 'center' });
      t(s, p, x + 0.15, y + 0.7, 2.1, 0.45, { fontSize: 13, align: 'center' });
    });
    t(s, '←', 3.15, 2.9, 0.8, 0.5, { align: 'center', fontSize: 24, color: C.purple, bold: true });
    t(s, '↓', 1.6, 3.85, 0.7, 0.7, { align: 'center', fontSize: 24, color: C.purple, bold: true });
    t(s, '→', 3.15, 5.0, 0.8, 0.5, { align: 'center', fontSize: 24, color: C.purple, bold: true });
    t(s, '↑', 4.8, 3.85, 0.7, 0.7, { align: 'center', fontSize: 24, color: C.purple, bold: true });
    t(s, 'מה יש בתיקיית הסקיל', 6.9, 2.45, X1 - 6.9, 0.45, { fontFace: H, fontSize: 21 });
    const rows = [['file-pen', 'SKILL.md', 'מתי משתמשים בו, ומה הכללים'], ['layout-template', 'תבנית', 'PPTX או HTML עם הצבעים והגופנים'], ['images', 'דוגמאות', 'ככה כן, וככה לא'], ['list-checks', "צ'קליסט בדיקה", 'מה בודקים לפני שמראים לכם']];
    rows.forEach(([ic, h, p], i) => {
      const x = 6.9, w = X1 - x, y = 3.0 + i * 0.8;
      hline(s, x, y, w, C.line, 0.5);
      tile(s, ic, X1 - 0.52, y + 0.13, 0.52, TILES[i]);
      t(s, h, X1 - 2.6, y + 0.15, 1.95, 0.5, { fontFace: H, fontSize: 17, valign: 'middle' });
      t(s, p, x, y + 0.15, w - 2.75, 0.5, { fontSize: 14, valign: 'middle' });
    });
    t(s, [{ text: 'מהשטח: ', options: { bold: true, color: C.purple } }, { text: 'המצגת הזו נבנתה ככה. מהאתר של הסדנה, למערכת עיצוב, לתבנית PowerPoint שאפשר לערוך.', options: {} }],
      X0, 6.25, CW, 0.45, { fontSize: 14 });
  }

  // ───────────── הפסקה
  section('הפסקה');
  await ctx.divider('הפסקה', "5'", 'הפסקה', 'קמים, שותים מים, וחוזרים לסושיאל.', 'BREAK', IMG + 'scene-break.jpg',
    { blue: true, numSize: 170, notes: '65–70 · הפסקה.' });
};
