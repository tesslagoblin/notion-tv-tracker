"""Curated Vibes tag bank + auto-tag rules.

Each vibe has:
 - keywords: TMDB keyword substrings that hint at this vibe
 - shows: explicit whitelist of shows in my library that fit
 - genres: TMDB genres that must be present (any-of)
 - anti_shows: shows that would false-positive on keywords but shouldn't be tagged

Auto-tagger checks a show against every vibe and applies each match.
The bank is intentionally opinionated. Prune it or add your own tags.
"""

VIBE_BANK = {
    # ─── COMEDY FLAVORS ───────────────────────────────────────
    'Sitcom Classic': {
        'keywords': ['sitcom'],
        'shows': ['Friends','Seinfeld','Curb Your Enthusiasm','Frasier','Cheers',
                  'The Big Bang Theory','How I Met Your Mother','Everybody Loves Raymond',
                  'Grace and Frankie','Dave','The Other Two','The Righteous Gemstones',
                  'Dynasty'],
        'genres': ['Comedy'],
    },
    'British Awkward': {
        'keywords': ['british', 'cringe', 'awkward'],
        'shows': ['The Inbetweeners','Peep Show','The Office (UK)','Fleabag',
                  'This Country','Derry Girls','Am I Being Unreasonable?',
                  'Friday Night Dinner','Fresh Meat','Gavin & Stacey'],
        'networks': ['Channel 4','BBC One','BBC Two','BBC Three'],
    },
    'Dark Comedy': {
        'keywords': ['dark comedy','black comedy','satire'],
        'shows': ['The End of the F***ing World','Fleabag','Barry','You',
                  'Killing Eve','Search Party','Dead to Me','Russian Doll',
                  'Bojack Horseman','I May Destroy You','The Other Two',
                  'The Righteous Gemstones','Dave','Hacks','Overcompensating',
                  'Atlanta','Shameless (US)','Nip/Tuck','Dear White People'],
    },
    'Workplace Comedy': {
        'keywords': ['workplace comedy','office','workplace'],
        'shows': ['The Office','The Office (UK)','Parks and Recreation',
                  'Superstore','30 Rock','Abbott Elementary','Brooklyn Nine-Nine',
                  'The Studio','Silicon Valley'],
    },
    'Ensemble Hangout': {
        'keywords': ['group of friends','friendship','roommates','ensemble cast'],
        'shows': ['Friends','New Girl','Community','How I Met Your Mother',
                  'Broad City','Insecure','Seinfeld','Girls','Living Single',
                  'Overcompensating','The Other Two','Colin From Accounts',
                  'Greek','Off Campus','Dear White People','Stumble'],
    },
    'Absurdist / Sketch': {
        'keywords': ['sketch comedy','absurd','absurdist','surreal comedy'],
        'shows': ['I Think You Should Leave','Astronomy Club: The Sketch Show',
                  'Key & Peele','Portlandia','What We Do in the Shadows',
                  'The Good Place','Rick and Morty','Regular Show','Adventure Time',
                  'Los Espookys','The OA'],
    },

    # ─── TEEN / YOUNG ADULT ────────────────────────────────────
    'Teen Soap': {
        'keywords': ['teen drama','teenage romance','high school'],
        'shows': ['Gossip Girl','One Tree Hill','Riverdale','Pretty Little Liars',
                  'The O.C.','90210','Beverly Hills 90210','Dawson\'s Creek',
                  'Elite','Euphoria','My Life with the Walter Boys',
                  'The Summer I Turned Pretty','Outer Banks','13 Reasons Why',
                  'Bel-Air','Smallville','Hannah Montana','Revenge','Greek',
                  'Spinning Out','Tell Me Lies','Off Campus','Maxton Hall - The World Between Us',
                  'Dollface','All\'s Fair'],
    },
    'Coming of Age': {
        'keywords': ['coming of age','coming-of-age','teenage sexuality'],
        'shows': ['Sex Education','Never Have I Ever','Derry Girls',
                  'The End of the F***ing World','Big Mouth','Normal People',
                  'The Half of It','PEN15','My So-Called Life',
                  'Bel-Air','Dear White People','Off Campus','Tell Me Lies','Greek'],
    },
    'Y2K Nostalgia': {
        'keywords': ['2000s','y2k'],
        'shows': ['The O.C.','Gossip Girl','One Tree Hill','Gilmore Girls',
                  'Buffy the Vampire Slayer','Charmed','Sex and the City',
                  'Dawson\'s Creek','Beverly Hills 90210','Sabrina, the Teenage Witch',
                  'That \'70s Show','Friends','Will & Grace',
                  'Hannah Montana','Smallville','Greek','Revenge','Nip/Tuck'],
    },
    'Supernatural Teen': {
        'keywords': ['supernatural','witch','vampire','teen witch'],
        'shows': ['Buffy the Vampire Slayer','Charmed','The Vampire Diaries',
                  'The Originals','Legacies','Sabrina, the Teenage Witch',
                  'Chilling Adventures of Sabrina','Wednesday','Locke & Key',
                  'Smallville','Lucifer'],
    },

    # ─── GIRLY POP / FEMME ─────────────────────────────────────
    'Girly Pop': {
        'keywords': [],
        'shows': ['Sex and the City','And Just Like That...','Emily in Paris',
                  'Bridgerton','Gossip Girl','The Bold Type','Younger',
                  'Legally Blonde','The Sisterhood of the Traveling Pants',
                  'Never Have I Ever','Ginny & Georgia','Selling Sunset',
                  'Nobody Wants This','The Summer I Turned Pretty','My Life with the Walter Boys',
                  'And Just Like That…','Elle','Emily in Paris','Dynasty',
                  'Dollface','My Lady Jane','Maxton Hall - The World Between Us',
                  'All\'s Fair','Dynasty (2017)','Insatiable'],
    },
    'Female Friendship': {
        'keywords': ['female friendship','sisterhood','best friends'],
        'shows': ['Broad City','Girls','Insecure','GLOW','Sex and the City',
                  'The Bold Type','Younger','PEN15','Girlfriends','2 Broke Girls',
                  'The Sisterhood of the Traveling Pants','And Just Like That...',
                  'Grace and Frankie','Hacks','Dollface','Too Much','The Girls on the Bus'],
    },
    'Chaotic Woman': {
        'keywords': ['female protagonist','anti-hero','messy'],
        'shows': ['Fleabag','Killing Eve','I May Destroy You','Yellowjackets',
                  'Sharp Objects','Russian Doll','Dead to Me','Poker Face',
                  'You','Search Party','The Girlfriend Experience',
                  'Hacks','Industry','Revenge','I Love Dick','Orphan Black',
                  'Nip/Tuck','Too Much','Secret Diary of a Call Girl'],
    },
    'Sad Girl': {
        'keywords': ['depression','loneliness','grief'],
        'shows': ['Fleabag','Normal People','The End of the F***ing World',
                  'I May Destroy You','Sharp Objects','My Mad Fat Diary',
                  'Skins','Euphoria','Girls'],
    },

    # ─── PRESTIGE ──────────────────────────────────────────────
    'Prestige Drama': {
        'keywords': ['prestige','critically acclaimed'],
        'shows': ['Mare of Easttown','Big Little Lies','Succession','The Crown',
                  'Sharp Objects','The White Lotus','Nine Perfect Strangers',
                  'Yellowjackets','The Handmaid\'s Tale','The Sopranos','Mad Men',
                  'Breaking Bad','Industry','House of Guinness','The Wire',
                  'Yellowstone','Atlanta','Squid Game','Station Eleven',
                  'The Testaments','1899','The Idol','Nip/Tuck','Underground'],
    },
    'British Class': {
        'keywords': ['british aristocracy','downton','british class system'],
        'shows': ['The Crown','Peaky Blinders','Downton Abbey','Bridgerton',
                  'Fleabag','The Great','Sanditon','Poldark','Victoria',
                  'Pistol','House of Guinness'],
    },
    'Anthology / Limited': {
        'keywords': ['miniseries','limited series','anthology'],
        'shows': ['Mare of Easttown','Big Little Lies','Nine Perfect Strangers',
                  'Sharp Objects','The Undoing','I\'ll Be Gone in the Dark',
                  'Black Mirror','American Horror Story','American Crime Story',
                  'The Studio','The Girl From Plainville','Station Eleven','Lost',
                  'The Testaments'],
    },

    # ─── FANTASY / GENRE ───────────────────────────────────────
    'Fantasy Epic': {
        'keywords': ['dragon','magic','fantasy','sword and sorcery'],
        'shows': ['Game of Thrones','House of the Dragon','The Witcher',
                  'The Wheel of Time','Shadow and Bone','His Dark Materials',
                  'The Lord of the Rings: The Rings of Power','Wednesday',
                  'Avatar: The Last Airbender','Daredevil: Born Again',
                  'X-Men \'97','My Lady Jane'],
    },
    'Witchy / Occult': {
        'keywords': ['witch','magic','occult','coven'],
        'shows': ['Buffy the Vampire Slayer','Charmed','Chilling Adventures of Sabrina',
                  'Sabrina, the Teenage Witch','What We Do in the Shadows',
                  'A Discovery of Witches','Practical Magic','American Horror Story: Coven'],
    },
    'Sci-Fi Weird': {
        'keywords': ['multiverse','existential','absurd','time travel'],
        'shows': ['Rick and Morty','The Good Place','Russian Doll','Legion',
                  'The Leftovers','Undone','Loki','Severance','Kevin Can F**k Himself',
                  '3 Body Problem','Altered Carbon','Dark Matter (2024)','1899',
                  'Station Eleven','The Man In The High Castle','Star Trek: Starfleet Academy',
                  'Orphan Black','To The Lake'],
    },

    # ─── VIBE / MOOD ───────────────────────────────────────────
    'Cozy Watch': {
        'keywords': ['heartwarming','feel-good','comforting','wholesome'],
        'shows': ['Ted Lasso','Schitt\'s Creek','The Great British Bake Off',
                  'Gilmore Girls','Sweet Magnolias','Virgin River','Heartstopper',
                  'Only Murders in the Building','Somebody Somewhere',
                  'The Four Seasons','Nobody Wants This','Colin From Accounts',
                  'Every Year After'],
    },
    'NYC-Set': {
        'keywords': ['new york city','manhattan, new york','brooklyn'],
        'shows': ['Sex and the City','And Just Like That...','Girls','Broad City',
                  'Friends','How I Met Your Mother','Seinfeld','Only Murders in the Building',
                  'Younger','The Bold Type','Search Party','Master of None',
                  'Elementary','Gossip Girl'],
    },
    'Small Town': {
        'keywords': ['small town','rural'],
        'shows': ['Schitt\'s Creek','Ted Lasso','Gilmore Girls','Sweet Magnolias',
                  'Virgin River','Somebody Somewhere','Everwood','Hart of Dixie',
                  'One Tree Hill','Sherlock','Northern Exposure'],
    },
    'Found Family': {
        'keywords': ['found family','chosen family'],
        'shows': ['Community','Parks and Recreation','Ted Lasso','Reservation Dogs',
                  'Schitt\'s Creek','The Good Place','Brooklyn Nine-Nine','Firefly',
                  'Somebody Somewhere','What We Do in the Shadows'],
    },
    'True Crime': {
        'keywords': ['true crime','murder investigation','serial killer'],
        'shows': ['Mare of Easttown','I\'ll Be Gone in the Dark','Making a Murderer',
                  'The Jinx','Dahmer','The Staircase','Tiger King',
                  'Only Murders in the Building','Sharp Objects','American Crime Story',
                  'Mindhunter','Poker Face','Interview With The Vampire',
                  'Murder Mountain','The Girl From Plainville'],
    },
    'Reality Comfort': {
        'keywords': ['reality tv','competition','cooking competition','drag'],
        'shows': ['RuPaul\'s Drag Race','The Great British Bake Off','Queer Eye',
                  'Selling Sunset','Jury Duty','The Ultimatum','Love is Blind',
                  'Nailed It!','Below Deck','The Bachelor','Chef\'s Table',
                  'Great Interior Design Challenge','Sex, Love & Goop'],
    },
    # ─── SETTING / AESTHETIC ───────────────────────────────────
    'Period Piece': {
        'keywords': ['period drama','historical drama','regency','victorian','georgian','edwardian'],
        'shows': ['Bridgerton','The Crown','Peaky Blinders','The Great','Mad Men',
                  'House of Guinness','Victoria','The Gilded Age','Pistol','Outlander',
                  'My Lady Jane','The Testaments','Interview With The Vampire','Reign',
                  'Underground'],
    },
    'Killer Costumes': {
        'keywords': [],
        'shows': ['Euphoria','Gossip Girl','Bridgerton','Emily in Paris','Sex and the City',
                  'The Idol','The Great','Peaky Blinders','Mad Men','The Crown','Girls',
                  'Younger','Ginny & Georgia','And Just Like That...','The Summer I Turned Pretty',
                  'My Lady Jane','Dynasty','Dynasty (2017)','House of Guinness','Reign',
                  'Nip/Tuck','Elle','Killing Eve','Interview With The Vampire'],
    },

    # ─── DOC / TRAVEL ──────────────────────────────────────────
    'Travel Doc': {
        'keywords': ['travel documentary','travelogue'],
        'shows': ['Joanna Lumley\'s Great Cities Of The World',
                  'Joanna Lumley\'s Greek Odyssey',
                  'Joanna Lumley\'s Hidden Caribbean',
                  'Joanna Lumley\'s Home Sweet Home',
                  'Joanna Lumley\'s India',
                  'Joanna Lumley\'s Japan',
                  'Joanna Lumley\'s Nile',
                  'Joanna Lumley\'s Silk Road Adventure',
                  'Joanna Lumley\'s Trans-Siberian',
                  'Lost Cities With Albert Lin'],
    },
}
