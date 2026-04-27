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
    ("مركبة سبورت بدون تصريح", "3000 + تغيير المركبة"),
    ("تدوير خط أصفر", "1000"),
    ("عدم تشغيل أضواء", "500"),
    ("لوحة مميزة بدون تصريح", "3000"),
    ("صدم أقماع", "5000 + منع يومين")
]

# ========= Select =========
class SelectMenu(disnake.ui.Select):
    def __init__(self, member, image):
        options = [disnake.SelectOption(label=v[0], description=v[1]) for v in VIOLATIONS]
        super().__init__(placeholder="اختر نوع المخالفة...", options=options)

        self.member = member
        self.image = image

    async def callback(self, inter):
        selected = next(v for v in VIOLATIONS if v[0] == self.values[0])

        embed = disnake.Embed(
            title="🚨 تم تسجيل مخالفة",
            color=disnake.Color.red(),
            timestamp=datetime.datetime.now()
        )

        embed.add_field(name="👮 العسكري", value=inter.author.mention)
        embed.add_field(name="👤 المواطن", value=self.member.mention)
        embed.add_field(name="📄 المخالفة", value=selected[0], inline=False)
        embed.add_field(name="💰 العقوبة", value=selected[1])

        if self.image:
            embed.set_image(url=self.image)

        await inter.message.delete()
        await inter.channel.send(embed=embed)

class View(disnake.ui.View):
    def __init__(self, member, image):
        super().__init__()
        self.add_item(SelectMenu(member, image))

# ========= أمر المخالفة =========
@bot.command(name="مخالفة")
async def violation(ctx, member: disnake.Member):

    image = None

    # 🔥 هنا السحر: يقرأ الصورة المرفوعة
    if ctx.message.attachments:
        image = ctx.message.attachments[0].url

    embed = disnake.Embed(
        title="🚓 نظام المخالفات",
        description=f"اختر نوع المخالفة لـ {member.mention}",
        color=disnake.Color.orange()
    )

    if image:
        embed.set_image(url=image)

    await ctx.send(embed=embed, view=View(member, image))

# ========= تشغيل =========
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

bot.run(os.getenv("TOKEN"))
