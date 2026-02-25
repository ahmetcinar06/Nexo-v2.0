import random
import asyncio

class PC:
    CPU = "AMD Ryzen 5 2600 6-Core Processor"
    GPU = "Radeon RX 570 Series"
    RAM = "16GB"
    SSD_C = "224GB"
    SSD_D = "224GB"

    async def about_PC(self, ctx):
        await ctx.send(f"CPU: {self.CPU}, GPU: {self.GPU}, RAM: {self.RAM}, SSD C: {self.SSD_C}, SSD D: {self.SSD_D}")

    async def PC_status_discord(self, ctx):
        CPU_utilization = random.randint(0, 100)
        GPU_utilization = random.randint(0, 100)
        RAM_utilization = random.randint(0, 100)
        SSD_C_utilization = random.randint(0, 100)
        SSD_D_utilization = random.randint(0, 100)
        await ctx.send(f"CPU: {CPU_utilization}%, GPU: {GPU_utilization}%, RAM: {RAM_utilization}%, SSD C: {SSD_C_utilization}%, SSD D: {SSD_D_utilization}%")
        if any(x > 80 for x in [CPU_utilization, GPU_utilization, RAM_utilization, SSD_C_utilization, SSD_D_utilization]):
            await ctx.send("Uyarı: Yüksek kaynak kullanımı tespit edildi! PC performansını optimize etmek ister misiniz? (evet/hayır)")
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel
            try:
                msg = await ctx.bot.wait_for('message', check=check, timeout=30)
                if msg.content.lower() == "evet":
                    await ctx.send("PC performansı optimize ediliyor...")
                elif msg.content.lower() == "hayır":
                    await ctx.send("Optimizasyon yapılmayacak. Uzun süre yüksek kullanım donanım ömrünü kısaltabilir.")
                else:
                    await ctx.send("Geçersiz yanıt. Lütfen 'evet' veya 'hayır' yazınız.")
            except asyncio.TimeoutError:
                await ctx.send("Yanıt alınamadı, işlem iptal edildi.")
        else:
            await ctx.send("PC'niz optimal çalışıyor.")

    async def antivirus_scan_discord(self, ctx):
        await ctx.send("Antivirüs taraması yapılıyor...")
        scan_result = random.choice(["Tehdit bulunamadı.", "Tehditler tespit edildi!"])
        await ctx.send(scan_result)
        if scan_result == "Tehditler tespit edildi!":
            await ctx.send("Bu bir yanlış alarm mı? (evet/hayır)")
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel
            try:
                msg = await ctx.bot.wait_for('message', check=check, timeout=30)
                if msg.content.lower() == "evet":
                    await ctx.send("Yanlış pozitif olarak işaretlendi.")
                else:
                    await ctx.send("Potansiyel tehditler kaldırılıyor...")
            except asyncio.TimeoutError:
                await ctx.send("Yanıt alınamadı, işlem iptal edildi.")

    async def system_update_discord(self, ctx):
        await ctx.send("Güncellemeler kontrol ediliyor...")
        update_available = random.choice([True, False])
        if update_available:
            await ctx.send("Güncellemeler mevcut. Sistem güncellensin mi? (evet/hayır)")
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel
            try:
                msg = await ctx.bot.wait_for('message', check=check, timeout=30)
                if msg.content.lower() == "evet":
                    await ctx.send("Sistem güncelleniyor...")
                    await ctx.send("Sistem güncellendi.")
                else:
                    await ctx.send("Güncelleme atlandı.")
            except asyncio.TimeoutError:
                await ctx.send("Yanıt alınamadı, işlem iptal edildi.")
        else:
            await ctx.send("Sisteminiz güncel.")

    async def processes(self, ctx):
        processes = ["Visual Studio Code", "Google Chrome", "File Explorer"]
        bg_processes = ["AMD External Events Client Module", "AMD Crash Defender", "Windows Security Service"]
        msg = "Çalışan işlemler:\n" + "\n".join(processes) + "\nArka plan işlemleri:\n" + "\n".join(bg_processes)
        await ctx.send(msg)