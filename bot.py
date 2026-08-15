import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
import config
from cops_api import cops_api_client
from cops_tracker import snipe_tracker, leaderboard_tracker
from database import db

# ==================== CRITICAL OPS GENUINE SKIN CATALOG DATA ====================

SKIN_CATALOG = {
    "Knives": {
        "Remix": [
            "PORCELAIN",
            "PREDATOR",
            "HOT ROD",
            "POWER SURGE",
            "WRAPPED",
            "PURPLE DAMASCUS",
            "GALAXY",
            "INFRARED",
            "POWERSHOT",
            "DRACO MAGNE",
            "TRIANGULATION",
            "SECURITY",
            "DRACO RUBRA",
            "DRACO UMBRA",
            "DRACO VIRIDIS",
            "WARP TUNNEL",
            "REANIMATION",
            "SPLIT WINDOW",
            "MEEP MEEP",
            "THE GOAT",
            "ZUMA BEACH",
            "CUDA",
            "SHELL-B",
            "FRACTAL",
            "JULIENNE"
        ],
        "Kukri": [
            "POLYCULT",
            "GLOW",
            "AVIARY",
            "MARITIME",
            "WAVES",
            "SUN STONE",
            "EXTERMINATION",
            "SHIPWRECK",
            "TRIPLE ATTACK",
            "PATROL",
            "NEW CHALLENGER",
            "INDIGO",
            "KETSUI",
            "SLICE OF LIME",
            "FULMINATION",
            "VIOLET QUARTZ"
        ],
        "Karambit": [
            "BITTEN",
            "INKDROP",
            "ELITE",
            "REVOLUTION",
            "ASTROLABE",
            "OLD MONEY",
            "EFFLORESCENCE",
            "ELVEN",
            "MAGENTA VICE",
            "CICERO",
            "SWEET TOOTH",
            "ARMADILLO",
            "FURIOUS",
            "VERGLAS",
            "GAS ATTACK",
            "SANGUINE",
            "VENOMOUS SPIKE",
            "EMERALD FORTUNE",
            "EXQUISITE COUTURE",
            "KOI",
            "DINO",
            "LOOP"
        ],
        "Balisong": [
            "RIME",
            "MONARCH",
            "CRUSTACEAN",
            "CANYON",
            "CHRYSANTHEMUM",
            "FIREBRAND",
            "FROM THE DEEP",
            "SLUDGE WORM",
            "HARMONY",
            "MAGENTA VICE",
            "LIVING BLADE",
            "THE GREAT WHITE",
            "FIRE AND ICE",
            "DEEP CUT",
            "AMUR",
            "WORLD CHAMPION 2022",
            "WORLD SUPPORTER 2022",
            "BRIGHT CUT",
            "AFTERGLOW",
            "GRAND SLAM",
            "DARK JESTER",
            "SLAM DUNK",
            "CYCLONE"
        ],
        "Tac-Knife": [
            "SCYTHE",
            "TIGRIS",
            "CATACOMB",
            "GRANDEUR",
            "TUNNELS",
            "PESTILENCE",
            "CONJUNCTIVITIS",
            "BANDIT",
            "HACKTOOL",
            "SCIURIDAE SABOTEUR",
            "VIBROSLICE",
            "SWAN SONG",
            "MENDED"
        ],
        "Pipe Wrench": [
            "STARE",
            "UNDEAD",
            "MANHUNT",
            "FLY SWATTER",
            "UPROOTED",
            "JUSTICE ROD",
            "SHATTERED ICE",
            "AVANT GARDE",
            "OFF ROAD"
        ],
        "Short Sword": [
            "POWER SWORD",
            "EXCRUCIATING STARVATION",
            "SOLAR FLARE",
            "ST OF WANT",
            "DIABOLIC DIVINE"
        ],
        "Tomahawk": [
            "THE GOLDEN AGE",
            "FLAME OF CONQUEST",
            "SCRATCH MARK",
            "WET INK"
        ],
        "Meat Cleaver": [
            "INFECTION",
            "CONSECRATED DAWN",
            "BIG APPETITE"
        ],
        "Jambiya": [
            "PRISTINE",
            "DEVILISH",
            "POISONOUS",
            "SKULL MANIA"
        ]
    },
    "Gloves": {
        "Specialist": [],
        "Operative": [],
        "Tactician": []
    },
    "Pistols": {
        "P250": [
            "ALL-TERRAIN DIGI",
            "OLIVE",
            "MAPLE",
            "ASH",
            "LOTUS",
            "ARCTIC",
            "STARSTRUCK",
            "BLOOD MONEY",
            "SUNGLOW",
            "DANGER ZONE",
            "PHOENIX",
            "HARVEST",
            "PEACOCK",
            "SUGAR RUSH",
            "GLACIER",
            "OTTOMAN",
            "SPEED",
            "CYCLONE",
            "INVADERS",
            "WINTER WOODS",
            "STINGER",
            "INVERSE",
            "HONEY",
            "SIAMESE",
            "ROYAL"
        ],
        "GSR 1911": [
            "BLUE STRIPES",
            "DUOTONE",
            "OLIVE",
            "MAPLE",
            "SWAMPLAND",
            "CARMINE",
            "LOTUS",
            "ARCTIC",
            "SPOOKY",
            "CONIFER",
            "CATACOMB",
            "KIND REGARDS",
            "SEISMIC",
            "PREDATOR",
            "CIRCUITRY",
            "ANTIQUE",
            "DREAMCATCHER",
            "SNOWFALL",
            "SAKURA",
            "BRAVERY",
            "SPACE BATTLE",
            "TOMBSTONES",
            "COMPACT",
            "INVERSE",
            "SIAMESE"
        ],
        "MR96": [
            "URBAN DIGITAL",
            "OLIVE",
            "MAPLE",
            "SKY",
            "LOTUS",
            "WOODLAND",
            "ARCTIC",
            "SUNGLOW",
            "OPPOSING FORCES",
            "CAL",
            "WASTELAND",
            "PLASTIC WARFARE",
            "NIGHT LIGHT",
            "IVORY",
            "FLORAL",
            "CRUSADER",
            "SPLATTERED",
            "CONSTRUCT",
            "BLACK",
            "BOREALIS",
            "BONFIRE",
            "PASTEL PIXEL",
            "AFTER DARK",
            "HONEY",
            "SIAMESE"
        ],
        "Deagle": [
            "GREEN MARMALADE",
            "PENGUIN",
            "SAIO",
            "SABERTOOTH",
            "HYPER",
            "BOX CUTTER",
            "ENERGETIC",
            "HOT PINK",
            "HOT ROD",
            "SLIPSTREAM",
            "TAIGA",
            "CARMINE",
            "OLIVE",
            "SKY",
            "WHITE",
            "MAPLE",
            "LOTUS",
            "SCION",
            "SAMURAI",
            "CAVALIER",
            "OBJECTIVE OMEGA",
            "OBJECTIVE BETA",
            "FEINT",
            "DESERT SKIES",
            "BANGTAIL"
        ],
        "Dual MTX": [
            "HIGHLAND",
            "PINSTRIPE",
            "MAPLE",
            "SKY",
            "CARMINE",
            "LOTUS",
            "ARCTIC",
            "RETALIATOR",
            "PURGATORY",
            "ARROWHEAD",
            "DANGER ZONE",
            "HOUND",
            "SHATTER",
            "FESTIVE",
            "DELFT",
            "COMPANY OF TANKS",
            "AFTER DARK",
            "SIGNAL",
            "GUNS N TOYS",
            "INVERSE",
            "HONEY",
            "SIAMESE",
            "ROSE",
            "SUITS",
            "DUALITATTOO"
        ],
        "XD .45": [
            "HIGHLAND",
            "OLIVE",
            "MAPLE",
            "SKY",
            "LOTUS",
            "ARCTIC",
            "LAUGHTER",
            "SLAUGHTER",
            "ARROWHEAD",
            "LA MUERTE",
            "OPPOSING FORCES",
            "MASQUERADE",
            "HOT PINK",
            "FEVER DREAM",
            "INKED",
            "METEOR SWARM",
            "BLACK",
            "SNOWFALL",
            "TROPICAL",
            "BRAVERY",
            "TOMBSTONES",
            "ROADSIDE",
            "INVERSE",
            "SIAMESE",
            "ROSE"
        ]
    },
    "SMGs": {
        "MP5": [
            "DUOTONE",
            "MAPLE",
            "WOODLAND",
            "SKY",
            "LOTUS",
            "ARCTIC",
            "CONIFER",
            "COIL",
            "ARROWHEAD",
            "HOT ROD",
            "KRAKEN",
            "SUGAR RUSH",
            "FEVER DREAM",
            "LEOPARD",
            "SYNTH",
            "SCAVENGED",
            "T-REX",
            "DANDELIONS",
            "ECLIPSE",
            "WHITE",
            "TRIBAL",
            "GLACIER",
            "DELFT",
            "SPACE BATTLE",
            "AFTER DARK"
        ],
        "MP7": [
            "TAIGA",
            "OLIVE",
            "MAPLE",
            "VICTORIAN",
            "HAVOC",
            "HONEYCOMB",
            "CARMINE",
            "LOTUS",
            "WOODLAND",
            "ARCTIC",
            "CONIFER",
            "OPPOSING FORCES",
            "NOVA ALPHA",
            "SHATTER",
            "BOX CUTTER",
            "FESTIVE",
            "OTTOMAN",
            "POP STAR",
            "BRAVERY",
            "SPEED",
            "MAD SCIENCE",
            "CYCLONE",
            "WINTER WOODS",
            "SIAMESE",
            "ROSE"
        ],
        "MPX": [
            "OLIVE",
            "CARMINE",
            "BLACK",
            "WHITE",
            "LOTUS",
            "MAPLE",
            "DANGER ZONE",
            "TURQUOISE",
            "CAL",
            "HOT PINK",
            "VELOCITY",
            "URBAN DIGICAMO",
            "RED BOLT",
            "GEODE",
            "HORUS",
            "GNATHOS",
            "TELEKINESIS",
            "FLIP AND SNATCH",
            "HANNIBAL",
            "PURGE",
            "WRONG TURN",
            "OOZE",
            "FREEZING WIND",
            "PENGUIN",
            "GREEN MARMALADE"
        ],
        "P90": [
            "OLIVE",
            "MAPLE",
            "ASH",
            "WOODLAND",
            "LOTUS",
            "ARCTIC",
            "THUNDERCLAP",
            "MAELSTROM",
            "ZEBRA",
            "PREDATOR",
            "COIL",
            "TRANSIT",
            "CARDBOARD",
            "CIRCUITRY",
            "VICE",
            "FROSTY",
            "TROPICAL",
            "SPEED",
            "OCULOTHORAX",
            "CYCLONE",
            "DEEP SEA",
            "GUNS N TOYS",
            "SIAMESE",
            "ALERT",
            "SCATTER"
        ],
        "Vector": [
            "LOTUS",
            "OLIVE",
            "ASH",
            "SKY",
            "MAPLE",
            "SPECIAL DELIVERY",
            "SUSHI",
            "WHITE",
            "ARROWHEAD",
            "SCION",
            "DUOTONE",
            "TENTACLES",
            "ARCTIC",
            "PATTON",
            "HOT PINK",
            "CONSTRUCT",
            "SWEETHEART",
            "RUSTED FROM THE RAINOUT",
            "WINKY",
            "DEAD MEN TELL NO TALES",
            "WORMS",
            "CROWS",
            "SALMIAK",
            "SPRUCE",
            "FROST-BOUND"
        ]
    },
    "Rifles": {
        "AK-47": [
            "CARMINE",
            "SANDSTORM",
            "ARCTIC",
            "URBAN DIGICAMO",
            "SKY",
            "FKYA",
            "HAVOC",
            "KOI",
            "DAHLIA",
            "SCION",
            "CLASSIC",
            "HOT ROD",
            "PREDATOR",
            "SUNSET",
            "LOTUS",
            "DANGER ZONE",
            "IVORY",
            "JUNGLE",
            "ABDUCTION",
            "POLAR",
            "SERPENT",
            "WHITE",
            "GLACIER",
            "KNIGHT OF SWORDS",
            "SAKURA"
        ],
        "M4": [
            "ASH",
            "SANDSTORM",
            "MAPLE",
            "LOTUS",
            "AQUAMARINE",
            "SKY",
            "ARCTIC",
            "CRITICAL FASHION",
            "SUPER HEXAGON",
            "NEON SWIRL",
            "AUTUMN CRYSTAL",
            "VALHALLA",
            "LEOPARD",
            "HOUND",
            "MAORI",
            "NIGHTMARE",
            "MOLTEN",
            "FROSTY",
            "JUSTICE",
            "RASKOL",
            "BOOMBOX",
            "SPACE BATTLE",
            "OCULOTHORAX",
            "CYCLONE",
            "ALERT"
        ],
        "HK417": [
            "SANDSTORM",
            "TAIGA",
            "OLIVE",
            "MAPLE",
            "WOODLAND",
            "CARMINE",
            "LOTUS",
            "SUNGLOW",
            "AUTUMN CRYSTAL",
            "HOT ROD",
            "LOCUST",
            "NURTURE",
            "HOUND",
            "CAL",
            "MASQUERADE",
            "WORMS",
            "NEON SWIRL",
            "ONI DEMON",
            "FROSTY",
            "RASKOL",
            "OTTOMAN",
            "RETRO FORCE",
            "SPACE BATTLE",
            "AFTER DARK",
            "DECO"
        ],
        "SA58": [
            "SANDSTORM",
            "OLIVE",
            "MAPLE",
            "HAVOC",
            "CARMINE",
            "CONIFER",
            "ARCTIC",
            "KISS N TELL",
            "LOTUS",
            "ARROWHEAD",
            "AUTUMN CRYSTAL",
            "TRANSIT",
            "PREDATOR",
            "NOVA GAMMA",
            "JAWBREAKER",
            "NURTURE",
            "LOCUST",
            "SNOWFALL",
            "RASKOL",
            "WAVE RIDER",
            "PASTEL PIXEL",
            "TOMBSTONES",
            "YETI",
            "INVERSE",
            "SIAMESE"
        ],
        "AR-15": [
            "SCION",
            "ROSE",
            "MAPLE",
            "DANGER ZONE",
            "DISTORT",
            "SEISMIC",
            "POWERSHOT",
            "CAL",
            "SLIPSTREAM",
            "FEVER DREAM",
            "IMPACT",
            "MOMENTUM",
            "OUROBOROS",
            "PRESTIGE",
            "NUCLEAR FIRE",
            "EXULTATION",
            "LUMINESCENCE",
            "SEASON 7 DIAMOND",
            "VENOM HEART GREEN",
            "VENOM HEART PURPLE",
            "VENOM HEART YELLOW",
            "JAMMER",
            "FILIGREE",
            "JELLY STING",
            "MILD JELLY STING"
        ],
        "SG 551": [
            "MAPLE",
            "SKY",
            "CARMINE",
            "LOTUS",
            "ARCTIC",
            "TAIGA",
            "CONIFER",
            "ANGRY HANDS",
            "REKT",
            "WINKY",
            "HERALD",
            "NIGHT LIGHT",
            "SOFT PACKAGE",
            "SWALLOW",
            "RASKOL",
            "GLITCH",
            "COMPANY OF TANKS",
            "MAD SCIENCE",
            "BLUESNAP",
            "WINTER WOODS",
            "INVERSE",
            "HONEY",
            "SIAMESE",
            "ROSE",
            "SCATTER"
        ],
        "SCAR-H": [
            "FLAT DARK EARTH",
            "VINNYS CUSTOM",
            "BRASS PREDATOR",
            "JAMMER",
            "LIONFISH",
            "MURKY WATER",
            "PROJECTILE",
            "GRAND MASTER",
            "SOUL EATER",
            "BREEZE",
            "ELDER ONE",
            "AETHER CHRONICLE",
            "MEGA GATTAI",
            "VIGOR BEAR",
            "CHIKARA",
            "PICTURE PERFECT",
            "PRO LEAGUE CHAMPION",
            "PROTECT",
            "SEASON 9 SPEC OPS",
            "TAKE TWO",
            "TOP DOG",
            "VENTURE",
            "AZURE DYNASTY",
            "HOOLIGAN ORANGE",
            "HOOLIGAN PURPLE"
        ],
        "AUG": [
            "TURQUOISE",
            "MAPLE",
            "ASH",
            "LOTUS",
            "SANDSTORM",
            "ARCTIC",
            "NINE LIVES",
            "IMPACT",
            "FLORAL",
            "COMIC",
            "BUTTERFLY",
            "CONIFER",
            "HOT PINK",
            "BOX CUTTER",
            "SAFARI",
            "BOREALIS",
            "SUNFLOWERS",
            "TROPICAL",
            "PASTEL PIXEL",
            "AFTER DARK",
            "ROADSIDE",
            "OWL",
            "INVERSE",
            "HONEY",
            "SIAMESE"
        ],
        "SVD": [
            "CLASSIC",
            "FOAMY",
            "CARBYNE",
            "SCION",
            "DAHLIA",
            "CAL",
            "HIGHLAND",
            "HOT PINK",
            "OLIVE",
            "AQUAMARINE",
            "WHITE",
            "DUO-TONE",
            "TIGER SHARK",
            "CORAX",
            "POP STAR",
            "PLATFORMER",
            "WALKER",
            "POISON",
            "WRONG TURN",
            "OOZE",
            "TIME TRAVEL",
            "FREEZING WIND",
            "PENGUIN",
            "GREEN MARMALADE",
            "TRANSMISSION"
        ]
    },
    "Shotguns": {
        "FP6": [
            "URBAN DIGICAMO",
            "MAPLE",
            "ASH",
            "ARCTIC",
            "CARMINE",
            "LOTUS",
            "WOODLAND",
            "CATACOMB",
            "CYAN",
            "CRITICAL BLOCKS",
            "SUNSET",
            "WINKY",
            "POWERSHOT",
            "IVORY",
            "KIND REGARDS",
            "SURVIVAL",
            "DANGER ZONE",
            "JUNGLE",
            "BOREALIS",
            "POPPY FLOWER",
            "TROPICAL",
            "FIZZY",
            "PASTEL PIXEL",
            "CYCLONE",
            "INVADERS"
        ],
        "Super 90": [
            "DUO-TONE",
            "BADLAND",
            "OLIVE",
            "MAPLE",
            "CARMINE",
            "LOTUS",
            "WOODLAND",
            "ANGRY HANDS",
            "FROSTBERG",
            "TERRAFLARE",
            "COIL",
            "ARROWHEAD",
            "SYNTH",
            "HOT PINK",
            "FKYA",
            "SOFT PACKAGE",
            "SAKURA",
            "DELFT",
            "SPEED",
            "TOMBSTONES",
            "INVERSE",
            "SIAMESE",
            "ROSE",
            "ALERT",
            "VINTAGE"
        ],
        "KSG": [
            "TRIGGER",
            "VANGUARD",
            "ZAP BLASTER",
            "POWER STANCE",
            "EXACT ASSEMBLY",
            "SEASON 8 SPEC OPS",
            "LAST GRAIN",
            "PEACE OUT",
            "ST OF FEASTS",
            "PRO LEAGUE CHAMPION",
            "ELEGANT TWIST",
            "TURBULENCE",
            "FROST DRAGON",
            "AZURE DYNASTY",
            "SERVER HOST",
            "SERVER CLIENT",
            "NEON DYE",
            "FRENZY",
            "MAULER",
            "WAX",
            "SEASON 13 SPEC OPS",
            "XENO",
            "DARK JESTER",
            "ELEGANCE",
            "GRACE"
        ],
        "M1887": [
            "BLACK WATER",
            "CAL",
            "CARMINE",
            "CATACOMB",
            "DANGER ZONE",
            "FKYA",
            "HOT PINK",
            "KIND REGARDS",
            "KOI",
            "LOTUS",
            "MEDIC",
            "OLIVE",
            "OPPOSING FORCES",
            "SCORPIO",
            "SKY",
            "WHITE",
            "WOODLAND",
            "SHERIFF",
            "BANDANA",
            "WATERMELON",
            "THERMAL PARANORMAL",
            "POISON",
            "WRONG TURN",
            "OOZE",
            "CANDY CANE"
        ]
    },
    "Snipers": {
        "TRG-22": [
            "JUNGLE",
            "OLIVE",
            "CARMINE",
            "DANGER ZONE",
            "ALL-TERRAIN DIGI",
            "MAPLE",
            "CONIFER",
            "ARCTIC",
            "THRILLER",
            "SHARK ATTACK",
            "HAZARDOUS",
            "HEAVY METAL",
            "TAN",
            "MANTIS",
            "URBAN DIGICAMO",
            "LEOPARD",
            "BLOOD MONEY",
            "TOMBSTONES",
            "CLAIRVOYANCE",
            "BLUESNAP",
            "INVERSE",
            "SIAMESE",
            "ROSE",
            "SUNSTREAM",
            "VORTEX"
        ],
        "M14": [
            "HUNTSMAN",
            "TAIGA",
            "OLIVE",
            "MAPLE",
            "SKY",
            "LOTUS",
            "ARROWHEAD",
            "AUTUMN CRYSTAL",
            "CRITICAL BLOCKS",
            "NOVA BETA",
            "CATACOMB",
            "WASTELAND",
            "KRAKEN",
            "CRAYONS",
            "BIOTIC",
            "CUBICATIOUS",
            "ANTIQUE",
            "VELOCITY",
            "COTTONY",
            "PATTON",
            "DOTS",
            "WHITE",
            "FESTIVE",
            "STRENGTH",
            "SAKURA"
        ],
        "URAT": [
            "AQUAMARINE",
            "TAIGA",
            "MAPLE",
            "ASH",
            "FKYA",
            "VICTORIAN",
            "LOTUS",
            "ARCTIC",
            "RED STAR",
            "CONIFER",
            "ANGRY HANDS",
            "SUNGLOW",
            "TRANSIT",
            "REKT",
            "HOUND",
            "SUPER SPLASHER",
            "JUNGLE",
            "BLACK",
            "SOFT PACKAGE",
            "DELFT",
            "COMPANY OF TANKS",
            "CYCLONE",
            "GIGGLES",
            "GINGERBREAD",
            "INVERSE"
        ],
        "Sako": []
    }
}

AI_VALUATIONS = {
    "Dragon": "AI Valuation: RARE C-OPS SKIN (HIGH DEMAND - WORTH TO BUY)",
    "Valkyrie": "AI Valuation: TOP TIER C-OPS SKIN (GREAT VALUE - WORTH TO BUY)",
    "Fade": "AI Valuation: HIGH VALUE KNIFE SKIN (BEST OFFER CANDIDATE)",
    "Hyperion": "AI Valuation: LEGENDARY C-OPS MARKET ITEM (HIGH LIQUIDITY)",
    "Golden Age": "AI Valuation: EXCLUSIVE EVENT ITEM (HIGH PROFIT POTENTIAL)"
}

def get_ai_recommendation(skin_name: str) -> str:
    for key, val in AI_VALUATIONS.items():
        if key.lower() in skin_name.lower():
            return val
    return "AI Valuation: RECOMMENDED C-OPS MARKETPLACE SKIN (Fair Credit Price)"

# ==================== HACKUSATE BUTTON VIEW ====================

class HackusateView(discord.ui.View):
    def __init__(self, target_ign: str, user_id: int, user_name: str):
        super().__init__(timeout=800)
        self.target_ign = target_ign
        self.user_id = user_id
        self.user_name = user_name

    @discord.ui.button(label="Hackusate Player", style=discord.ButtonStyle.danger, custom_id="hackusate_btn")
    async def hackusate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        count = db.hackusate_player(
            ign=self.target_ign,
            reported_by=self.user_id,
            reporter_name=self.user_name
        )
        
        embed = discord.Embed(
            title="Hackusation Registered",
            description=(
                f"Player **{self.target_ign}** has been added to the **Hacker Watchlist** (`/hackerlist`)\n"
                f"Total Hackusations: **{count}**\n\n"
                f"Reported by: <@{self.user_id}>\n"
                f"Status: `Under Investigation`"
            ),
            color=discord.Color.red()
        )
        embed.set_footer(text="made by pown • C-Ops Anti-Cheat Watch")
        button.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(embed=embed, ephemeral=False)

# ==================== MARKETPLACE SELECT SKIN VIEWS ====================

class CustomSkinModal(discord.ui.Modal, title="Custom Critical Ops Skin Input"):
    skin_name_input = discord.ui.TextInput(
        label="Exact C-Ops Skin Name",
        placeholder="Type any Tier 1-7 skin name (e.g., Valkyrie, Glitch, Dragon...)",
        required=True,
        max_length=50
    )

    def __init__(self, category: str, gun_name: str):
        super().__init__()
        self.category = category
        self.gun_name = gun_name

    async def on_submit(self, interaction: discord.Interaction):
        skin_name = self.skin_name_input.value.strip()
        ai_advice = get_ai_recommendation(skin_name)
        
        db.add_marketplace_subscription(
            user_id=interaction.user.id,
            category=self.category,
            gun_name=self.gun_name,
            skin_name=skin_name,
            track_type="both"
        )

        embed = discord.Embed(
            title=f"Marketplace Snipe Activated: {self.gun_name} | {skin_name}",
            description=(
                f"Now tracking **{self.gun_name} — {skin_name}** live on Critical Ops Marketplace\n\n"
                f"{ai_advice}\n\n"
                f"Live Notifications Enabled:\n"
                f"• Sell Requests: Player X is Selling {skin_name} for X credits best offer\n"
                f"• Buy Requests: Player X bought requested {skin_name} for X credits best offer"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text="made by pown • Live C-Ops Marketplace AI Notifier")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class SkinSelectView(discord.ui.View):
    def __init__(self, category: str, gun_name: str, options_list: list):
        super().__init__(timeout=600)
        self.category = category
        self.gun_name = gun_name
        self.add_item(SkinSelectDropdown(category, gun_name, options_list))

    @discord.ui.button(label="✍️ Type Custom Skin Name", style=discord.ButtonStyle.secondary, custom_id="custom_skin_btn")
    async def custom_skin_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CustomSkinModal(self.category, self.gun_name))


class SkinSelectDropdown(discord.ui.Select):
    def __init__(self, category: str, gun_name: str, options_list: list):
        self.category = category
        self.gun_name = gun_name
        select_options = [
            discord.SelectOption(label=skin, description=f"{gun_name} skin for market sniping")
            for skin in options_list[:25]
        ]
        super().__init__(
            placeholder=f"Select a skin for {gun_name}...",
            min_values=1,
            max_values=1,
            options=select_options
        )

    async def callback(self, interaction: discord.Interaction):
        skin_name = self.values[0]
        ai_advice = get_ai_recommendation(skin_name)
        
        db.add_marketplace_subscription(
            user_id=interaction.user.id,
            category=self.category,
            gun_name=self.gun_name,
            skin_name=skin_name,
            track_type="both"
        )

        embed = discord.Embed(
            title=f"Marketplace Snipe Activated: {self.gun_name} | {skin_name}",
            description=(
                f"Now tracking **{self.gun_name} — {skin_name}** live on Critical Ops Marketplace\n\n"
                f"{ai_advice}\n\n"
                f"Live Notifications Enabled:\n"
                f"• Sell Requests: Player X is Selling {skin_name} for X credits best offer\n"
                f"• Buy Requests: Player X bought requested {skin_name} for X credits best offer"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text="made by pown • Live C-Ops Marketplace AI Notifier")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class GunSelectDropdown(discord.ui.Select):
    def __init__(self, category: str, guns_dict: dict):
        self.category = category
        self.guns_dict = guns_dict
        select_options = [
            discord.SelectOption(label=gun, description=f"Select {gun} models and skins")
            for gun in guns_dict.keys()
        ]
        super().__init__(
            placeholder=f"Select a {category[:-1]} model...",
            min_values=1,
            max_values=1,
            options=select_options
        )

    async def callback(self, interaction: discord.Interaction):
        gun_name = self.values[0]
        skins = self.guns_dict.get(gun_name, [])
        
        view = SkinSelectView(self.category, gun_name, skins)
        
        embed = discord.Embed(
            title=f"Select Skin for {gun_name}",
            description=(
                f"Choose which **{gun_name}** skin you want to snipe on C-Ops Marketplace,\n"
                f"or click **✍️ Type Custom Skin Name** to type any specific C-Ops Tier 1-7 skin name:"
            ),
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class CategorySelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=600)

    @discord.ui.button(label="Knives", style=discord.ButtonStyle.primary, custom_id="cat_knives")
    async def knives_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_guns(interaction, "Knives")

    @discord.ui.button(label="Gloves", style=discord.ButtonStyle.primary, custom_id="cat_gloves")
    async def gloves_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_guns(interaction, "Gloves")

    @discord.ui.button(label="Pistols", style=discord.ButtonStyle.primary, custom_id="cat_pistols")
    async def pistols_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_guns(interaction, "Pistols")

    @discord.ui.button(label="SMGs", style=discord.ButtonStyle.primary, custom_id="cat_smgs")
    async def smgs_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_guns(interaction, "SMGs")

    @discord.ui.button(label="Rifles", style=discord.ButtonStyle.success, custom_id="cat_rifles")
    async def rifles_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_guns(interaction, "Rifles")

    @discord.ui.button(label="Shotguns", style=discord.ButtonStyle.secondary, custom_id="cat_shotguns")
    async def shotguns_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_guns(interaction, "Shotguns")

    @discord.ui.button(label="Snipers", style=discord.ButtonStyle.danger, custom_id="cat_snipers")
    async def snipers_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_guns(interaction, "Snipers")

    async def _show_guns(self, interaction: discord.Interaction, category: str):
        guns = SKIN_CATALOG.get(category, {})
        view = discord.ui.View()
        view.add_item(GunSelectDropdown(category, guns))
        
        embed = discord.Embed(
            title=f"Marketplace Selection — {category}",
            description=f"Click the dropdown below to select the **{category}** gun model:",
            color=discord.Color.purple()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# ==================== PAGINATION VIEW ====================

class LeaderboardPaginationView(discord.ui.View):
    def __init__(self, players: list, per_page: int = 10):
        super().__init__(timeout=600)
        self.players = players
        self.per_page = per_page
        self.current_page = 1
        self.total_pages = max(1, (len(self.players) + self.per_page - 1) // self.per_page)
        self._update_buttons()

    def _update_buttons(self):
        self.first_button.disabled = (self.current_page <= 1)
        self.prev_button.disabled  = (self.current_page <= 1)
        self.next_button.disabled  = (self.current_page >= self.total_pages)
        self.last_button.disabled  = (self.current_page >= self.total_pages)

    def get_page_embed(self) -> discord.Embed:
        start = (self.current_page - 1) * self.per_page
        page  = self.players[start:start + self.per_page]

        lines = []
        for p in page:
            pos     = p.get("rank_position")
            pos_str = f"#{pos}" if pos else "#?"
            rating  = p.get("rating", 0)
            rank    = p.get("rank", "Unknown")
            ign     = p.get("ign", "?")
            lines.append(f"**{pos_str}** {ign} — **{rating:,}** Rating ({rank})")

        embed = discord.Embed(
            title="CRITICAL OPS LEADERBOARD",
            description="\n".join(lines) if lines else "No players found.",
            color=discord.Color.gold()
        )
        embed.set_footer(
            text=f"Page {self.current_page}/{self.total_pages} — {len(self.players)} Spec Ops+ Players • made by pown"
        )
        return embed

    @discord.ui.button(label="⏮ First",    style=discord.ButtonStyle.secondary, custom_id="lb_first")
    async def first_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_page_embed(), view=self)

    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.primary,   custom_id="lb_prev")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 1:
            self.current_page -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_page_embed(), view=self)

    @discord.ui.button(label="Next ▶",    style=discord.ButtonStyle.primary,   custom_id="lb_next")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages:
            self.current_page += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_page_embed(), view=self)

    @discord.ui.button(label="Last ⏭",   style=discord.ButtonStyle.secondary, custom_id="lb_last")
    async def last_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = self.total_pages
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_page_embed(), view=self)

# ==================== BOT CLASS ====================

class CriticalOpsBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"[BOT] Global slash command sync complete.")

    async def on_ready(self):
        print(f"==========================================")
        print(f"[BOT LOGGED IN] {self.user.name} ({self.user.id})")
        print(f"[TARGET CHANNEL] {config.LEADERBOARD_CHANNEL_ID}")
        print(f"==========================================")

        await self.change_presence(
            activity=discord.Game(name="Critical Ops | /search /snipe /marketplaceselectskin")
        )

        try:
            channel = self.get_channel(config.LEADERBOARD_CHANNEL_ID)
            if channel and hasattr(channel, "guild"):
                guild = channel.guild
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                print(f"[BOT] Instant guild sync to '{guild.name}': {len(synced)} commands.")
        except Exception as e:
            print(f"[BOT WARNING] Guild sync failed: {e}")

        try:
            channel = self.get_channel(config.LEADERBOARD_CHANNEL_ID)
            if channel:
                embed = discord.Embed(
                    title="SPEC OPS+ LEADERBOARD TRACKER ONLINE",
                    description=(
                        "Bot connected to Critical Ops live API & Railway DB.\n"
                        "Actively monitoring Spec Ops+ rank changes, Live Mid-Game Scores, & Marketplace..."
                    ),
                    color=discord.Color.blue()
                )
                embed.set_footer(text="made by pown • Auto Tracker System")
                await channel.send(embed=embed)
        except Exception as e:
            print(f"[ON_READY WARNING] Startup message failed: {e}")

        if not background_tracking_loop.is_running():
            background_tracking_loop.start()
            print(f"[BOT] Background tracking loop started.")


bot = CriticalOpsBot()

# ==================== SLASH COMMANDS ====================

@bot.tree.command(name="search", description="Search a Critical Ops player profile with detailed season & creation info")
@app_commands.describe(ign="Player In-Game Name (IGN)")
async def cmd_search(interaction: discord.Interaction, ign: str):
    await interaction.response.defer()
    player = await cops_api_client.get_player_by_ign(ign)
    if not player:
        await interaction.followup.send(f"Player **{ign}** not found in Critical Ops database.", ephemeral=True)
        return

    banned_str = " | BANNED" if player.get("banned") else ""
    embed = discord.Embed(
        title=f"Critical Ops Player Profile: {player['ign']}{banned_str}",
        color=discord.Color.red() if player.get("banned") else discord.Color.blue()
    )
    embed.add_field(name="IGN",                  value=f"`{player['ign']}`",                              inline=True)
    embed.add_field(name="Account ID",           value=f"`{player['id']}`",                              inline=True)
    embed.add_field(name="Rank & Rating",        value=f"**{player['rank']}** ({player['rating']:,} MMR)", inline=True)
    
    sn = player.get('season_num', 17)
    sg = player.get('season_games', 0)
    sw = player.get('season_wins', 0)
    sl = player.get('season_losses', 0)
    swr = player.get('season_winrate', 0)
    sk = player.get('season_kills', 0)
    sd = player.get('season_deaths', 0)
    skd = player.get('season_kd', 0)

    embed.add_field(
        name=f"Season {sn} Ranked Breakdown",
        value=(
            f"Games Played: **{sg:,}** ({sw} W / {sl} L - **{swr}% Winrate**)\n"
            f"Kills / Deaths: **{sk:,}** / **{sd:,}** (K/D: **{skd}**)"
        ),
        inline=False
    )

    embed.add_field(
        name="Total Career Ranked Stats",
        value=f"Games: **{player['career_games']:,}** | Kills: **{player['career_kills']:,}** | Deaths: **{player['career_deaths']:,}** | Career K/D: **{player['kd_ratio']}**",
        inline=False
    )

    embed.add_field(name="Peak / Lowest Rating",  value=f"Peak: **{player['peak_rating']:,}** | Lowest: **{player['lowest_rating']:,}**", inline=False)
    embed.add_field(name="Account Creation & History", value=f"`{player['account_creation_detail']}`", inline=False)
    embed.add_field(name="Level",                value=f"Level **{player['level']}**",                   inline=True)
    embed.set_footer(text="made by pown • Detailed Profile Analytics")
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="snipe", description="Snipe and track player with LIVE mid-game score & match notifications (DMs Only)")
@app_commands.describe(ign="Player IGN to snipe")
async def cmd_snipe(interaction: discord.Interaction, ign: str):
    await interaction.response.defer()
    user_id = interaction.user.id

    added, player = await snipe_tracker.add_target(user_id, ign)
    if not added:
        await interaction.followup.send(
            f"Player **{ign}** is already being sniped by you!",
            ephemeral=True
        )
        return

    if player:
        display_name = player["ign"]
        rank_str     = player.get("rank", "Unknown")
        rating_str   = f"{player.get('rating', 0):,}"
        lb_pos       = player.get("rank_position")
        pos_str      = f" | Rank: **#{lb_pos}**" if lb_pos else ""
        
        if player.get("banned"):
            await interaction.followup.send(
                f"Player **{display_name}** has been BANNED by Critical Ops. You don't need to snipe them!",
                ephemeral=True
            )
            return

        profile_line = (
            f"**{rank_str}** — {rating_str} MMR{pos_str}\n"
            f"Season Games: **{player['season_games']:,}** | Season K/D: **{player['season_kills']:,} / {player['season_deaths']:,}**"
        )
    else:
        display_name = ign
        profile_line = "Player added to snipe database — live tracking active."

    embed = discord.Embed(
        title="Player Snipe Activated",
        description=(
            f"Now actively sniping **{display_name}**\n"
            f"{profile_line}\n\n"
            f"Live In-Game Score Alerts Enabled:\n"
            f"• During Game: Receive live mid-match score updates (message edited live).\n"
            f"• Match Completion: Instant DM summary when season games count increases (+1 Game Finished).\n\n"
            f"Notifications are sent to your DMs ONLY."
        ),
        color=discord.Color.dark_purple()
    )
    embed.set_footer(text="made by pown • Direct Message Live Snipe System")
    view = HackusateView(target_ign=display_name, user_id=user_id, user_name=interaction.user.name)
    await interaction.followup.send(embed=embed, view=view)


@bot.tree.command(name="unsnipe", description="Stop sniping a player")
@app_commands.describe(ign="Player IGN to stop sniping")
async def cmd_unsnipe(interaction: discord.Interaction, ign: str):
    await interaction.response.defer()
    user_id = interaction.user.id

    player = await cops_api_client.get_player_by_ign(ign)
    display_name = player["ign"] if player else ign

    removed = snipe_tracker.remove_target(user_id, display_name)
    if not removed:
        await interaction.followup.send(
            f"You are not currently sniping player **{display_name}**.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="Player Snipe Deactivated",
        description=f"Stopped sniping **{display_name}**.",
        color=discord.Color.dark_red()
    )
    embed.set_footer(text="made by pown")
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="marketplaceselectskin", description="Select or type skin to snipe on Critical Ops Marketplace with AI Valuation")
async def cmd_marketplaceselectskin(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Critical Ops Marketplace Skin Snipe",
        description=(
            "Select the weapon category below to pick a skin or type any specific Tier 1-7 C-Ops skin name.\n"
            "Our AI system will analyze item valuation, best offers, buy requests, and sell requests live from C-Ops Marketplace!"
        ),
        color=discord.Color.gold()
    )
    embed.set_footer(text="made by pown • Live C-Ops Marketplace AI Notifier")
    view = CategorySelectView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@bot.tree.command(name="hackerlist", description="View the Critical Ops Hacker Watchlist & Banned Players")
async def cmd_hackerlist(interaction: discord.Interaction):
    await interaction.response.defer()
    entries = db.get_hacker_list()
    
    if not entries:
        await interaction.followup.send("No players currently reported in the Hacker List.", ephemeral=True)
        return

    lines = []
    for e in entries[:20]:
        banned_tag = " [BANNED]" if e["is_banned"] else ""
        lines.append(
            f"• **{e['ign']}**{banned_tag} — **{e['hackusations']}** report(s)\n"
            f"  Status: `{e['status']}` | Reported by: `{e['reporter']}`"
        )

    embed = discord.Embed(
        title="CRITICAL OPS HACKER WATCHLIST",
        description="\n".join(lines),
        color=discord.Color.dark_red()
    )
    embed.set_footer(text="made by pown • Anti-Cheat Watchlist")
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="leaderboard", description="Show Critical Ops Spec Ops & Elite Ops Leaderboard")
async def cmd_leaderboard(interaction: discord.Interaction):
    await interaction.response.defer()

    players = await cops_api_client.get_elite_leaderboard()
    if not players:
        await interaction.followup.send(
            "Could not retrieve Critical Ops Leaderboard. API may be down.",
            ephemeral=True
        )
        return

    view  = LeaderboardPaginationView(players=players, per_page=10)
    embed = view.get_page_embed()
    await interaction.followup.send(embed=embed, view=view)


# ==================== BACKGROUND TRACKING LOOP ====================

@tasks.loop(seconds=8)
async def background_tracking_loop():
    try:
        channel = bot.get_channel(config.LEADERBOARD_CHANNEL_ID)

        # ---- Snipe Alerts (DMs ONLY with Live Message Editing & User Tagging) ----
        snipe_alerts = await snipe_tracker.check_snipes(bot)
        for alert in snipe_alerts:
            u_id   = alert["user_id"]
            ign    = alert["ign"]
            a_type = alert["type"]
            msg_id = alert.get("live_message_id")

            try:
                user = bot.get_user(u_id) or await bot.fetch_user(u_id)
                if not user:
                    continue

                dm_channel = user.dm_channel or await user.create_dm()

                if a_type == "live_mid_game":
                    edited = False
                    if msg_id and dm_channel:
                        try:
                            existing_msg = await dm_channel.fetch_message(msg_id)
                            if existing_msg:
                                await existing_msg.edit(content=alert["message"])
                                edited = True
                                print(f"[SNIPE LIVE EDIT SUCCESS] Edited DM {msg_id} for user {user.name}")
                        except Exception as ex:
                            print(f"[SNIPE LIVE EDIT WARNING] Could not edit msg {msg_id}: {ex}")

                    if not edited:
                        sent_msg = await user.send(alert["message"])
                        db.update_live_message_id(u_id, ign, sent_msg.id)
                        print(f"[SNIPE DM LIVE START] Sent new live DM {sent_msg.id} to user {user.name}")

                elif a_type == "match_ended":
                    db.update_live_message_id(u_id, ign, None)
                    sent_msg = await user.send(alert["message"])
                    print(f"[SNIPE DM MATCH FINISHED] Sent match ended DM to user {user.name}")

                elif a_type == "banned":
                    db.update_live_message_id(u_id, ign, None)
                    await user.send(alert["message"])

            except Exception as e:
                print(f"[SNIPE DM ERROR] Failed DM for user {u_id}: {e}")

        # ---- Auto Leaderboard Updates ----
        leaderboard_updates = await leaderboard_tracker.check_updates()
        if leaderboard_updates:
            if channel:
                embed = discord.Embed(
                    title="SPEC OPS+ LEADERBOARD TRACKER",
                    description="\n".join(leaderboard_updates),
                    color=discord.Color.green()
                )
                embed.set_footer(text="made by pown • Auto Leaderboard Tracking")
                await channel.send(embed=embed)
                print(f"[TRACKER] Posted {len(leaderboard_updates)} update(s) to channel.")

    except Exception as e:
        import traceback
        print(f"[BACKGROUND LOOP ERROR] {e}")
        traceback.print_exc()


@background_tracking_loop.before_loop
async def before_tracking_loop():
    await bot.wait_until_ready()


if __name__ == "__main__":
    token = config.DISCORD_TOKEN
    if not token:
        print("[ERROR] DISCORD_TOKEN is not set!")
        exit(1)
    bot.run(token)
