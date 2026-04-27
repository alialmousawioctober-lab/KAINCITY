import disnake
from disnake.ext import commands
import datetime
import json
import os

intents = disnake.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="-", intents=intents)

DB_FILE = 'violations.json'
BANK_FILE = 'bank.json'

# ========= ملفات =========
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

# ========= البنك =========
def get_balance(user_id):
    data = load_db(BANK_FILE)
    uid = str(user_id)

    if uid not in data:
        data[uid] = {"cash": 0, "bank": 5000, "loan": 0}
        save_db(BANK_FILE, data)

    return data[uid]

def update_balance(user_id, cash=0, bank=0, loan=0):
    data = load_db(BANK_FILE)
    uid = str(user_id)

    if uid not in data:
        data[uid] = {"cash": 0, "bank": 5000, "loan": 0}

    data[uid]["cash"] += cash
    data[uid]["bank"] += bank
    data[uid]["loan"] += loan

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
            disnake.SelectOption(label=v["label"], description=f"الغرامة: {v['fine']}")
            for v in VIOLATIONS
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

        # خصم من البنك
        update_balance(self.member.id, bank=-selected["fine"])

        embed = disnake.Embed(
            title="📄 تقرير مخالفة مرورية",
            color=disnake.Color.red(),
            timestamp=datetime.datetime.now()
        )

        embed.add_field(name="👮 العسكري", value=self.officer.mention)
        embed.add_field(name="👤 المواطن", value=self.member.mention)
        embed.add_field(name="🚫 نوع المخالفة", value=selected["label"], inline=False)
        embed.add_field(name="💰 الغرامة", value=str(selected["fine"]))
        embed.add_field(name="🔢 رقم المخالفة", value=f"#{v_id}")

        if self.image:
            embed.set_image(url=self.image)

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

# ========= البنك =========

# رصيد
@bot.command(name="رصيد")
async def balance(ctx, member: disnake.Member = None):
    member = member or ctx.author
    data = get_balance(member.id)

    embed = disnake.Embed(title="🏦 مصرف الراجحي", color=disnake.Color.green())
    embed.add_field(name="💵 الكاش", value=data["cash"])
    embed.add_field(name="🏦 البنك", value=data["bank"])
    embed.add_field(name="📊 المجموع", value=data["cash"] + data["bank"])

    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"طلب بواسطة: {ctx.author}")

    await ctx.send(embed=embed)

# تحويل
@bot.command(name="تحويل")
async def transfer(ctx, member: disnake.Member, amount: int):
    if amount <= 0:
        return await ctx.send("❌ مبلغ غير صحيح")

    data = get_balance(ctx.author.id)

    if data["bank"] < amount:
        return await ctx.send("❌ رصيدك ما يكفي")

    update_balance(ctx.author.id, bank=-amount)
    update_balance(member.id, bank=amount)

    await ctx.send(f"✅ تم تحويل {amount} إلى {member.mention}")

# قرض
@bot.command(name="قرض")
async def loan(ctx, amount: int):
    if amount <= 0:
        return await ctx.send("❌ مبلغ غير صحيح")

    update_balance(ctx.author.id, bank=amount, loan=amount)

    await ctx.send(f"💰 تم إعطاؤك قرض {amount}")

# إيداع
@bot.command(name="إيداع")
async def deposit(ctx, amount: int):
    data = get_balance(ctx.author.id)

    if amount > data["cash"]:
        return await ctx.send("❌ ما عندك كاش كافي")

    update_balance(ctx.author.id, cash=-amount, bank=amount)

    await ctx.send(f"🏦 تم إيداع {amount}")

# سحب
@bot.command(name="سحب")
async def withdraw(ctx, amount: int):
    data = get_balance(ctx.author.id)

    if amount > data["bank"]:
        return await ctx.send("❌ ما عندك رصيد بالبنك")

    update_balance(ctx.author.id, cash=amount, bank=-amount)

    await ctx.send(f"💵 تم سحب {amount}")

# ========= تشغيل =========
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

bot.run(os.getenv("TOKEN"))
