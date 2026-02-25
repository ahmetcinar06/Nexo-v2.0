import sqlite3
import datetime
import requests

# Veritabanı bağlantısı
DB_PATH = "bellek.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS pokemons (
    trainer TEXT PRIMARY KEY,
    name TEXT,
    hp INTEGER,
    power INTEGER,
    rarity TEXT,
    level INTEGER,
    experience INTEGER,
    shiny INTEGER,
    type TEXT,
    pokemon_number INTEGER
)
''')
try:
    cursor.execute('ALTER TABLE pokemons ADD COLUMN pokemon_number INTEGER')
    conn.commit()
except sqlite3.OperationalError:
    pass

def save_pokemon_to_db(pokemon):
    poke_type = type(pokemon).__name__
    cursor.execute('''
        INSERT OR REPLACE INTO pokemons (trainer, name, hp, power, rarity, level, experience, shiny, type, pokemon_number)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        pokemon.pokemon_trainer,
        pokemon.name or "",
        pokemon.hp,
        pokemon.power,
        pokemon.rarity,
        pokemon.level,
        pokemon.experience,
        int(pokemon.shiny),
        poke_type,
        getattr(pokemon, "pokemon_number", None)
    ))
    conn.commit()

def load_pokemons_from_db():
    cursor.execute('SELECT trainer, name, hp, power, rarity, level, experience, shiny, type, pokemon_number FROM pokemons')
    rows = cursor.fetchall()
    for row in rows:
        trainer, name, hp, power, rarity, level, experience, shiny, poke_type, pokemon_number = row
        if poke_type == "Fighter":
            p = Fighter(trainer, from_db=True)
        elif poke_type == "Wizard":
            p = Wizard(trainer, from_db=True)
        else:
            p = Pokemon(trainer, from_db=True)
        p.name = name
        p.hp = hp
        p.power = power
        p.rarity = rarity
        p.level = level
        p.experience = experience
        p.shiny = bool(shiny)
        p.pokemon_number = pokemon_number
        Pokemon.pokemons[trainer] = p

def delete_pokemon_from_db(trainer):
    cursor.execute('DELETE FROM pokemons WHERE trainer=?', (trainer,))
    conn.commit()

def clear_all_pokemons_from_db():
    cursor.execute('DELETE FROM pokemons')
    conn.commit()



import aiohttp  # Eşzamansız HTTP istekleri için bir kütüphane
import random
import time

class Pokemon:
    last_feed_time = {}

    def __init__(self, pokemon_trainer, from_db=False):
        self.pokemon_trainer = pokemon_trainer
        if not from_db:
            self.rarity = self.get_random_rarity()
            self.pokemon_number = self.get_pokemon_by_rarity()
            self.name = None
            self.abilities = []
            self.types = []
            self.image_url = None
            self.level = 1
            self.experience = 0
            self.evolution_chain_url = None
            self.shiny = random.random() < 0.01 # 1% chance of being shiny
            self._data_fetched = False # Verilerin API'den çekilip çekilmediğini kontrol eden bayrak
            self.hp = random.randint(50, 150)
            self.power = random.randint(10, 50)
            self.süre = 10
            while self.süre:
                time.sleep(1)
                self.süre -= 1
            Pokemon.pokemons[pokemon_trainer] = self
            if pokemon_trainer not in Pokemon.pokepoints:
                Pokemon.pokepoints[pokemon_trainer] = 0
            # Oluşturulan pokemonu veritabanına kaydet
            try:
                save_pokemon_to_db(self)
            except Exception:
                pass
        else:
            self._data_fetched = False

    @staticmethod
    def get_pokemon_id_by_name(name):
        url = f'https://pokeapi.co/api/v2/pokemon/{name.lower()}'
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                return data['id']
        except Exception:
            pass
        return 25  # Pikachu'nun id'si, hata olursa default

    pokemons = {}
    pokepoints = {}

    rarity_tiers = {
        "legendary": 0.001,
        "epic": 0.009,
        "rare": 0.05,
        "uncommon": 0.24,
        "common": 0.7
    }

    legendary = ["Mew", "Mewtwo", "Rayquaza"]
    epic = ["Yveltal", "Zygarde", "Darkrai"]
    rare = ["Dragonite", "Tyranitar", "Salamence"]
    uncommon = ["Charmeleon", "Ivysaur", "Wartortle"]

    def get_random_rarity(self):
        return random.choices(list(self.rarity_tiers.keys()), list(self.rarity_tiers.values()))[0]

    def get_pokemon_by_rarity(self):
        if self.rarity == "legendary":
            return self.get_pokemon_id_by_name(random.choice(self.legendary))
        elif self.rarity == "epic":
            return self.get_pokemon_id_by_name(random.choice(self.epic))
        elif self.rarity == "rare":
            return self.get_pokemon_id_by_name(random.choice(self.rare))
        elif self.rarity == "uncommon":
            return self.get_pokemon_id_by_name(random.choice(self.uncommon))
        else:
            return random.randint(1, 1000)

    async def _fetch_data(self):
        if self._data_fetched:
            return
        url = f'https://pokeapi.co/api/v2/pokemon/{self.pokemon_number}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    self.name = data['name'].capitalize()
                    self.abilities = [a['ability']['name'].capitalize() for a in data['abilities']]
                    self.types = [t['type']['name'].capitalize() for t in data['types']]
                    if self.shiny:
                        self.image_url = data['sprites']['front_shiny']
                    else:
                        self.image_url = data['sprites']['front_default']
                    species_url = data['species']['url']
                    async with session.get(species_url) as species_response:
                        if species_response.status == 200:
                            species_data = await species_response.json()
                            self.evolution_chain_url = species_data['evolution_chain']['url']
                else:
                    self.name = "Pikachu"
                    self.abilities = ["Static"]
                    self.types = ["Electric"]
                    self.image_url = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/25.png"
                self._data_fetched = True

    async def info(self):
        await self._fetch_data()
        rarity_message = f"**Nadirlik:** {self.rarity.capitalize()}\n"
        hp_power_message = f"**Sağlık:** {self.hp}\n**Güç:** {self.power}\n"
        if self.shiny:
            rarity_message = f"✨ **SHINY** ✨\n" + rarity_message
            Pokemon.pokepoints[self.pokemon_trainer] += 50
        if self.rarity == "legendary":
            Pokemon.pokepoints[self.pokemon_trainer] += 10
            return (f"🎉 Vay canına, {self.pokemon_trainer}! Çok şanslısın! {self.name} adlı efsanevi Pokémon'u buldun! 🎉\n"
                    f"{rarity_message}{hp_power_message}"
                    f"**Seviye:** {self.level} ({self.experience}/{100 * self.level})\n"
                    f"**Türleri:** {', '.join(self.types)}\n"
                    f"**Yetenekleri:** {', '.join(self.abilities)}\n"
                    f"+10 PokéPoint aldın! Toplam {Pokemon.pokepoints[self.pokemon_trainer]} PokéPoint'un var.")
        elif self.rarity == "epic":
            Pokemon.pokepoints[self.pokemon_trainer] += 5
            return (
                    f"Vay canına, {self.pokemon_trainer}! Çok şanslısın! {self.name} adlı epik Pokémon'u buldun! 🎉\n"
                    f"{rarity_message}{hp_power_message}"
                    f"**Seviye:** {self.level} ({self.experience}/{100 * self.level})\n"
                    f"**Türleri:** {', '.join(self.types)}\n"
                    f"**Yetenekleri:** {', '.join(self.abilities)}\n"
                    f"+5 PokéPoint aldın! Toplam {Pokemon.pokepoints[self.pokemon_trainer]} PokéPoint'un var.")
        else:
            return (
                    f"İşte Pokémon'un, **{self.name}**!\n"
                    f"{rarity_message}{hp_power_message}"
                    f"**Seviye:** {self.level} ({self.experience}/{100 * self.level})\n"
                    f"**Türleri:** {', '.join(self.types)}\n"
                    f"**Yetenekleri:** {', '.join(self.abilities)}")

    async def attack(self, enemy):
        if enemy.hp > self.power:
            enemy.hp -= self.power
            # Kazanan bonusu ekle
            return f"Pokémon eğitmeni @{self.pokemon_trainer} @{enemy.pokemon_trainer}'ne saldırdı\n@{enemy.pokemon_trainer}'nin sağlık durumu {enemy.hp}"
        else:
            enemy.hp = 0
            Pokemon.pokepoints[self.pokemon_trainer] += 20  # Kazanan bonusu
            return f"Pokémon eğitmeni @{self.pokemon_trainer} @{enemy.pokemon_trainer}'ni yendi! +20 PokéPoint kazandın!"

    async def heal(self):
        heal_amount = random.randint(20, 50)
        self.hp += heal_amount
        return f"Pokémon'un {heal_amount} sağlık puanı ile iyileşti! Toplam sağlık: {self.hp}"

    async def defend(self, attacker=None):
        # Basic defense: 50% chance to heal, 50% chance to do nothing
        action = random.choice(["heal", "none"])
        if action == "heal":
            heal_msg = await self.heal()
            return f"Savunma turu: {self.pokemon_trainer} {heal_msg}"
        else:
            return f"Savunma turu: {self.pokemon_trainer} savunma yapmadı."

    async def show_img(self):
        await self._fetch_data()
        return self.image_url

    async def feed(self):
        now = datetime.datetime.now()
        cooldown = datetime.timedelta(hours=12)
        last_time = Pokemon.last_feed_time.get(self.pokemon_trainer)
        if last_time and now - last_time < cooldown:
            kalan = cooldown - (now - last_time)
            saat = kalan.seconds // 3600
            dakika = (kalan.seconds % 3600) // 60
            return f"Besleme cooldown aktif! {saat} saat {dakika} dakika sonra tekrar besleyebilirsin.", None
        # Sağlık +5, maksimum 200
        if self.hp < 200:
            self.hp = min(self.hp + 5, 200)
            Pokemon.last_feed_time[self.pokemon_trainer] = now
            return f"Pokémon'unu besledin! Sağlığı +5 arttı. Toplam sağlık: {self.hp}", None
        else:
            return f"Pokémon'un sağlığı zaten maksimumda (200)!", None

class Fighter(Pokemon):
    def __init__(self, pokemon_trainer, from_db=False):
        super().__init__(pokemon_trainer, from_db=from_db)
        if not from_db:
            self.power += 30  # Dövüşçülere sabit ekstra güç

    async def attack(self, enemy):
        super_guc = 10  # Sabit ek güç
        self.power += super_guc
        result = await super().attack(enemy)
        self.power -= super_guc
        return result + f"\nDövüşçü Pokémon süper saldırı kullandı. Eklenen güç: {super_guc}"

    async def info(self):
        base_info = await super().info()
        return "Dövüşçü pokémonunuz var.\n" + base_info

class Wizard(Pokemon):
    def __init__(self, pokemon_trainer, from_db=False):
        super().__init__(pokemon_trainer, from_db=from_db)
        if not from_db:
            self.hp += 60  # Sihirbazlara sabit ekstra sağlık

    async def info(self):
        base_info = await super().info()
        return "Sihirbaz pokémonunuz var.\n" + base_info

# Pokemon sınıfı ve alt sınıflar tanımlandıktan sonra veritabanından yükleme yapılmalı
load_pokemons_from_db()