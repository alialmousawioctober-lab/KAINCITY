import disnake
from disnake.ext import commands
import datetime
import json
import os

intents = disnake.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="-", intents=intents)

# ========= ملفات =========
DB_FILE = 'violations.json'
BANK_FILE = 'bank.json'

# ========= تحميل =========
def load_db(file):
    if os.path.exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_db(file, data):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ========= الرصيد =========
def get_balance(user_id):
    data = load_db(BANK_FILE)
    uid = str(user_id)

    if uid not in data:
        data[uid] = {"cash": 0, "bank": 5000}
        save_db(BANK_FILE, data)

    return data[uid]

def update_balance(user_id, cash=0, bank=0):
    data = load_db(BANK_FILE)
    uid = str(user_id)

    if uid not in data:
        data[uid] = {"cash": 0, "bank": 5000}

    data[uid]["cash"] += cash
    data[uid]["bank"] += bank

    save_db(BANK_FILE, data)

# ========= المخالفات =========
VIOLATIONS = [
    {"label": "استخدام الجوال أثناء القيادة", "fine": 300},
    {"label": "عدم ربط حزام الأمان", "fine": 150},
    {"label": "قطع الإشارة", "fine": 500},
    {"label": "سرعة زائدة", "fine": 400},
]

class SelectViolation(disnake.ui.Select):
    def __init__(self, member, image, officer):
        options = [
            disnake.SelectOption(
                label=v["label"],
                description=f"الغرامة: {v['fine']}"
            ) for v in VIOLATIONS
        ]

        super().__init__(placeholder="اختر نوع المخالفة...", options=options)

        self.member = member
        self.image = image
        self.officer = officer

    async def callback(self, inter: disnake.MessageInteraction):
        db = load_db(DB_FILE)

        uid = str(self.member.id)
        if uid not in db:
            db[uid] = []

        selected = next(v for v in VIOLATIONS if v["label"] == self.values[0])

        v_id = len(db[uid]) + 1

        db[uid].append({
            "id": v_id,
            "type": selected["label"],
            "fine": selected["fine"],
            "officer": str(self.officer),
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        })

        save_db(DB_FILE, db)

        # 💸 يخصم من البنك
        update_balance(self.member.id, bank=-selected["fine"])

        embed = disnake.Embed(
            title="📄 تقرير مخالفة مرورية",
            color=disnake.Color.red(),
            timestamp=datetime.datetime.now()
        )

        embed.add_field(name="👮 العسكري", value=self.officer.mention, inline=True)
        embed.add_field(name="👤 المواطن", value=self.member.mention, inline=True)
        embed.add_field(name="🚫 نوع المخالفة", value=selected["label"], inline=False)
        embed.add_field(name="💰 الغرامة", value=str(selected["fine"]), inline=True)
        embed.add_field(name="🔢 رقم المخالفة", value=f"#{v_id}", inline=True)

        if self.image:
            embed.set_image(url=self.image)

        embed.set_footer(text="تم خصم الغرامة من البنك")

        await inter.message.delete()
        await inter.channel.send(embed=embed)

class View(disnake.ui.View):
    def __init__(self, member, image, officer):
        super().__init__()
        self.add_item(SelectViolation(member, image, officer))

# ========= أمر مخالفة =========
@bot.command(name="مخالفة")
async def violation(ctx, member: disnake.Member = None):
    if not member:
        return await ctx.send("❌ حدد شخص")

    image = None
    if ctx.message.attachments:
        image = ctx.message.attachments[0].url

    embed = disnake.Embed(
        title="🚨 نظام المخالفات",
        description=f"اختر نوع المخالفة لـ {member.mention}",
        color=disnake.Color.orange()
    )

    await ctx.send(embed=embed, view=View(member, image, ctx.author))

# ========= أمر الرصيد =========
@bot.command(name="رصيد")
async def balance(ctx, member: disnake.Member = None):
    member = member or ctx.author

    data = get_balance(member.id)

    cash = data["cash"]
    bank = data["bank"]
    total = cash + bank

    embed = disnake.Embed(
        title="🏦 مصرف الراجحي",
        color=disnake.Color.green()
    )

    embed.add_field(name="💵 الكاش", value=f"{cash}", inline=False)
    embed.add_field(name="🏦 البنك", value=f"{bank}", inline=False)
    embed.add_field(name="📊 المجموع الكلي", value=f"{total}", inline=False)

    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"طلب بواسطة: {ctx.author}")

    await ctx.send(embed=embed)

# ========= تشغيل =========
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

bot.run(os.getenv("TOKEN"))
