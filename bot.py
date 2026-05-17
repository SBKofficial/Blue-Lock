import asyncio
import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
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
    
    # Safety Check: Prevent users from double-drafting by clicking an old button
    if user_id in users_db:
        await callback.answer("You have already drafted your team!", show_alert=True)
        return

    # Create user profile in RAM Cache
    users_db[user_id] = {
        "rank": "Unranked",
        "stratum": "Stratum 5",
        "energy": 5,
        "ep": 0,
        "cash": 0,
        "roster": ["Isagi", "Bachira", "Kunigami", "Chigiri", "Raichi"],
        "active_team": ["Isagi", "Bachira", "Kunigami", "Chigiri", "Raichi"] # NEW LIST
    }

    # The dynamic message edit using HTML
    text = (
        "🟦🔥 <b>SELECTION GATE OPENED!</b> 🔥🟦\n\n"
        "You have drafted <b>Team Z</b>. Right now, they are nothing but unpolished trash. It is your job to turn them into monsters.\n\n"
        "🎁 <b>YOUR STARTING 5:</b>\n"
        "⭐ Isagi Yoichi (Playmaker)\n"
        "⭐ Meguru Bachira (Dribbler)\n"
        "⭐ Rensuke Kunigami (Striker)\n"
        "⭐ Hyoma Chigiri (Speedster)\n"
        "⭐ Jingo Raichi (Tank)\n\n"
        "📖 <b>MANAGER'S SURVIVAL GUIDE:</b>\n"
        "<b>1. View Stats:</b> Check your [📋 Roster] to see their individual Ego, Speed, and Shoot stats. Understand their weapons.\n"
        "<b>2. The Arena:</b> Enter the [🏟️ Arena] to battle other managers. Win to earn Cash and Ego Points (EP).\n"
        "<b>3. Evolve:</b> Use Cash to [🏋️ Train] your players' stats, and use EP at the Selection Gate to pull S-Rank prodigies."
    )
    
    # Edit the original message to show the results
    await callback.message.edit_text(text, reply_markup=get_draft_success_kb())
    
    # Acknowledge the callback to stop the loading icon on the user's button
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

# --- BOT RUNNER ---
async def main():
    # Setup logging to see errors in Termux
    logging.basicConfig(level=logging.INFO)
    
    # Set default parse mode to HTML globally for the bot
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    
    print("⚽ Blue Lock Bot is starting...")
    
    # Drop pending updates so it doesn't spam old messages when you restart the script
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by Manager.")

