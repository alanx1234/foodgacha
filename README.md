# foodgacha

foodgacha is a Python command-line tool that combines restaurant recommendations
with gacha pulls and dating app mechanics. I chose this idea because I suck
at finding new places to eat and also cause I love food.

## Usage

Set your default location and swipe through preference cards:

```console
$ foodgacha config --location "San Diego, CA"
$ foodgacha swipe
```

Pull a restaurant using your saved preferences:

```console
$ foodgacha pull
```

Override saved filters for one pull without changing them:

```console
$ foodgacha pull --location "La Jolla, CA" --cuisine japanese --price 2
```

Log a visit using a full or partial restaurant name, then review your history
and statistics:

```console
$ foodgacha visit "Tajima" --rating 8 --notes "Get the miso ramen"
$ foodgacha history --limit 20
$ foodgacha stats
```

Run `foodgacha --help` or `foodgacha COMMAND --help` for every option.

## Installation

foodgacha requires Python 3.11 or newer and
[uv](https://docs.astral.sh/uv/). It uses OpenStreetMap and does not require an
API key or paid account.

Install the command directly from GitHub:

```console
$ uv add "git+https://github.com/alanx1234/foodgacha.git"
$ uv run foodgacha --help
```

## How Recommendations Work

Foodgacha uses OpenStreetMap to turn your location into coordinates and find
nearby restaurants, cafes, fast-food places, and food courts. Location lookups
are cached locally, and restaurant results are reused for six hours to avoid
unnecessary requests to community-run services.

### Swiping

The swipe feature works like a terminal-based dating app. Press the right arrow
or `y` to keep a cuisine, price, or vibe, and press the left arrow or `n` to
skip it. Foodgacha saves your choices for future pulls and uses them to find
restaurants that fit what you are in the mood for.

### Rarity Tiers

Rarity describes how well a restaurant matches **you**, not whether the
restaurant is objectively good or bad. A Common result can still be a great
restaurant; it simply matched fewer of your current preferences.

Foodgacha gives each nearby restaurant match points:

- Exact cuisine match: **+40 points**
- Each matching vibe: **+15 points**
- Matching price preference, when available: **+10 points**
- Within two miles: **+15 points**
- Helpful details such as hours, a website, takeaway, or accessibility:
  **up to +10 points**
- Previously visited: **-20 points**, unless you selected Old Favorite

The final score determines the restaurant's tier:

| Tier | Match score | Pull rate | What it means |
| --- | ---: | ---: | --- |
| SSR | 85-100 | 5% | The restaurant of your dreams |
| SR | 70-84 | 15% | A restaurant you'll love |
| Rare | 50-69 | 25% | A memorable restaurant|
| Uncommon | 30-49 | 30% | A decent restaurant|
| Common | 0-29 | 25% | A forgettable restaurant |

Every non-SSR result raises the pity counter. When the counter reaches nine,
the next pull is guaranteed to be SSR when the current search contains an SSR
match. This is a popular mechanic in gacha games. If that search has no SSR
matches, foodgacha chooses from the available tiers and keeps the pity counter
active for a future pull.

Restaurants marked as visited in the last seven days are excluded. "Something
New" excludes every restaurant already in your history, while "Old Favorite"
only permits previously visited restaurants, including recent favorites. If
you select both Something New and Old Favorite, they cancel each other out so
the search remains broad instead of becoming impossible.

Restaurant and location data is provided by
[OpenStreetMap contributors](https://www.openstreetmap.org/copyright) under the
Open Data Commons Open Database License. Public OpenStreetMap services are
best-effort resources, so occasional timeouts may require trying the pull
again.
