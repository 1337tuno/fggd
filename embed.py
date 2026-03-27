import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import asyncio
import os

# ================= BOT TOKEN =================
# Read token from environment variable (Railway/Local)
TOKEN = os.getenv('TOKEN')

if not TOKEN:
    print("❌ ERROR: TOKEN environment variable not set!")
    print("💡 Add TOKEN to your Railway Variables panel")
    exit(1)

if len(TOKEN) < 50:
    print("❌ ERROR: Token looks invalid or incomplete!")
    exit(1)

print("✅ Token loaded successfully")
# =============================================

# Define Intents
intents = discord.Intents.default()
intents.message_content = True
intents.guild_messages = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ================= CONFIGURATION =================
TICKET_CATEGORY_ID = 1486177708168843417  # Replace with your category ID
SUPPORT_ROLE_IDS = [
    1486176548642982814, 
    1465627423583240193, 
    1486176813599424512
]
# =================================================

class ServiceModal(Modal):
    def __init__(self, service_name: str):
        super().__init__(title=f"Order: {service_name}")
        self.service_name = service_name
        
        self.address = TextInput(
            label="Address",
            placeholder="Enter your delivery/service address",
            required=True,
            style=discord.TextStyle.long,
            max_length=500
        )
        
        self.payment = TextInput(
            label="Payment Method",
            placeholder="Crypto, Cash App, Zelle, etc.",
            required=True,
            style=discord.TextStyle.short,
            max_length=100
        )
        
        self.notes = TextInput(
            label="Additional Notes (Optional)",
            placeholder="Any special instructions...",
            required=False,
            style=discord.TextStyle.long,
            max_length=1000
        )
        
        self.add_item(self.address)
        self.add_item(self.payment)
        self.add_item(self.notes)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            category = interaction.guild.get_channel(TICKET_CATEGORY_ID)
            if not category:
                await interaction.response.send_message(
                    "❌ Ticket category not found! Check TICKET_CATEGORY_ID in config.",
                    ephemeral=True
                )
                return
            
            # Create safe channel name
            safe_name = self.service_name.lower().replace(' ', '-').replace('/', '-')
            channel_name = f"ticket-{safe_name}-{interaction.user.id}"
            channel_name = "".join(c for c in channel_name if c.isalnum() or c in "-").lower()[:48]
            
            # Set permissions
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }
            
            for role_id in SUPPORT_ROLE_IDS:
                role = interaction.guild.get_role(role_id)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            
            # Create channel
            channel = await interaction.guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                reason=f"Ticket created by {interaction.user}"
            )
            
            # Mention support roles
            role_mentions = " ".join([f"<@&{role_id}>" for role_id in SUPPORT_ROLE_IDS])
            
            embed = discord.Embed(
                title=f"🎫 Ticket: {self.service_name}",
                description=f"Ticket created by {interaction.user.mention}\n\n{role_mentions}",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(name="📍 Address", value=self.address.value or "Not provided", inline=False)
            embed.add_field(name="💳 Payment Method", value=self.payment.value or "Not provided", inline=False)
            if self.notes.value:
                embed.add_field(name="📝 Additional Notes", value=self.notes.value, inline=False)
            
            embed.set_footer(text=f"Ticket ID: {channel.id} | User ID: {interaction.user.id}")
            
            view = TicketCloseView()
            await channel.send(embed=embed, view=view)
            await channel.send(f"{interaction.user.mention} Your ticket has been created! Support will assist you shortly.")
            
            await interaction.response.send_message(
                f"✅ Ticket created: {channel.mention}\n\nSupport roles have been notified!",
                ephemeral=True
            )
            
        except Exception as e:
            print(f"❌ Error creating ticket: {e}")
            await interaction.response.send_message(
                f"❌ Error creating ticket: {e}",
                ephemeral=True
            )

class TicketCloseView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        try:
            user_roles = [role.id for role in interaction.user.roles]
            is_support = any(role_id in SUPPORT_ROLE_IDS for role_id in user_roles)
            
            channel_name = interaction.channel.name
            user_id = channel_name.split('-')[-1] if '-' in channel_name else None
            is_creator = user_id and str(interaction.user.id) == user_id
            
            if not is_support and not is_creator:
                await interaction.response.send_message("❌ You don't have permission to close this ticket!", ephemeral=True)
                return
            
            await interaction.response.send_message("🔒 Ticket will be closed in 5 seconds...")
            await asyncio.sleep(5)
            await interaction.channel.delete()
            
        except Exception as e:
            print(f"❌ Error closing ticket: {e}")
            await interaction.response.send_message("❌ Error closing ticket.", ephemeral=True)

class ServiceButton(Button):
    def __init__(self, label: str, emoji: str, service_name: str):
        super().__init__(label=label, emoji=emoji, style=discord.ButtonStyle.red)
        self.service_name = service_name
    
    async def callback(self, interaction: discord.Interaction):
        try:
            modal = ServiceModal(self.service_name)
            await interaction.response.send_modal(modal)
        except Exception as e:
            print(f"❌ Error opening modal: {e}")
            await interaction.response.send_message("❌ Error opening form. Try again.", ephemeral=True)

class MainServiceView(View):
    def __init__(self):
        super().__init__(timeout=None)
        
        services = [
            ("Hotel", "🏨", "Hotel"),
            ("Airbnb", "🏠", "Airbnb"),
            ("Car Rental", "🚗", "Car-Rental"),
            ("Flights", "✈️", "Flights"),
            ("Movie", "🎬", "Movie"),
            ("Concerts/Viator", "🎵", "Concerts-Viator"),
            ("Event / Experience", "🎪", "Event-Experience"),
            ("IKEA", "🛋️", "IKEA"),
            ("URides", "🚕", "URides"),
            ("UEats", "🛒", "UEats"),
            ("Groceries", "🛍️", "Groceries"),
            ("Other Services", "🔧", "Other-Services"),
            ("FOOD", "🍕", "FOOD"),
            ("Any Type Tickets", "🎟️", "Any-Type-Tickets"),
        ]
        
        for label, emoji, name in services:
            self.add_item(ServiceButton(label=label, emoji=emoji, service_name=name))

class TicketsView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ServiceButton(label="Tickets", emoji="🎟️", service_name="Tickets"))

@bot.command(name='services')
@commands.has_permissions(administrator=True)
async def services_command(ctx):
    """Send the service buttons message"""
    embed = discord.Embed(
        title="🔥 30–50% OFF Everyday Purchases & Services 🔥",
        description="Select a service below to begin your Beast order.",
        color=discord.Color.red()
    )

    embed.add_field(name="🍔 Food", value="Fast food • Casual dining • Local restaurants • + more", inline=False)
    embed.add_field(
        name="🍽️ Restaurants (Min $40 cart)",
        value="CAVA • Jersey Mike's • Domino's • Wingstop • Applebee's • Five Guys • Panda Express • Chipotle • Pizza Hut • Papa John's • Jet's Pizza • Marco's Pizza • Sweetgreen • Carl's Jr • Habit Burger • Smashburger • Biryani • Pf Chang's • Jollibee • Nordstrom • Chuy's • A1 Wings • Church's • Square Eatmanaao (Thai) • Pizza151 • Bawarchi Biryani • Mod Pizza • Pizza King NY • Don Martin Modern Mexican • Hungry Howie's • Clover • Cafe Veloce • Square Platform Websites • + more",
        inline=False
    )
    embed.add_field(name="✈️ Travel & Stays", value="Car Rentals (Avis, Budget) • Flights • Bus • Train\nHotels • Airbnb", inline=False)
    embed.add_field(name="🎬 Entertainment & Events", value="Movie Tickets – Regal, Cinemark, Marcus, Showcase, Apple Cinemas + more\nEvent Tickets • Concerts • Sports & more", inline=False)
    embed.add_field(name="🛍️ Shopping", value="IKEA • + more", inline=False)
    embed.add_field(name="🔧 Other Services", value="Dine-in bills • Rent payments • Utility/Bill payments • + more", inline=False)
    embed.add_field(name="💳 Payment Methods", value="Crypto (+5% extra discount)\nCash App • Zelle", inline=False)

    await ctx.send(embed=embed, view=MainServiceView())

@bot.command(name='tickets')
@commands.has_permissions(administrator=True)
async def tickets_command(ctx):
    """Send the tickets button"""
    embed = discord.Embed(
        title="🎟️ Tickets",
        description="Click below to order tickets",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=TicketsView())

@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user}')
    print(f'🔗 Invite Link: https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot')
    print(f'📋 Support Role IDs: {SUPPORT_ROLE_IDS}')
    print('🚀 Bot is ready and running on Railway!')

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors gracefully"""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.", ephemeral=True)
    elif isinstance(error, commands.CommandNotFound):
        pass  # Ignore unknown commands
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("❌ An error occurred. Please try again.", ephemeral=True)

# ================= RUN BOT =================
if __name__ == "__main__":
    try:
        print("🚀 Starting Beast Eats Ticket Bot...")
        bot.run(TOKEN)
    except discord.errors.LoginFailure:
        print("❌ ERROR: Invalid token! Check your Railway TOKEN variable.")
        exit(1)
    except KeyboardInterrupt:
        print("👋 Bot shutting down...")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        exit(1)