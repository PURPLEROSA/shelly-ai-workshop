# Explainer pages

An explainer is a page that teaches one thing by letting the reader move it. It is built from pieces: each idea on the page is one piece, and the number that piece runs on is the idea. The worked example is `examples/explainer/agent.shell.html` (in Hebrew, right to left): how an AI agent works, in six stations.

## Before any piece: four decisions

1. **One question.** The page answers a single question a real reader has: *what happens inside an AI agent?* Write it down, with who is asking and what they should be able to say afterwards in their own words.
2. **A through-line.** One concrete example that travels through every station. In the example it is a single request, *"book me a meeting with Dana on Thursday"*: it is cut into tokens at station 1, it is the request the tools answer at station 4, the job the loop works through at station 5, and a finished slip in the pile at station 6. The hero shows it; the last station returns it. Without a through-line an explainer is a list of demos.
3. **Stations as claims.** Four to seven. Each one is a sentence that could be wrong, and its headline is that sentence: *"It does not read words."* not *"Tokenization"*. Order them so each needs only the ones before it.
4. **A number for every claim.** For each station name the thing the reader will move and what moving it shows. If a claim has no number to move, it is a paragraph inside another station, not a station.

| Station | Claim (the headline) | The reader moves | And sees |
|---|---|---|---|
| tokens | It does not read words | how closely they look | the sentence cut into numbered slips |
| temperature | It guesses, and you set how boldly | the mercury | the wording drift from fact to rumour |
| memory | Its desk is not big | the tape | old lines leave the window; the counts stay honest |
| tools | Alone, it only talks | three keys | the same request answered eight different ways |
| loop | Thinks, acts, checks, again | a wheel | a log that writes one line per lap |
| result | And in the morning, a pile of slips | the pile | the request from the hero, done |

## Each station

Write the piece's sentence with `conceit.md` and build and probe it alone, in its own file, before it goes near the page. Then give it four lines of copy, always these four:

- **The claim** as the headline. Short enough to read in one glance.
- **Two or three plain sentences.** What is true, in the reader's words. No term used before it is explained; a term is introduced once, in passing (*small pieces called tokens*).
- **The try line.** What to do with the piece, naming the gesture and the direction as the reader will see it. On a right-to-left page a slider grows to the left, so the line says *left*.
- **The takeaway.** What to remember when the page is closed, eight words or fewer. This is the line worth a highlight.

**Facts.** Check every claim against something you can point to. Where a piece simplifies, it says so on the piece itself: the token cutter is an illustration with a fixed seed, not a real tokenizer, and a caption under it says exactly that. Never show an invented number as a measured one.

## The page

A shell is an ordinary HTML page with markers where pieces go. `compose.mjs` sets the pieces in and writes one file.

```html
<head> ... your page styles ... <!-- pieces:css --> </head>
<body>
  <section class="station" id="tokens">
    <div class="copy"> claim, sentences, try line, takeaway </div>
    <div class="bench"><!-- piece: ../tokens.html --></div>
  </section>
  ...
  <!-- pieces:js -->
  <script> the page's own behaviour </script>
</body>
```

```
node scripts/compose.mjs shell.html --out page.html                              a complete page for a site
node scripts/compose.mjs shell.html --out page.html --artifact page.artifact.html   also a variant for a Claude artifact
```

What the page is responsible for, and nothing more:

- **The stage for each station.** A full-width band with its own ground colour; the bench that holds the piece is a size container (`container-type: inline-size`), because pieces size themselves from their container.
- **Theme.** Use the project's own palette and type. Give each piece its colours and typeface through the custom properties it lists above its styles: `.fever { --hot: var(--mag); --display: var(--font-display); }`.
- **Complete at rest.** Everything that is meant to be read is visible without scrolling into it. A station may gain a flourish when it arrives (a highlight drawing under the takeaway); it never starts hidden.
- **A first showing.** The first time most of a piece is on screen, the page may play it once (`PIECES.tokens.hello()`, `PIECES.fever.set(0.62)`), then it belongs to the reader. Never replay it. Skip it under reduced motion.
- **Where you are.** A progress line and a list of stations that marks the current one. Plain anchor links; never take over scrolling.
- **A quiet switch.** `?quiet` turns off the first showings and any opening flourish, so a piece can be probed in place.
- **The hero and the recap.** The hero states the question and shows the through-line. The recap lists the claims, each linking back to its station, and ends on the one formula worth keeping.

## Checking a page

```
node scripts/probe.mjs page.html --root "[data-piece=keys]" --query quiet --allow fonts.googleapis.com,fonts.gstatic.com
```

Probe every piece in place: a piece that passed alone can still break when it lands. Then photograph the whole page at desktop and phone width and read it top to bottom.

Faults that only appeared once the pieces were on one page, all of them caught building the example:

| Symptom | Cause | Guard |
|---|---|---|
| A piece arrives half styled | Some of its rules were in its stage `<style>` block, which is left behind | `compose.mjs` refuses a piece whose stage block styles its class |
| Part of a piece vanishes on a phone, or picks up a tilt and a shadow | The page styled a bare class name (`.rail`, `.slip`) the piece also uses inside itself | `compose.mjs` refuses the clash; rename the page's class |
| A piece ignores the typeface you gave it | `--display: var(--display)` refers to itself and cancels out | Name page tokens differently from piece properties (`--font-display`) |
| The first sheet of content loses its rounded top | `:first-of-type` matched the first `section` as well as the header | Select by class |
| The station list stays on the last station at the top of the page | Only stations were observed, so nothing cleared the mark | Observe the hero and the recap too |
| Keyboard checks wander off to another station | Tab order was started from the top of a long page | The probe starts it just before the piece |
| "Moves at rest" on a piece that is still | The page's first showing was playing during the measurement | Probe with `--query quiet` |

## Delivering it

- **On a site:** the `--out` file is one page with no build step. It can name fonts and images beside itself.
- **As a Claude artifact:** publish the `--artifact` file. The wrapper tags are dropped, the language and direction are set by script, local fonts are inlined, and only Google Fonts is fetched.
- **The source of truth** is the shell and the piece files. Change those and compose again; never edit the composed page.
