# foodgacha

foodgacha is a Python command-line tool that combines restaurant recommendations with
gacha pulls and dating app mechanics. I chose this idea because I'm terrible at finding new places
to eat.

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

foodgacha requires Python 3.11 or newer, [uv](https://docs.astral.sh/uv/), and
a Yelp API key.

1. Create an API key in the
   [Yelp developer portal](https://docs.developer.yelp.com/docs/fusion-authentication).
2. Make the key available in your shell:

   ```console
   $ export YELP_API_KEY="your-key-here"
   ```

3. Install the command directly from GitHub:

   ```console
   $ uv tool install "git+https://github.com/alanx1234/foodgacha.git"
   ```

## How Recommendations Work


Each Yelp result is placed into a rarity tier:

| Tier | Rule | Pull rate |
| --- | --- | ---: |
| SSR | Yelp rating at least 4.5 and at least 200 reviews | 5% |
| SR | Yelp rating at least 4.0 or at least 100 reviews | 35% |
| R | Every other result | 60% |

Every non-SSR result raises the pity counter. This is a popular mechanic in gacha games. When the counter
reaches nine, the next pull is guaranteed to be SSR when the current search
contains an SSR candidate. If Yelp returns no SSR candidate, foodgacha chooses
from the available tiers and keeps the pity counter active for a future pull.

The swipe feature works like a dating app. Foodgacha saves the
preferences you choose for future pulls. Cuisines and prices filter Yelp results, while vibes
filter or increase the weight of matching restaurants.

Restaurants marked  as visited in the last seven days are excluded. "Something
New" excludes every restaurant already in your history, while "Old Favorite"
only permits previously visited restaurants. Other vibes boost likely matches
within a rarity tier because Yelp does not expose exact filters for concepts
such as "filling" or "quick."
