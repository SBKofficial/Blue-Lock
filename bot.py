import asyncio
import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

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

def get_main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏟️ ARENA", callback_data="menu_arena"), 
         InlineKeyboardButton(text="📋 ROSTER", callback_data="menu_roster")],
        [InlineKeyboardButton(text="🏋️ TRAIN", callback_data="menu_train"), 
         InlineKeyboardButton(text="🚪 SELECTION GATE", callback_data="menu_gacha")],
        [InlineKeyboardButton(text="⚙️ SETTINGS", callback_data="menu_settings")]
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
        "roster": ["Isagi", "Bachira", "Kunigami", "Chigiri", "Raichi"]
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

