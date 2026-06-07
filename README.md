# foodgacha

foodgacha is a Python command-line tool that makes choosing a nearby restaurant
feel like a gacha pull. It saves your cuisine, price, and dining preferences,
searches Yelp, and uses rarity odds plus a pity counter to recommend somewhere
to eat without making you scroll through another long list.

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

The assignment's required dependency-install check also works from inside
another uv project:

```console
$ uv add "git+https://github.com/alanx1234/foodgacha.git"
$ uv run foodgacha --help
```

For local development:

```console
$ git clone https://github.com/alanx1234/foodgacha.git
$ cd foodgacha
$ uv sync
$ uv run foodgacha --help
$ uv run pytest
```

## How Recommendations Work

Each Yelp result is placed into a rarity tier:

| Tier | Rule | Pull rate |
| --- | --- | ---: |
| SSR | Yelp rating at least 4.5 and at least 200 reviews | 5% |
| SR | Yelp rating at least 4.0 or at least 100 reviews | 35% |
| R | Every other result | 60% |

Every non-SSR result raises the persistent pity counter. When the counter
reaches nine, the next pull is guaranteed to be SSR when the current search
contains an SSR candidate. If Yelp returns no SSR candidate, foodgacha chooses
from the available tiers and keeps the pity counter active for a future pull.

Restaurants marked visited in the last seven days are excluded. "Something
New" excludes every restaurant already in your history, while "Old Favorite"
only permits previously visited restaurants. Other vibes boost likely matches
within a rarity tier because Yelp does not expose exact filters for concepts
such as "filling" or "quick."

## Local Data

Preferences, pull history, ratings, and the pity counter are stored in:

```text
~/.foodgacha/data.json
```

Set `FOODGACHA_DATA_FILE` to use a different path, which is useful for testing
or keeping separate profiles. Your Yelp API key is only read from the
environment and is never written to this file.
