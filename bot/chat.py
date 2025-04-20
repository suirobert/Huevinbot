from datetime import datetime
from openai import OpenAI
from bot.config import OPENAI_API_KEY, ALLOWED_CHANNEL_ID, ALLOWED_ROLE_ID, CONVERSATION_TIMEOUT, MAX_HISTORY

openai_client = OpenAI(api_key=OPENAI_API_KEY)
user_conversations = {}

def manage_conversation(user_id, user_message, bot_response):
    current_time = datetime.now()
    if user_id not in user_conversations:
        user_conversations[user_id] = {'history': [], 'last_active': current_time}
    user_conversations[user_id]['history'].append({"role": "user", "content": user_message})
    user_conversations[user_id]['history'].append({"role": "assistant", "content": bot_response})
    user_conversations[user_id]['last_active'] = current_time
    if len(user_conversations[user_id]['history']) > MAX_HISTORY * 2:
        user_conversations[user_id]['history'] = user_conversations[user_id]['history'][-MAX_HISTORY * 2:]
    to_remove = [uid for uid, data in user_conversations.items() if current_time - data['last_active'] > CONVERSATION_TIMEOUT]
    for uid in to_remove:
        del user_conversations[uid]

def setup_chat_commands(bot):
    @bot.command()
    async def huevin(ctx, *, message: str):
        if ctx.channel.id != ALLOWED_CHANNEL_ID:
            return await ctx.send(f"Este comando solo se puede usar en <#{ALLOWED_CHANNEL_ID}>. ¡Muévete pa’llá! 🚫")

        if not any(role.id == ALLOWED_ROLE_ID for role in ctx.author.roles):
            return await ctx.send("No tienes permiso para usar este comando. Necesitas el rol @Friends. 🔒")

        user_id = ctx.author.id
        conversation = user_conversations.get(user_id, {'history': []})['history']

        messages = [
            {"role": "system", "content": "Habla con humor negro y sarcasmo cabrón. Usa apodos duros. Máx 60 palabras."}
        ] + conversation + [{"role": "user", "content": message}]

        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=75,
            temperature=1.0
        )
        reply = response.choices[0].message.content.strip()

        manage_conversation(user_id, message, reply)
        await ctx.send(f"{ctx.author.mention} {reply}")
