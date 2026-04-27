import disnake
from disnake.ext import commands
import datetime
import json
import os

GUILD_ID = 1365331666406543411 

intents = disnake.Intents.default()
intents.message_content = True 
intents.members = True 

bot = commands.Bot(command_prefix="-", intents=intents)

DB_FILE = 'mountain_violations.json'
BANK_FILE = 'mountain_bank.json'
LOANS_FILE = 'mountain_loans.json'

def load_db(file):
    if os.path.exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_db(file, data):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_user_data(guild_id, user_id):
    bank = load_db(BANK_FILE)
    gid, uid = str(guild_id), str(user_id)
    if gid not in bank: bank[gid] = {}
    if uid not in bank[gid]:
        bank[gid][uid] = {"cash": 0, "bank": 0}
        save_db(BANK_FILE, bank)
    return bank[gid][uid]

def update_user_data(guild_id, user_id, cash=0, bank_amt=0):
    bank = load_db(BANK_FILE)
    gid, uid = str(guild_id), str(user_id)
    if gid not in bank: bank[gid] = {}
    data = get_user_data(guild_id, user_id)
    data["cash"] += cash
    data["bank"] += bank_amt
    bank[gid][uid] = data
    save_db(BANK_FILE, bank)

VIOLATION_TYPES = [
    {"label": "استخدام الجوال أثناء القيادة", "value": "استخدام الجوال أثناء القيادة", "fine": 300},
    {"label": "عدم ربط حزام الأمان", "value": "عدم ربط حزام الأمان", "fine": 150},
    {"label": "قطع الإشارة الضوئية", "value": "قطع الإشارة الضوئية", "fine": 500},
    {"label": "السرعة الزائدة", "value": "السرعة الزائدة", "fine": 400},
    {"label": "عكس السير", "value": "عكس السير", "fine": 600},
]

class ViolationSelect(disnake.ui.Select):
    def __init__(self, member, image_url, officer, guild_id):
        options = [disnake.SelectOption(label=v["label"], value=v["value"], description=f"الغرامة: {v['fine']}") for v in VIOLATION_TYPES]
        super().__init__(placeholder="اختر نوع المخالفة من هنا...", options=options)
        self.member, self.image_url, self.officer, self.guild_id = member, image_url, officer, guild_id

    async def callback(self, inter: disnake.MessageInteraction):
        selected = next(v for v in VIOLATION_TYPES if v["value"] == self.values[0])
        db = load_db(DB_FILE)
        gid, uid = str(self.guild_id), str(self.member.id)
        if gid not in db: db[gid] = {}
        if uid not in db[gid]: db[gid][uid] = []
        v_id = len(db[gid][uid]) + 1
        db[gid][uid].append({"id": v_id, "type": selected["value"], "fine": selected["fine"], "officer": str(self.officer), "date": datetime.datetime.now().strftime('%Y-%m-%d %H:%M')})
        save_db(DB_FILE, db)
        embed = disnake.Embed(title="🚨 تم قيد مخالفة عسكرية", color=disnake.Color.red(), timestamp=datetime.datetime.now())
        embed.add_field(name="👮‍♂️ العسكري", value=self.officer.mention, inline=True)
        embed.add_field(name="👤 المواطن", value=self.member.mention, inline=True)
        embed.add_field(name="📄 نوع المخالفة", value=selected["value"], inline=False)
        embed.add_field(name="💰 الغرامة", value=f"{selected['fine']}", inline=True)
        embed.add_field(name="🔢 رقم المخالفة", value=f"#{v_id}", inline=True)
        if self.image_url: embed.set_image(url=self.image_url)
        embed.set_footer(text="لتسديد المخالفة اكتب: -تسديد")
        await inter.message.delete()
        await inter.channel.send(embed=embed)

class PaySelect(disnake.ui.Select):
    def __init__(self, violations, guild_id, user_id):
        options = [disnake.SelectOption(label=f"مخالفة #{v['id']}", value=str(v['id']), description=f"{v['type']} | الغرامة: {v['fine']}") for v in violations]
        super().__init__(placeholder="اختر المخالفة التي تريد تسديدها...", options=options)
        self.guild_id, self.user_id = guild_id, user_id

    async def callback(self, inter: disnake.MessageInteraction):
        v_id = int(self.values[0])
        db = load_db(DB_FILE)
        gid, uid = str(self.guild_id), str(self.user_id)
        violation = next((v for v in db[gid][uid] if v["id"] == v_id), None)
        if not violation: return
        fine = violation["fine"]
        data = get_user_data(self.guild_id, self.user_id)
        if data["bank"] >= fine: update_user_data(self.guild_id, self.user_id, bank_amt=-fine)
        elif (data["bank"] + data["cash"]) >= fine:
            rem = fine - data["bank"]
            update_user_data(self.guild_id, self.user_id, bank_amt=-data["bank"], cash=-rem)
        else: return await inter.response.send_message(f"❌ رصيدك لا يكفي ({fine})", ephemeral=True)
        db[gid][uid] = [v for v in db[gid][uid] if v["id"] != v_id]
        save_db(DB_FILE, db)
        await inter.message.delete()
        await inter.channel.send("✅ تم التسديد")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# 🔥 الأوامر (هذي كانت ناقصة)
@bot.command(name="مخالفة")
async def violation_cmd(ctx, member: disnake.Member):
    view = disnake.ui.View()
    view.add_item(ViolationSelect(member, None, ctx.author, ctx.guild.id))
    await ctx.send("اختر نوع المخالفة:", view=view)

@bot.command(name="تسديد")
async def pay_cmd(ctx):
    db = load_db(DB_FILE)
    gid, uid = str(ctx.guild.id), str(ctx.author.id)
    if gid not in db or uid not in db[gid]:
        return await ctx.send("❌ ما عندك مخالفات")
    view = disnake.ui.View()
    view.add_item(PaySelect(db[gid][uid], ctx.guild.id, ctx.author.id))
    await ctx.send("اختر المخالفة:", view=view)

@bot.command(name="رصيد")
async def balance(ctx):
    d = get_user_data(ctx.guild.id, ctx.author.id)
    await ctx.send(f"💰 الكاش: {d['cash']} | البنك: {d['bank']}")

bot.run(os.getenv("TOKEN"))
