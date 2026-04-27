import disnake
from disnake.ext import commands
import datetime
import json
import os

intents = disnake.Intents.all()
bot = commands.Bot(command_prefix="-", intents=intents)

DB_FILE = "violations.json"
BANK_FILE = "bank.json"
SALARY_AMOUNT = 500

# ========= داتا =========
def load_db(file):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_db(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_user(gid, uid):
    bank = load_db(BANK_FILE)
    gid, uid = str(gid), str(uid)

    if gid not in bank:
        bank[gid] = {}

    if uid not in bank[gid]:
        bank[gid][uid] = {"cash": 0, "bank": 0}
        save_db(BANK_FILE, bank)

    return bank[gid][uid]

def update_user(gid, uid, cash=0, bank_amt=0):
    bank = load_db(BANK_FILE)
    gid, uid = str(gid), str(uid)

    data = get_user(gid, uid)
    data["cash"] += cash
    data["bank"] += bank_amt

    bank[gid][uid] = data
    save_db(BANK_FILE, bank)

# ========= المخالفات =========
VIOLATIONS = [
    ("زره", "500"),
    ("قطع اشارة", "3000"),
    ("عكس سير متعمد", "منع يومين"),
    ("سحب جلنط متقصد", "1000"),
    ("سرعة 75-80", "منع يومين"),
    ("سرعة 81-90", "منع 3 أيام"),
    ("سرعة 90+", "منع 5 أيام"),
    ("تجاوز سيارات", "1000"),
    ("هروب من عسكري", "باند"),
    ("تطلع الرصيف", "500"),
    ("بدون لوحة", "3000"),
    ("تفحيط", "4500"),
    ("مركبة سبورت بدون تصريح", "3000"),
    ("تدوير خط أصفر", "1000"),
    ("عدم تشغيل أضواء", "500"),
    ("لوحة مميزة بدون تصريح", "3000"),
    ("صدم أقماع", "5000")
]

# ========= تسجيل مخالفة =========
class SelectMenu(disnake.ui.Select):
    def __init__(self, member, image, guild_id):
        options = [disnake.SelectOption(label=v[0], description=v[1]) for v in VIOLATIONS]
        super().__init__(placeholder="اختر نوع المخالفة...", options=options)

        self.member = member
        self.image = image
        self.guild_id = guild_id

    async def callback(self, inter):
        selected = next(v for v in VIOLATIONS if v[0] == self.values[0])

        db = load_db(DB_FILE)
        gid = str(self.guild_id)
        uid = str(self.member.id)

        if gid not in db:
            db[gid] = {}

        if uid not in db[gid]:
            db[gid][uid] = []

        v_id = len(db[gid][uid]) + 1

        db[gid][uid].append({
            "id": v_id,
            "type": selected[0],
            "fine": selected[1]
        })

        save_db(DB_FILE, db)

        embed = disnake.Embed(
            title="🚨 تم تسجيل مخالفة",
            color=disnake.Color.red()
        )

        embed.add_field(name="👤 المواطن", value=self.member.mention)
        embed.add_field(name="📄 المخالفة", value=selected[0], inline=False)
        embed.add_field(name="💰 العقوبة", value=selected[1])
        embed.add_field(name="🔢 رقم المخالفة", value=f"#{v_id}")

        if self.image:
            embed.set_image(url=self.image)

        await inter.message.delete()
        await inter.channel.send(embed=embed)

class View(disnake.ui.View):
    def __init__(self, member, image, guild_id):
        super().__init__()
        self.add_item(SelectMenu(member, image, guild_id))

@bot.command(name="مخالفة")
async def violation(ctx, member: disnake.Member):
    image = None
    if ctx.message.attachments:
        image = ctx.message.attachments[0].url

    embed = disnake.Embed(
        title="🚓 نظام المخالفات",
        description=f"اختر نوع المخالفة لـ {member.mention}",
        color=disnake.Color.orange()
    )

    if image:
        embed.set_image(url=image)

    await ctx.send(embed=embed, view=View(member, image, ctx.guild.id))

# ========= تسديد =========
class PaySelect(disnake.ui.Select):
    def __init__(self, violations, guild_id, user_id):
        options = [
            disnake.SelectOption(
                label=f"#{v['id']} - {v['type']}",
                description=v['fine']
            ) for v in violations
        ]

        super().__init__(placeholder="اختر المخالفة للتسديد...", options=options)

        self.guild_id = guild_id
        self.user_id = user_id

    async def callback(self, inter):
        v_id = int(self.values[0].split("#")[1].split(" ")[0])

        db = load_db(DB_FILE)
        gid = str(self.guild_id)
        uid = str(self.user_id)

        violation = next((v for v in db[gid][uid] if v["id"] == v_id), None)

        if not violation:
            return

        # فقط إذا كانت رقم
        if not violation["fine"].isdigit():
            return await inter.response.send_message("❌ هذه مخالفة بدون غرامة مالية", ephemeral=True)

        fine = int(violation["fine"])
        data = get_user(self.guild_id, self.user_id)

        if data["bank"] < fine:
            return await inter.response.send_message("❌ رصيدك ما يكفي", ephemeral=True)

        update_user(self.guild_id, self.user_id, bank_amt=-fine)

        db[gid][uid] = [v for v in db[gid][uid] if v["id"] != v_id]
        save_db(DB_FILE, db)

        embed = disnake.Embed(
            title="✅ تم التسديد",
            color=disnake.Color.green()
        )

        embed.add_field(name="💰 المبلغ", value=fine)
        embed.add_field(name="📄 المخالفة", value=violation["type"])

        await inter.message.delete()
        await inter.channel.send(embed=embed)

class PayView(disnake.ui.View):
    def __init__(self, violations, guild_id, user_id):
        super().__init__()
        self.add_item(PaySelect(violations, guild_id, user_id))

@bot.command(name="تسديد")
async def pay(ctx):
    db = load_db(DB_FILE)
    gid = str(ctx.guild.id)
    uid = str(ctx.author.id)

    if gid not in db or uid not in db[gid] or len(db[gid][uid]) == 0:
        return await ctx.send("❌ ما عندك مخالفات")

    violations = db[gid][uid]

    embed = disnake.Embed(
        title="💳 اختر مخالفة للتسديد",
        color=disnake.Color.blue()
    )

    await ctx.send(embed=embed, view=PayView(violations, ctx.guild.id, ctx.author.id))

# ========= تشغيل =========
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

bot.run(os.getenv("TOKEN"))
