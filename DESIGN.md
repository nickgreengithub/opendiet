# Design notes

Why the site is built the way it is. `index.html` at the root is the whole app and the
only copy of it; this file is the reasoning behind it, kept apart so the README can stay
short.

There used to be a second copy at `opendiet.org/beta/` to try changes against. It is gone:
there are no users to protect from a bad change, and a staging copy that has to be promoted
by hand is a way to ship the wrong file, not a safety net. Changes go to `index.html` and
to `main`.

The layout rules below were the first things it was built to test, and still hold:

- A tablet gets the touch layout, not the table. The table's numeric columns are fixed,
  so every pixel of squeeze lands on the one flexible track — the food name — and below
  about 960px of viewport every row reads "Cheese, parmes…" and identifies nothing. The
  line is drawn at 1000px: every iPad in portrait falls under it, landscape tablets stay
  above it and keep the table. Width is the right signal rather than the user agent,
  since it handles split-screen for free. The touch layout then stops widening at 640px
  and centres, so a tablet shows a comfortable column rather than a stretched phone —
  and 640 is not an arbitrary cap: the donut's bracket geometry was already computed
  against it, so holding to it keeps that arithmetic true on a tablet too. Where the cap
  bites, the panel is inset on all four sides and given a hairline edge, because a column
  with air either side and none above or below reads as an accident rather than a
  decision. A phone keeps its screen edge to edge, as an app does; the inset is fixed
  rather than matched to the side margins, since those grow with the screen and 90px of
  dead space top and bottom would cost a third of the list to buy nothing.
- ABOUT carries a **build stamp** beside the version, taken from `document.lastModified`.
  That is the Last-Modified of the copy the browser is actually holding, so a cached page
  reports the age of the cache rather than of the deploy — which is the whole point. It
  answers "which build am I looking at" without anyone having to infer it from whether a fix
  appears to be present, which is how several rounds of this project were lost.
- ABOUT ends on its two links held in opposite corners — LinkedIn bottom left, GitHub
  bottom right — on a row of its own rather than the one the unbuilt apps use, taking the
  full width with an auto top margin so it sits on the floor of the panel wherever the text
  above it ends. The byline lost its year to fit both corners inside the padding at 360px;
  with it, the pair overran the container by 10px and GitHub finished 3px from the screen
  edge. The disclaimer steps up to 1rem on a phone. The note about Nutrition5k is gone: the
  game has not been dealt from that deck for some time, and a credit for pictures the site
  no longer shows is worse than no credit at all.
- **A phone opens on the launcher.** Three rows, one per app, each a container you press:
  a mark, the name, one short line on what it is, and a chevron if there is somewhere to
  go. A desktop is wide enough to open straight into the table with the others a tab away,
  so it still does. The rows are rows rather than the tall cards they were, because a phone
  reads a list top to bottom and three cards of 7.4rem did not leave the third on screen.
- All three rows are **one height** — 78px, measured — and that is why neither the name nor
  the line under it may wrap. Both are held to one line and would ellipsis rather than
  break, the name's letter spacing came down to .1em and the COMING SOON tag to .62rem to
  pay for it. Before that, CALORIE CALC broke over two lines and stood taller than the other
  two, which read as though it mattered more than the apps that actually work.
- **Nothing is labelled LIVE.** A row that opens says so by opening; a badge saying the
  working thing works is noise on two rows out of three. Only the unbuilt one carries a word.
- The marks are from the same set as the portion marks — a glass for the table, a balance
  for the game, since the game is a question about which side weighs more, and a calculator
  for the one that is not built. 30px, in the accent for the two that open and a flat grey
  for the one that does not.
- **The order is the order of use, not of building:** search, game, calc. The tab row reads
  from the same list, so it cannot disagree with the launcher.
- The descriptions are one short line each. "Search 18,000 foods and read their macros side
  by side" described a comparison tool the site is not — the table is one list you sort, not
  two foods set against each other.
- **CALORIE CALC is inert, not merely marked.** It is dimmed, labelled COMING SOON, carries
  no chevron, and has `pointer-events: none` — which takes the hover with it, so nothing
  about it invites a press. The same is true of its tab. It was previously a live door into
  a page that said the thing was not built yet, which is a worse answer than the door not
  opening. The tab and the row are both driven from `live()`, which now counts the game as
  built: it had been claiming SOON on a screen you can play.
- The site is a set of small apps rather than one page, and both layouts open straight
  into the built one. The others sit beside it in a tab row — FOOD SEARCH, CALORIE CALC,
  CALORIE GAME, shortened to SEARCH, CALC, GAME on a phone — with ABOUT holding the
  right-hand corner. The launcher screen it replaces is gone from both, and ABOUT is a
  page in the same language as the unbuilt ones rather than a dialog over the top: it
  lights its tab like any other, and Escape returns to the search.
- CALORIE GAME is built, on a phone. It opens by **showing** the game rather than
  describing it: HOW TO PLAY, one line of instruction — select the food with the highest
  calories — then a working miniature of two cards with a hand drifting from one to the
  other, and BEGIN. The hand does not press either of them. The page is saying what the
  choice is, not making it: a demonstration that answers its own question tells the reader
  the wrong thing about what is being asked of them, so no figure appears on it at all. The
  pair it uses is three tablespoons of olive oil against three cups of courgette, read from
  the live deck by id so the mock can never drift from the real thing.
- The miniature's pictures are near enough square, because the plate sits in the middle of
  a square tile and a letterbox crop of one is a photograph of the tablecloth. The block is
  centred where there is room and pinned below the tabs where there is not — with the
  demonstration in it, it very nearly fills a 640px screen, and a centred block that
  overflows spills equally at both ends, which had put the heading underneath the tab row.
  Measured clear at 844, 640 and 568px tall.
- Then it asks one question six times: two foods stacked one above the other, and which of
  them is more. Six rather than ten because every pair carries the same size of lesson, so
  the tenth teaches nothing the sixth did not, and a game that ends while it is still
  interesting gets played twice.
- Each food is a card — the picture, and under it a solid bar with the name, the portion
  and, once answered, the calories. **The portion is set at the name's size**, told apart by
  colour alone. It is half the question — a cup of one thing against three cups of another —
  and at two thirds the size it read as a footnote on the name rather than part of it. The
  bar takes the card's colour when the answer lands, so the picture, the label and the
  figure all say the same thing at once, and the losing card dims to about two thirds rather
  than half, which was dim enough to stop being readable.
- The right of that bar carries the portion drawn rather than written: a cup, a spoon, a
  slice or a whole item, repeated as many times as the portion says. USDA hands the deck
  14 distinct unit strings across 26 phrasings — cups, tablespoons, slices, fruit, halves,
  containers, rashers — which is far too many shapes to read at a glance on a phone, so
  they collapse to **four families**: cup (20 of the 36 foods, a tub of yogurt among them),
  whole (9), slice (4, bacon rashers included), spoon (3). Three cups of courgette is three
  cups; a tall glass of milk is one and a half, so the half is the same glyph at 42%
  opacity. They are drawn at 18px in a bar whose height is fixed at 2.9rem, so they read at
  arm's length without the banner growing to meet them — the height was measured across 42
  rounds and never moved off 46px. Going up from 14px cost about 10px of width, which
  clipped "3 tablespoons" on a 360px screen; it came back out of the bar's side padding
  (.55rem to .42rem), its column gap (.38 to .28rem) and the gap between the marks, which is
  now zero. They can sit flush because each is drawn on a 24 grid with the shape inset from
  it, so flush is not touching. Above five the count stops being countable and one glyph stands for the lot,
  since the words beside it already say "8 slices". The glyphs are 14px and the name's
  letter spacing came down to .03em to pay for them — swept over twelve games at 360px
  wide with nothing truncated.
- The four marks are **Material Design Icons** (Apache 2.0): `cup-outline`,
  `silverware-spoon`, `bread-slice-outline`, `food-apple-outline`, inlined as paths rather
  than loaded, since the only thing this site fetches from anywhere else is React. Drawn
  ones sat here first and looked drawn: the cup wore a floating lid, the slice was a
  tombstone, the whole item a circle on a stick. Tabler, Lucide, Phosphor, Iconoir, Solar
  and Material Symbols were all rendered side by side at 12, 13 and 16px against the real
  bar first; MDI was the only set of them carrying all four families in one hand — none of
  the stroke sets has a plain spoon at all, and Tabler's nearest is a fork and spoon
  together. The spoon keeps its diagonal: stood upright it stops reading as a spoon and
  starts reading as a pin.
- **The first answer of a session gets a sentence.** A donut and two figures mean nothing to
  someone who has never played: they show what the answer was without saying what the
  question tested. So the first pick — and only the first — holds the round and puts up a
  card: CORRECT or NOT THAT ONE, then which food actually carried more. It holds rather than
  racing the 1.78s auto-advance, because that is not long enough to read a sentence, and it
  goes on a tap.
- The sentence is "More calories in X than in Y" rather than "X has more calories than Y",
  because the verb has to agree with the food and half this deck is plural — almonds have,
  brown rice has. Putting the foods after the preposition sidesteps an agreement bug that
  would read as sloppy on every other round.
- Once a session, tracked in `sessionStorage`: play again in the same tab and the lesson does
  not repeat; open the site fresh tomorrow and it does. A runtime flag alone would repeat it
  on every reload, and `localStorage` would mean a player who cleared nothing never saw it
  twice in their life, which is too stingy for a thing this short.
- Answering is where the game does its teaching, so it is where the motion is. Tapping a
  card drops both photographs to a third of their brightness and most of their colour, and
  a donut rises over each one with the food's calories in the hole. The pair holds for
  about a second and a quarter, then slides out to the left while the next arrives from the
  right.
- The donut is drawn against **the largest figure in that whole game**, not against its own
  partner, and the maximum is settled at the start from the twelve foods in play — before a
  card has been seen — so the scale cannot shift under the player mid-game. That is what
  makes the sixth reveal comparable with the first: a three-quarter ring means the same
  thing in every round. The arc sweeps because the circle is mounted from the first frame
  at a full dash offset and only the offset changes when the answer lands, which is a
  transition rather than a keyframe and so can carry a different value per food.
  `pathLength="100"` turns the dash arithmetic into percentages. The figure in the hole is
  HTML over the drawing rather than SVG text, because the template engine wraps interpolated
  text in a span and SVG will not paint one.
- **Every `<img src="{{ ... }}">` in the template was fetched literally before the framework
  ran.** The markup is live DOM, not a `<template>`, so the browser's preload scanner reads
  `src="{{ gTop.img }}"` off the raw bytes and requests that string as a path — four 404s a
  page load, and four `<img>` elements sitting in an error state before React ever set a
  real source. On a fast connection the swap follows quickly enough that nothing shows; on a
  slow or flaky one, an element can be left holding the browser's broken-image glyph, which
  is what a card with no picture and a "?" in it is. `loading="lazy" decoding="async"` on
  the four game images defers the fetch past the preload scan, and the bogus requests are
  gone — measured at zero over four loads, with both intro pictures and all twelve card
  pictures still decoded when they are needed. The framework offers placeholder hints for
  `sc-if` and `sc-for` but nothing for an attribute, so there is no way to give the raw
  `src` a harmless default.
- The two cards are the same <img> nodes every round, so advancing only swaps their src —
  and a browser keeps painting the old picture until the new one has decoded, which is why
  the pair used to slide out and then flash to the next one part way through. All twelve
  are fetched and decoded up front, during the intro, when there is nothing else to do.
- Both halves of the pass are keyframes, not transitions. The cards always carry an
  animation with fill-mode both, and an animation's value beats a transition on the same
  property — so setting a transform and removing the animation in one update does not
  interpolate, it jumps. Sampling every frame showed exactly that: the card sat at 0 and
  was fully 95px away one frame later. Out and in are now four keyframe names, two each,
  alternating by round, because the cards are the same nodes every time and only a change
  of animation-name restarts an animation on a node that was never unmounted.
- The reveal animates on the way in and snaps on the way out. Without that, the next
  question arrived with its own donut un-drawing itself from full to empty and its
  photograph lightening — the whole reveal playing backwards over the top of the new pair,
  which is what made the pass look broken rather than merely quick.
- The round is 1.78s: the arc sweeps for the first 0.68s, the pair holds for 0.8s, and the
  last 0.28s is the slide out, which the next pair's arrival overlaps. Before, the sweep
  finished at 0.98s and nothing happened at all until 1.72s — three quarters of a second of
  dead screen followed by a jump.
- Which round it is and how many are right sit at the bottom. They are a thing to glance
  at between pairs rather than the first thing on the screen.
- The app row is set a size up — .88rem on a phone, .94rem on a desktop — and the bar grows
  with it. It is the site's own navigation read at arm's length like everything else on the
  page, and it had stayed at the size it was drawn at before anything else stepped up. At
  360px SEARCH CALC GAME still hold one line with ABOUT on the right corner, ending 10px
  clear of the edge.
- The round bar at the foot of a card goes from 2.1rem to 2.75rem. It had been sitting hard
  against the bottom of the screen, which on a phone means hard against the browser's own
  chrome, and the boxes in it looked like they were falling off.
- During a round, the bottom right carries **six boxes rather than a count**. A tally says
  how many; the boxes say which ones, and how much of the game is left, in the same glance —
  filled with a tick or a cross as each answer lands, faint and empty ahead of it.
- The results page is a grade and six tiles. The grade is a letter on percentage correct,
  with the percentage and the tally printed beside it. The bands are the school scale
  stretched, because the school scale is the wrong shape for this game: the deck is built so
  that guessing scores about half, and on an unstretched scale that put three of six at F and
  four of six at D+ — four of the seven possible scores collapsing to F, which tells a player
  less than the tally already had. **Half is now the floor of a pass rather than a fail.** A
  coin toss deserves the bottom mark rather than no mark; below half is worse than guessing,
  and that is what F is for. The seven scores now read F, F, F, D, C+, A-, A+.
- The head is a letter with two lines set against it: the score on the first, what the
  misses cost on the second. The grade is 3.5rem so it stands as tall as both together —
  under the block rather than beside it, either line read as a footnote hung off the bottom
  of the letter. Picking the lighter plate means the heavier one was worth more than you
  gave it credit for. The second line used to average that gap over the game and print it in
  kcal, which is a fact about the game rather than about food — nobody carries a number like
  that out of the room. It now **names the plate that surprised you most**: the widest gap
  you got wrong. That is a fact about a food, and it is the kind a person keeps. The figure
  is not repeated beside it, because the tile below is already printing it and the eye goes
  straight there. A clean game says nothing on the table surprised you.
- That line had to lose words to move. Beside a grade there is roughly 100px less to spend
  than beneath one, and the worst case is not the F it was first tested against but **A+**,
  which is some 40px wider. "On average, you underestimated by 144 kcalories" does not fit;
  "Underestimated by 144 kcal a round" does, with room, and says the same thing. The worst
  case was measured rather than reasoned about, by forcing every band to A+ for one run.
- **The list is the search list.** Same 1.02rem name in the reading weight, same #d7e6ef,
  same 1.04rem tabular figure right-aligned, same hairline under every row, and the same
  kind of head naming the column once above a heavier rule. Nothing is set in capitals: the
  site reserves those for labels, and these are food names, so they are sentence case here
  exactly as they are in the table. The bordered lime and red tiles are gone — two screens
  listing foods should not look like two different products.
- **A pair opens into a comparison, not two readings.** Tap either line and the pair unfolds
  into one table: the two foods in two columns, every macro and sub-macro the site lists —
  water, ash, macros, protein, fats with saturated, mono and poly under it, carbs with
  sugars, fibre and starch — and calories on a heavier rule at the foot. Both at the portion
  the round showed. A donut each was the first attempt and it was the wrong shape: two
  drawings side by side are two separate readings, and the question a pair asks is which is
  bigger. A table is the only form where the eye runs along a row and answers that.
- **The table stands in place of the two rows, not under them.** The names become the column
  heads, so leaving the rows up printed each food twice; they collapse to nothing and the
  table arrives on a short rise, which reads as the foods moving into their columns rather
  than as a panel appearing beneath them. A tap anywhere else on the screen puts them back —
  the whole game view carries the closing handler and only the table stops the event, since
  with the rows gone there is nothing left to tap twice.
- The label column takes only what its longest word needs (`auto`) and the two foods split
  what is left (`1fr 1fr`), which is what lets a name be set at **1.02rem, the size it is in
  the row it replaced**. Fixed 4.9rem columns had it at .76rem and still colliding.
- **The whole table is one grid, not a grid per row.** A row that is its own grid resolves
  its `auto` column against its own content, so the header's empty first cell was 0 wide
  while every data row's was ninety-odd — which is why the first food's name sat well left
  of its own figures. Each row is now `display: contents` and its three cells join the grid
  above them, so one `auto` is measured for the whole table. The column gap went to zero
  with it and the space moved inside the cells, because per-cell borders across a gap draw a
  broken rule.
- The two totals share the left edge of the nutrient names, and the round's tick sits in a
  gutter ahead of them — .95rem, the same indent the colour dots occupy — so GRAMS and
  CALORIES start together instead of the mark shunting one of them right.
- The foot is two lines: **grams first, calories under it as the secondary total**, with the
  round's tick or cross against the calories, since calories are what the round turned on.
  Grams is the heavier line because it is the thing the two plates are actually being weighed
  on — two cakes is 20 g and two tablespoons of butter is 28 g, and that is most of the
  answer before a calorie is read.
- **Only the larger figure in a row is lit.** White against the grey of the smaller one, so
  a column of white tells you where a food is heavy before a single number is read. Equal
  values light neither, which is the honest reading of a tie.
- The join costs nothing: the deck carries USDA's own name for every food, and all 36 match
  a row in the legacy library exactly, so `deck.usda -> library row` is a lookup rather than
  a guess. There is no amount control and no ADD: the portion is the question, and there is
  no plate in the game.
- Two things the layout had to be told. A grid item will not let its child ellipsis until
  the item itself may shrink, so the header names collided until `min-width: 0` and
  `overflow: hidden` went on the cell. And aligning that cell to `flex-end` made an
  over-long name lose its *beginning* — "·k chocolate" — so the cells stretch and the text
  is right-aligned inside them instead, which puts the ellipsis at the end of the word where
  it reads as truncation.
- The wrapper's style is built on the tile rather than inside the comparison model, because
  a closed pair has no model and an undefined style is not `display: none` — the first
  version leaked a stray CALORIES onto every closed pair.
- The library is 937KB and the game does not otherwise need it, so it is fetched when a game
  begins rather than at boot — a player who never reaches the results page never pays for it.
- **The rule falls where the pair ends, not through the middle of it.** Two foods joined
  with nothing between them, a hairline closing the pair, then air. A line inside a group is
  the group being cut in half, and that is what the list was doing: the strongest mark on
  the screen sat inside the thing meant to read as one unit, while the boundary between
  units was carried by whitespace alone. The gap still does the heavy lifting — a rule on
  its own would give six sections that read as one continuous ruled table again — but the
  rule gives each pair a floor and keeps the family resemblance to the search list, which is
  ruled throughout. The risk taken was that two foods with no rule between them read as one
  two-line entry; they do not, because each carries its own portion and its own figure.
- **The pair is told by space more than by anything else.** Two rows tight together, 21px of
  air to the next pair, and both rows set identically — same weight, same #d7e6ef. Dimming one of
  them was a second and weaker way of saying which carried more, and all it achieved was to
  make the two lines of a pair read as a heading and a subheading. The figures already say
  which is bigger. The tick or cross rides the pair's first line; centred between the two it
  landed exactly on the rule and read as a smudge on it.
- **That gap did not exist for two commits.** The pair wrapper is a `<span>`, and a span is
  inline by default; an inline box drops vertical margin on the floor. The margin was set to
  .95rem and then to 1.35rem and measured 0px both times — the pairs were not weakly
  separated, they were not separated at all. `display: block` on the wrapper is the whole
  fix. Measured since: 0px within a pair, 21px between them.
- Room for that air came from the head, which is gone; from PLAY AGAIN, down from 3.1rem to
  2.5rem; and from the caveat, which now sits behind a mark at the end of the grade's own
  row and opens above the button when it is asked for. A caveat has to be readable when it
  is read, not resident on a screen whose whole problem is that six pairs need room to look
  like six pairs. The mark costs the head 1.6rem of width, which is why the second line lost
  the word "Biggest" — with it, the longest food name in the deck beside the widest grade
  overran by 21px.
- **The list scrolls, and that is the point of copying the search screen.** Twelve rows, a
  head, a caveat and a button do not fit 640px — PLAY AGAIN finished 218px below the fold —
  and the screen this borrows from has always scrolled its rows under a fixed head. So the
  head is pinned, the rows take the space that is left, and the caveat and the button hold
  the floor.
- Each pair used to be a tile, stacked in the order it was played, holding its two foods in the
  order they stood on the screen — name, portion, calories — with a tick or a cross and a
  border in lime or red. The answer is legible from the shape of the page before a word of
  it is read. Which food actually carried more is told by weight, never by being too dark
  to read: this page is the only record of what the six pairs were.
- The tile costs about 40px of width that a flat row did not — two borders, side padding,
  the gap and the mark's column — and at 360px that is the difference between "3
  tablespoons" fitting and not. It was paid for out of the mark (1.05rem), the tile padding
  (.35rem), the column gap (.3rem) and the calorie column (2.5rem), and the name track was
  changed from `auto` to `minmax(0,auto)` so a long name gives ground instead of the
  portion always paying. Ten games at 360x640 and five at 390x844, 30 distinct pairs, clean.
- The page ends on a caveat, and it goes here rather than on the way in. Before a game it
  is throat-clearing nobody reads; after a grade it lands, because that is the moment
  someone might take a score about calories for a verdict about food. It names the actual
  relationship rather than gesturing at balance: calories drive body fat, and a healthy diet
  also means hitting macro and micronutrient targets, which is a second thing this game does
  not teach. "Calories are one number among many, and a good diet is a balanced one rather
  than a small one" said less than it appeared to — it never said what the other numbers were
  or what calories do. Length is a constraint, not a preference: the caveat has to hold three
  lines at 360px or PLAY AGAIN goes off the bottom of a 640px screen, which the longer draft
  did by 13px. It follows the tiles directly rather than being
  pushed to the floor by PLAY AGAIN's auto margin, which had left it stranded halfway down an
  empty screen, and it is set at .95rem in the same grey as the portions — a caveat nobody
  can read is not one.
- **The clipping check was broken too, in the other direction.** The narrow shell is
  `position: fixed` with `overflow: hidden`, so content that does not fit is not an
  overflow — the document never grows and `scrollHeight` never exceeds the viewport. The
  caveat pushed PLAY AGAIN 45px off the bottom of a 640px screen and the check called it
  clean. It now finds the button and asserts its rect is on screen, which is the honest
  question: is the last thing on the page reachable. The 45px came back out of the tile
  padding and margins, the header, and the caveat's own wording, which wanted shortening
  anyway.
- **Known limit: 320x568.** At that size — an iPhone SE of the first generation — the tile
  layout clips portions badly and the button is still pushed off. 360x640 and up is clean
  and is what the layout is built to.
- **The truncation check that cleared the earlier versions of this page was broken.** It
  skipped any element with children, and this framework wraps every interpolated string in
  a `<span class="sc-interp">` — so it was scanning the styled label, finding one child, and
  moving on. It reported "(none)" for pages that were visibly clipping. It now walks every
  element and compares `scrollWidth` against `clientWidth` with no filter, and was validated
  by forcing a 300px viewport and confirming it fires. Six rounds are also drawn from a
  reshuffled deck each run, so a single clean game proves nothing; the sweep plays five
  games per browser session and reports the pair count it actually saw.
- **The deck is built so that size cannot answer the question.** That is the whole design,
  and it is a measured property rather than a hope: across the 399 playable pairings, the
  bigger portion carries more calories 51% of the time. A player who knows nothing and
  always picks the fuller plate scores a coin toss. The first deck scored 58% that way,
  which is a real shortcut; matching the calories instead only inverts it — always pick
  the smaller plate scored 56% on that version. Neither matching sizes nor matching
  calories is the answer. What works is having, at every size, both a cheap food and an
  expensive one: one carrot is 25 kcal and half a cup of almonds is 428, both a small
  plate; three cups of cucumber is 47 and two cups of brown rice is 497, both a large one.
  Calories still run 25 to 604, which is what keeps a pair answerable at all.
- 36 foods, four sets of nine, portions that are what a person would actually serve —
  three tablespoons of olive oil is a dressed salad, not a thimble. `tools/build_pairs_deck.py`
  builds it from four 3x3 grids in `data/pairs/raw/`, and the rule it is built on is that
  **the weight is never typed in**: it is USDA's own published household portion for that
  food multiplied by a whole number, and the calories are that weight against USDA's own
  energy density. The tool fails rather than invent a figure.
- Every tile is counted against its label before it is used. Three of the 36 came back
  holding something other than what was asked: seven strawberries rather than eight, four
  rashers of bacon rather than three, and a whole bar of dark chocolate rather than half
  of one — which alone moved that card from 302 kcal to 604. They are relabelled rather
  than rejected, because the rule survives it: the number is simply counted off the
  finished picture instead of taken from the prompt. Counting is the only reason any of
  this can be checked, which is why the deck leans on foods that arrive in countable units.
- The Nutrition5k plate deck and `tools/build_game_deck.py` stay in the repo. That game
  asked how many calories a whole tray held, against a figure that had been weighed; this
  one asks a smaller question about pictures that were not. They are different trades and
  the first is one revert away.
- CALORIE CALC will work a daily target backwards from a body-fat goal. It is not built. Their pages say UNDER DEVELOPMENT and then invite
  the reader to follow the project on GitHub or reach Nick Green on LinkedIn, because an
  unbuilt app is a better invitation than a dead end. The lines arrive in turn rather than
  appearing at once — two identical keyframes, picked by which app is open, because
  switching tabs keeps the same node and only a change of animation-name restarts it —
  and the sentence reserves room for the longer of the two, so the pages are the same
  height to the pixel and nothing moves when you switch between them.

- ADD and the bin are drawn as the same object in opposite colours: a bordered box, a mark
  and a word — a plus and ADD in cyan on a search food, a bin and DEL in coral on a plate
  row. They were a bare word and a bare icon, which read as decoration sitting next to the
  steppers: the one control on the row that actually commits anything looked the least like
  a control. Same size as each other, so neither is the louder of the two.
- The measure is two words, not a menu: 100 G or OZ. On desktop they sit above the
  table's right side, the active one lit like a tab — the SIZE header and its popover
  are gone, though the column of values stays. Mobile's popover stacks full-width
  sections: MEASURE (the two options side by side), COLUMN (a two-by-five grid in the
  donut's own order — water before protein, each macro ahead of its parts), SORT
  (RELEVANCE, or the chosen column with an arrow that flips between highest-first and
  lowest-first on a second tap), then the thermic-effect switch. Picking a new column
  carries an active column-sort with it.
- The FULLNESS column is fixed now — the expanded sub-columns made a swappable extra
  column redundant. Every header explains itself the same way: hovering any of them —
  water, the macros, the six sub-macros, calories, fullness — gives its name and a
  sentence. The basis menu that used to hang off PROT, CARBS and FATS is gone with the
  bases themselves: a column that could silently be showing percentages or calories made
  every figure a question, and grams answers it.
- The desktop table wears the donut's own colours: each macro column's bar is its slice's
  hue — protein cyan, carbs green, fat coral, water an indigo the donut wears too, moved
  off blue so it could never be read as protein's cyan — sheer enough that the
  figure stays the loudest thing in the cell. The six sub-macro bars keep to two flat
  tones, one green and one coral: the donut's brightness ramp died into the ground at
  bar alpha. WATER rides its own sortable column left of
  PROT, and the macro headers say CARBS and FATS, as the drawing does. The SIZE header
  sits at its column's left edge, where its values start, and with OZ as the measure the
  whole table speaks ounces wherever it spoke grams — figures, water, sub-macros,
  totals — two decimals below ten. The actions header
  carries a circled triangle pointing where the table will go — right to open, left to
  come home: pressing it widens the app and trades
  the CARBS and FATS totals for six sub-macro columns of the same weight as any other —
  SUGAR FIBRE STARCH, SAT MONO POLY — each header wearing its parent's three-letter mark
  (CAR, FAT) pinned at the cell's left in darker type, names six characters at most, no
  unit suffixes, all on the one header line. Every track exists all
  the time (a grid ignores display:none children, which would shuffle every cell that
  follows); collapsed sub tracks are 0rem wide and the two totals make the reverse
  journey, and keeping the track count constant is
  what lets grid-template-columns interpolate, so the whole table — rows, headers, plate,
  totals, even the continuation lines below the last row — breathes as one animation
  rather than snapping. Column gaps are gone (a gap beside a 0rem track is dead space
  that never closes); the cells carry their own padding instead. The sub columns always
  speak grams, whatever basis the macro columns are in. The numeric tracks hold one
  narrow width in both modes — the figures never needed more — so the expansion animates
  only the six sub tracks and the shell, and offscreen rows carry content-visibility so
  a 250-row table isn't relaid out per frame; the two together are the difference
  between a stutter and a glide. Two strong rules and no more: one opens the numeric
  block at WATER, one fences the actions column — everything between is a hairline,
  because two strong lines side by side read as a doubled border; the actions fence is
  1px like everything else, since double thickness read as a doubled line. The desktop
  totals row says MY FOOD SUMMARY, keeps a copy button in the actions column — the same
  shopping list the mobile header copies — and its FULLNESS is the average of its foods'
  scores, each weighing in at the grams it was added at. There is deliberately no
  target to compare against: converting a calorie figure into a protein or carbohydrate
  goal is contested enough that the table would be taking a side it has no business
  taking. It states what is on the plate.
  SAT reads SATURA in the expanded header, since six characters were there to spend.
  With OZ as the measure the plate's size inputs read and edit in ounces to one
  decimal — what is being typed is held verbatim until the field blurs, so a dot never
  vanishes mid-thought — while the plate keeps counting grams underneath, and the
  totals line follows suit.
- Both layouts open on the search line alone, centred both ways — on mobile the magnifier
  and library button step out of the flow so the placeholder holds the exact middle — and
  lift it to the header on the first keystroke. Reaching for the search box, or typing a different query, returns the list to
  the top.
- The plate reads newest first. A food joins at the top row: a slot opens to the row's
  height and the row drops into it from above, out of a cyan wash. Taking one off reverses
  it — the row lifts out and the slot folds shut, and only then does the food actually leave,
  so it can rise back into the search list from below through a slot of its own. The slots
  are wrappers around each row, because the rows carry a `min-height` and `min-height` beats
  `max-height`; `--od-row` tells each slot the height it is opening to, since a phone's rows
  are taller than a desktop's.
- No CORE library. The everyday-food problem is solved in the search order rather than by
  filtering the data, so a long result list costs nothing. SR Legacy is the library; the
  switcher that once offered FNDDS is gone — one good default beat a menu — though the
  FNDDS file still ships for the loader. `data/core.json` stays for the root site, which
  still opens on it. ABOUT, which lived in that menu, is a quiet line on the launcher now.
- Mobile's measure · column selector rides in the search bar itself rather than a bar of
  its own, sharing one type size with the input, and its column names run to eight
  characters at most — FULLNESS, SAT FAT — so the selector never crowds the query.
- Search matches every word of the query, in any order, and treats a plural as its
  singular in both directions — "apple" finds `Apples, raw`, "eggs" finds `Egg, whole, raw`,
  "berry" reaches `Blueberries`. Results are then scored by how the query landed: 20 for a
  whole word, 12 for the start of a longer one, 4 for a hit buried inside one. Filling a
  whole word only reaches the top tier if the query was three characters or more — "t" fills
  the "t" of `t-bone steak` exactly and means nothing by doing so.
  Bonuses mostly settle foods that landed the same way: 10 for being the whole head of the
  name, all of it, before USDA's qualifiers start — `Cheese,` is cheese and `Cheese food,`
  is something else, so it outweighs even being an everyday food, and it can only apply
  where every query word already filled a word of the name. Then 7 for the everyday list,
  up to 3 for landing in the name's first words, and up to 3 for how much of the word the
  query spelled — measured on the singular, so a plural is not a worse match than its own
  singular. Opening the name is worth 1 when the query was a whole word and 9 when it was a
  fragment: a whole word identifies the food by itself, so where it sits hardly matters,
  while a fragment carries nothing else, so typing "j" is a request for foods called
  J-something rather than for `Orange juice`, however everyday orange juice is. A multi-word
  query that opens the name gets the same 9 — "chicken br" is the user typing
  `Chicken breast` from its start, and it outranks the everyday `Chicken, broilers`. The exception is 8 for not being a brand,
  which is a whole tier: nobody searching for a food means a restaurant's version of it
  first, so `T.G.I. FRIDAY'S` loses "t" to `Tomatoes` and `Tofu`. A brand is USDA shouting
  in capitals (`QUAKER`, `MEAD JOHNSON`, `KFC`) or a possessive (`McDonald's`) — which
  catches SR Legacy well and FNDDS barely, since FNDDS keeps its brands inside parentheses
  that generic foods use too (`(Alaska Native)`). Ties go to the shorter name, then the
  alphabet. Nothing about any of it is visible: no badge, no dot.
- The everyday flag is an eleventh element on each food row, written by
  `tools/mark_common.py`; the root site reads ten and ignores it.
- Opening a food on mobile shows the amount two ways, with an `=` between them: grams, and
  the same amount as household servings ("1 MEDIUM", "1 SLICE", "1 TBSP"). Every food has a
  second unit — the quarter of SR Legacy that USDA only ever weighs falls back to OUNCES,
  or to cups and tablespoons if it is a liquid. If OUNCES is the header measure too, that
  pair turns round: your chosen measure on the left, grams on the right, since "28 g = 1
  OUNCES" converts nothing. Whichever side you tap takes the
  − and + — grams move in tens, servings in whole servings, and picking a side does not
  round until a stepper is pressed. The macros follow, a reset arrow (faint until the
  amount moves off the header measure) puts it back, and ADD puts that amount on the plate.
  `tools/add_portions.py` writes the serving onto the food row as a twelfth and thirteenth
  element.
- With OZ as the header measure, the bar under the search says simply OZ behind a small
  monochrome stars-and-stripes flag — the audience that thinks in ounces is one country —
  and the whole drawing speaks ounces with it: the table beside the donut, and the figure
  the hole shows with a macro open, two decimals below ten because most foods are
  fractions of an ounce. Picking any measure also restates an open food's amount as one
  of it, so choosing OZ lands on exactly 1 oz.
- FULLNESS is checked against evidence rather than asserted. `tools/calibrate_fullness.py`
  matches 33 of the 38 foods in Holt's 1995 satiety index — the only measured satiety data
  there is — to SR Legacy and reports rank correlation, judged leave-one-out: fit on 32
  foods, predict the 33rd. Refitting all six parameters scores 0.795 on the foods it was
  fitted to and 0.530 on one it has not seen, which is overfitting, so the weights chosen by
  judgement stand. One term survived the test on its own and is now in the score: sugar per
  100 kcal at −0.5, which takes the correlation from 0.759 to 0.805. Water was tested too
  and earns nothing — it correlates 0.96 with the bulk term and the fit sets its weight to
  zero every time. The sugar term's known unfairness is that USDA reports total sugars, so
  an apple is charged the same gram as a jellybean.
- An open food is a donut in two equal rings, with two levels of story. At rest it tells
  the whole food: the inner ring is all of 100 g — macros as one light slice, then water,
  ash, alcohol when there is any — and the outer ring rides only the macros slice's arc,
  breaking it into protein, fat, carbs (fat between the two, because cyan and green are
  the pair a tritan eye loses), the run centred at three o'clock to face the table. The
  hole states the split that matters, everything-else / macros of 100: watermelon says
  92/8, parmesan 30/70. With a macro open it says that macro's grams instead, and the two
  figures trade places on the choreography's own clock — the split slips out with the
  flare, the grams arrive as the sweep closes, leave first on the way back, and the split
  returns as the sweep lands, ahead of the final brighten. Each macro's grams is its own layer, so switching
  straight from fat to carbs cross-fades the two figures directly. The sub rows' hairline
  is an inset shadow inside their 30px rather than a border — a border adds height the
  height transition does not govern, and its snap at the end of a switch was a visible
  jolt — and opening and closing share one duration and curve, so when a switch runs both
  at once the two groups' heights cancel exactly and nothing below them moves off-beat. The table sits against the right edge on a subtle interior grid —
  hairlines between rows and before the gram column, no outer border, the gram figures
  held a step off the screen's edge — dot, name, grams,
  with the macro rows indented under MACROS. Fats and carbs are the two slices with more
  to say, so those rows wear a ringed +, pinned against the gram column — unless the
  macro is under 1 g per 100, where there is nothing worth opening and no ring to
  promise it. Only the ring opens: the row's name is a pick like any other row's, so
  tapping CARBS highlights carbs rather than unpacking them. Collapse is more lenient —
  with a macro open, its name, its −, and the drawing itself all fold it. Pressing one
  plays the move rather than cutting to it: the slice first flares bright where it
  stands, then slides in from the outer ring and sweeps the inner one like a clock hand
  until the macro owns the whole circle — the hole handing its split over to that
  macro's grams, in that macro's colour — while its
  own parts fade up on the ring it vacated — saturated, mono, poly for fat; sugars,
  fibre, starch for carbs — and the rest of the donut steps back to quarter strength.
  The outer ring and both sub-rings are dash patterns on pathLength-100 circles rather
  than arc paths, because a dash can wind and an arc cannot. Opening a macro, the rest
  of the donut dulls in the same breath as the flare — the slice is the only bright thing
  from the first frame — then its neighbours wind out dull, the slice slides in (the
  circle's own r) and sweeps the inner ring like a clock hand, and its own parts wind in
  on the ring it left; closing runs the film backwards — the parts wind up first,
  dulled the instant the unwinding starts, the sweep retraces still bright, the resting
  ring winds back in still dull, and brightness returns to everything only after the
  winding has fully landed. The bracket shrinks with the rows it hugs before it fades,
  rather than fading before its shrink can be seen. The row scrolls to the top, and that macro's table
  rows slide open beneath their parent — they are always in the table, holding no height
  and a zero-width border until their macro is pressed, so opening is a height transition
  the rows below ride along with — inside a bracket drawn in the drawing's own pixels,
  possible because every row height and the table's right-hugging width are fixed. The
  open macro's rows lean forward and the rest lean back, the same quarter-step the donut
  takes. Tapping any other row is a pick: its slice brightens above a receding ring, its
  name and figure do the same in the table, and the hole's emphasis swaps with it — a
  water-side pick brightens the left figure, a macro pick the right. Every dim and every lift in the
  drawing is an opaque stroke colour computed in JS — never opacity, which lets the layer
  beneath a slice read as a second, ghost donut, and never a CSS filter, which iOS Safari
  does not apply to SVG elements at all; the rgba shades are composited onto the panel
  first, so no slice is ever see-through. The flare is a stroke tint keyframe for the
  same reason. The brackets are spans rather
  than paths — a span's top and height can animate where a path's d cannot — so each one
  grows, shrinks and shifts with the very rows it hugs. Picking MACROS
  lights the inner macros slice alone and dulls the outer run with everything else, so
  one thing on the ring answers the tap; under a sub pick the sweep dulls harder than
  usual, because a macro's own colour is naturally brighter than its parts and the picked
  part must win. While a macro is
  open, its own sub rows pick in place; any other row folds the macro on its way to the
  pick, quickly — the long unwinding is reserved for a tap on the drawing itself, held by
  a short-lived wind flag so that clearing a pick never waits on the choreography's
  delays. TRANS is wired through the fat breakup — loader, row, slice, remainder — and
  appears the moment the data pipeline runs with FDC nutrient 1257 aboard; MONO and POLY
  say what MUFA and PUFA meant. The ring's position is a constant that nothing beneath it
  may move, and the expansion's height is computed from what the table actually needs. A tap anywhere on the drawing folds it back — the ringed − on the open row says
  so — and the other macro's + presses through and switches directly. Ash stays a top-level part rather
  than a macro, because it is the mineral residue — matter with no energy in it — and the
  macros figure is the food's energy-bearing weight. A whole ring is drawn as two semicircles rather than a 359.8° arc,
  whose butt caps would meet in a hairline seam. The SVG holds geometry only (the template
  engine wraps interpolated text in spans, which SVG will not paint); the hole's figures
  and the table are HTML. The chosen column's figure keeps the row's top right corner; the
  reset opens the controls row.
- While a search food is open, the plate lends it the height: the summary folds to its
  header line, which lays itself on the same three tracks as the rows so the gram and
  chosen-column totals stay on show, right-aligned where they always are, with the ringed
  + on the far left of the title; the copy button steps aside while tucked.
  The fold is also the user's to work: tapping the header of an open summary folds it (and
  closes any open plate row, whose height it was), and tapping a folded one anywhere brings
  it back, closing the open search food that had borrowed the room. The fold animates as a
  grid row going 1fr to 0fr — the one animatable route to a content-sized height, since
  max-height as a length and as a percentage never interpolate, which is why it used to
  snap shut.
- Plate rows open the same way, with a bin where ADD was, and edit the plate's own
  amount. A row can also be swiped off to the left: the gesture only takes over once it
  is clearly more sideways than down, so the list still scrolls under a travelling
  thumb, and only a closed row will take it — an open one has a drawing in it that owns
  the finger. The row slides as a solid strip over a coral ground with the bin waiting
  at the edge, runs slower past the point of no return so the thumb is told it has gone
  far enough, and springs back if let go short of it. Past it, the row keeps going off
  its own edge and the fold that always followed a removal takes it from there. An open plate row sits on its own lighter ground, so the food being edited
  reads as lifted out of the list it came from.
  Collapsed, a plate row just states its grams — the steppers live in the expansion.
- The totals line wears the same ringed + as fats and carbs, on its left so the totals
  keep their right-hand columns, and the whole bar is the button. Pressing it expands the
  bottom bar into the very drawing an open food gets — donut, hole split, table, macro
  rings, picks, the lot — computed for the plate summed as one food: absolute grams
  re-expressed per 100 g, so the same code that explains one food explains the whole
  plate at once. Open, the bar's three shorthands (PRO CAR FAT) step aside for the view's
  name — SUM TOTALS drifts up into their place — and the panel keeps one expansion at a
  time: opening the totals folds any open plate row, and opening a plate or search food
  folds the totals. Nothing else does — a stray tap outside the drawing leaves it be;
  only its own ring, the bar, or a deliberate expansion elsewhere folds it.
- The plate's totals line rides the same three tracks as its rows, so the amount and the
  chosen measure sit under the columns they are totals of rather than in a row of evenly
  spaced figures. Its header carries one control: copy, which puts the plate on the
  clipboard as a shopping list — a dashed line per food with its grams, its own household
  measure in brackets, and the chosen column, then the totals — because the place a plate
  gets pasted is a message, not a spreadsheet. Removal mode is gone with the bin that
  opened it; a food leaves from the bin in its own expansion.

There is one `index.html`, at the root, and it is what opendiet.org serves. Edit it and
push to `main`; GitHub Pages builds from `main` and there is no promotion step to forget.
