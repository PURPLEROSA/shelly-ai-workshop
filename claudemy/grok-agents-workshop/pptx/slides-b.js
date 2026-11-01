// 04 סושיאל · 05 עוד סוכנים (דיוור, אתרים, בוטים מוכנים, ראש מטה) · 06 סקילים · 07 מקימים בלייב · סגירה
const L = require('./lib');
const { C, H, B, X0, X1, CW, t, en, chrome, head, card, box, hline, icon, tile, pill, numPill, checks, btn, arrow, prompt, tip, crop, photo, robot, rr } = L;
const IMG = 'assets/img/';
const TILES = [C.tPink, C.tMint, C.tButter, C.tBlue, C.tLilac];

// horizontal flow of sharp boxes, right to left
function flow(s, steps, y, h, o = {}) {
  const n = steps.length, gap = o.gap || (n > 4 ? 0.33 : 0.6);
  const w = (CW - gap * (n - 1)) / n;
  steps.forEach(([num, h3, p], i) => {
    const x = X1 - w - i * (w + gap);
    box(s, x, y, w, h, (o.pinkLast !== false && i === n - 1) ? C.pink : C.white);
    let yy = y + 0.15;
    if (num) { en(s, num, x + 0.2, yy, w - 0.4, 0.42, { align: 'right', fontFace: H, fontSize: 20, color: C.purple }); yy += 0.43; }
    t(s, h3, x + 0.2, yy, w - 0.4, 0.42, { fontFace: H, fontSize: o.hs || 17 });
    t(s, p, x + 0.2, yy + 0.43, w - 0.4, h - (yy - y) - 0.5, { fontSize: o.ps || 12.5 });
    if (i < n - 1) arrow(s, x - gap, y + h / 2 - 0.25, gap, 0.5);
  });
}
// site-style role card: icon, category, title, "you give", "you get"
function roleCard(s, x, y, w, h, ic, bg, cat, title, give, get) {
  card(s, x, y, w, h);
  tile(s, ic, x + w - 0.72, y + 0.2, 0.48, bg);
  t(s, cat, x + 0.2, y + 0.3, w - 1.05, 0.3, { fontSize: 11, color: C.muted, align: 'left' });
  t(s, title, x + 0.22, y + 0.75, w - 0.44, 0.42, { fontFace: H, fontSize: 18 });
  t(s, [{ text: 'אתם נותנים: ', options: { bold: true, color: C.muted } }, { text: give, options: {} }], x + 0.22, y + 1.17, w - 0.44, 0.38, { fontSize: 12 });
  rr(s, x + 0.18, y + h - 0.62, w - 0.36, 0.46, C.pale, C.paleLine, 0.08);
  t(s, [{ text: 'מקבלים: ', options: { color: C.muted } }, { text: get, options: {} }], x + 0.3, y + h - 0.62, w - 0.6, 0.46, { fontSize: 12, bold: true, valign: 'middle' });
}
function table(s, rows, x, y, w, colW, o = {}) {
  // rows: first is header. columns given right-to-left; reversed so the first column sits on the right
  const data = rows.map((r, ri) => r.slice().reverse().map((c, ci) => ({
    text: c, options: {
      fontFace: ri === 0 ? H : B, fontSize: ri === 0 ? 16 : (o.size || 13), bold: ri > 0 && ci === r.length - 1, color: C.ink,
      align: 'right', rtlMode: true, valign: 'middle', fill: { color: ri === 0 ? C.pink : (ri % 2 ? C.white : C.paper) },
      border: [{ type: 'none' }, { type: 'none' }, { pt: 0.75, color: C.line }, { type: 'none' }], margin: [0.06, 0.15, 0.06, 0.15],
    },
  })));
  s.addTable(data, { x, y, w, colW: colW.slice().reverse(), rowH: o.rowH || 0.5 });
}

module.exports = async (ctx) => {
  const { slide, section } = ctx;

  // ───────────── 04 סושיאל
  section('04 סושיאל');
  await ctx.divider('04 סושיאל', '04', 'סוכן סושיאל', 'מחברים, קוראים, מציעים. ואתם מפרסמים.', 'INSTAGRAM · SAFETY', IMG + 'scene-social.jpg',
    { notes: '70–92 · סוכן סושיאל ובטיחות ברשתות.' });
  {
    const s = slide('BLUE', '04 סושיאל', "תוסף (מומלץ): Connect apps > Postiz או Composio, חשבון Business/Creator. הדפדפן של הבוט: לקריאה בלבד. אחרי שבוע של טיוטות טובות: 'שמור כסקיל פוסט בוקר', ורק אז שגרה. דמו 8 דק'.");
    chrome(s, 'INSTAGRAM AGENT');
    head(s, '70–85', 'מחברים, קוראים, ', 'מציעים');
    box(s, X0, 2.45, 5.2, 2.0, C.pink);
    t(s, 'תוסף · מומלץ', X0 + 0.3, 2.62, 4.6, 0.45, { fontFace: H, fontSize: 21 });
    t(s, 'Postiz או Composio, דרך Connect apps. חשבון Business או Creator.', X0 + 0.3, 3.12, 4.6, 1.2, { fontSize: 15 });
    box(s, X0, 4.7, 5.2, 2.0, C.white);
    t(s, 'הדפדפן של הבוט', X0 + 0.3, 4.87, 4.6, 0.45, { fontFace: H, fontSize: 21 });
    t(s, 'לקריאה בלבד. כניסה מהענן עלולה להפעיל בדיקת אבטחה.', X0 + 0.3, 5.37, 4.6, 1.2, { fontSize: 15 });
    const tasks = [['eye', 'קריאת עמוד', 'מה עבד, ובאיזה טון'], ['pen-line', 'ביו', '3 גרסאות, עד 150 תווים'], ['radar', 'טרנדים', '5 נושאים, ולכל אחד מקור'], ['sunrise', 'פוסט בוקר', 'טיוטה ב-7:30, לאישור שלכם']];
    const x = 6.45, w = X1 - x;
    tasks.forEach(([ic, h, p], i) => {
      const y = 2.45 + i * 1.07;
      hline(s, x, y, w);
      tile(s, ic, X1 - 0.62, y + 0.22, 0.62, TILES[i]);
      t(s, h, x, y + 0.18, w - 0.85, 0.45, { fontFace: H, fontSize: 21 });
      t(s, p, x, y + 0.62, w - 0.85, 0.38, { fontSize: 14 });
    });
  }
  {
    const s = slide('PAPER', '04 סושיאל', 'הסיפור שלי, 2 דק\', בגוף ראשון. כניסות ממחשב בענן מכתובת לא מוכרת נראות כמו פריצה. הרשתות מזהות התנהגות אוטומטית.');
    chrome(s, 'SOCIAL SAFETY · MY STORY');
    head(s, '85–92 · מהשטח', 'הבוט פרסם סטורי. ', 'אינסטגרם חסם.');
    rr(s, X0, 2.45, 5.3, 4.25, C.tLilac, 'D8C8E3', 0.25);
    t(s, '“', X0 + 0.35, 2.5, 4.6, 0.8, { fontFace: 'Georgia', fontSize: 60, color: C.purple, rtlMode: false });
    t(s, 'נתתי לבוט להיכנס לאינסטגרם מהדפדפן שלו. הוא פרסם סטורי, ואינסטגרם חסם את החשבון.', X0 + 0.35, 3.3, 4.6, 1.7, { fontSize: 21, bold: true, lineSpacingMultiple: 1.3 });
    t(s, 'כניסה ממחשב בענן, מכתובת זרה, נראית לרשת כמו פריצה.', X0 + 0.35, 5.15, 4.6, 0.9, { fontSize: 15 });
    t(s, 'שלי, אוקטובר 2026', X0 + 0.35, 6.2, 4.6, 0.3, { fontSize: 12, color: C.muted });
    const rules = [['תוסף לפני דפדפן', 'הרשאה רשמית בטוחה יותר מלחיצה על כפתורים'], ['מתחברים בעצמכם, פעם אחת', 'ואימות דו-שלבי פעיל'], ['קצב של בן אדם', 'בלי עשרות פעולות ברצף'], ['טיוטה קודם', 'הבוט מכין, אתם מפרסמים']];
    const x = 6.55, w = X1 - x;
    rules.forEach(([h, p], i) => {
      const y = 2.45 + i * 1.07;
      hline(s, x, y, w);
      t(s, String(i + 1), X1 - 0.5, y + 0.12, 0.5, 0.6, { fontFace: H, fontSize: 28, color: C.purple });
      t(s, h, x, y + 0.17, w - 0.75, 0.45, { fontFace: H, fontSize: 21 });
      t(s, p, x, y + 0.62, w - 0.75, 0.38, { fontSize: 14 });
    });
  }
  {
    const s = slide('BLUE', '04 סושיאל', "הכספת: Settings > Vault. Reset ו-Update יכולים למחוק סיסמאות שנכתבו בקבצים. לאן הולך המידע: לשרתים של Cursor, מחשב נפרד לכל משתמש. לא להגיד 'הכל מוצפן ולא נשלח'.");
    chrome(s, 'VAULT · PASSWORDS & CARDS');
    head(s, 'Settings › Vault', 'איפה שמים ', 'סיסמאות וכרטיסים');
    table(s, [['מה שומרים', 'מה הבוט רואה', 'מתי עוצר ושואל'], ['התחברויות', 'שהחשבון קיים, בלי הסיסמה', 'לא מתואר אישור לפני כניסה'], ['כרטיס אשראי', '4 ספרות אחרונות', 'לפני כל שימוש בקופה'], ['פרטי קשר', 'הכל', 'ממלא לבד משלוח וחיוב']],
      X0, 2.45, CW, [3.2, 4.3, 4.33], { rowH: 0.62, size: 15 });
    const r = [['vault', "סיסמה לא בצ'אט ולא בקובץ"], ['credit-card', 'שבוע ראשון בלי כרטיס'], ['laptop', 'המחשב שלכם: Never allow']];
    r.forEach(([ic, p], i) => {
      const w = 3.71, x = X1 - w - i * (w + 0.35), y = 5.4;
      card(s, x, y, w, 1.25);
      tile(s, ic, x + w - 0.83, y + 0.33, 0.58, TILES[i]);
      t(s, [{ text: 'כלל: ', options: { color: C.purple } }, { text: p, options: {} }], x + 0.25, y + 0.2, w - 1.2, 0.85, { fontSize: 15, bold: true, valign: 'middle' });
    });
  }

  // ───────────── 05 עוד סוכנים
  section('05 עוד סוכנים');
  await ctx.divider('05 עוד סוכנים', '05', 'עוד סוכנים', 'לידים, דיוור, אתרים, בוטים מוכנים, וצוות עם ראש מטה.', 'LEADS · NEWSLETTER · WEBSITES · TEAM', IMG + 'mini-agent-clients.png',
    { blue: true, notes: '92–105 · עוד סוכנים. ערב 1: משפך הלידים והגלריה. ערב 2: דיוור, אתרים, ראש מטה.' });
  {
    const s = slide('PAPER', '05 עוד סוכנים', "ורוד = הרגעים שאתם פועלים בהם. כל השאר הבוט מכין. חשבוניות: קריאה בלבד, חשבון נפרד.");
    chrome(s, 'FROM COMMENT TO LEAD');
    head(s, '92–100', 'מתגובה ', 'לליד');
    const st = [['פוסט עם מילה', 'הבוט מנסח, אתם מפרסמים', 1], ['מי הגיב', 'הבוט אוסף לרשימה', 0], ['קישור בפרטי', 'אתם שולחים', 1], ['דף נחיתה', 'לפי "העיצוב שלי"', 0], ['טבלת לידים', 'Google Sheet', 0], ['מייל אישור', 'נוסח מאושר, ואז שגרה', 1]];
    st.forEach(([h, p, you], i) => {
      const col = i % 3, row = Math.floor(i / 3), w = 3.4, x = X1 - w - col * (w + 0.81), y = 2.45 + row * 1.6;
      box(s, x, y, w, 1.3, you ? C.pink : C.white);
      t(s, String(i + 1), X1 - w - col * (w + 0.81) + w - 0.55, y + 0.18, 0.4, 0.5, { fontFace: H, fontSize: 24, color: C.purple });
      t(s, h, x + 0.25, y + 0.2, w - 0.9, 0.45, { fontFace: H, fontSize: 19 });
      t(s, p, x + 0.25, y + 0.7, w - 0.9, 0.45, { fontSize: 14 });
      if (col < 2) arrow(s, x - 0.81, y + 0.4, 0.81, 0.5);
    });
    tip(s, X0, 5.75, CW, 0.98, 'חשבוניות', 'הבוט מסדר בטבלה ושומר בתיקייה. קריאה בלבד: לא משלם, לא מוחק, לא מעביר.', { fill: C.blue });
  }
  {
    const s = slide('BLUE', '05 עוד סוכנים', "איך מייצרים דיוור במייל. עובדה מהעזרה של Grok Bot: מייל שנכתב בשגרה מחכה כטיוטה עד שלוחצים Send. רשימה גדולה: שירות דיוור, לא Gmail (מגבלות שליחה וסיכון ספאם). חוק הספאם: רק למי שאישר, וקישור הסרה.");
    chrome(s, 'EMAIL NEWSLETTER');
    head(s, 'מחומרים של השבוע לטיוטה מוכנה', 'איך מייצרים ', 'דיוור במייל');
    flow(s, [['01', 'חומרים', '3 דברים מהשבוע: קישורים, תמונות, הערות'], ['02', 'סקיל "ניוזלטר"', 'מבנה קבוע, הקול שלכם והעיצוב שלכם'], ['03', 'טיוטה', 'כותרת, 3 פריטים קצרים, הנעה אחת לפעולה'], ['04', 'אתם קוראים', 'ומתקנים במשפט'], ['05', 'אתם שולחים', 'לוחצים Send, או מתזמנים']], 2.45, 1.9);
    const opts = [['mail', 'רשימה קטנה', 'עשרות נמענים: טיוטה ב-Gmail, ואתם שולחים.'], ['send', 'רשימה גדולה', 'שירות דיוור (Mailchimp, Brevo, Beehiiv): הבוט מכין טקסט ו-HTML, אתם מדביקים ומתזמנים.'], ['shield-check', 'החוק', 'רק למי שאישר לקבל, וקישור הסרה בכל מייל.']];
    opts.forEach(([ic, h, p], i) => {
      const w = 3.71, x = X1 - w - i * (w + 0.35), y = 4.7;
      card(s, x, y, w, 2.0, i === 2 ? C.paper : C.white);
      tile(s, ic, x + w - 0.83, y + 0.25, 0.58, TILES[i + 1]);
      t(s, h, x + 0.25, y + 0.3, w - 1.2, 0.45, { fontFace: H, fontSize: 20 });
      t(s, p, x + 0.25, y + 0.95, w - 0.5, 0.95, { fontSize: 14 });
    });
  }
  {
    const s = slide('PAPER', '05 עוד סוכנים', "השגרה מכינה, אתם שולחים. קודם עושים פעם אחת בצ'אט, מתקנים, ורק אז 'שמור כסקיל' ושגרה.");
    chrome(s, 'NEWSLETTER ROUTINE');
    head(s, 'סקיל + שגרה', 'השגרה מכינה. ', 'אתם שולחים.');
    prompt(s, X0, 2.45, 6.1, 4.25, 'פרומפט · ניוזלטר ראשון', "תכין ניוזלטר ל[שם העסק] מהחומרים בתיקייה [ניוזלטר]: כותרת, 3 פריטים קצרים בקול שלי, והנעה אחת לפעולה. תשמור כטיוטה ב-Gmail ואל תשלח. אחרי שאאשר, תשמור את התהליך כסקיל 'ניוזלטר שבועי'.", { size: 16 });
    const rows = [['calendar-clock', 'חמישי 09:00', 'שגרה מכינה טיוטה מהסקיל'], ['mail', 'טיוטה, לא שליחה', 'מייל שנכתב בשגרה מחכה עד שלוחצים Send'], ['list-todo', 'נרשמים', 'Google Sheet שמתמלא מדף הנחיתה'], ['repeat', 'כל תיקון', '"תעדכן את הסקיל". הגיליון הבא כבר יודע']];
    const x = 7.2, w = X1 - x;
    rows.forEach(([ic, h, p], i) => {
      const y = 2.45 + i * 1.07;
      hline(s, x, y, w);
      tile(s, ic, X1 - 0.6, y + 0.22, 0.6, TILES[i]);
      t(s, h, x, y + 0.18, w - 0.8, 0.45, { fontFace: H, fontSize: 20 });
      t(s, p, x, y + 0.62, w - 0.8, 0.38, { fontSize: 14 });
    });
  }
  {
    const s = slide('BLUE', '05 עוד סוכנים', "איך מקימים אתר. הבוט כותב קוד במחשב שלו ובודק בדפדפן שלו. לפני הסדנה לבדוק: אילו שירותי אחסון מופיעים ב-Connect apps (Netlify / Vercel / GitHub). Netlify Drop: גוררים תיקייה ומקבלים כתובת. דומיין עולה כסף: קונים לבד. ל-Grok יש גם מצב בניית אתרים (Build) עם כתובת grok.me, בגישה מוקדמת ובמנוי נפרד, לאמת.");
    chrome(s, 'WEBSITES WITH GROK BOT');
    head(s, 'בלי לכתוב שורת קוד', 'איך מקימים ', 'אתר עם Grok Bot');
    flow(s, [['01', 'בריף', 'מטרה, קהל, עמודים, והסקיל "העיצוב שלי"'], ['02', 'כותב קוד', 'HTML במחשב שלו, בלי שתכתבו שורה'], ['03', 'בודק', 'פותח בדפדפן שלו ושולח צילום מסך'], ['04', 'מתקנים', 'בשיחה, כמו עם מעצב'], ['05', 'עולה לאוויר', 'רק אחרי אישור שלכם']], 2.45, 1.9);
    const opts = [['plug', 'אחסון מחובר', 'מחברים פעם אחת שירות אחסון. הבוט מעלה גרסה חדשה, אתם מאשרים.'], ['upload', 'קובץ שאתם מעלים', 'הבוט נותן תיקייה מוכנה. גוררים ל-Netlify Drop ומקבלים כתובת.'], ['globe', 'דומיין משלכם', 'עולה כסף, אז קונים בעצמכם. הבוט מסביר איך לחבר.']];
    opts.forEach(([ic, h, p], i) => {
      const w = 3.71, x = X1 - w - i * (w + 0.35), y = 4.7;
      card(s, x, y, w, 2.0);
      tile(s, ic, x + w - 0.83, y + 0.25, 0.58, TILES[i + 2]);
      t(s, h, x + 0.25, y + 0.3, w - 1.2, 0.45, { fontFace: H, fontSize: 20 });
      t(s, p, x + 0.25, y + 0.95, w - 0.5, 0.95, { fontSize: 14 });
    });
  }
  {
    const s = slide('PAPER', '05 עוד סוכנים', "מה זה 'מחובר'. Added = הותקן. מחובר = אחרי Authenticate. חיבור לאחסון = הבוט יכול לשנות אתר חי, ולכן Ask first על כל העלאה. מנתקים מאותו מסך, ואפשר גם לבטל הרשאה בשירות עצמו.");
    chrome(s, 'WHAT "CONNECTED" MEANS');
    head(s, 'Connect apps › Authenticate', 'מחובר: ', 'מה זה אומר?');
    card(s, X0, 2.45, 5.3, 4.25, C.white);
    t(s, 'מחובר =', X0 + 0.35, 2.65, 4.6, 0.55, { fontFace: H, fontSize: 26, color: C.purple });
    t(s, 'נתתם לבוט מפתח לחשבון שלכם. הוא פועל בשמכם, עם ההרשאות שלכם.', X0 + 0.35, 3.25, 4.6, 1.1, { fontSize: 18, bold: true, lineSpacingMultiple: 1.25 });
    const nodes = [['אתם', C.pink], ['מפתח', C.white], ['הבוט', C.white], ['החשבון', C.tMint]];
    nodes.forEach(([n, f], i) => {
      const w = 0.95, x = X0 + 5.3 - 0.35 - w - i * (w + 0.22), y = 4.75;
      box(s, x, y, w, 0.75, f);
      t(s, n, x, y, w, 0.75, { align: 'center', valign: 'middle', fontSize: 13, bold: true });
      if (i < 3) t(s, '←', x - 0.22, y + 0.15, 0.22, 0.45, { align: 'center', fontSize: 14, color: C.purple, bold: true });
    });
    t(s, 'Gmail, Calendar, Canva, Drive, אחסון לאתר', X0 + 0.35, 5.8, 4.6, 0.6, { fontSize: 13, color: C.muted });
    const rows = [['Added זה לא מחובר', 'Added = הותקן. מחובר רק אחרי Authenticate.'], ['פועל בשמכם', 'אתר מחובר = הבוט יכול לשנות אתר חי. Ask first על כל העלאה.'], ['מחברים רק מה שצריך', 'כל חיבור זמין לבוטים שלכם. פחות חיבורים, פחות סיכון.'], ['מנתקים בכל רגע', 'מאותו מסך שחיברתם, או בהגדרות של השירות עצמו.']];
    const x = 6.6, w = X1 - x;
    rows.forEach(([h, p], i) => {
      const y = 2.45 + i * 1.07;
      hline(s, x, y, w);
      t(s, String(i + 1), X1 - 0.5, y + 0.12, 0.5, 0.6, { fontFace: H, fontSize: 28, color: C.purple });
      t(s, h, x, y + 0.17, w - 0.75, 0.45, { fontFace: H, fontSize: 20 });
      t(s, p, x, y + 0.62, w - 0.75, 0.4, { fontSize: 14 });
    });
  }
  {
    const s = slide('BLUE', '05 עוד סוכנים', "מזכירה: תדריך בוקר, הבטחות פתוחות במייל. וואטסאפ: אין חיבור רשמי, הבוט מנסח ואתם מדביקים. בוט תקלות: מסביר ומציע, לא מתקן לבד. מוסיפים בוט רק כשיש משימה חוזרת שתקועה.");
    chrome(s, 'MORE AGENTS');
    head(s, '100–105', 'סוכן לכל משימה ', 'שחוזרת ותקועה');
    const cards = [
      ['calendar-check', 'העסק והעבודה', 'מזכירה', 'מייל ויומן', 'תדריך בוקר ומה דורש תשובה'],
      ['users', 'לקוחות', 'לקוחות ומעקב', 'רשימת פניות', 'מי מחכה, וטיוטת מעקב'],
      ['mail', 'תוכן ושיווק', 'דיוור', '3 דברים מהשבוע', 'טיוטת ניוזלטר מוכנה לבדיקה'],
      ['house', 'בית ומשפחה', 'משפחה ויומן', 'הודעות מבית הספר', 'מי, מה, מתי, ומה להביא'],
      ['message-circle', 'לקוחות', 'וואטסאפ', 'שאלה של לקוח', 'ניסוח להדבקה. אין חיבור רשמי'],
      ['wrench', 'העסק והעבודה', 'בוט תקלות', 'מה נתקע', 'הסבר והצעה. לא מתקן לבד'],
    ];
    const w = 3.71, h = 2.1;
    cards.forEach((c, i) => {
      const col = i % 3, row = Math.floor(i / 3);
      roleCard(s, X1 - w - col * (w + 0.35), 2.42 + row * (h + 0.2), w, h, c[0], TILES[i % 5], c[1], c[2], c[3], c[4]);
    });
  }
  {
    const s = slide('PAPER', '05 עוד סוכנים', "בוטים מוכנים מהספרייה (readmultiplex.com/grokbot-rocks ו-x.ai/bot). קישור x.ai/bot מוסיף עותק של המתכון: הוראות, סקילים ושגרות. קוראים לפני שמפעילים. Brian Roemmele בנה את רובם.");
    chrome(s, 'MUST-KNOW BOTS');
    head(s, 'מוסיפים מקישור x.ai/bot', 'בוטים מוכנים ', 'שחייבים להכיר');
    const bots = [
      ['dr eggbot', 'לבנות', 'מעצב לכם בוטים חדים: שואל כמה שאלות ובונה את הבוט'],
      ['Memory Transfer', 'לבנות', 'מביא מה ש-ChatGPT או Claude יודעים עליכם. רק מה שתאשרו'],
      ['Grok Bot Tutorial', 'ללמוד', 'קורס של 20 שיעורים, בתוך הבוט'],
      ['Mission Control', 'לנהל', 'כל בוט מקבל ירוק, צהוב או אדום, ותחזית מכסה'],
      ['Bot Optimizer', 'לנהל', 'מוצא בדיקות מיותרות, לולאות ובוטים כפולים'],
      ['Librarian', 'לנהל', 'מראיין את הבוטים כל שבוע ומוצא הוראות שנשכחו'],
      ["Don't Leave Me Hanging", 'לעבוד', 'מוצא הבטחות פתוחות במייל ומנסח follow-up'],
      ['Tradbot', 'לעבוד', 'מנהל משפחה: טפסים, חשבונות ואישורי הגעה. לא שולח בלעדיכם'],
    ];
    const w = 2.73, h = 1.92, tagFill = { 'לבנות': C.pink, 'ללמוד': C.tButter, 'לנהל': C.tBlue, 'לעבוד': C.tMint };
    bots.forEach(([n, tag, p], i) => {
      const col = i % 4, row = Math.floor(i / 4), x = X1 - w - col * (w + 0.3), y = 2.42 + row * (h + 0.22);
      card(s, x, y, w, h, i === 0 ? C.white : C.white, i === 0 ? C.ink : C.line);
      pill(s, tag, x + w - 0.95, y + 0.2, 0.75, { h: 0.32, fill: tagFill[tag], line: null, size: 11 });
      en(s, n, x + 0.2, y + 0.6, w - 0.4, 0.4, { align: 'right', fontSize: n.length > 16 ? 13 : 15, bold: true });
      t(s, p, x + 0.2, y + 1.02, w - 0.4, 0.8, { fontSize: 12.5 });
    });
    t(s, 'קוראים הוראות, חיבורים ושגרות של כל בוט מוכן לפני שמפעילים.', X0, 6.6, CW, 0.3, { fontSize: 12, color: C.muted });
  }
  {
    const s = slide('BLUE', '05 עוד סוכנים', "dr eggbot (מאת Lauren Tan): 'Designs high-quality Grok Bots. Asks a few preference questions, then creates them with CreateAgent.' אחרי שהוא בונה: עוברים על ההוראות ומוסיפים את משפט ההרשאה.");
    chrome(s, 'DR EGGBOT');
    head(s, 'בוט שבונה בוטים', 'dr eggbot ', 'מעצב לכם בוטים חדים');
    flow(s, [['01', 'שואל', 'כמה שאלות על מה שאתם צריכים ואיך אתם עובדים'], ['02', 'מנסח', 'תפקיד, הוראות וגבולות'], ['03', 'יוצר', 'את הבוט, מוכן בחשבון שלכם'], ['04', 'אתם בודקים', 'קוראים, ומוסיפים משפט הרשאה']], 2.45, 1.75);
    prompt(s, X0 + 1.7, 4.55, CW - 1.7, 2.15, 'פרומפט · ל-dr eggbot', "אני [מאמנת כושר עצמאית]. תבנה לי בוט ש[עונה לפניות ומכין טיוטות להצעות]. כלל: אף פעם לא שולח, מפרסם או קונה בלי אישור שלי. תשאל מה חסר לפני שאתה בונה.", { size: 15 });
    robot(s, 'clients', X0 - 0.05, 4.85, 1.6);
  }
  {
    const s = slide('PAPER', '05 עוד סוכנים', "ראש מטה (Chief of Staff) עם רשימת צוות. העברות דרך קבצים במחשב המשותף או צ'אט קבוצתי. השלב הסודי: בוט בודק. בוטים מוכנים לתפקיד: Nero, Hollis (בספרייה).");
    chrome(s, 'HOW BOTS TALK');
    head(s, 'צוות קטן, תפקידים ברורים', 'צוות: ', 'ראש מטה ומומחים');
    const cw = 3.6, cx = X0 + (CW - cw) / 2;
    rr(s, cx, 2.42, cw, 1.0, C.ink, null, 0.1);
    t(s, 'ראש המטה', cx, 2.47, cw, 0.5, { align: 'center', fontFace: H, fontSize: 22, color: C.white });
    t(s, 'מחזיק רשימת צוות ומחלק עבודה', cx, 2.92, cw, 0.4, { align: 'center', fontSize: 13, color: C.white });
    const team = [['סורק', '10 פריטים'], ['עורך', 'בוחר 3'], ['כותב', 'בקול שלכם'], ['בודק', 'השלב הסודי'], ['אתם', 'מאשרים']];
    const gap = 0.45, w = (CW - gap * 4) / 5, y = 4.05;
    s.addShape('line', { x: X0 + 6 * 0 + CW / 2, y: 3.42, w: 0, h: 0.3, line: { color: C.ink, width: 0.75 } });
    hline(s, X1 - w / 2 - 3 * (w + gap), 3.72, 3 * (w + gap));
    team.forEach(([h, p], i) => {
      const x = X1 - w - i * (w + gap);
      if (i < 4) s.addShape('line', { x: x + w / 2, y: 3.72, w: 0, h: 0.33, line: { color: C.ink, width: 0.75 } });
      box(s, x, y, w, 1.25, i === 4 ? C.pink : (i === 3 ? C.tLilac : C.white));
      t(s, h, x + 0.1, y + 0.2, w - 0.2, 0.45, { align: 'center', fontFace: H, fontSize: 20 });
      t(s, p, x + 0.1, y + 0.7, w - 0.2, 0.4, { align: 'center', fontSize: 13 });
      if (i < 4) arrow(s, x - gap, y + 0.38, gap, 0.5);
    });
    tip(s, X0, 5.65, CW, 1.05, 'טיפ', 'מעבירים עבודה דרך קבצים בתיקייה משותפת במחשב. מוסיפים בוט רק לתפקיד יציב.', { fill: C.blue });
  }
  {
    const s = slide('BLUE', '05 עוד סוכנים', "ריכוז אצל הצ'יף: דלת אחת. כל בקשה עוברת אליו, הוא מחלק, ומחזיר אליכם הכל במקום אחד. שער אישור אחד = פחות כרטיסי אישור מפוזרים. בקרה שבועית עם Librarian ו-Bot Optimizer.");
    chrome(s, 'CHIEF OF STAFF · ONE DOOR');
    head(s, 'דלת אחת לכל הצוות', 'הכל עובר ', "דרך הצ'יף");
    const rows = [['users', 'רשימת צוות', 'מי עושה מה, ומה אסור לכל אחד'], ['sunrise', 'תדריך אחד', 'כל בוקר: מה כל בוט עשה, ומה מחכה לכם'], ['shield-check', 'שער אישור אחד', 'שליחה, תשלום, פרסום והעלאה עוברים דרכו אליכם'], ['folder-open', 'העברות בקבצים', 'תיקייה משותפת: נכנס, בעבודה, מוכן'], ['gauge', 'בקרה שבועית', 'Librarian ו-Bot Optimizer בודקים את הצוות']];
    const x = 6.55, w = X1 - x;
    rows.forEach(([ic, h, p], i) => {
      const y = 2.42 + i * 0.86;
      hline(s, x, y, w);
      tile(s, ic, X1 - 0.55, y + 0.16, 0.55, TILES[i]);
      t(s, h, X1 - 2.75, y + 0.15, 2.05, 0.55, { fontFace: H, fontSize: 18, valign: 'middle' });
      t(s, p, x, y + 0.15, w - 2.9, 0.6, { fontSize: 14, valign: 'middle' });
    });
    prompt(s, X0, 2.42, 5.45, 4.3, "פרומפט · ראש מטה", "אתה ראש המטה שלי. תחזיק רשימת צוות: [הבוטים ומה כל אחד עושה]. כל בקשה שלי עוברת אליך, ואתה מחלק. כל בוקר ב-07:00 תדריך אחד. שום דבר לא נשלח, מתפרסם או משולם בלי שאני מאשרת דרכך.", { size: 15 });
  }

  // ───────────── 06 סקילים
  section('06 סקילים');
  await ctx.divider('06 סקילים', '06', 'סקילים', 'למה סקיל, מאיפה מביאים, ואיזה סקילים שלי אפשר לקחת.', 'SKILLS · SHARE · REUSE', IMG + 'agents-gift-illustration-v2.png',
    { notes: 'סקילים. בערב 1 בקצרה (שקף "למה סקיל"), ובהרחבה בערב 2.' });
  {
    const s = slide('PAPER', '06 סקילים', "למה סקיל. ההבדל: הוראות = מי הבוט. זיכרון = עובדות עליכם. סקיל = איך עושים משימה. סקיל הוא תיקייה עם הוראות, ולכן הוא עובר בין כלים ואפשר לשתף אותו.");
    chrome(s, 'WHY A SKILL');
    head(s, 'למה סקיל?', 'עשיתם פעמיים? ', 'זה סקיל.');
    const cols = [['01', 'אותה איכות', 'המתכון לא שוכח שלב, גם בפעם המאה'], ['02', 'לא מסבירים מחדש', 'חוסך זמן, וחוסך מכסה'], ['03', 'עובר בין כלים', 'תיקייה עם הוראות: Grok, Claude ו-GPT'], ['04', 'משתפים', 'קישור או תיקייה לצוות, ללקוחות ולקהל']];
    const w = (CW - 3 * 0.35) / 4;
    cols.forEach(([n, h, p], i) => {
      const x = X1 - w - i * (w + 0.35), y = 2.45;
      hline(s, x, y, w);
      numPill(s, n, x + w - 0.62, y + 0.25);
      t(s, h, x, y + 0.75, w, 0.5, { fontFace: H, fontSize: 22 });
      t(s, p, x, y + 1.3, w, 0.8, { fontSize: 14 });
    });
    const cmp = [['הוראות', 'מי הבוט', 'תפקיד וכללים, בכל הודעה', C.white], ['זיכרון', 'מה הוא יודע', 'עובדות עליכם', C.white], ['סקיל', 'איך עושים', 'מתכון למשימה, בכל בוט', C.pink]];
    cmp.forEach(([h, k, p, f], i) => {
      const w2 = 3.71, x = X1 - w2 - i * (w2 + 0.35), y = 4.95;
      box(s, x, y, w2, 1.75, f);
      t(s, h, x + 0.3, y + 0.2, w2 - 0.6, 0.5, { fontFace: H, fontSize: 24 });
      t(s, k, x + 0.3, y + 0.75, w2 - 0.6, 0.4, { fontSize: 15, bold: true, color: C.purple });
      t(s, p, x + 0.3, y + 1.15, w2 - 0.6, 0.45, { fontSize: 14 });
    });
  }
  {
    const s = slide('BLUE', '06 סקילים', "מאיפה: גלריית Bot templates תחת Connect apps, קישורי x.ai/bot (עותק של המתכון בלבד), Marketplace, GitHub ו-npx skills add, dr eggbot, Memory Transfer. סדר: Hide מסתיר, Delete מוחק לתמיד.");
    chrome(s, 'SKILLS · WHERE FROM · ORDER');
    head(s, 'סקילים שכדאי להכיר', 'מאיפה מביאים, ', 'ואיך עושים סדר');
    const cols = [
      ['store', 'מאיפה מביאים', ['גלריית Bot templates', 'קישורי x.ai/bot', 'GitHub · npx skills add', 'Marketplace של תוספים']],
      ['list-checks', 'איך עושים סדר', ['בוט אחד, תפקיד אחד', 'רשימת צוות אצל ראש המטה', 'Hide מסתיר · Delete מוחק', 'אף פעם לא Reset כשנתקע']],
    ];
    cols.forEach(([ic, h, list], i) => {
      const w = 3.75, x = X1 - w - i * (w + 0.3), y = 2.42;
      card(s, x, y, w, 3.0);
      tile(s, ic, x + w - 0.83, y + 0.25, 0.58, TILES[i]);
      t(s, h, x + 0.25, y + 0.3, w - 1.2, 0.45, { fontFace: H, fontSize: 21 });
      checks(s, list, x + 0.25, y + 1.05, w - 0.5, 1.85, { size: 14, gap: 6 });
    });
    box(s, X0, 2.42, 3.73, 3.0, C.pink);
    t(s, 'עובד גם אצלם', X0 + 0.25, 2.62, 3.23, 0.45, { fontFace: H, fontSize: 21 });
    ['ai-claude', 'ai-openai', 'ai-gemini'].forEach((n, i) => {
      rr(s, X0 + 2.75 - i * 1.05, 3.2, 0.8, 0.8, C.white, null, 0.4);
      s.addImage({ path: IMG + n + '.png', x: X0 + 2.87 - i * 1.05, y: 3.32, w: 0.56, h: 0.56, altText: n });
    });
    t(s, 'סקיל = תיקייה עם הוראות. אותו רעיון עובד ב-Claude, ב-GPT וב-Gemini.', X0 + 0.25, 4.2, 3.23, 1.1, { fontSize: 14 });
    tip(s, X0, 5.7, CW, 1.0, 'בטיחות', 'קוראים הוראות, חיבורים ושגרות של כל בוט או סקיל מוכן לפני שמוסיפים.', { fill: C.paper });
  }
  const skillGrid = (s, list) => {
    const w = 2.73, h = 1.95;
    list.forEach(([n, cat, p], i) => {
      const col = i % 4, row = Math.floor(i / 4), x = X1 - w - col * (w + 0.3), y = 2.42 + row * (h + 0.2);
      card(s, x, y, w, h);
      pill(s, cat, x + w - 1.05, y + 0.2, 0.85, { h: 0.32, fill: TILES[i % 5], line: null, size: 11 });
      en(s, n, x + 0.2, y + 0.62, w - 0.4, 0.4, { align: 'right', fontSize: n.length > 15 ? 13 : 15, bold: true, color: C.purple });
      t(s, p, x + 0.2, y + 1.04, w - 0.4, 0.8, { fontSize: 13 });
    });
  };
  {
    const s = slide('PAPER', '06 סקילים', "הסקילים שלי לווידאו. אפשר לשתף אותם כתיקייה עם SKILL.md. לפני שיתוף: בלי מפתחות, בלי פרטי לקוחות. סקילים של לקוחות (כמו Amdocs) לא משתפים.");
    chrome(s, "SHELLY'S SKILLS · VIDEO");
    head(s, 'בניתי, בדקתי, ואפשר לקחת', 'הסקילים שלי: ', 'וידאו');
    skillGrid(s, [
      ['VIDEO PROMPT8', 'פרומפט', 'פרומפטים דינמיים לווידאו AI, מתמונה לסרט'],
      ['VIDEO STYLE CODES', 'עריכה', 'עריכת טוקינג-הד ומושן לפי קודי סגנון'],
      ['CHARACTER LOCK', 'דמות', 'אותה דמות בכל שוט: Character Bible'],
      ['SCRIPT DECODER', 'תסריט', '6 סוכנים שמפרקים תסריט לפרומפטים'],
      ['TALKING HEAD EDIT', 'ריל', 'מילים קינטיות, 3 לוקים ו-CTA'],
      ['BANANA POP', 'ריל', 'טיפוגרפיה קינטית לריל 9:16 בעברית'],
      ['CURSOR SHOWCASE', 'עיצוב', 'סמן שמעצב לייב מהתמונות שלכם'],
      ['MIVZAK', 'חדשות', 'סרטוני חדשות 9:16 עם גרפים ונתונים'],
    ]);
    t(s, 'לשתף: תיקייה עם SKILL.md. בלי מפתחות, ובלי פרטי לקוחות.', X0, 6.62, CW, 0.3, { fontSize: 12, color: C.muted });
  }
  {
    const s = slide('BLUE', '06 סקילים', 'הסקילים שלי ליצירה ועיצוב. SKILOTREITOR הוא הסקיל שבונה ומשדרג סקילים, הכי שימושי למי שרוצה לבנות לבד.');
    chrome(s, "SHELLY'S SKILLS · CREATE & DESIGN");
    head(s, 'בניתי, בדקתי, ואפשר לקחת', 'הסקילים שלי: ', 'יצירה ועיצוב');
    skillGrid(s, [
      ['GISSER MAGIC PRO', 'תמונה', 'פרומפטים לתמונות היפר-ריאליסטיות'],
      ['CREATIVE SCRIPT', 'קונספט', 'מ-5 טריטוריות קריאייטיב לתסריט'],
      ['FASHENISTA', 'אופנה', 'בימוי, שוטים ופרומפטים לאופנה'],
      ['WES PALETTE', 'צבע', 'פלטות קולנועיות ב-5 רמות'],
      ['Y2K STUDIO', 'מצגת', 'PPTX ו-HTML בסגנון Y2K'],
      ['CIA', 'הסבר', 'דפי הסבר HTML קולנועיים'],
      ['KEYNOTE BY SHELLY', 'הרצאה', 'הרצאות קצרות לכנסים'],
      ['SKILOTREITOR', 'סקילים', 'הסקיל שבונה ומשדרג סקילים'],
    ]);
  }
  {
    const s = slide('PAPER', '06 סקילים', "מ-Claude ל-Grok: סקיל הוא תיקייה עם SKILL.md. מעלים כ-ZIP לשיחה או דרך GitHub ו-npx skills add, ומבקשים מהבוט להתקין ולהריץ בדיקה. מ-Anthropic שווה לקחת: skill-creator, pptx, docx, xlsx, pdf.");
    chrome(s, 'MOVE · SHARE');
    head(s, 'סקיל אחד, בכל מקום', 'מ-Claude ל-Grok, ', 'ומשם לכולם');
    flow(s, [['01', 'תיקיית סקיל', 'SKILL.md וקבצים'], ['02', 'מעלים', 'ZIP לשיחה, או GitHub ו-npx skills add'], ['03', 'מתקינים', '"תתקין את הסקיל ותריץ בדיקה"'], ['04', 'משתפים', 'קישור GitHub או Drive']], 2.45, 1.7);
    t(s, 'מה שווה לקחת מ-Claude', X1 - 7.0, 4.45, 7.0, 0.45, { fontFace: H, fontSize: 20 });
    const take = [['skill-creator', 'בונה סקילים'], ['pptx', 'מצגות שאפשר לערוך'], ['docx', 'מסמכי Word'], ['xlsx · pdf', 'טבלאות ו-PDF']];
    take.forEach(([n, p], i) => {
      const w = 1.6, x = X1 - w - i * (w + 0.2), y = 5.0;
      card(s, x, y, w, 1.7);
      en(s, n, x + 0.1, y + 0.3, w - 0.2, 0.4, { align: 'center', fontSize: 14, bold: true, color: C.purple });
      t(s, p, x + 0.1, y + 0.8, w - 0.2, 0.75, { align: 'center', fontSize: 13 });
    });
    tip(s, X0, 4.45, 4.45, 2.25, 'לפני ששולחים', 'בודקים שאין בסקיל מפתחות API, מיילים או פרטי לקוחות. ומשאירים קרדיט.');
  }
  {
    const s = slide('BLUE', '06 סקילים', 'סיכום מהיר של מה שעובד אצל אנשים. מהטבלה שאספתי מהשטח.');
    chrome(s, 'WHAT WORKS FOR PEOPLE');
    head(s, 'מה שאספתי מהשטח', 'מה עובד ', 'אצל אנשים');
    table(s, [['סוג', 'דוגמאות', 'איך עושים'],
      ['שגרות', 'תדריך בוקר · בדיקה יומית · מעקב מתחרים', '"תזכור" פעם אחת, ומגדירים זמן'],
      ['סקילים', 'מצגות · GitHub workflow · בדיקת עובדות', 'מבקשים מהבוט, או npx skills add'],
      ['צוותים', 'ראש מטה + מומחים', "צ'אט קבוצתי · העברות · אישורים"],
      ['ספריות', 'מאגרי GitHub · dr eggbot', 'GitHub ו-Marketplace'],
      ['שימושים מדהימים', 'משחק קלפים · עסק ב-4 ימים · מיזוג קוד', 'תוצאה ברורה + בדיקה']],
      X0, 2.42, CW, [2.6, 4.9, 4.33], { rowH: 0.68, size: 14 });
  }

  // ───────────── 07 מקימים בלייב
  section('07 מקימים בלייב');
  await ctx.divider('07 מקימים בלייב', '07', 'מקימים בלייב', '15 דקות. כרטיס תפקיד, 3 אבנים, משפט הרשאה ומשימה ראשונה.', 'YOUR TURN', IMG + 'scene-live-portrait.jpg',
    { blue: true, gravity: 'south', notes: '105–120 · מקימים בלייב.' });
  {
    const s = slide('PAPER', '07 מקימים בלייב', 'אם אין זמן: מוותרים על החיבור. סוכן עם כרטיס תפקיד טוב מועיל גם בלי חיבורים.');
    chrome(s, 'LIVE BUILD · 15 MIN');
    head(s, '105–120', 'הקימו את ', 'הסוכן שלכם');
    const st = [['105', 'בוט חדש'], ['107', 'כרטיס תפקיד'], ['111', 'הרשאה וכללים'], ['113', '"מה הבנת?"'], ['116', 'משימה ראשונה'], ['120', "כותבים בצ'אט"]];
    const gap = 0.25, w = (CW - gap * 5) / 6;
    st.forEach(([tm, h], i) => {
      const x = X1 - w - i * (w + gap), y = 2.45;
      hline(s, x, y, w);
      rr(s, x + w - 0.8, y + 0.22, 0.8, 0.34, i === 5 ? C.pink : C.white, C.ink, 0.17);
      en(s, tm, x + w - 0.8, y + 0.22, 0.8, 0.34, { align: 'center', valign: 'middle', fontSize: 11 });
      t(s, h, x, y + 0.7, w, 0.5, { fontFace: H, fontSize: 18 });
    });
    prompt(s, X0, 3.85, 7.4, 2.85, 'המשימה הראשונה', 'תביא לי 3 רעיונות לפוסטים לפי 3 האבנים שלי, עם טיוטה לאחד מהם.', { size: 18 });
    tip(s, 8.45, 3.85, X1 - 8.45, 2.85, 'בסוף', "כל אחד כותב בצ'אט איזה סוכן הקים. אין זמן לחיבור? מוותרים. כרטיס תפקיד טוב מועיל גם בלי.");
  }
  {
    const s = slide('BLUE', '07 מקימים בלייב', "יומיים לפני מפגש ההמשך: שאלון 'מה הסוכן עשה השבוע? איפה נתקעת?'");
    chrome(s, 'UNTIL NEXT WEEK');
    head(s, 'רושמים כל תקלה וכל הצלחה', 'השבוע שלכם ', 'עם הסוכן');
    const cols = [['מחר', 'פוסט בוקר, טיוטה בלבד'], ['כל יום', 'משפרים ומתקנים במשפט'], ['אמצע שבוע', '"מה אתה יודע עליי?"'], ['שבוע טוב', 'סקיל, ואז שגרה']];
    const w = (CW - 3 * 0.35) / 4;
    cols.forEach(([h, p], i) => {
      const x = X1 - w - i * (w + 0.35), y = 2.45;
      hline(s, x, y, w);
      numPill(s, String(i + 1).padStart(2, '0'), x + w - 0.62, y + 0.25);
      t(s, h, x, y + 0.75, w, 0.5, { fontFace: H, fontSize: 24 });
      t(s, p, x, y + 1.3, w, 0.7, { fontSize: 15 });
    });
    rr(s, X0, 4.65, CW, 2.05, C.pink, null, 0.16);
    en(s, '09.11', X0 + 0.4, 4.85, 3.0, 1.0, { fontSize: 50, bold: true });
    t(s, 'מפגש המשך · 60 דקות', X0 + 3.6, 4.9, CW - 4.0, 0.5, { fontFace: H, fontSize: 24 });
    t(s, 'מה בניתם · תקלות ופתרונות · סקילים ושגרות · ראש מטה · אתרים ודיוור · הצעד הבא', X0 + 3.6, 5.5, CW - 4.0, 0.9, { fontSize: 15 });
  }
  {
    section('סגירה');
    const s = slide('DIVIDER', 'סגירה', 'סגירה. בניתם משהו? תייגו אותי.');
    chrome(s, '3 RULES THAT STAY WITH YOU');
    t(s, 'הסוכן מכין.', 5.4, 1.15, 7.18, 1.1, { fontFace: H, fontSize: 60 });
    t(s, 'אתם מחליטים.', 5.4, 2.2, 7.18, 1.1, { fontFace: H, fontSize: 60, color: C.purple });
    const r = ['שום דבר לא מתפרסם, נשלח או נקנה בלי אישור', 'מתחברים בעצמכם, ורק למה שצריך', 'עשיתם פעמיים? סקיל. עבד שבוע? שגרה'];
    const x = 5.9, w = X1 - x;
    r.forEach((p, i) => {
      const y = 3.6 + i * 0.75;
      hline(s, x, y, w);
      t(s, String(i + 1), X1 - 0.5, y + 0.1, 0.5, 0.55, { fontFace: H, fontSize: 24, color: C.purple });
      t(s, p, x, y + 0.15, w - 0.7, 0.5, { fontSize: 17, bold: true });
    });
    en(s, '@shelly_or_gisser · shelly@aigosai.com', 5.9, 6.05, w, 0.35, { align: 'right', fontSize: 14 });
    const p = await crop(IMG + 'shelly-portrait-blue.jpg', 4.0 / 4.6, 'close-portrait.jpg');
    photo(s, p, 1.1, 1.3, 4.0, 4.6, -3, C.blue);
    robot(s, 'home', 0.5, 5.2, 1.4);
  }
};
