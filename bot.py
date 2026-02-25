from datetime import datetime
from pc import PC
from game import Game  # Game sınıfını içe aktar
from db_mngr import DB_Manager  # DB_Manager sınıfını içe aktar
from poke import Pokemon, Fighter, Wizard, delete_pokemon_from_db  # Pokemon ve alt sınıfları içe aktar
from translator import *
from langdetect import detect as detect_lang
from config import db, token  # client tokenini config.py dosyasından al
import discord # discord.py kütüphanesini içe aktar
from discord.ext import commands # Komutlar için gerekli modülü içe aktar
import time
import openai  # pip install openai
import sqlite3

# SQLite veritabanı bağlantısı ve tablo oluşturma
DB_PATH = "bellek.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS sohbet_bellek (
    user_id TEXT,
    role TEXT,
    content TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

def bellek_yukle(user_id, limit=5):
    cursor.execute("SELECT role, content FROM sohbet_bellek WHERE user_id=? ORDER BY timestamp DESC LIMIT ?", (str(user_id), limit))
    rows = cursor.fetchall()
    # Son eklenenler başta, OpenAI için ters çevir
    return [{"role": role, "content": content} for role, content in reversed(rows)]

def bellek_ekle(user_id, role, content):
    cursor.execute("INSERT INTO sohbet_bellek (user_id, role, content) VALUES (?, ?, ?)", (str(user_id), role, content))
    conn.commit()

openai.api_key = 'Your_API_KEY_HERE'  # OpenAI API anahtarınızı buraya girin

# clientun hangi olaylara erişeceğini belirten intents nesnesi oluştur
intents = discord.Intents.default()
intents.members = True  # clientun kullanıcılarla çalışmasına ve onları banlamasına izin verir
# Mesaj içeriğine erişim izni ver
intents.message_content = True
manager = DB_Manager(db)

# clientu oluştur, komut ön ekini ve intents'i ayarla
client = commands.Bot(command_prefix='nexo ', intents=intents)
# Varsayılan help komutunu kaldır, kendi help komutumuzu ekleyeceğiz
client.remove_command('help')


# client Discord'a başarıyla bağlandığında çalışacak fonksiyon
@client.event
async def on_ready():
    print(f'Giriş yaptı:  {client.user}')  # clientun kullanıcı adı konsola yazdırılır



# Her mesaj gönderildiğinde tetiklenen olay
@client.event
async def on_message(message):
    # clientun kendi mesajlarını dikkate alma
    if message.author == client.user:
        return

    # Reklam veya bağlantı kontrolü
    link_keywords = ["http://", "https://", "www.", ".com", ".net", ".org"]
    if any(keyword in message.content.lower() for keyword in link_keywords):
        try:
            await message.author.ban(reason="Reklam veya bağlantı paylaşıldı.")
            await message.channel.send(f"{message.author.mention} kullanıcısı reklam/bağlantı nedeniyle banlandı!")
        except discord.Forbidden:
            await message.channel.send("Banlama işlemi için yetkim yok!")
        except Exception as e:
            await message.channel.send(f"Banlama sırasında hata oluştu: {str(e)}")
        return  # Banladıktan sonra başka işlem yapma

    # Mesajda ek (attachment) var mı kontrol et
    if message.attachments:
        # Her ek için kontrol et
        for attachment in message.attachments:
            # Eğer ek bir resim dosyası ise (jpg, png, gif vs.)
            resim_uzantilari = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
            for uzanti in resim_uzantilari:
                if attachment.filename.lower().endswith(uzanti):
                    dosya_turu = uzanti.replace('.', '').upper()
                    await message.channel.send(f"Sanırım bir resim gönderdiniz! Dosya türü: {dosya_turu}")  # Kullanıcıya yanıt ver
                    break
            else:
                continue
            break  # Sadece bir kez yanıt ver

    # Mesaj bir komutla başlıyorsa komutları işle
    if message.content.startswith(client.command_prefix):
        await client.process_commands(message)

# Zeka modu aktif kullanıcıları tutan set
# Zeka modu aktif kullanıcıları tutan set
zeka_modu_aktif = set()

# Kullanıcıya özel sohbet belleği
sohbet_bellek = {}

fighting_users = set()

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Zeka modu açma/kapama komutları
    if message.content.lower().startswith("nexo ai"):
        zeka_modu_aktif.add(message.author.id)
        await message.channel.send("AI modu aktif.\nÇıkmak için 'nexo çık' yazın.")
        return

    if message.content.lower().startswith("nexo çık"):
        zeka_modu_aktif.discard(message.author.id)
        await message.channel.send("AI modu kapatıldı.")
        return

    # Zeka modu aktifse prefix olmadan cevap ver
    if message.author.id in zeka_modu_aktif and not message.author.bot:
            # Kullanıcıya ait geçmişi veritabanından al
            history = bellek_yukle(message.author.id, limit=5)
            # Yeni mesajı belleğe ekle
            bellek_ekle(message.author.id, "user", message.content)
            history.append({"role": "user", "content": message.content})

            try:
                response = openai.ChatCompletion.create(
                    model="gpt-4.1-mini",
                    messages=history,
                    max_tokens=500
                )
                cevap = response.choices[0].message.content
                # clientun cevabını da belleğe ekle
                bellek_ekle(message.author.id, "assistant", cevap)
                await message.channel.send(cevap)
            except Exception as e:
                await message.channel.send(f"Yanıt alınamadı: {str(e)}")
            return

    # Reklam veya bağlantı kontrolü
    link_keywords = ["http://", "https://", "www.", ".com", ".net", ".org"]
    if any(keyword in message.content.lower() for keyword in link_keywords):
        try:
            await message.author.ban(reason="Reklam veya bağlantı paylaşıldı.")
            await message.channel.send(f"{message.author.mention} kullanıcısı reklam/bağlantı nedeniyle banlandı!")
        except discord.Forbidden:
            await message.channel.send("Banlama işlemi için yetkim yok!")
        except Exception as e:
            await message.channel.send(f"Banlama sırasında hata oluştu: {str(e)}")
        return

    # Mesajda ek (attachment) var mı kontrol et
    if message.attachments:
        for attachment in message.attachments:
            resim_uzantilari = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
            for uzanti in resim_uzantilari:
                if attachment.filename.lower().endswith(uzanti):
                    dosya_turu = uzanti.replace('.', '').upper()
                    await message.channel.send(f"Sanırım bir resim gönderdiniz! Dosya türü: {dosya_turu}")
                    break
            else:
                continue
            break

    # Komutları işle
    if message.content.startswith(client.command_prefix):
        await client.process_commands(message)

@client.command()
async def apikota(ctx):
    """OpenAI API token sınırı hakkında bilgi verir."""
    await ctx.send(
        "OpenAI API token kullanım sınırını doğrudan client üzerinden öğrenmek mümkün değildir.\n"
        "Kota ve kullanım bilgisi için https://platform.openai.com/usage adresini ziyaret edebilirsiniz."
    )

@client.command()
async def version(ctx):
    """Yapay zeka modelinin sürümünü gösterir."""
    await ctx.send("Kullandığım yapay zeka modeli: GPT-4.1-mini")

# Ping komutu: clientun gecikmesini gösterir
@client.command()
async def ping(ctx):
    """clientun gecikmesini gösterir."""
    latency = round(client.latency * 1000)  # Gecikmeyi milisaniye cinsinden hesapla
    await ctx.send(f'Pong! Gecikme: {latency}ms')  # Sonucu kanala gönder

# Avatar komutu: Kullanıcının avatarını gösterir
@client.command()
async def avatar(ctx, member: discord.Member = None):
    """Kullanıcının avatarını gösterir."""
    member = member or ctx.author
    await ctx.send(f'{member.display_name} adlı kullanıcının avatarı: {member.avatar.url}')

# Kullanıcı komutu: Komutu kullanan kişinin adını ve ID'sini gösterir
@client.command()
async def kullanici(ctx):
    """Kullanıcı adını ve ID'sini gösterir."""
    await ctx.send(f'Adınız: {ctx.author.display_name}\nID: {ctx.author.id}')

# Sunucuinfo komutu: Sunucu oluşturulma tarihi ve bölgesini gösterir
@client.command()
async def sunucuinfo(ctx):
    """Sunucu oluşturulma tarihi ve bölgesini gösterir."""
    guild = ctx.guild
    await ctx.send(f'Sunucu oluşturulma tarihi: {guild.created_at.strftime("%d.%m.%Y %H:%M")}\nBölge: {getattr(guild, "region", "Bilinmiyor")}')

# Davet komutu: Sunucuya davet linki oluşturur (izin varsa)
@client.command()
async def davet(ctx):
    """Sunucuya davet linki oluşturur."""
    try:
        invite = await ctx.channel.create_invite(max_age=300)
        await ctx.send(f'Davet linkiniz (5 dakika geçerli): {invite.url}')
    except Exception:
        await ctx.send('Davet linki oluşturulamadı. Yetkiniz olmayabilir.')

# Rastgele komutu: 1-100 arası rastgele sayı gönderir
import random
@client.command()
async def rastgele(ctx):
    """1-100 arası rastgele sayı gönderir."""
    num1 = random.randint(1, 100)
    num2 = random.randint(1, 100)
    sayi = num1 + num2  # İki rastgele sayının toplamını gönder
    await ctx.send(f'Rastgele sayıların toplamı: {sayi}')


# Sunucu bilgisi komutu: Sunucu adı ve üye sayısını gösterir
@client.command()
async def sunucu(ctx):
    """Sunucu adı ve üye sayısını gösterir."""
    guild = ctx.guild  # Komutun kullanıldığı sunucu bilgisini al
    await ctx.send(f'Sunucu adı: {guild.name}\nÜye sayısı: {guild.member_count}')  # Bilgileri gönder


# Temizle komutu: Belirtilen kadar mesajı siler
@client.command()
async def temizle(ctx, miktar: int = 5):
    """Belirtilen kadar mesajı siler. (Varsayılan: 5)"""
    deleted = await ctx.channel.purge(limit=miktar+1)  # Komut dahil miktar kadar mesajı sil
    await ctx.send(f'{len(deleted)-1} mesaj silindi.', delete_after=2)  # Sonucu bildir, 2 sn sonra sil


# Hakkında komutu: client hakkında bilgi verir
@client.command()
async def about(ctx):
    await ctx.send('Bu discord.py kütüphanesi ile oluşturulmuş echo-client!')


# client hakkında bilgi veren komut
@client.command()
async def info(ctx):
    """client hakkında bilgi verir."""
    await ctx.send('Ben bir Discord echo-clientuyum! Komutlarım ve özelliklerim hakkında bilgi almak için /help yazabilirsin.')

# Merhaba komutu: Selam mesajı gönderir
@client.command()
async def hello(ctx):
    await ctx.send('Merhaba! Ben bir echo-clientum!')




# Yardım komutu: Tüm komutları listeler
@client.command()
async def help(ctx):
    embed = discord.Embed(title="Nexo Komutları", color=discord.Color.blue())
    embed.add_field(
        name="Genel",
        value=(
            "`nexo about`, `nexo hello`, `nexo info`, `nexo ping`, `nexo uptime`, `nexo version`, `nexo apikota`"
        ),
        inline=False,
    )
    embed.add_field(
        name="Sunucu",
        value=(
            "`nexo avatar [kullanıcı]`, `nexo kullanici`, `nexo sunucu`, `nexo sunucuinfo`, `nexo roller`, `nexo aktif`, `nexo davet`, `nexo temizle [miktar]`"
        ),
        inline=False,
    )
    embed.add_field(
        name="Pokémon",
        value=(
            "`nexo go`, `nexo pokemon`, `nexo feed`, `nexo evolve`, `nexo heal`, `nexo delete_pokemon`"
        ),
        inline=False,
    )
    embed.add_field(
        name="Sistem",
        value=(
            "`nexo pc_about`, `nexo pc_status`, `nexo antivirus`, `nexo update`, `nexo processes`"
        ),
        inline=False,
    )
    embed.add_field(
        name="Diğer",
        value=(
            "`nexo game`, `nexo dm [mesaj]`, `nexo rastgele`, `nexo ai`, `nexo translate [mesaj]`"
        ),
        inline=False,
    )
    embed.set_footer(text="Resim gönderirseniz, client dosya türünü bildirir!")
    await ctx.send(embed=embed)


# Komutlarda hata oluşursa kullanıcıya bilgi verir
@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):  # Eksik argüman hatası
        await ctx.send('Eksik argüman girdiniz!')
    elif isinstance(error, commands.CommandNotFound):  # Komut bulunamadı hatası
        await ctx.send('Böyle bir komut yok!')
        await ctx.send('Komutları görmek için `nexo help` yazabilirsiniz.')
    elif isinstance(error, commands.MissingPermissions):  # Yetki hatası
        await ctx.send('Bu komutu kullanmak için izniniz yok!')
    else:
        await ctx.send(f'Bir hata oluştu: {str(error)}')  # Diğer hatalar


# PC yönetim ve oyun komutları (sadece Discord'a özel async fonksiyonlar)
@client.command()
async def pc_about(ctx):
    """PC donanım bilgilerini gösterir."""
    await PC().about_PC(ctx)

@client.command()
async def pc_status(ctx):
    """PC kaynak kullanımını gösterir."""
    await PC().PC_status_discord(ctx)

@client.command()
async def antivirus(ctx):
    """Antivirüs taraması yapar."""
    await PC().antivirus_scan_discord(ctx)

@client.command()
async def update(ctx):
    """Sistem güncellemesi kontrolü yapar."""
    await PC().system_update_discord(ctx)

@client.command()
async def processes(ctx):
    """Çalışan işlemleri listeler."""
    await PC().processes(ctx)

@client.command()
async def game(ctx):
    """Sayı tahmin oyunu oynatır."""
    await Game().game(ctx)

# Sunucudaki rollerin listesini gösterir
@client.command()
async def roller(ctx):
    """Sunucudaki tüm rolleri listeler."""
    roles = [role.name for role in ctx.guild.roles if role.name != "@everyone"]
    await ctx.send("Sunucudaki roller:\n" + ", ".join(roles) if roles else "Hiç rol yok.")

# Kullanıcıya özel DM mesajı gönderir
@client.command()
async def dm(ctx, *, mesaj: str):
    """Kullanıcıya özel DM mesajı gönderir."""
    try:
        await ctx.author.send(mesaj)
        await ctx.send("DM gönderildi!")
    except Exception:
        await ctx.send("DM gönderilemedi.")

# Sunucudaki aktif üyeleri listeler
@client.command()
async def aktif(ctx):
    """Sunucudaki çevrimiçi üyeleri listeler."""
    aktifler = [m.display_name for m in ctx.guild.members if m.status == discord.Status.online and not m.bot]
    await ctx.send("Çevrimiçi üyeler:\n" + ", ".join(aktifler) if aktifler else "Şu anda kimse çevrimiçi değil.")

# clientun uptime bilgisini gösterir
client_start_time = time.time()
@client.command()
async def uptime(ctx):
    """clientun ne kadar süredir aktif olduğunu gösterir."""
    elapsed = int(time.time() - client_start_time)
    saat = elapsed // 3600
    dakika = (elapsed % 3600) // 60
    saniye = elapsed % 60
    await ctx.send(f"client {saat} saat, {dakika} dakika, {saniye} saniyedir aktif.")

@client.command()
async def saat(ctx):
    """Sunucudaki saat bilgisini gösterir."""
    await ctx.send(f"Sunucudaki saat: {datetime.now().strftime('%H:%M:%S')}")

@client.command()
async def go(ctx):
    author = ctx.author.name
    if author not in Pokemon.pokemons.keys():
        await ctx.send("Hangi tür Pokémon istiyorsun?\n1. Sıradan\n2. Dövüşçü\n3. Sihirbaz\nYanıt olarak 1, 2 veya 3 yaz.")
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content in ["1", "2", "3"]
        try:
            msg = await client.wait_for("message", check=check, timeout=30)
            if msg.content == "2":
                pokemon = Fighter(author)
            elif msg.content == "3":
                pokemon = Wizard(author)
            else:
                pokemon = Pokemon(author)
        except Exception:
            pokemon = Pokemon(author)
        await ctx.send(await pokemon.info())
        image_url = await pokemon.show_img()
        if image_url:
            embed = discord.Embed()
            embed.set_image(url=image_url)
            await ctx.send(embed=embed)
        else:
            await ctx.send("Pokémonun görüntüsü yüklenemedi!")
    else:
        await ctx.send("Zaten kendi Pokémonunuzu oluşturdunuz!\nSahip olduğunuz Pokémon'u silmek için `nexo delete_pokemon` komutunu kullanabilirsiniz.")

@client.command()
async def delete_pokemon(ctx):
    """Kullanıcının Pokémon'unu siler."""
    await ctx.send("Pokémon'u silmek için onay verin. Bu işlem 10 PokéPuan'a mal olacaktır. (evet/hayır)")
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["evet", "hayır"]
    try:
        msg = await client.wait_for("message", check=check, timeout=30)
    except TimeoutError:
        await ctx.send("Zaman aşımına uğradı. Pokémon silme işlemi iptal edildi.")
        return
    if msg.content.lower() == "hayır":
        await ctx.send("Pokémon silme işlemi iptal edildi.")
        return
    if msg.content.lower() == "evet":
        author = ctx.author.name
        if author not in Pokemon.pokemons:
            await ctx.send("Silinecek bir Pokémon'un bulunmuyor.")
            return
        if Pokemon.pokepoints.get(author, 0) < 10:
            await ctx.send(f"Yeterli PokéPuan'ın yok! Bu işlem için 10 puan gerekir. Mevcut puanın: {Pokemon.pokepoints.get(author, 0)}")
            await ctx.send(f"Eğer puan kazanmak istersen, `nexo game` komutunu kullanarak oyun oynayabilirsin!")
            return
        # Silme işlemini gerçekleştir
        del Pokemon.pokemons[author]
        Pokemon.pokepoints[author] -= 10
        delete_pokemon_from_db(author)
        await ctx.send(f"{author}, Pokémon'un başarıyla silindi! Kalan PokéPuan'ın: {Pokemon.pokepoints[author]}")

@client.command()
async def pokemon(ctx):
    """Sahip olduğunuz Pokémon'un bilgilerini gösterir."""
    author = ctx.author.name
    if author in Pokemon.pokemons:
        pokemon = Pokemon.pokemons[author]
        info_msg = await pokemon.info()
        # Son besleme zamanı
        last_time = getattr(Pokemon, 'last_feed_time', {}).get(author)
        if last_time:
            last_time_str = last_time.strftime('%d.%m.%Y %H:%M')
            info_msg += f"\nSon besleme zamanı: {last_time_str}"
        else:
            info_msg += "\nSon besleme zamanı: Henüz beslenmedi."
        await ctx.send(info_msg)
        image_url = await pokemon.show_img()
        if image_url:
            embed = discord.Embed()
            embed.set_image(url=image_url)
            await ctx.send(embed=embed)
        else:
            await ctx.send("Pokémon'un görüntüsü yüklenemedi!")
    else:
        await ctx.send("Henüz bir Pokémon'un yok. `nexo go` komutu ile bir tane alabilirsin.")

@client.command()
async def feed(ctx):
    """Pokémon'unuzu besleyerek deneyim kazandırırsınız (savaşta kullanılamaz)."""
    author = ctx.author.name
    if author in fighting_users:
        await ctx.send("Savaşta besleme yapılamaz!")
        return
    if author in Pokemon.pokemons:
        pokemon = Pokemon.pokemons[author]
        feed_message, levelup_message = await pokemon.feed()
        await ctx.send(feed_message)
        if levelup_message:
            await ctx.send(levelup_message)
    else:
        await ctx.send("Besleyecek bir Pokémon'un yok. 'nexo go' komutu ile bir tane alabilirsin.")

@client.command()
async def evolve(ctx):
    """Pokémon'unuzu evrimleştirirsiniz (savaşta kullanılamaz)."""
    author = ctx.author.name
    if author in fighting_users:
        await ctx.send("Savaşta evrim yapılamaz!")
        return
    if author in Pokemon.pokemons:
        pokemon = Pokemon.pokemons[author]
        evolve_message = await pokemon.evolve()
        await ctx.send(evolve_message)
    else:
        await ctx.send("Evrimleştirecek bir Pokémon'un yok. 'nexo go' komutu ile bir tane alabilirsin.")

@client.command()
async def heal(ctx):
    """Pokémon'unuzu iyileştirir (sadece savaşta kullanılabilir)."""
    author = ctx.author.name
    if author not in fighting_users:
        await ctx.send("Heal komutu sadece savaşta kullanılabilir!")
        return
    if author in Pokemon.pokemons:
        pokemon = Pokemon.pokemons[author]
        heal_message = await pokemon.heal()
        await ctx.send(heal_message)
    else:
        await ctx.send("Henüz bir Pokémon'un yok. 'nexo go' komutu ile bir tane alabilirsin.")

class PersistentView(discord.ui.View):
    def __init__(self, owner):
        super().__init__(timeout=None)
        self.owner = owner

    @discord.ui.button(label="Mesajı çevirin", style=discord.ButtonStyle.secondary, custom_id="text_translate")
    async def text_translate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Dil seçenekleri
        languages = [
            ("İngilizce", "en"),
            ("Türkçe", "tr"),
            ("Almanca", "de"),
            ("Fransızca", "fr"),
            ("İspanyolca", "es"),
            ("Arapça", "ar"),
            ("Rusça", "ru"),
            ("Japonca", "ja"),
        ]
        options = [discord.SelectOption(label=label, value=code) for label, code in languages]

        # Son çevrilecek metni owner ile eşleştirerek saklamak için bir dict kullanıyoruz
        if not hasattr(self, 'last_text'):
            self.last_text = {}

        class LanguageSelect(discord.ui.Select):
            def __init__(self, parent_view):
                super().__init__(placeholder="Hangi dile çevrilsin?", min_values=1, max_values=1, options=options)
                self.parent_view = parent_view

            async def callback(self, select_interaction: discord.Interaction):
                lang_code = self.values[0]
                text = self.parent_view.last_text.get(self.parent_view.owner, None)
                if not text:
                    await select_interaction.response.send_message("Çevrilecek metin bulunamadı.", ephemeral=True)
                    return
                # Mesajın dilini otomatik algıla (langdetect)
                try:
                    detected_lang = detect_lang(text)
                except Exception:
                    detected_lang = "tr"  # Algılanamazsa varsayılan Türkçe
                try:
                    translated = translate_text(text, lang_code, from_lang=detected_lang)
                    await select_interaction.response.send_message(f"Tespit edilen dil: {detected_lang}\nÇeviri ({lang_code}): {translated}", ephemeral=True)
                except Exception as e:
                    await select_interaction.response.send_message(f"Çeviri sırasında hata oluştu: {str(e)}", ephemeral=True)

        view = discord.ui.View()
        view.add_item(LanguageSelect(self))
        await interaction.response.send_message("Hangi dile çevirmek istersiniz?", view=view, ephemeral=True)

# translate komutunu global scope'a taşı
@client.command(name="translate")
async def translate(ctx, *, text: str):
    view = PersistentView(ctx.author.name)
    # Son girilen metni view'a kaydet
    setattr(view, 'last_text', {ctx.author.name: text})
    await ctx.send("Mesajını aldım! Bununla ne yapmak istiyorsun?", view=view)

@client.command(name='new_project') # nexo new_project, yeni bir proje oluşturur ve bunu bellek.db'ye ekler
async def new_project(ctx):
    await ctx.send("Lütfen projenin adını girin!")

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    name = await client.wait_for('message', check=check)
    data = [ctx.author.id, name.content]
    await ctx.send("Lütfen projeye ait bağlantıyı gönderin!")
    link = await client.wait_for('message', check=check)
    data.append(link.content)

    statuses = [x[0] for x in manager.get_statuses()]
    await ctx.send("Lütfen projenin mevcut durumunu girin!", delete_after=60.0)
    await ctx.send("\n".join(statuses), delete_after=60.0)
    
    status = await client.wait_for('message', check=check)
    if status.content not in statuses:
        await ctx.send("Seçtiğiniz durum listede bulunmuyor. Lütfen tekrar deneyin!", delete_after=60.0)
        return

    status_id = manager.get_status_id(status.content)
    data.append(status_id)
    manager.insert_project([tuple(data)])
    await ctx.send("Proje kaydedildi")


@client.command(name='set_description')
async def set_description(ctx):
    await ctx.send('Hangi projeye açıklama eklemek istiyorsunuz?')
    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel
    projects = [x[2] for x in manager.get_projects(ctx.author.id)]
    await ctx.send('\n'.join(projects))
    project_name = await client.wait_for('message', check=check)
    if project_name.content not in projects:
        await ctx.send('Geçersiz proje seçimi')
        return
    await ctx.send('Yeni açıklamayı girin:')
    desc = await client.wait_for('message', check=check)
    manager.update_projects('description', (desc.content, project_name.content, ctx.author.id))
    await ctx.send('Açıklama kaydedildi')


@client.command(name='add_screenshot')
async def add_screenshot(ctx):
    await ctx.send('Lütfen ekran görüntüsünü (dosya olarak) gönderin (tek fotoğraf).')
    def check_file(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel and msg.attachments
    msg = await client.wait_for('message', check=check_file)
    attachment = msg.attachments[0]
    # choose project
    projects = [x[2] for x in manager.get_projects(ctx.author.id)]
    if not projects:
        await ctx.send('Önce bir proje ekleyin.')
        return
    await ctx.send('Bu görseli eklemek istediğiniz projeyi seçin:')
    await ctx.send('\n'.join(projects))
    project_name = await client.wait_for('message', check=lambda m: m.author==ctx.author and m.channel==ctx.channel)
    if project_name.content not in projects:
        await ctx.send('Geçersiz proje')
        return
    project_id = manager.get_project_id(project_name.content, ctx.author.id)
    # save file locally
    import os
    save_dir = os.path.join(os.path.dirname(__file__), 'screenshots')
    os.makedirs(save_dir, exist_ok=True)
    filename = f"{project_id}_{attachment.filename}"
    path = os.path.join(save_dir, filename)
    await attachment.save(path)
    # record filename in DB
    manager.add_screenshot(project_id, filename)
    await ctx.send('Ekran görüntüsü kaydedildi ve projeye eklendi.')


@client.command(name='add_status')
async def add_status(ctx):
    await ctx.send('Yeni durum adını girin:')
    def check(msg):
        return msg.author==ctx.author and msg.channel==ctx.channel
    msg = await client.wait_for('message', check=check)
    manager.add_status(msg.content)
    await ctx.send('Yeni durum eklendi.')


@client.command(name='add_skill')
async def add_skill_name(ctx):
    await ctx.send('Yeni beceri adını girin:')
    def check(msg):
        return msg.author==ctx.author and msg.channel==ctx.channel
    msg = await client.wait_for('message', check=check)
    manager.add_skill_name(msg.content)
    await ctx.send('Yeni beceri eklendi.')

@client.command(name='projects') # nexo projects, kullanıcının oluşturduğu tüm projelerini listeler
async def get_projects(ctx):
    user_id = ctx.author.id
    projects = manager.get_projects(user_id)
    if projects:
        text = "\n".join([f"Project name: {x[2]} \nLink: {x[4]}\n" for x in projects])
        await ctx.send(text)
    else:
        await ctx.send('Henüz herhangi bir projeniz yok!\nBir tane eklemeyi düşünün! !new_project komutunu kullanabilirsiniz.')

@client.command(name='skills') # nexo skills, belirli bir projeye (projede kullanılan) beceri ekler
async def skills(ctx):
    user_id = ctx.author.id
    projects = manager.get_projects(user_id)
    if projects:
        projects = [x[2] for x in projects]
        await ctx.send('Bir beceri eklemek istediğiniz projeyi seçin')
        await ctx.send("\n".join(projects))

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        project_name = await client.wait_for('message', check=check)
        if project_name.content not in projects:
            await ctx.send('Bu projeye sahip değilsiniz, lütfen tekrar deneyin! Beceri eklemek istediğiniz projeyi seçin')
            return

        skills = [x[1] for x in manager.get_skills()]
        await ctx.send('Bir beceri seçin')
        await ctx.send("\n".join(skills))

        skill = await client.wait_for('message', check=check)
        if skill.content not in skills:
            await ctx.send('Görünüşe göre seçtiğiniz beceri listede yok! Lütfen tekrar deneyin! Bir beceri seçin')
            return

        manager.insert_skill(user_id, project_name.content, skill.content)
        await ctx.send(f'{skill.content} becerisi {project_name.content} projesine eklendi')
    else:
        await ctx.send('Henüz herhangi bir projeniz yok!\nBir tane eklemeyi düşünün! !new_project komutunu kullanabilirsiniz.')

@client.command(name='delete') # !delete, belirli bir projeyi siler
async def delete_project(ctx):
    user_id = ctx.author.id
    projects = manager.get_projects(user_id)
    if projects:
        projects = [x[2] for x in projects]
        await ctx.send("Silmek istediğiniz projeyi seçin")
        await ctx.send("\n".join(projects))

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        project_name = await client.wait_for('message', check=check)
        if project_name.content not in projects:
            await ctx.send('Bu projeye sahip değilsiniz, lütfen tekrar deneyin!')
            return

        project_id = manager.get_project_id(project_name.content, user_id)
        manager.delete_project(user_id, project_id)
        await ctx.send(f'{project_name.content} projesi veri tabanından silindi!')
    else:
        await ctx.send('Henüz herhangi bir projeniz yok!\nBir tane eklemeyi düşünün! !new_project komutunu kullanabilirsiniz.')

@client.command(name='update_projects') # !update_projects, kullanıcının seçtiği projedeki belirli bir alanı günceller
async def update_projects(ctx):
    user_id = ctx.author.id
    projects = manager.get_projects(user_id)
    if projects:
        projects = [x[2] for x in projects]
        await ctx.send("Güncellemek istediğiniz projeyi seçin")
        await ctx.send("\n".join(projects))

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        project_name = await client.wait_for('message', check=check)
        if project_name.content not in projects:
            await ctx.send("Bir hata oldu! Lütfen güncellemek istediğiniz projeyi tekrar seçin:")
            return

        await ctx.send("Projede neyi değiştirmek istersiniz?")
        attributes = {'Proje adı': 'project_name', 'Açıklama': 'description', 'Proje bağlantısı': 'url', 'Proje durumu': 'status_id'}
        await ctx.send("\n".join(attributes.keys()))

        attribute = await client.wait_for('message', check=check)
        if attribute.content not in attributes:
            await ctx.send("Hata oluştu! Lütfen tekrar deneyin!")
            return

        if attribute.content == 'Durum':
            statuses = manager.get_statuses()
            await ctx.send("Projeniz için yeni bir durum seçin")
            await ctx.send("\n".join([x[0] for x in statuses]))
            update_info = await client.wait_for('message', check=check)
            if update_info.content not in [x[0] for x in statuses]:
                await ctx.send("Yanlış durum seçildi, lütfen tekrar deneyin!")
                return
            update_info = manager.get_status_id(update_info.content)
        else:
            await ctx.send(f"{attribute.content} için yeni bir değer girin")
            update_info = await client.wait_for('message', check=check)
            update_info = update_info.content

        manager.update_projects(attributes[attribute.content], (update_info, project_name.content, user_id))
        await ctx.send("Tüm işlemler tamamlandı! Proje güncellendi!")
    else:
        await ctx.send('Henüz herhangi bir projeniz yok!\nBir tane eklemeyi düşünün! !new_project komutunu kullanabilirsiniz.')



# clientu başlatmak için token ile çalıştır
client.run(token)