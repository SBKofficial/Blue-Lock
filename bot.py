import random
import asyncio
import logging
import difflib
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
active_matches = {}

# Router setup
router = Router()

# --- GAME CONSTANTS & HELPERS ---
RARITY_CAPS = {2: 20, 3: 35, 4: 50, 5: 70}

# 🟢 NEW: The 5x8 Tactical Playbook
FORMATIONS = {
    "1-2-1": {
        "name": "Balanced (1-2-1)",
        "slots": {"FW": "Striker", "MF_L": "Left Mid", "MF_R": "Right Mid", "DF": "Center Back", "GK": "Goalkeeper"},
        "coords": {"FW": (4, 2), "MF_L": (5, 1), "MF_R": (5, 3), "DF": (6, 2), "GK": (7, 2)}
    },
    "2-1-1": {
        "name": "Attacking (2-1-1)",
        "slots": {"FW_L": "Left Wing", "FW_R": "Right Wing", "MF": "Center Mid", "DF": "Center Back", "GK": "Goalkeeper"},
        "coords": {"FW_L": (4, 1), "FW_R": (4, 3), "MF": (5, 2), "DF": (6, 2), "GK": (7, 2)}
    },
    "1-1-2": {
        "name": "Defensive (1-1-2)",
        "slots": {"FW": "Striker", "MF": "Center Mid", "DF_L": "Left Back", "DF_R": "Right Back", "GK": "Goalkeeper"},
        "coords": {"FW": (4, 2), "MF": (5, 2), "DF_L": (6, 1), "DF_R": (6, 3), "GK": (7, 2)}
    }
}

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

    b_rank_pool = [name for name, data in master_characters.items() if data['rarity'] == 2]
    starting_team = random.sample(b_rank_pool, 5)

    roster_dict = {char_name: create_char_profile() for char_name in starting_team}

    users_db[user_id] = {
        "rank": "Unranked",
        "stratum": "Stratum 5",
        "energy": 5,
        "ep": 10000,
        "cash": 0,
        "roster": roster_dict,
        "formation": "1-2-1", # 🟢 NEW: Default Formation
        "active_team": {
            "FW": None,
            "MF_L": None,
            "MF_R": None,
            "DF": None,
            "GK": None
        },
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
        "<b>1. Set Your Formation:</b> Your pitch is currently empty! Go to [⚽ MY TEAM] to assign your 5 players to their positions.\n"
        "<b>2. View Stats:</b> Check your [📋 Roster] to see their individual weapons.\n"
        "<b>3. The Arena:</b> Enter the [🏟️ Arena] to battle other managers once your team is set."
    )
    
    await callback.message.edit_text(text, reply_markup=get_draft_success_kb())
    await callback.answer()

async def display_stats_ui(message: Message, user_id: int, char_name: str):
    """Helper function to render and send the stats UI so we can use it from commands AND buttons."""
    user_data = users_db[user_id]
    
    if char_name not in user_data.get("roster", {}):
        await message.answer(f"❌ <b>Error:</b> You do not own {char_name}. Head to the Selection Gate to draft them.")
        return
        
    char_data = master_characters[char_name]
    char_profile = user_data["roster"][char_name] 
    
    rarity_stars = "⭐" * char_data['rarity']
    
    tot_spd = char_data['speed'] + char_profile['bonus_stats']['speed']
    tot_sht = char_data['shoot'] + char_profile['bonus_stats']['shoot']
    tot_ego = char_data['ego'] + char_profile['bonus_stats']['ego']
    tot_pas = char_data['pass'] + char_profile['bonus_stats']['pass']
    tot_def = char_data['defense'] + char_profile['bonus_stats']['defense']
    tot_dri = char_data['dribble'] + char_profile['bonus_stats']['dribble']
    
    overall = (tot_spd + tot_sht + tot_ego + tot_pas + tot_def + tot_dri) // 6
    
    text = (
        f"{rarity_stars} <b>{char_data['name']}</b> (Lv.{char_profile['level']})\n"
        f"🧬 <b>Variant:</b> <i>{char_data['variant']}</i>\n"
        f"📍 <b>Natural Position:</b> {char_data['position']}\n\n"
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
    
    is_active = char_name in user_data.get("active_team", {}).values()
    
    if is_active:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            # 🟢 FIX: Changed "none" to "ignore"
            [InlineKeyboardButton(text="✅ CURRENTLY IN ACTIVE TEAM", callback_data="ignore")]
        ])

    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ ADD TO ACTIVE TEAM", callback_data=f"swap_init_{char_name}")]
        ])
        
    await message.answer(text, reply_markup=kb)


@router.message(Command("stats"))
async def cmd_stats(message: Message, command: CommandObject):
    user_id = message.from_user.id
    
    if user_id not in users_db:
        return await message.answer("System Error: Manager not found. Please send /start.")
    
    if not command.args:
        return await message.answer("⚠️ <b>Error:</b> Please provide a character name. (Usage: <code>/stats Bachira</code>)")
    
    # Clean the user's input and make it lowercase
    query = command.args.strip().lower()
    
    # 1. Try an Exact Case-Insensitive Match First
    char_name = next((k for k in master_characters.keys() if k.lower() == query), None)
    
    # 2. If no exact match, trigger the "Funky" Fuzzy Matching
    if not char_name:
        keys_lower = [k.lower() for k in master_characters.keys()]
        # Find the closest match with a minimum similarity cutoff of 40%
        matches = difflib.get_close_matches(query, keys_lower, n=1, cutoff=0.4)
        
        if matches:
            # Grab the proper case-sensitive key from the database
            closest_char = next(k for k in master_characters.keys() if k.lower() == matches[0])
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"🔍 YES, SHOW {closest_char.upper()}", callback_data=f"stats_fuzzy_{closest_char}")]
            ])
            return await message.answer(f"⚠️ <b>Character Not Found.</b>\n\nDid you mean <b>{closest_char}</b>?", reply_markup=kb)
        else:
            return await message.answer(f"⚠️ <b>Error:</b> No character found matching '{command.args}'.")
            
    # 3. If exact match found, render stats immediately
    await display_stats_ui(message, user_id, char_name)


@router.callback_query(F.data.startswith("stats_fuzzy_"))
async def process_stats_fuzzy(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in users_db:
        return await callback.answer("System Error: Manager not found.", show_alert=True)

    char_name = callback.data.split("_", 2)[2]
    
    # Clean up the chat by deleting the "Did you mean?" message
    await callback.message.delete()
    
    # Render the actual stats
    await display_stats_ui(callback.message, user_id, char_name)
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
    active_team = user_data.get("active_team", {})
    form_id = user_data.get("formation", "1-2-1")
    form_data = FORMATIONS[form_id]
    
    text = f"📋 <b>TACTICAL FORMATION: {form_data['name']}</b>\n\n"
    total_power = 0
    
    # 🟢 Dynamically load the roles for this specific formation
    for role_key, role_name in form_data["slots"].items():
        char_name = active_team.get(role_key)
        
        if char_name and char_name in master_characters:
            char_data = master_characters[char_name]
            pos_warning = "⚠️" if char_data.get('position') != role_key.split('_')[0] else "✅"
            
            power = (char_data['pass'] + char_data['dribble'] + char_data['shoot'] + char_data['defense'] + char_data['speed'] + char_data['ego']) // 6
            total_power += power
            
            text += f"<b>{role_name}:</b> {pos_warning} {char_name} (OVR: {power})\n"
            text += f"└ <i>Natural: {char_data.get('position', 'UNK')} | {char_data['variant']}</i>\n\n"
        else:
            text += f"<b>{role_name}:</b> ⚠️ EMPTY\n└ <i>Assign a player to this slot!</i>\n\n"

    text += f"📊 <b>TOTAL SQUAD OVR: {total_power}</b>\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗺️ CHANGE FORMATION", callback_data="menu_formations")],
        [InlineKeyboardButton(text="🔙 BACK TO MAIN MENU", callback_data="menu_main")]
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "menu_formations")
async def process_menu_formations(callback: CallbackQuery):
    text = (
        "🗺️ <b>TACTICAL BOARD</b>\n\n"
        "Select a new tactical layout. \n"
        "⚠️ <i>WARNING: Changing your formation will bench your entire active team. You will need to re-assign your players!</i>"
    )
    
    buttons = []
    for form_id, form_data in FORMATIONS.items():
        buttons.append([InlineKeyboardButton(text=f"📋 {form_data['name']}", callback_data=f"setform:{form_id}")])
        
    buttons.append([InlineKeyboardButton(text="❌ CANCEL", callback_data="menu_team")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@router.callback_query(F.data.startswith("setform:"))
async def process_set_formation(callback: CallbackQuery):
    user_id = callback.from_user.id
    form_id = callback.data.split(":")[1]
    
    user_data = users_db[user_id]
    user_data["formation"] = form_id
    
    # 🟢 Wipe the active team clean and build the new empty slots
    new_team = {}
    for role_key in FORMATIONS[form_id]["slots"].keys():
        new_team[role_key] = None
        
    user_data["active_team"] = new_team
    
    await callback.answer(f"✅ Formation updated to {FORMATIONS[form_id]['name']}!", show_alert=True)
    await process_menu_team(callback) # Return to the team menu to see the empty slots

@router.callback_query(F.data.startswith("swap_init_"))
async def process_swap_init(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in users_db:
        return await callback.answer("Error: Manager not found.", show_alert=True)
        
    # 🟢 FIX: Added maxsplit=2 so it doesn't shatter names like Wanima_J
    char_to_swap_in = callback.data.split("_", 2)[2]
    
    active_team = users_db[user_id].get("active_team", {})
   
    text = (
        "🔄 <b>TACTICAL SUBSTITUTION</b>\n\n"
        f"Deploying <b>{char_to_swap_in}</b> to the pitch.\n"
        "Select which position slot they will fill:"
    )
    
    buttons = []
    form_id = users_db[user_id].get("formation", "1-2-1")
    roles = FORMATIONS[form_id]["slots"]
    
    for slot_key, slot_name in roles.items():
        current_player = active_team.get(slot_key) or "Empty"
        callback_string = f"swap_confirm:{char_to_swap_in}:{slot_key}"
        buttons.append([InlineKeyboardButton(text=f"🔁 {slot_name} (Bench {current_player})", callback_data=callback_string)])

    buttons.append([InlineKeyboardButton(text="❌ CANCEL", callback_data="menu_main")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("swap_confirm:")) 
async def process_swap_confirm(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in users_db:
        return await callback.answer("Error: Manager not found.", show_alert=True)
        
    # 🟢 FIX: Split by colon!
    parts = callback.data.split(":") 
    char_in = parts[1]
    slot_key = parts[2] 
    
    user_data = users_db[user_id]
    active_team = user_data["active_team"]
    
    # 🟢 FIX: Prevent Mid-Match Swapping
    if user_data.get("in_match"):
        return await callback.answer("❌ You cannot substitute players while an Arena match is active!", show_alert=True)
    
    # Remove player from any existing slot first
    for existing_slot in active_team:
        if active_team[existing_slot] == char_in:
            active_team[existing_slot] = None

    char_out = active_team.get(slot_key)
    
    # Execute the swap
    active_team[slot_key] = char_in
        
    text = (
        "✅ <b>SUBSTITUTION COMPLETE!</b>\n\n"
        f"<b>{char_in}</b> has entered the pitch at <b>{slot_key}</b>.\n"
        f"<i>{char_out} has been benched.</i>"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚽ VIEW ACTIVE TEAM", callback_data="menu_team")],
        [InlineKeyboardButton(text="⚙️ MAIN MENU", callback_data="menu_main")]
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
    active_team = user_data.get("active_team", {}) # 🟢 Changed default to dictionary
    
    text = (
        "🏋️ <b>BLUE LOCK PHYSICAL TRAINING CENTER</b>\n\n"
        "<i>Break your limits. Who are we pushing to the brink today?</i>\n\n"
        f"💵 <b>Available Cash:</b> {user_data['cash']}\n\n"
        "Select a player from your Active Team to allocate stats:"
    )
    
    buttons = []
    # 🟢 FIX: Iterate over values() and ignore "Empty" slots
    for char_name in active_team.values():
        if not char_name:
            continue
            
        # Look up their unspent points safely
        unspent = user_data["roster"][char_name]["unspent_points"]
        btn_text = f"⭐ {char_name} ({unspent} Pts)"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"trainselect:{char_name}")])
        
    buttons.append([InlineKeyboardButton(text="🔙 BACK TO MAIN MENU", callback_data="menu_main")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("trainselect:"))
async def process_train_select(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in users_db:
        return await callback.answer("System Error: Manager not found.", show_alert=True)

    char_name = callback.data.split(":", 1)[1]
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
        [InlineKeyboardButton(text="➕ SPEED", callback_data=f"trainadd:speed:{char_name}"),
         InlineKeyboardButton(text="➕ SHOOT", callback_data=f"trainadd:shoot:{char_name}")],
        [InlineKeyboardButton(text="➕ EGO", callback_data=f"trainadd:ego:{char_name}"),
         InlineKeyboardButton(text="➕ PASS", callback_data=f"trainadd:pass:{char_name}")],
        [InlineKeyboardButton(text="➕ DEFENSE", callback_data=f"trainadd:defense:{char_name}"),
         InlineKeyboardButton(text="➕ DRIBBLE", callback_data=f"trainadd:dribble:{char_name}")],
        [InlineKeyboardButton(text="🔄 RESET BUILD (500 Cash)", callback_data=f"trainreset:{char_name}")],
        [InlineKeyboardButton(text="🔙 BACK TO FACILITY", callback_data="menu_train")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("trainadd:"))
async def process_train_add(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in users_db:
        return await callback.answer("Error: Manager not found.", show_alert=True)
        
    parts = callback.data.split(":")
    stat_to_add = parts[1]
    char_name = parts[2]
    
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
    
    # 🟢 FIX: Overwrite the callback data before forwarding so it extracts the name correctly!
    callback.data = f"trainselect:{char_name}"
    await process_train_select(callback)

@router.callback_query(F.data.startswith("trainreset:"))
async def process_train_reset(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in users_db:
        return await callback.answer("Error: Manager not found.", show_alert=True)
        
    char_name = callback.data.split(":", 1)[1]
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
    
    # 🟢 FIX: Overwrite the callback data here too!
    callback.data = f"trainselect:{char_name}"
    await process_train_select(callback)

@router.callback_query(F.data == "menu_arena")
async def process_menu_arena(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in users_db:
        return await callback.answer("System Error: Manager not found.", show_alert=True)

    text = (
        "🏟️ <b>BLUE LOCK ARENA</b>\n\n"
        "Welcome to the battlefield. Here, only your Ego and your stats matter.\n\n"
        "<i>Select your matchmaking queue:</i>"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 AI PRACTICE (SOLO)", callback_data="arena_start_ai")],
        # 🟢 FIX: Changed "none" to "ignore"
        [InlineKeyboardButton(text="👥 RANKED MATCH (COMING SOON)", callback_data="ignore")],
        [InlineKeyboardButton(text="🔙 BACK TO MAIN MENU", callback_data="menu_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "menu_settings")
async def process_menu_settings(callback: CallbackQuery):
    # 🟢 FIX: Added a placeholder handler for the Settings menu
    await callback.answer("⚙️ Settings Room is currently under construction by Ego.", show_alert=True)

def render_match_ui(user_id):
    match = active_matches[user_id]
    
    header = (
        f"📊 <b>SCORE: [ BHARAT {match['player_score']} - {match['ai_score']} AI ]</b>\n"
        f"🔋 <b>EGO GAUGE: {match['ego_gauge']}%</b>\n"
        f"⏱️ <b>TURN: {match['turn']}</b>\n"
        "〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️\n"
    )

    if match["ui_state"] == "overview":
        text = header + f"{match['log']}\n\n<i>Tap your ball carrier (⚽) to make a play, or tap any player to view stats.</i>"
    
        buttons = []
        for row in range(8): # 🟢 8 Rows
            row_buttons = []
            for col in range(5): # 🟢 5 Columns
                
                # 🟢 If it's the top or bottom row, everything is a net EXCEPT the center tile (col 2) where the GK stands
                if (row == 0 or row == 7) and col != 2:
                    row_buttons.append(InlineKeyboardButton(text="🥅", callback_data="ignore"))
                    continue
                
                # 🟢 Priority Logic
                occupants_here = [char for char, pos in match["positions"].items() if pos == (row, col)]
                occupant = None
                
                if occupants_here:
                    if match["ball_carrier"] in occupants_here:
                        occupant = match["ball_carrier"] 
                    elif match.get("ui_state") == "defense" and match.get("active_defender") in occupants_here:
                        occupant = match["active_defender"] 
                    else:
                        occupant = occupants_here[0] 

                    # 🟢 FIX: We restored the color and prefix logic that was deleted!
                    if occupant == "AI_GK":
                        btn_text = "🧤 AI GK"
                    elif occupant in match["player_team"]:
                        prefix = "⚽ 🟢 " if occupant == match["ball_carrier"] else "🟢 "
                        btn_text = f"{prefix}{occupant}"
                    else:
                        prefix = "⚽ 🔴 " if occupant == match["ball_carrier"] else "🔴 "
                        btn_text = f"{prefix}{occupant}"

                    row_buttons.append(InlineKeyboardButton(text=btn_text, callback_data=f"match_tap_{occupant}"))
                else:
                    row_buttons.append(InlineKeyboardButton(text="⬛️", callback_data="ignore"))
            buttons.append(row_buttons)
            
        buttons.append([InlineKeyboardButton(text="🏳️ FORFEIT MATCH", callback_data="match_forfeit")])
        return text, InlineKeyboardMarkup(inline_keyboard=buttons)
        
    elif match["ui_state"] == "targeting":
        text = header + "👁️ <b>PASS INITIATED</b>\n<i>Select a teammate on the pitch to receive the ball.</i>"
        
        buttons = []
        for row in range(8): # 🟢 FIX: Upgraded to 8 Rows
            row_buttons = []
            for col in range(5): # 🟢 FIX: Upgraded to 5 Columns
                
                # 🟢 FIX: Updated Goalpost logic to match the 5x8 board
                if (row == 0 or row == 7) and col != 2:
                    row_buttons.append(InlineKeyboardButton(text="🥅", callback_data="ignore"))
                    continue
                
                # 🟢 Priority Logic
                occupants_here = [char for char, pos in match["positions"].items() if pos == (row, col)]
                occupant = None
                
                if occupants_here:
                    if match["ball_carrier"] in occupants_here:
                        occupant = match["ball_carrier"] 
                    elif match.get("ui_state") == "defense" and match.get("active_defender") in occupants_here:
                        occupant = match["active_defender"] 
                    else:
                        occupant = occupants_here[0] 

                    if occupant in match["player_team"] and occupant != match["ball_carrier"]:
                        btn_text = f"📍 {occupant}"
                        row_buttons.append(InlineKeyboardButton(text=btn_text, callback_data=f"match_execute_pass_{occupant}"))
                    elif occupant == match["ball_carrier"]:
                        row_buttons.append(InlineKeyboardButton(text="⚽ (You)", callback_data="ignore"))
                    elif occupant == "AI_GK":
                        row_buttons.append(InlineKeyboardButton(text="🧤", callback_data="ignore"))
                    else:
                        row_buttons.append(InlineKeyboardButton(text="🔴", callback_data="ignore"))
                else:
                    row_buttons.append(InlineKeyboardButton(text="⬛️", callback_data="ignore"))
            buttons.append(row_buttons)
            
        buttons.append([InlineKeyboardButton(text="🔙 CANCEL PASS", callback_data="match_action_back")])
        return text, InlineKeyboardMarkup(inline_keyboard=buttons)

    elif match["ui_state"] == "defense":
        defender = match["active_defender"]
        carrier = match["ball_carrier"]
        stamina = match["stamina"][defender]
        
        text = (
            f"{header}"
            f"🛡️ <b>DEFENSIVE ENGAGEMENT</b>\n"
            f"🟢 <b>Your Defender:</b> {defender} (Stamina: {stamina}/100)\n"
            f"🔴 <b>Enemy Carrier:</b> {carrier}\n\n"
            f"<i>Read the enemy's play. What is {defender} going to do?</i>"
        )
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛑 BLOCK DRIBBLE", callback_data="match_defend_dribble"),
             InlineKeyboardButton(text="🦅 CUT PASS", callback_data="match_defend_pass")],
            [InlineKeyboardButton(text="🧱 BLOCK SHOOT", callback_data="match_defend_shoot")],
            [InlineKeyboardButton(text="🔙 BACK TO PITCH", callback_data="match_action_back")]
        ])
        return text, kb

    elif match["ui_state"] == "action":
        carrier = match["ball_carrier"]
        stamina = match["stamina"][carrier]
        
        row, col = match["positions"][carrier]
        # 🟢 NEW: 8 Rows and 5 Lanes of text descriptions
        zones = {1: "AI Penalty Box", 2: "Attacking 3rd", 3: "Upper Midfield", 4: "Lower Midfield", 5: "Defensive 3rd", 6: "Own Penalty Box"}
        lane = {0: "Far Left Wing", 1: "Left Half-Space", 2: "Center", 3: "Right Half-Space", 4: "Far Right Wing"}
        
        zone_name = zones.get(row, "Goal Line") 
        current_zone = f"{lane.get(col, 'Center')} ({zone_name})"
        
        text = (
            f"{header}"
            f"🏃‍♂️ <b>{carrier}</b>\n"
            f"🔋 <b>Stamina:</b> {stamina}/100\n"
            f"📍 <b>Location:</b> {current_zone}\n\n"
            f"<i>What is your move?</i>"
        )
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚡ DRIBBLE", callback_data="match_action_dribble"),
             InlineKeyboardButton(text="🎯 SHOOT", callback_data="match_action_shoot")],
            [InlineKeyboardButton(text="👁️ PASS", callback_data="match_action_pass")],
            [InlineKeyboardButton(text="🔙 BACK TO PITCH", callback_data="match_action_back")]
        ])
        return text, kb

    return header, InlineKeyboardMarkup(inline_keyboard=[])

@router.callback_query(F.data.startswith("match_defend_"))
async def process_match_defense(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in active_matches:
        return await callback.answer("Match expired.", show_alert=True)
        
    match = active_matches[user_id]
    user_data = users_db[user_id]
    
    player_action = callback.data.split("_")[2] # 'dribble', 'pass', or 'shoot'
    defender = match["active_defender"]
    carrier = match["ball_carrier"]
    
    # AI Logic: Decide what the AI is going to do
    ai_choices = ["dribble", "pass"]
    ai_row = match["positions"][carrier][0]
    if ai_row >= 3: # If AI is deep in your half, they might shoot
        ai_choices.append("shoot")
        
    ai_action = random.choice(ai_choices)
    
    # Get Stats
    def_data = master_characters[defender]
    def_prof = user_data["roster"][defender]
    ai_data = master_characters[carrier]
    
    # Calculate Power
    def_power = def_data["defense"] + def_prof["bonus_stats"]["defense"]
    ai_power = ai_data[ai_action] # AI just uses base stats for now
    
    log_msgs = [f"🤖 AI chose to <b>{ai_action.upper()}</b>!"]
    
    # ⚠️ OOP Penalty for Defender
    assigned_role = next((role for role, char in user_data["active_team"].items() if char == defender), None)
    if assigned_role and not assigned_role.startswith(def_data["position"]):
        def_power = int(def_power * 0.70)
        log_msgs.append(f"⚠️ {defender} is out of position! Defense drops by 30%.")
        
    # Fatigue
    if match["stamina"][defender] < 30:
        def_power = int(def_power * 0.50)
        log_msgs.append(f"💦 {defender} is exhausted!")
        
    match["stamina"][defender] = max(0, match["stamina"][defender] - 10)
    
    # 🧠 PREDICTION MULTIPLIER
    if player_action == ai_action:
        def_power = int(def_power * 1.5)
        log_msgs.append(f"🧠 <b>PERFECT READ!</b> {defender} perfectly predicted the {ai_action}!")
    else:
        ai_power = int(ai_power * 1.5)
        log_msgs.append(f"❌ <b>MISREAD!</b> You moved to stop a {player_action}, leaving {ai_action} wide open!")
        
    # --- RESOLVE CLASH ---
    success = def_power >= ai_power
    
    if success:
        # Player wins the ball back!
        match["possession"] = "player"
        match["ball_carrier"] = defender
        match["ego_gauge"] = min(100, match["ego_gauge"] + 20)
        match["log"] = "\n".join(log_msgs) + f"\n✅ <b>INTERCEPTION!</b> {defender} crushes {carrier}! ({def_power} vs {ai_power})"

    else:
        # AI Wins and advances
        if ai_action == "shoot":
            match["ai_score"] += 1
            match["log"] = "\n".join(log_msgs) + f"\n🥅 <b>GOAL CONCEDED!</b> {carrier} blasts it into your net! ({ai_power} vs {def_power})"
            
            # 🟢 KICKOFF RESET: You get the ball back, everyone resets to formation!
            match["possession"] = "player"
            match["ball_carrier"] = match["player_team"][0] # Give ball to your striker
            
            form_id = user_data.get("formation", "1-2-1")
            new_positions = {
                "AI_GK": (0, 2),
                match["ai_team"][0]: (3, 2),
                match["ai_team"][1]: (2, 1),
                match["ai_team"][2]: (2, 3),
                match["ai_team"][3]: (1, 2),
            }
            # Snap player team back to their chosen formation
            for role, char_name in user_data["active_team"].items():
                if char_name: 
                    new_positions[char_name] = FORMATIONS[form_id]["coords"][role]
                    
            match["positions"] = new_positions

        elif ai_action == "pass":
            # AI passes to a random teammate
            ai_receiver = random.choice([p for p in match["ai_team"] if p != carrier])
            match["ball_carrier"] = ai_receiver
            match["log"] = "\n".join(log_msgs) + f"\n❌ <b>DEFENSE BROKEN!</b> {carrier} passes to {ai_receiver}."
            
            # AI defensive line pushes down
            if ai_receiver != "AI_GK": 
                r, c = match["positions"][ai_receiver]
                # 🟢 FIX 2: Restrict AI field players to row 4!
                if r < 6: 
                    new_pos = (r+1, c)
                    if new_pos not in match["positions"].values():
                        match["positions"][ai_receiver] = new_pos
                        
        elif ai_action == "dribble":
            match["log"] = "\n".join(log_msgs) + f"\n❌ <b>ANKLES BROKEN!</b> {carrier} blows past {defender}!"
            
            if carrier != "AI_GK": 
                r, c = match["positions"][carrier]
                # 🟢 FIX 2: Restrict AI to row 4!
                if r < 6: 
                    target_pos = (r+1, c)
                    for char, pos in match["positions"].items():
                        if pos == target_pos:
                            match["positions"][char] = (r, c)
                            break
                    match["positions"][carrier] = target_pos
            
    match["turn"] += 1
    match["ui_state"] = "overview"
    
    if match["ai_score"] >= 2:
        match["log"] += "\n\n💀 <b>THE WHISTLE BLOWS! YOU WERE DEFEATED!</b>"
        return await end_match(callback, user_id, win=False)

    text, kb = render_match_ui(user_id)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "arena_start_ai")
async def process_arena_start_ai(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = users_db[user_id]
    
    if any(v is None for v in user_data["active_team"].values()):
        return await callback.answer(
            "❌ INCOMPLETE SQUAD!\n\nYou must assign 5 players to your formation before entering the Arena. Go to [⚽ MY TEAM] to set up.", 
            show_alert=True
        )
        
    player_team_list = list(user_data["active_team"].values())
    form_id = user_data.get("formation", "1-2-1")
    
    available_ai_pool = [char for char in master_characters.keys() if char not in player_team_list]
    ai_team = random.sample(available_ai_pool, 4) 
    
    positions = {
        "AI_GK": (0, 2),             # AI Goalkeeper (Center of Row 0)
        ai_team[0]: (3, 2),          # AI Center Forward 
        ai_team[1]: (2, 1),          # AI Left Mid
        ai_team[2]: (2, 3),          # AI Right Mid
        ai_team[3]: (1, 2),          # AI Center Back
    }
    
    # 🟢 NEW: Loop through the player's custom formation and place them on the grid!
    for role, char_name in user_data["active_team"].items():
        positions[char_name] = FORMATIONS[form_id]["coords"][role]

    stamina = {char: 100 for char in player_team_list + ai_team}

    active_matches[user_id] = {
        "status": "active",
        "player_score": 0,
        "ai_score": 0,
        "turn": 1,
        "possession": "player",
        "ball_carrier": player_team_list[0], 
        "player_team": player_team_list,
        "ai_team": ai_team,
        "positions": positions,
        "stamina": stamina,
        "ego_gauge": 0,
        "log": "<i>The whistle blows! You have the kickoff.</i>",
        "ui_state": "overview" 
    }
    
    user_data["in_match"] = True
    text, kb = render_match_ui(user_id)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer("Match started!", show_alert=True)

@router.callback_query(F.data == "ignore")
async def process_ignore(callback: CallbackQuery):
    await callback.answer()

@router.callback_query(F.data.startswith("match_tap_"))
async def process_match_tap(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in active_matches:
        return await callback.answer("Match expired.", show_alert=True)
        
    match = active_matches[user_id]
    tapped_char = callback.data.split("_", 2)[2] 
        
    # Transition to State 2 (Action Menu) - OFFENSE
    if tapped_char == match["ball_carrier"] and match["possession"] == "player":
        match["ui_state"] = "action"
        text, kb = render_match_ui(user_id)
        await callback.message.edit_text(text, reply_markup=kb)
        return await callback.answer()
        
    # 🟢 NEW: Transition to Defense Menu - DEFENSE
    elif tapped_char in match["player_team"] and match["possession"] == "ai":
        match["active_defender"] = tapped_char
        match["ui_state"] = "defense"
        text, kb = render_match_ui(user_id)
        await callback.message.edit_text(text, reply_markup=kb)
        return await callback.answer()

    # Change it to just look for the AI Goalkeeper
    if tapped_char == "AI_GK":
        return await callback.answer(f"{tapped_char}\nRole: Goalkeeper", show_alert=True)
        
    stamina = match["stamina"].get(tapped_char, 100)
    team_prefix = "🟢" if tapped_char in match["player_team"] else "🔴"
    
    await callback.answer(f"{team_prefix} {tapped_char}\nStamina: {stamina}/100\nClick ball carrier to move.", show_alert=True)

@router.callback_query(F.data == "match_action_back")
async def process_match_action_back(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in active_matches:
        return await callback.answer("Match expired.", show_alert=True)
        
    # Revert state back to the board
    active_matches[user_id]["ui_state"] = "overview"
    text, kb = render_match_ui(user_id)
    
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "match_action_pass")
async def process_match_action_pass(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in active_matches:
        return await callback.answer("Match expired.", show_alert=True)
        
    active_matches[user_id]["ui_state"] = "targeting"
    text, kb = render_match_ui(user_id)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.in_(["match_action_dribble", "match_action_shoot"]) | F.data.startswith("match_execute_pass_"))
async def process_match_execution(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in active_matches:
        return await callback.answer("Match expired.", show_alert=True)
        
    match = active_matches[user_id]
    user_data = users_db[user_id]
    
    carrier = match["ball_carrier"]
    carrier_pos = match["positions"][carrier]
    
    # Determine the exact action being taken
    if callback.data.startswith("match_execute_pass_"):
        action = "pass"
        target_char = callback.data.split("_", 3)[3] 
    else:
        action = callback.data.split("_")[2] # 'dribble' or 'shoot'
        target_char = None
        
    # --- ⚠️ OUT OF POSITION (OOP) CHECK ---
    # Find what slot the manager assigned this player to
    assigned_role = None
    for role, char_name in user_data["active_team"].items():
        if char_name == carrier:
            assigned_role = role
            break
            
    carrier_data = master_characters[carrier]
    carrier_profile = user_data["roster"][carrier]
    
    # Base + Bonus Stats
    active_power = carrier_data[action] + carrier_profile["bonus_stats"][action]
    
    log_msgs = []
    
    # The OOP Penalty (-30% to all actions)
    if assigned_role and not assigned_role.startswith(carrier_data["position"]):
        active_power = int(active_power * 0.70)
        log_msgs.append(f"⚠️ <b>OOP PENALTY:</b> {carrier} is out of position! Power reduced by 30%.")
        
    # The Fatigue Penalty (-50% if under 30 Stamina)
    if match["stamina"][carrier] < 30:
        active_power = int(active_power * 0.50)
        log_msgs.append(f"💦 <b>FATIGUE:</b> {carrier} is exhausted! Movement is sluggish.")
        
    # 🔥 Flow State / Ego Check
    ego_stat = carrier_data["ego"] + carrier_profile["bonus_stats"]["ego"]
    if random.randint(1, 100) <= ego_stat:
        active_power = int(active_power * 1.5)
        log_msgs.append(f"🔥 <b>FLOW STATE!</b> {carrier}'s Ego awakens!")
        
    # Drain Stamina (Pass is cheap, Dribble/Shoot is heavy)
    match["stamina"][carrier] = max(0, match["stamina"][carrier] - (15 if action != "pass" else 5))
    
    # --- CLASH RESOLUTION ---
    # Determine who is defending
    if action == "shoot":
        ai_defender = "AI_GK"
        ai_defense = 95 # Base stat for Blue Lock Man
        defense_name = "Blue Lock Man"
    else:
        # Pick a random AI field player to attempt an interception
        ai_defender = random.choice(match["ai_team"])
        ai_defense = master_characters[ai_defender]["defense"]
        defense_name = ai_defender
        
    success = active_power >= ai_defense
    
    if success:
        match["ego_gauge"] = min(100, match["ego_gauge"] + 20)
        if action == "shoot":
            match["player_score"] += 1
            match["log"] = "\n".join(log_msgs) + f"\n✅ <b>GOAL!</b> {carrier} blasts past {defense_name}! ({active_power} vs {ai_defense})"
            
            # 🟢 KICKOFF RESET: AI gets the ball, everyone resets to formation!
            match["possession"] = "ai"
            match["ball_carrier"] = match["ai_team"][0] # Give ball to AI striker
            
            form_id = user_data.get("formation", "1-2-1")
            new_positions = {
                "AI_GK": (0, 2),
                match["ai_team"][0]: (3, 2),
                match["ai_team"][1]: (2, 1),
                match["ai_team"][2]: (2, 3),
                match["ai_team"][3]: (1, 2),
            }
            # Snap player team back to their chosen formation
            for role, char_name in user_data["active_team"].items():
                if char_name: 
                    new_positions[char_name] = FORMATIONS[form_id]["coords"][role]
            
            match["positions"] = new_positions

        elif action == "pass":
            match["log"] = "\n".join(log_msgs) + f"\n✅ <b>PASS CONNECTS!</b> {carrier} finds {target_char}! ({active_power} vs {ai_defense})"
            match["ball_carrier"] = target_char
            
            # 🗺️ DYNAMIC MOVEMENT: Push defensive line up!
            target_row = match["positions"][target_char][0]
            if target_row < carrier_pos[0]:
                for p in match["player_team"]:
                    # 🟢 FIX: The Goalkeeper NEVER moves!
                    if p == user_data["active_team"].get("GK"): 
                        continue
                        
                    r, c = match["positions"][p]
                    if r > 1: 
                        new_pos = (r-1, c)
                        # 🟢 FIX: Only move if the tile is completely empty!
                        if new_pos not in match["positions"].values():
                            match["positions"][p] = new_pos
                    
        elif action == "dribble":
            match["log"] = "\n".join(log_msgs) + f"\n✅ <b>BROKE THROUGH!</b> {carrier} destroys {defense_name}! ({active_power} vs {ai_defense})"
            
            # 🗺️ DYNAMIC MOVEMENT: Move carrier up 1 row
            r, c = match["positions"][carrier]
            if r > 1: 
                target_pos = (r-1, c)
                # 🟢 FIX: Swap places with whoever is in front of you so you don't overlap!
                for char, pos in match["positions"].items():
                    if pos == target_pos:
                        match["positions"][char] = (r, c)
                        break
                match["positions"][carrier] = target_pos
            
    else:
        # Turnover!
        match["log"] = "\n".join(log_msgs) + f"\n❌ <b>TURNOVER!</b> {defense_name} stops {carrier}! ({ai_defense} vs {active_power})"
        match["possession"] = "ai"
        match["ball_carrier"] = ai_defender if action != "shoot" else match["ai_team"][0]
            
    match["turn"] += 1
    match["ui_state"] = "overview"
    
    # Check Win Condition
    if match["player_score"] >= 2:
        match["log"] += "\n\n🏆 <b>THE WHISTLE BLOWS! YOU WIN!</b>"
        return await end_match(callback, user_id, win=True)

    text, kb = render_match_ui(user_id)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

async def end_match(callback: CallbackQuery, user_id: int, win: bool):
    match = active_matches[user_id]
    user_data = users_db[user_id]
    
    # Free the manager
    user_data["in_match"] = False
    
    level_up_log = ""
    
    if win:
        user_data["cash"] += 500
        user_data["ep"] += 150
        reward_txt = "🏆 <b>VICTORY!</b>\n\nRewards: 💵 +500 Cash, 💎 +150 EP\n📈 <b>Team gained +50 EXP!</b>\n"
        

        # --- XP & LEVEL UP LOGIC ---
        for char_name in user_data["active_team"].values():
            # 🟢 FIX: Safeguard against empty slots crashing the dictionary lookup
            if not char_name:
                continue
                
            char_profile = user_data["roster"][char_name]
            char_base_data = master_characters[char_name]
            
            max_level = RARITY_CAPS[char_base_data['rarity']]
            
            # Only give XP if they haven't hit their rarity level cap
            if char_profile["level"] < max_level:
                char_profile["exp"] += 50
                
                # Calculate required EXP for next level: 100 * (1.5 ^ (level - 1))
                req_exp = int(100 * (1.5 ** (char_profile["level"] - 1)))
                
                if char_profile["exp"] >= req_exp:
                    char_profile["level"] += 1
                    char_profile["exp"] -= req_exp  # Carry over excess EXP
                    char_profile["unspent_points"] += 3
                    level_up_log += f"\n🆙 <b>{char_name}</b> leveled up to Lv.{char_profile['level']}! (+3 Stat Pts)"
                    
    else:
        user_data["cash"] += 50
        reward_txt = "💀 <b>DEFEAT.</b>\n\nRewards: 💵 +50 Cash (Consolation)"
        
    text = (
        f"{match['log']}\n\n"
        f"⚽ <b>MATCH CONCLUDED</b>\n"
        f"{reward_txt}"
        f"{level_up_log}"
    )
    
    del active_matches[user_id]
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 RETURN TO FACILITY", callback_data="menu_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "match_forfeit")
async def process_match_forfeit(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id in active_matches:
        active_matches[user_id]["log"] = "<i>You surrendered to the AI.</i>"
        await end_match(callback, user_id, win=False)
    else:
        await callback.answer("No active match.", show_alert=True)

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

