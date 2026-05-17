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

# --- GAME CONSTANTS & HELPERS ---
RARITY_CAPS = {2: 20, 3: 35, 4: 50, 5: 70}

def create_char_profile():
    """Generates a fresh stat profile for a newly pulled character."""
    return {
        "level": 1,
        "exp": 0,
        "unspent_points": 0,
        "bonus_stats": {
            "speed": 0, "shoot": 0, "dribble": 0, 
            "defense": 0, "pass": 0, "ego": 0
        }
    }

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
        return await callback.answer("You have already drafted your team!", show_alert=True)

    # Filter for ONLY 2-Star (B-Rank) characters
    b_rank_pool = [name for name, data in master_characters.items() if data['rarity'] == 2]
    starting_team = random.sample(b_rank_pool, 5)

    # Create the new dictionary-based roster
    roster_dict = {char_name: create_char_profile() for char_name in starting_team}

    users_db[user_id] = {
        "rank": "Unranked",
        "stratum": "Stratum 5",
        "energy": 5,
        "ep": 10000,  # Keeping this at 10k for your Gacha testing
        "cash": 0,
        "roster": roster_dict, # Now a dictionary!
        "active_team": starting_team.copy(), # Keep as a list of names for easy swapping
        "in_match": False
    }

    text = (
        "🟦🔥 <b>SELECTION GATE OPENED!</b> 🔥🟦\n\n"
        "You have drafted your initial squad. Right now, they are nothing but unpolished trash. It is your job to turn them into monsters.\n\n"
        "🎁 <b>YOUR STARTING 5:</b>\n"
    )
    
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
        
    if char_name not in user_data.get("roster", {}):
        await message.answer(f"❌ <b>Error:</b> You do not own {char_name}. Head to the Selection Gate to draft them.")
        return
        
    # Grab both the base template AND the player's unique profile
    char_data = master_characters[char_name]
    char_profile = user_data["roster"][char_name] 
    
    rarity_stars = "⭐" * char_data['rarity']
    
    # Calculate Total Stats = Base + Bonus
    tot_spd = char_data['speed'] + char_profile['bonus_stats']['speed']
    tot_sht = char_data['shoot'] + char_profile['bonus_stats']['shoot']
    tot_ego = char_data['ego'] + char_profile['bonus_stats']['ego']
    tot_pas = char_data['pass'] + char_profile['bonus_stats']['pass']
    tot_def = char_data['defense'] + char_profile['bonus_stats']['defense']
    tot_dri = char_data['dribble'] + char_profile['bonus_stats']['dribble']
    
    overall = (tot_spd + tot_sht + tot_ego + tot_pas + tot_def + tot_dri) // 6
    
    text = (
        f"{rarity_stars} <b>{char_data['name']}</b> (Lv.{char_profile['level']})\n"
        f"🧬 <b>Variant:</b> <i>{char_data['variant']}</i>\n\n"
        "📊 <b>CURRENT ATTRIBUTES (Base + Bonus):</b>\n"
        f"👟 <b>Speed:</b> {tot_spd}\n"
        f"🎯 <b>Shoot:</b> {tot_sht}\n"
        f"🧠 <b>Ego:</b> {tot_ego}\n"
        f"👁️ <b>Pass:</b> {tot_pas}\n"
        f"🛡️ <b>Defense:</b> {tot_def}\n"
        f"⚡ <b>Dribble:</b> {tot_dri}\n\n"
        f"📈 <b>Overall Rating:</b> {overall}\n"
        f"🔵 <b>Unspent Points:</b> {char_profile['unspent_points']}\n"
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
    roster_dict = user_data.get("roster", {})
    
    text = f"📋 <b>YOUR FULL ROSTER (Owned: {len(roster_dict)})</b>\n\n"
    
    # Iterate through the keys (character names) in the new dictionary
    for char_name, char_profile in roster_dict.items():
        if char_name in master_characters:
            rarity_stars = "⭐" * master_characters[char_name]['rarity']
            # We can now show their actual level!
            text += f"{rarity_stars} <b>{char_name}</b> (Lv.{char_profile['level']})\n"

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
    
    if user_data["ep"] < 100:
        return await callback.answer("❌ Not enough Ego Points (EP)! Win Arena matches to earn more.", show_alert=True)
        
    user_data["ep"] -= 100
    
    roll = random.randint(1, 100)
    if roll <= 2: target_rarity = 5
    elif roll <= 10: target_rarity = 4
    elif roll <= 40: target_rarity = 3
    else: target_rarity = 2
        
    pool = [name for name, data in master_characters.items() if data['rarity'] == target_rarity]
    pulled_char = random.choice(pool)
    char_data = master_characters[pulled_char]
    rarity_stars = "⭐" * char_data['rarity']
    
    # --- DEVOUR LOGIC ---
    if pulled_char in user_data["roster"]:
        current_level = user_data["roster"][pulled_char]["level"]
        max_level = RARITY_CAPS[char_data['rarity']]
        
        if current_level < max_level:
            # Level Up!
            user_data["roster"][pulled_char]["level"] += 1
            user_data["roster"][pulled_char]["unspent_points"] += 3
            dupe_text = f"\n\n🔥 <i>DEVOUR SUCCESSFUL! {pulled_char} reached Lv.{current_level + 1}! (+3 Stat Points)</i>"
        else:
            # Max Level Hit
            user_data["cash"] += 2500
            dupe_text = f"\n\n⚠️ <i>{pulled_char} is at MAX LEVEL! Converted to 💵 2,500 Cash.</i>"
    else:
        # First time pulling this character
        user_data["roster"][pulled_char] = create_char_profile()
        dupe_text = f"\n\n✅ <i>Added to your [📋 Roster]. Use /stats {pulled_char} to view their weapons.</i>"
        
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

@router.callback_query(F.data == "menu_train")
async def process_menu_train(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if user_id not in users_db:
        return await callback.answer("System Error: Manager not found.", show_alert=True)

    user_data = users_db[user_id]
    active_team = user_data.get("active_team", [])
    
    text = (
        "🏋️ <b>BLUE LOCK PHYSICAL TRAINING CENTER</b>\n\n"
        "<i>Break your limits. Who are we pushing to the brink today?</i>\n\n"
        f"💵 <b>Available Cash:</b> {user_data['cash']}\n\n"
        "Select a player from your Active Team to allocate stats:"
    )
    
    # Generate a button for each active player
    buttons = []
    for char_name in active_team:
        unspent = user_data["roster"][char_name]["unspent_points"]
        btn_text = f"⭐ {char_name} ({unspent} Pts)"
        # callback format: train_select_Bachira
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"train_select_{char_name}")])
        
    buttons.append([InlineKeyboardButton(text="🔙 BACK TO MAIN MENU", callback_data="menu_main")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("train_select_"))
async def process_train_select(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in users_db:
        return await callback.answer("System Error: Manager not found.", show_alert=True)

    char_name = callback.data.split("_")[2]
    user_data = users_db[user_id]
    
    char_data = master_characters[char_name]
    char_profile = user_data["roster"][char_name]
    
    unspent = char_profile["unspent_points"]
    cash = user_data["cash"]
    
    # Calculate Total Stats (Base + Bonus) to show what they are working with
    tot_spd = char_data['speed'] + char_profile['bonus_stats']['speed']
    tot_sht = char_data['shoot'] + char_profile['bonus_stats']['shoot']
    tot_ego = char_data['ego'] + char_profile['bonus_stats']['ego']
    tot_pas = char_data['pass'] + char_profile['bonus_stats']['pass']
    tot_def = char_data['defense'] + char_profile['bonus_stats']['defense']
    tot_dri = char_data['dribble'] + char_profile['bonus_stats']['dribble']
    
    text = (
        f"🏋️ <b>TRAINING: {char_name.upper()} (Lv.{char_profile['level']})</b>\n\n"
        f"💵 <b>Available Cash:</b> {cash}\n"
        f"🔵 <b>Unspent Points:</b> {unspent}\n\n"
        "<i>Applying 1 Stat Point costs 💵 100 Cash.</i>\n\n"
        f"👟 <b>Speed:</b> {tot_spd} <i>(+{char_profile['bonus_stats']['speed']})</i>\n"
        f"🎯 <b>Shoot:</b> {tot_sht} <i>(+{char_profile['bonus_stats']['shoot']})</i>\n"
        f"🧠 <b>Ego:</b> {tot_ego} <i>(+{char_profile['bonus_stats']['ego']})</i>\n"
        f"👁️ <b>Pass:</b> {tot_pas} <i>(+{char_profile['bonus_stats']['pass']})</i>\n"
        f"🛡️ <b>Defense:</b> {tot_def} <i>(+{char_profile['bonus_stats']['defense']})</i>\n"
        f"⚡ <b>Dribble:</b> {tot_dri} <i>(+{char_profile['bonus_stats']['dribble']})</i>\n"
    )
    
    # Generate the stat addition buttons
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ SPEED", callback_data=f"train_add_speed_{char_name}"),
         InlineKeyboardButton(text="➕ SHOOT", callback_data=f"train_add_shoot_{char_name}")],
        [InlineKeyboardButton(text="➕ EGO", callback_data=f"train_add_ego_{char_name}"),
         InlineKeyboardButton(text="➕ PASS", callback_data=f"train_add_pass_{char_name}")],
        [InlineKeyboardButton(text="➕ DEFENSE", callback_data=f"train_add_defense_{char_name}"),
         InlineKeyboardButton(text="➕ DRIBBLE", callback_data=f"train_add_dribble_{char_name}")],
        [InlineKeyboardButton(text="🔄 RESET BUILD (500 Cash)", callback_data=f"train_reset_{char_name}")],
        [InlineKeyboardButton(text="🔙 BACK TO FACILITY", callback_data="menu_train")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("train_add_"))
async def process_train_add(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in users_db:
        return await callback.answer("Error: Manager not found.", show_alert=True)
        
    parts = callback.data.split("_")
    stat_to_add = parts[2] # e.g., 'speed'
    char_name = parts[3]   # e.g., 'Bachira'
    
    user_data = users_db[user_id]
    char_profile = user_data["roster"][char_name]
    
    # Validation Checks
    if char_profile["unspent_points"] < 1:
        return await callback.answer("❌ No unspent points available!", show_alert=True)
    if user_data["cash"] < 100:
        return await callback.answer("❌ You need 100 Cash to apply a point!", show_alert=True)
        
    # Apply the upgrade
    user_data["cash"] -= 100
    char_profile["unspent_points"] -= 1
    char_profile["bonus_stats"][stat_to_add] += 1
    
    # We cheat a little bit here: We just re-call the exact same screen to refresh the UI!
    await process_train_select(callback)


@router.callback_query(F.data.startswith("train_reset_"))
async def process_train_reset(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in users_db:
        return await callback.answer("Error: Manager not found.", show_alert=True)
        
    char_name = callback.data.split("_")[2]
    user_data = users_db[user_id]
    char_profile = user_data["roster"][char_name]
    
    # Calculate how many points they actually spent so we can refund them
    total_spent = sum(char_profile["bonus_stats"].values())
    
    if total_spent == 0:
        return await callback.answer("⚠️ No points have been spent on this character yet.", show_alert=True)
        
    if user_data["cash"] < 500:
        return await callback.answer("❌ You need 500 Cash to reset a build!", show_alert=True)
        
    # Execute the reset
    user_data["cash"] -= 500
    char_profile["unspent_points"] += total_spent
    
    # Zero out all bonus stats
    for stat in char_profile["bonus_stats"]:
        char_profile["bonus_stats"][stat] = 0
        
    await callback.answer("🔄 Build successfully reset!", show_alert=True)
    await process_train_select(callback)

async def on_startup(bot: Bot):
    print("⚙️ Running Facility Maintenance (Startup Hook)...")
    
    # 1. Auto-load the commands into Telegram's menu
    commands = [
        BotCommand(command="start", description="Access the Blue Lock facility"),
        BotCommand(command="stats", description="View player stats (e.g., /stats Bachira)")
    ]
    await bot.set_my_commands(commands)
    print("✅ Bot commands successfully uploaded.")
    
    # 2. Match State Reset & Compensation Logic
    compensated_count = 0
    for user_id, user_data in users_db.items():
        if user_data.get("in_match") == True:
            # Reset their state
            user_data["in_match"] = False
            
            # Award compensation
            user_data["cash"] += 150
            user_data["ep"] += 15
            
            # Send them a direct notification
            try:
                text = (
                    "🛠️ <b>FACILITY MAINTENANCE COMPLETE</b>\n\n"
                    "The Blue Lock system underwent an unexpected reboot while you were in a match. "
                    "Your match has been safely terminated to prevent data corruption.\n\n"
                    "🎁 <b>Compensation Received:</b> +150 Cash, +15 EP\n\n"
                    "<i>Return to the pitch when you are ready.</i>"
                )
                # We use bot.send_message because there is no 'message' or 'callback' to reply to here
                await bot.send_message(chat_id=user_id, text=text)
                compensated_count += 1
            except Exception as e:
                print(f"⚠️ Failed to send compensation to {user_id}: {e}")
                
    print(f"✅ Maintenance complete. Compensated {compensated_count} trapped managers.")

# --- BOT RUNNER ---
async def main():
    logging.basicConfig(level=logging.INFO)
    
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    
    # Register the startup hook here BEFORE polling starts
    dp.startup.register(on_startup)
    
    print("⚽ Blue Lock Bot is starting...")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by Manager.")

