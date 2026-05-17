import random
import asyncio
import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from characters import master_characters

# --- CONFIGURATION ---
# ⚠️ SECURITY WARNING: Put your NEW token here. The old one is likely revoked!
BOT_TOKEN = "8543296575:AAGsAL_exd_D2MZAmUMMPXF-KjleyKPSj3M"

# Mock Database (RAM Cache)
users_db = {}

# Router setup
router = Router()

# --- INLINE KEYBOARDS ---
def get_new_user_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚪 OPEN SELECTION GATE (DRAFT TEAM)", callback_data="draft_team")]
    ])

def get_draft_success_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 VIEW ROSTER & STATS", callback_data="menu_roster")],
        [InlineKeyboardButton(text="🏟️ ENTER THE ARENA", callback_data="menu_arena")],
        [InlineKeyboardButton(text="⚙️ MAIN MENU", callback_data="menu_main")]
    ])

# --- REPLACE THIS IN INLINE KEYBOARDS ---
def get_main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏟️ ARENA", callback_data="menu_arena"), 
         InlineKeyboardButton(text="📋 ROSTER", callback_data="menu_roster")],
        [InlineKeyboardButton(text="⚽ MY TEAM", callback_data="menu_team"), # NEW BUTTON
         InlineKeyboardButton(text="🏋️ TRAIN", callback_data="menu_train")],
        [InlineKeyboardButton(text="🚪 SELECTION GATE", callback_data="menu_gacha"),
         InlineKeyboardButton(text="⚙️ SETTINGS", callback_data="menu_settings")]
    ])

# --- HANDLERS ---

@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    # Path B: Returning Manager (User exists in RAM DB)
    if user_id in users_db:
        user_data = users_db[user_id]
        text = (
            "🟦 <b>BLUE LOCK FACILITY: ONLINE</b>\n\n"
            f"Welcome back to the monitoring room, Manager {first_name}. "
            "Your team is awaiting orders.\n\n"
            "📊 <b>MANAGER STATUS:</b>\n"
            f"🏆 <b>Rank:</b> {user_data['rank']} ({user_data['stratum']})\n"
            f"⚡ <b>Energy:</b> {user_data['energy']}/5\n"
            f"💎 <b>Ego Points (EP):</b> {user_data['ep']}\n"
            f"💵 <b>Cash:</b> {user_data['cash']}\n\n"
            "<i>The Arena is currently active. What is your next move?</i>"
        )
        await message.answer(text, reply_markup=get_main_menu_kb())
        
    # Path A: New Arrival (User not in RAM DB)
    else:
        text = (
            "👁️ <b>WELCOME TO BLUE LOCK.</b>\n\n"
            f"Congratulations, Manager {first_name}. You have been selected from thousands of candidates.\n\n"
            "Football isn't about the power of friendship. It’s about crushing the opposition and proving your striker is the best in the world. Your job is to find uncut gems and draw out their raw ego.\n\n"
            "The facility is waiting. It is time to draft your first 5 players."
        )
        await message.answer(text, reply_markup=get_new_user_kb())

@router.callback_query(F.data == "draft_team")
async def process_draft_team(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if user_id in users_db:
        await callback.answer("You have already drafted your team!", show_alert=True)
        return

    # Filter for ONLY 2-Star (B-Rank) characters
    b_rank_pool = [name for name, data in master_characters.items() if data['rarity'] == 2]
    
    # Randomly select 5 unique characters from the 2-star pool
    starting_team = random.sample(b_rank_pool, 5)

    users_db[user_id] = {
        "rank": "Unranked",
        "stratum": "Stratum 5",
        "energy": 5,
        "ep": 10000,  # We will give them 0 to start
        "cash": 0,
        "roster": starting_team.copy(),
        "active_team": starting_team.copy()
    }

    text = (
        "🟦🔥 <b>SELECTION GATE OPENED!</b> 🔥🟦\n\n"
        "You have drafted your initial squad. Right now, they are nothing but unpolished trash. It is your job to turn them into monsters.\n\n"
        "🎁 <b>YOUR STARTING 5:</b>\n"
    )
    
    # Dynamically generate the text for whoever they pulled
    for char_name in starting_team:
        char_data = master_characters[char_name]
        text += f"⭐ {char_data['name']} (<i>{char_data['variant']}</i>)\n"

    text += (
        "\n📖 <b>MANAGER'S SURVIVAL GUIDE:</b>\n"
        "<b>1. View Stats:</b> Check your [📋 Roster] to see their individual weapons.\n"
        "<b>2. The Arena:</b> Enter the [🏟️ Arena] to battle other managers for Cash and EP.\n"
        "<b>3. Evolve:</b> Use EP at the Selection Gate to pull S-Rank prodigies."
    )
    
    await callback.message.edit_text(text, reply_markup=get_draft_success_kb())
    await callback.answer()

@router.message(Command("stats"))
async def cmd_stats(message: Message, command: CommandObject):
    user_id = message.from_user.id
    
    if user_id not in users_db:
        await message.answer("System Error: Manager not found. Please send /start.")
        return
    
    if not command.args:
        await message.answer("⚠️ <b>Error:</b> Please provide a character name. (Usage: <code>/stats Bachira</code>)")
        return
    
    char_name = command.args.capitalize()
    user_data = users_db[user_id]
    
    if char_name not in master_characters:
        await message.answer(f"⚠️ <b>Error:</b> {char_name} does not exist in the Blue Lock database.")
        return
        
    if char_name not in user_data.get("roster", []):
        await message.answer(f"❌ <b>Error:</b> You do not own {char_name}. Head to the Selection Gate to draft them.")
        return
        
    char_data = master_characters[char_name]
    rarity_stars = "⭐" * char_data['rarity']
    overall = (char_data['pass'] + char_data['dribble'] + char_data['shoot'] + char_data['defense'] + char_data['speed'] + char_data['ego']) // 6
    
    text = (
        f"{rarity_stars} <b>{char_data['name']}</b>\n"
        f"🧬 <b>Variant:</b> <i>{char_data['variant']}</i>\n\n"
        "📊 <b>BASE ATTRIBUTES:</b>\n"
        f"👟 <b>Speed:</b> {char_data['speed']}\n"
        f"🎯 <b>Shoot:</b> {char_data['shoot']}\n"
        f"🧠 <b>Ego:</b> {char_data['ego']}\n"
        f"👁️ <b>Pass:</b> {char_data['pass']}\n"
        f"🛡️ <b>Defense:</b> {char_data['defense']}\n"
        f"⚡ <b>Dribble:</b> {char_data['dribble']}\n\n"
        f"📈 <b>Overall Rating:</b> {overall}\n"
    )
    
    is_active = char_name in user_data.get("active_team", [])
    
    if is_active:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ CURRENTLY IN ACTIVE TEAM", callback_data="none")]
        ])
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ ADD TO ACTIVE TEAM", callback_data=f"swap_init_{char_name}")]
        ])
        
    await message.answer(text, reply_markup=kb)

@router.callback_query(F.data.startswith("swap_init_"))
async def process_swap_init(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if user_id not in users_db:
        return await callback.answer("Error: Manager not found.", show_alert=True)
        
    # Extract the character name we want to swap IN (e.g., "swap_init_Bachira" -> "Bachira")
    char_to_swap_in = callback.data.split("_")[2]
    active_team = users_db[user_id].get("active_team", [])
    
    text = (
        "🔄 <b>TEAM SUBSTITUTION</b>\n\n"
        f"You are moving <b>{char_to_swap_in}</b> to the Active Lineup.\n"
        "Select a current player to bench:"
    )
    
    # Dynamically generate buttons for the 5 currently active players
    buttons = []
    for active_char in active_team:
        # Callback data format: swap_confirm_IN_OUT (e.g., swap_confirm_Bachira_Raichi)
        callback_string = f"swap_confirm_{char_to_swap_in}_{active_char}"
        buttons.append([InlineKeyboardButton(text=f"🔁 Bench {active_char}", callback_data=callback_string)])
        
    buttons.append([InlineKeyboardButton(text="❌ CANCEL", callback_data="menu_main")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("swap_confirm_"))
async def process_swap_confirm(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if user_id not in users_db:
        return await callback.answer("Error: Manager not found.", show_alert=True)
        
    # Parse the data: "swap_confirm_Bachira_Raichi"
    parts = callback.data.split("_")
    char_in = parts[2]
    char_out = parts[3]
    
    active_team = users_db[user_id]["active_team"]
    
    # Execute the swap in the RAM database
    if char_out in active_team:
        idx = active_team.index(char_out)
        active_team[idx] = char_in
        
    text = (
        "✅ <b>SUBSTITUTION COMPLETE!</b>\n\n"
        f"<b>{char_in}</b> has entered the pitch.\n"
        f"<i>{char_out} has been benched.</i>"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚽ VIEW ACTIVE TEAM", callback_data="menu_team")],
        [InlineKeyboardButton(text="⚙️ MAIN MENU", callback_data="menu_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "menu_main")
async def process_menu_main(callback: CallbackQuery):
    user_id = callback.from_user.id
    first_name = callback.from_user.first_name
    
    if user_id not in users_db:
        return await callback.answer("System Error: Manager not found.", show_alert=True)
    
    user_data = users_db[user_id]
    
    text = (
        "🟦 <b>BLUE LOCK FACILITY: ONLINE</b>\n\n"
        f"Welcome back to the monitoring room, Manager {first_name}. "
        "Your team is awaiting orders.\n\n"
        "📊 <b>MANAGER STATUS:</b>\n"
        f"🏆 <b>Rank:</b> {user_data['rank']} ({user_data['stratum']})\n"
        f"⚡ <b>Energy:</b> {user_data['energy']}/5\n"
        f"💎 <b>Ego Points (EP):</b> {user_data['ep']}\n"
        f"💵 <b>Cash:</b> {user_data['cash']}\n\n"
        "<i>The Arena is currently active. What is your next move?</i>"
    )
    
    await callback.message.edit_text(text, reply_markup=get_main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "menu_team")
async def process_menu_team(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if user_id not in users_db:
        return await callback.answer("System Error: Manager not found.", show_alert=True)

    user_data = users_db[user_id]
    active_team = user_data.get("active_team", [])
    
    text = "⚽ <b>YOUR ACTIVE LINEUP (STARTING 5)</b>\n\n"
    total_power = 0

    for char_name in active_team:
        if char_name in master_characters:
            char_data = master_characters[char_name]
            power = (char_data['pass'] + char_data['dribble'] + char_data['shoot'] + char_data['defense'] + char_data['speed'] + char_data['ego']) // 6
            total_power += power
            rarity_stars = "⭐" * char_data['rarity']
            text += f"{rarity_stars} <b>{char_name}</b> (<i>{char_data['variant']}</i>) - OVR: {power}\n"

    text += f"\n📊 <b>TOTAL SQUAD RATING: {total_power}</b>\n"
    text += "<i>This is the team you will take into the Arena.</i>"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 BACK TO MAIN MENU", callback_data="menu_main")]
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "menu_roster")
async def process_menu_roster(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if user_id not in users_db:
        return await callback.answer("System Error: Manager not found.", show_alert=True)

    user_data = users_db[user_id]
    roster = user_data.get("roster", [])
    
    text = f"📋 <b>YOUR FULL ROSTER (Owned: {len(roster)})</b>\n\n"
    
    # Simple list of all owned characters
    for char_name in roster:
        if char_name in master_characters:
            rarity_stars = "⭐" * master_characters[char_name]['rarity']
            text += f"{rarity_stars} <b>{char_name}</b>\n"

    text += "\n<i>Use <code>/stats [Name]</code> to view their details or swap them into your active team.</i>"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 BACK TO MAIN MENU", callback_data="menu_main")]
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "menu_gacha")
async def process_menu_gacha(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if user_id not in users_db:
        return await callback.answer("System Error: Manager not found.", show_alert=True)
        
    user_ep = users_db[user_id]["ep"]
    
    text = (
        "🚪 <b>THE SELECTION GATE</b>\n\n"
        "Test your luck and draw new Egoists to strengthen your roster.\n\n"
        f"💎 <b>Your Ego Points:</b> {user_ep} EP\n"
        "🎟️ <b>Cost per pull:</b> 100 EP\n\n"
        "<b>Drop Rates:</b>\n"
        "⭐⭐ (B-Rank): 60%\n"
        "⭐⭐⭐ (A-Rank): 30%\n"
        "⭐⭐⭐⭐ (S-Rank): 8%\n"
        "⭐⭐⭐⭐⭐ (EX-Rank): 2%"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 PULL 1x (100 EP)", callback_data="gacha_pull")],
        [InlineKeyboardButton(text="🔙 BACK TO MAIN MENU", callback_data="menu_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "gacha_pull")
async def process_gacha_pull(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if user_id not in users_db:
        return await callback.answer("System Error: Manager not found.", show_alert=True)
        
    user_data = users_db[user_id]
    
    # 1. Check if they have enough EP
    if user_data["ep"] < 100:
        return await callback.answer("❌ Not enough Ego Points (EP)! Win Arena matches to earn more.", show_alert=True)
        
    # 2. Deduct EP
    user_data["ep"] -= 100
    
    # 3. Roll for Rarity (1 to 100)
    roll = random.randint(1, 100)
    if roll <= 2:
        target_rarity = 5 # 2% EX-Rank
    elif roll <= 10:
        target_rarity = 4 # 8% S-Rank
    elif roll <= 40:
        target_rarity = 3 # 30% A-Rank
    else:
        target_rarity = 2 # 60% B-Rank
        
    # 4. Filter characters by the rolled rarity
    pool = [name for name, data in master_characters.items() if data['rarity'] == target_rarity]
    
    # 5. Select the character
    pulled_char = random.choice(pool)
    char_data = master_characters[pulled_char]
    rarity_stars = "⭐" * char_data['rarity']
    
    # 6. Check for duplicates ("Devour" mechanic placeholder)
    if pulled_char in user_data["roster"]:
        # If they already own them, give them compensation cash for now
        user_data["cash"] += 500
        dupe_text = f"\n\n⚠️ <i>You already own this Egoist! They were devoured and converted into 💵 500 Cash.</i>"
    else:
        user_data["roster"].append(pulled_char)
        dupe_text = f"\n\n✅ <i>Added to your [📋 Roster]. Use /stats {pulled_char} to view their weapons.</i>"
        
    # 7. Build the visual output
    text = (
        "🟦🔥 <b>SELECTION GATE OPENED!</b> 🔥🟦\n\n"
        f"You pulled a {rarity_stars} player!\n\n"
        f"👤 <b>{char_data['name']}</b>\n"
        f"🧬 <b>Variant:</b> <i>{char_data['variant']}</i>\n"
        f"📈 <b>Base Ego:</b> {char_data['ego']}"
        f"{dupe_text}\n\n"
        f"💎 <b>Remaining EP:</b> {user_data['ep']}"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 PULL AGAIN (100 EP)", callback_data="gacha_pull")],
        [InlineKeyboardButton(text="🔙 BACK TO GATE", callback_data="menu_gacha")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Access the Blue Lock facility"),
        BotCommand(command="stats", description="View player stats (e.g., /stats Bachira)")
    ]
    await bot.set_my_commands(commands)
    print("✅ Bot commands successfully uploaded to Telegram.")

# --- BOT RUNNER ---
async def main():
    # Setup logging to see errors in Termux
    logging.basicConfig(level=logging.INFO)
    
    # Set default parse mode to HTML globally for the bot
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    
    print("⚽ Blue Lock Bot is starting...")
    
    # Auto-load the commands into Telegram's menu
    await setup_bot_commands(bot)
    
    # Drop pending updates so it doesn't spam old messages when you restart the script
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Start polling
    await dp.start_polling(bot)

