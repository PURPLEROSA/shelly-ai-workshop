# 7 הבילדים מהקרוסלה, בסגנון של שלי

איך משתמשים: מדביקים קודם את **בלוק הסגנון**, ומיד אחריו את הפרומפט של הבילד הרצוי, באותה הודעה.
כל פרומפט מייצר קובץ HTML אחד שרץ בדפדפן, מוכן להקלטת מסך.

---

## 0. בלוק הסגנון (מדביקים לפני כל פרומפט)

```text
HOUSE STYLE — follow it strictly, it overrides your defaults.

Palette (use only these, plus tints and shades of them):
  ink #303039 · sky #DDF4FF · pink #F4B8CA · magenta #B93372 · plum #60445D
  cream #F7F2ED · lilac #E8E0F2 · paper #FFFDFB
  Accent gradient, used sparingly on one hero element or the main button:
  linear-gradient(120deg, #C2337A 0%, #8E3FB8 55%, #5B4BD6 100%)

Typography: Heebo from Google Fonts. Headings weight 900, tight line-height (1.08),
slightly negative letter-spacing. Small labels in Anton, uppercase, letter-spacing 1.8px,
plum. Body Heebo 400–500.

Language: all on-screen text in Hebrew, dir="rtl". Small Anton labels may stay in English.

Mood: soft editorial pastel. Tactile, handmade, warm daylight. Playful but clean.
No emojis, no neon, no glitter, no dark sci-fi look, no stock-looking gradients.
Backgrounds are sky or cream, never pure white or black.

UI: pill buttons (border-radius 999px) with a circular arrow badge on one side;
1px ink outlines on secondary buttons; soft shadows tinted purple, never grey-black.

Motion: easing cubic-bezier(.2,.8,.2,1). Everything eases in and settles;
nothing snaps or bounces wildly. Respect prefers-reduced-motion.

Tech: one self-contained HTML file, no build step. Three.js from a CDN is allowed.
Must work with mouse and touch, and must look good when screen-recorded in 9:16
(keep the important action inside a centred vertical safe area).
Small signature in a corner: "SHELLY GISSER" in Anton, plum, 11px.
```

---

## 1. רקמה תלת־ממדית שאפשר לרקום

```text
Build an interactive 3D embroidery hoop.

Scene: a wooden embroidery hoop holding cream linen, seen slightly from above, lit by soft
window light. The linen has a visible woven texture (procedural, generated in code) and
catches light along the weave.

Interaction: wherever I click or tap on the fabric, a small flower is stitched in real time:
the thread is drawn stitch by stitch (petals as satin stitch, centre as a French knot, a short
stem in back stitch), each stitch a raised 3D tube with its own highlight and tiny shadow, and
the fabric puckers very slightly around it. Each flower takes about 1.2 seconds to stitch.
Dragging stitches a running vine of leaves that follows the pointer.

Thread colours: pink, magenta, plum and lilac, with sky for leaves. A small row of thread
spools at the bottom lets me choose the colour; the active spool lifts slightly.

Details: a needle follows the pointer and dips through the fabric on every stitch. The hoop
can be rotated by dragging outside the fabric. Buttons: "לנקות" (unpick everything, with the
threads pulling out in reverse) and "לשמור תמונה" (export PNG).

On load, auto-stitch the word "שלום" in magenta chain stitch in the centre, then hand over control.
```

**מה לצלם:** טעינה עם ה"שלום" שנרקם, ואז 5–6 קליקים מהירים ומשיכה אחת ארוכה.

---

## 2. סרט סטופ־מושן בפלסטלינה

```text
Build a 20-second stop-motion clay short film, rendered entirely in code, that loops.

Look: everything is modelled clay. Surfaces show fingerprints, small dents and slightly uneven
edges (procedural noise on geometry and normals). Animate at 12 frames per second on purpose,
with a tiny random wobble in shape and position on every frame, so it reads as real
stop-motion and not as smooth CGI. Soft studio lighting, shallow depth of field, a faint
flicker in exposure from frame to frame. The set is a small tabletop with a sky-coloured paper
backdrop curved into the floor.

Story: a ball of pink clay rolls into frame, squashes, and pulls itself up into a small
character with two dot eyes. It finds a grey lump, kneads it, and the lump becomes an
ice-cream cone with three scoops (pink, lilac, cream). The character takes a bow, the scoops
topple one by one, and the last scoop rolls out of frame to become the pink ball that starts
the loop.

Controls, kept minimal under the frame: play / pause, a frame-by-frame scrubber, and a toggle
"מאחורי הקלעים" that pulls the camera back to show the set edges, the light stands and a
clay-smudged thumbprint on the lens.

Opening title card in clay letters: "סרט קצר מאוד". Closing card: "הסוף. בערך."
```

**מה לצלם:** לופ מלא אחד, ואז מעבר ל"מאחורי הקלעים" וגרירה של הסקראבר.

---

## 3. משחק מירוץ של צעצועי קפיץ

```text
Build a complete, original 3D racing game called "מירוץ הקפיץ" played by wind-up toys on a
tabletop.

World: the track is drawn in chalk and washi tape across a big cream desk. Obstacles are
everyday objects at giant scale: a stack of books as a ramp, a pencil bridge, a spilled jar of
pastel buttons that slide underfoot, a ruler straightaway, a teacup tunnel. Warm daylight from
a window, soft real-time shadows, gentle depth of field.

Racers: four tin wind-up toys, each with a turning key on its back: a snail, a rabbit, a small
robot and a duck. Painted in pink, lilac, sky and magenta, with slightly chipped paint.

Core mechanic: speed comes from the spring. Hold the button to wind up before the start
(over-winding makes the toy spin out). During the race the spring unwinds and the toy slows,
so I must hit wind-up pads on the track to recharge, and steer left and right. The key on the
toy's back visibly spins faster or slower with the remaining charge.

Game structure: start screen, toy select, countdown, three laps against three AI racers,
position and lap display, spring gauge as a pill-shaped meter, finish podium with confetti made
of paper punch-outs, and a "עוד סיבוב" button. Keyboard (arrows + space) and touch controls
(two thumbs zones). Simple sound made in code: ticking spring, soft clacks, a small bell on
the final lap.
```

**מה לצלם:** בחירת צעצוע, הקפצת קפיץ לפני הזינוק, מעבר על רמפת הספרים, פודיום.

---

## 4. אתר תלת־ממדי מונפש לבקבוק מים

```text
Build a scroll-driven 3D product website for a fictional sparkling water called "טיפה".

Hero: a glass bottle floating in the centre on a sky background, with real refraction through
the glass and water, condensation droplets that slowly run down, and a paper label in cream
with the name in heavy black Hebrew type. Inside the bottle runs a live bubble simulation:
bubbles nucleate at the bottom and on the glass, rise with a slight wobble, merge when they
touch, and pop at the surface with a tiny ripple. Moving the pointer tilts the bottle and the
water level and bubbles respond to the tilt. Clicking the bottle "shakes" it and triggers a
burst of fizz.

Scroll story, five sections, the bottle stays pinned and transforms between them:
1. Hero: headline "מים. רק יותר שמחים." with one gradient pill button "לטעום".
2. The bottle rotates to show the back label; three facts fade in beside it.
3. The cap twists off and bubbles escape the bottle and drift up through the page behind the text.
4. Three flavours: the water tint changes between pink grapefruit, lilac lavender and clear;
   I can switch flavour with three pill buttons and the label colour follows.
5. The bottle tips and pours into a glass that fills; closing line and a sign-up field.

Performance: hold 60fps on a laptop; reduce bubble count automatically on mobile.
Section labels in small Anton uppercase (01 — THE WATER, 02 — THE LABEL, and so on).
```

**מה לצלם:** גלילה רציפה מלמעלה עד המזיגה, ואז חזרה ל־hero ולחיצה לניעור.

---

## 5. הסטודיו שלי בתלת־ממד

```text
Build an explorable 3D miniature of a creative studio, shown as an isometric diorama room with
two walls cut away.

The room: a long desk with a desktop computer, a drawing tablet, a mug of pens, a camera on a
small tripod, a ring light, a mood-board wall with pinned pastel swatches and printed
letterforms, a shelf of design books, a plant, a pink armchair, a rug in lilac, and a window
that throws a warm patch of light across the floor. Walls in sky, floor in cream wood.
Slightly toy-like proportions, rounded edges, soft baked-looking shadows.

Interaction: drag to orbit, scroll or pinch to zoom. Objects highlight softly on hover and each
does something small when clicked: the ring light switches on and changes the room lighting,
the plant sways, the camera flashes and saves a snapshot of the current view, the books slide
out and show a title, the armchair cushion squashes.

The computer: clicking it flies the camera smoothly into the monitor until the screen fills
the view, and a small working desktop appears with two icons. One opens an original mini-game,
"לתפוס גלידה": scoops of ice cream fall from the top, I move a cone left and right to stack
them as high as I can, the tower sways more as it grows, and a dropped scoop ends the round.
Score, best score and "שוב" button. The other icon opens a notes window with a short
"about the studio" text. An "יציאה" button flies the camera back out to the room.

Time of day: a slider under the scene moves the sun from morning to golden hour to evening,
when the desk lamp and the monitor glow take over.
```

**מה לצלם:** סיבוב של החדר, הדלקת ה־ring light, טיסה לתוך המסך, כמה שניות משחק, יציאה.
**הערה:** אם רוצים שזה ייראה כמו הסטודיו האמיתי, לצרף לפרומפט צילום או שניים של החדר ולכתוב "match this room".

---

## 6. נורת זכוכית שנראית אמיתית

```text
Build a photorealistic clear glass filament light bulb, rendered in real time in the browser.

The bulb: thin blown glass with real refraction and reflection, slight thickness variation,
a faint seam, a few specks of dust and one soft fingerprint. Inside: the glass stem, support
wires and a long coiled filament. A brass screw base with fine thread and small scratches.
The bulb hangs from a fabric-wrapped cord in plum and sways very slightly.

Light: a dimmer below the scene, styled as a pill slider. At zero the filament is cold grey
metal. As I raise it the filament warms from dull red to orange to bright warm white, with
bloom, and the glow lights the inside of the glass, the base and the wall behind. Turning it
down, the filament cools slowly and keeps a red afterglow for a second. On fast changes add a
very slight flicker.

Set: a sky-coloured plaster wall with subtle texture, lit softly from one side so the bulb is
readable when off; when on, the bulb becomes the key light and the wall falls into warm light
with a soft shadow of the cord.

Interaction: drag to orbit close around the bulb, including a macro view where the filament
coils are clearly visible. Tap the glass to make it ring softly and swing. One button, "כיבוי",
runs the full power-down.

Priority is physical accuracy of glass and filament over everything else.
```

**מה לצלם:** נורה כבויה, דימר עולה לאט, מאקרו על הסליל, טאפ על הזכוכית, כיבוי.

---

## 7. ספר פופ־אפ שאפשר לדפדף

```text
Build an interactive 3D pop-up book with six spreads that I can actually flip.

The book lies open on a cream tabletop in soft daylight. Pages are thick paper with visible
fibre texture, slightly uneven cut edges and soft shadows between layers. I turn a page by
dragging its corner; the page bends naturally as it turns and can be dropped back halfway.
As a spread opens, its paper constructions unfold with correct pop-up mechanics: V-folds,
box layers, pull tabs and a rotating wheel, all driven by the page angle, so opening slowly
raises them slowly.

Story, "הגלידה שרצתה לראות את הים", one line of Hebrew text per spread in heavy black type:
1. A small town of paper houses rises; an ice-cream cart stands in the square.
2. A scoop of pink ice cream jumps off its cone (pull tab makes it hop).
3. A paper forest with layered trees; a wheel turns day into night behind them.
4. A mountain unfolds in steps; the scoop climbs when I slide a tab.
5. The sea: layered waves that rock as the page moves, a lighthouse that lights up.
6. Sunset on the beach; the scoop melts happily into a small pink puddle shaped like a heart.

Everything is cut paper in the house palette, no outlines, depth from layering and shadow only.
Extras: paper rustle sounds made in code, a ribbon bookmark that jumps to any spread, and a
"מההתחלה" button that closes the book and shows the cover with the title embossed.
```

**מה לצלם:** פתיחת הכריכה, דפדוף איטי אחד שמראה את המנגנון מתרומם, משיכת לשונית, הכפולה של הים.

---

## הערות

- בקרוסלה יש 7 בילדים. ששת הנוספים קיימים רק בסרטון המלא, לא בתיקייה.
- אלה פרומפטים מקוריים שכתבתי לפי תיאור הבילדים, לא הפרומפטים של יוצר הקרוסלה.
- שני שינויים מכוונים: למשחק המירוץ שם משלך, ובמקום המשחק המוכר שבתוך המחשב בסטודיו יש משחק מקורי ("לתפוס גלידה").
