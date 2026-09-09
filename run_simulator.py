import asyncio
import sys
from pathlib import Path

# Force UTF-8 on Windows consoles to support emojis without crashing
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from colorama import init, Fore, Style

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import settings
from src.pipeline import pipeline
from src.memory.session_manager import session_manager

init(autoreset=True)

SAMPLE_SCENARIOS = [
    ("Alice", "+1-202-555-0143", "Hi Adarsh! Are you free for a quick 20-minute Zoom call this Thursday to discuss a Python project?"),
    ("DevOps Lead", "+1-415-555-0188", "URGENT: Production API is throwing 502 errors and users cannot log in!"),
    ("Bob", "+1-312-555-0199", "What kind of AI agent services do you specialize in?"),
    ("Sarah", "+1-650-555-0112", "#human I need to discuss a confidential matter directly with Adarsh."),
    ("John", "+1-555-012-3456", "Hey Adarsh, hope you are doing well! Just wanted to say hello."),
    ("Spam Bot", "+1-800-555-0100", "Claim your free crypto giveaway now! Limited time offer click here.")
]

def print_banner():
    print(Fore.CYAN + Style.BRIGHT + "=" * 65)
    print(Fore.GREEN + Style.BRIGHT + "   📱 WhatsApp Executive AI Assistant Simulator")
    print(Fore.CYAN + Style.BRIGHT + "=" * 65)
    print(f"{Fore.YELLOW}Owner:{Style.RESET_ALL} {settings.OWNER_NAME}")
    print(f"{Fore.YELLOW}Bot Persona:{Style.RESET_ALL} {settings.BOT_NAME}")
    print(f"{Fore.YELLOW}Active Provider:{Style.RESET_ALL} {settings.AI_PROVIDER.upper()}")
    print(Fore.CYAN + "-" * 65)
    print("Commands:")
    print("  [1-6]  Run a preset realistic scenario")
    print("  'all'  Run all preset scenarios consecutively")
    print("  'exit' Exit the simulator")
    print("  Or simply type any message to simulate an incoming WhatsApp chat!")
    print(Fore.CYAN + "=" * 65 + "\n")

async def test_message(sender_name: str, phone: str, message: str):
    print(f"\n{Fore.MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"{Fore.WHITE}{Style.BRIGHT}Incoming from {sender_name} ({phone}):")
    print(f"{Fore.YELLOW}\"{message}\"")
    print(Fore.MAGENTA + "-------------------------------------------------------------")

    result = await pipeline.process_message(phone, sender_name, message)
    
    triage = result.get("triage")
    if triage:
        urgency = triage.get("urgency", 1)
        urgency_color = Fore.RED if urgency >= 4 else (Fore.YELLOW if urgency >= 3 else Fore.GREEN)
        print(f"{Fore.CYAN}🔍 Triage Classification:")
        print(f"   • Category: {Fore.WHITE}{Style.BRIGHT}{triage.get('category')}")
        print(f"   • Urgency:  {urgency_color}{urgency}/5")
        print(f"   • Action:   {Fore.WHITE}{triage.get('action')}")
        print(f"   • Summary:  {Fore.WHITE}{triage.get('summary')}")

    status = result.get("status")
    reply = result.get("reply")

    print(f"{Fore.CYAN}⚡ Pipeline Status: {Fore.WHITE}{status}")
    if reply:
        print(f"{Fore.GREEN}{Style.BRIGHT}🤖 Assistant Reply:")
        print(f"{Fore.GREEN}{reply}")
    else:
        print(f"{Fore.LIGHTBLACK_EX}(No reply sent - bot silenced or message ignored)")

    # Check takeover
    is_takeover = session_manager.is_human_takeover_active(phone)
    if is_takeover:
        print(f"{Fore.RED}⚠️ Human Takeover: ACTIVE (Bot is paused for {phone})")

    print(f"{Fore.MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

async def run_all_scenarios():
    for name, phone, msg in SAMPLE_SCENARIOS:
        await test_message(name, phone, msg)
        await asyncio.sleep(0.5)

async def main():
    print_banner()
    sim_phone = "+1-555-099-8877"
    sim_name = "User"

    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        await run_all_scenarios()
        return

    while True:
        try:
            user_input = input(f"{Fore.CYAN}Type message or [1-6, all, exit] > {Style.RESET_ALL}").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting simulator.")
            break

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit", "q"]:
            print("Simulator closed.")
            break

        if user_input.lower() == "all":
            await run_all_scenarios()
            continue

        if user_input in ["1", "2", "3", "4", "5", "6"]:
            idx = int(user_input) - 1
            name, phone, msg = SAMPLE_SCENARIOS[idx]
            await test_message(name, phone, msg)
            continue

        # Custom message
        await test_message(sim_name, sim_phone, user_input)

if __name__ == "__main__":
    asyncio.run(main())
