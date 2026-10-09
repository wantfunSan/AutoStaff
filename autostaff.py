import discord
import requests
import time
import json

from discord.ext import commands
from discord import app_commands

import asyncio
from asyncio import sleep

from openai import OpenAI

import sqlite3

import time
import os

import functools 
import operator

conn = sqlite3.connect('data.db')
c = conn.cursor()

#Создание таблицы для хранения данных пользователей
c.execute('''CREATE TABLE IF NOT EXISTS data (
				serverName TEXT PRIMARY KEY,
				age INTEGER,
				adekvat INTEGER,
				gramotnost INTEGER,
				activity INTEGER,
				toxic INTEGER,
				termin TEXT,
				chatId INTEGER
			)''')

config = {
	'token': 'TOKEN',
	'bot': 'AutoStaff',
	'id': '7534'
}

bot = commands.Bot(command_prefix = '!', intents=discord.Intents.all())
bot.remove_command('help')

def askAI(termin, meaning):
	client = OpenAI(
		base_url="https://api.orcarouter.ai/v1",
		api_key='API-KEY',
	)
	response = client.chat.completions.create(
		model="orcarouter/free",
		messages=[{"role": "user", "content": f'Данное определение хоть частично соответсвует определению термина "{termin}": {meaning}? Ответь 0, если да или 1, если нет'}],
	)

	if '0' in response.choices[0].message.content:
		return True
	else:
		return False


class MyModal(discord.ui.Modal, title='Анкета'):
	def __init__(self, serverName, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.serverName = serverName
		self.params = dict()
		self.texts = list()

		c.execute('SELECT * FROM data WHERE serverName = ?', (self.serverName, ))
		data = c.fetchone()

		if data[1] != None:
			self.add_item(discord.ui.TextInput(label="Возраст"))
			self.params['age'] = data[1]
			self.texts.append(0)
		else:
			self.texts.append(None)
		if data[2] != None: 
			self.add_item(discord.ui.TextInput(label="Оцените вашу адекватность"))
			self.params['adequacy'] = data[2]
			self.params['age'] = data[1]

			if self.texts[0] == None:
				self.texts.append(0)
			else:
				self.texts.append(1)
		else:
			self.texts.append(None)
		if data[3] != None:
			self.add_item(discord.ui.TextInput(label="Оцените вашу грамотность"))
			self.params['literacy'] = data[3]
			notNone = None
			for i in range(len(self.texts)):
				if self.texts[i] != None:
					notNone = i
			if notNone == None:
				self.texts.append(0)
			else:
				self.texts.append(notNone+1)
		else:
			self.texts.append(None)
		if data[4] != None:
			self.add_item(discord.ui.TextInput(label="Оцените вашу активность"))
			self.params['activity'] = data[4]
			notNone = None
			for i in range(len(self.texts)):
				if self.texts[i] != None:
					notNone = i
			if notNone == None:
				self.texts.append(0)
			else:
				self.texts.append(notNone+1)
		else:
			self.texts.append(None)
			
		if data[5] != None: 
			self.add_item(discord.ui.TextInput(label="Оцените вашу токсичность"))
			self.params['toxicity'] = data[5]
			notNone = None
			for i in range(len(self.texts)):
				if self.texts[i] != None:
					notNone = i
			if notNone == None:
				self.texts.append(0)
			else:
				self.texts.append(notNone+1)
		else:
			self.texts.append(None)
		if data[6] != None:
			self.add_item(discord.ui.TextInput(label=f'Обоснуйте термин "{data[6]}"', style=discord.TextStyle.long))
			self.params['termin'] = data[6]
			notNone = None
			for i in range(len(self.texts)):
				if self.texts[i] != None:
					notNone = self.texts[i]
			if notNone == None:
				self.texts.append(0)
			else:
				self.texts.append(notNone+1)
		else:
			self.texts.append(None)

	async def on_submit(self, interaction: discord.Interaction):
		await interaction.response.defer()
		self.incorrect = 0

		if 'age' in self.params:
			if self.params['age'] > int(str(self.children[self.texts[0]])):
				self.incorrect+=1
		if 'adequacy' in self.params:
			if self.params['adequacy'] > int(str(self.children[self.texts[1]])):
				self.incorrect+=1
		if 'literacy' in self.params:
			if self.params['literacy'] > int(str(self.children[self.texts[2]])):
				self.incorrect+=1
		if 'activity' in self.params:
			if self.params['activity'] > int(str(self.children[self.texts[3]])):
				self.incorrect+=1
		if 'toxicity' in self.params:
			if self.params['toxicity'] < int(str(self.children[self.texts[4]])):
				self.incorrect+=1
		if 'termin' in self.params:
			result = askAI(self.params['termin'], str(self.children[self.texts[5]]))
			if not result:
				self.incorrect+=1

		if self.incorrect == 0:
			channel2 = await interaction.guild.create_voice_channel(name=f'Опрос {interaction.user.display_name}')
			try:
				await interaction.user.move_to(channel2)
				await interaction.followup.send(f'Вы прошли! Ожидайте захода проверяющего состава в голосовой канал!', file = discord.File('AD6J8Sd-2-1.gif'), ephemeral=True)
			except discord.errors.HTTPException:
				await interaction.followup.send(f'Вы прошли! Зайдите в <#{channel2.id}> и ожидайте захода проверяющего состава в голосовой канал!', file = discord.File('AD6J8Sd-2-1.gif'), ephemeral=True)
		else:
			await interaction.followup.send(f'Вы не прошли, так как вы не соответсвуете критериям отбора', file = discord.File('orig-1-1.gif'), ephemeral=True)

class OpenModalButton(discord.ui.Button):
	def __init__(self):
		# custom_id ОБЯЗАТЕЛЕН для persistent view
		super().__init__(
			label="Анкета",
			style=discord.ButtonStyle.green,
			custom_id="open_modal_button",
		)

	async def callback(self, interaction: discord.Interaction):
		try:
			await interaction.response.send_modal(MyModal(serverName=interaction.guild.name))
		except Exception as err:
			await interaction.response.send_messsage('Бот не настроен. Ожидайте объявлений от администрации', ephemeral = True)

class MyView(discord.ui.View):
	def __init__(self):
		# timeout=None делает view постоянным (бесконечным)
		super().__init__(timeout=None)
		self.add_item(OpenModalButton())

@bot.event
async def on_ready():
	print('ERRORS ARE SUCK!(maybe) )')
	await bot.change_presence(status=discord.Status.idle, activity=discord.Game(name = '''/help\nBot created by wF#2016'''))
	await bot.tree.sync()
	print("Слэш-команды синхронизированы!")	
	bot.add_view(MyView())

@bot.tree.command(name="help", description="Показать справку по боту")
@app_commands.checks.has_permissions(manage_roles = True)
async def help(interaction: discord.Interaction):
	await interaction.response.defer(ephemeral=True)

	embed = discord.Embed(color = discord.Color.orange())
	embed.add_field(name='**Установить канал**', value='``set_channel [упоминание канала]``; ')
	embed.add_field(name='**Установить минимальный возраст**', value='``set_age [минимальный_возраст]``')
	embed.add_field(name='**Установить минимальную оценку адекватности**', value='``set_adequacy [минимальная_оценка_адекватности]``')
	embed.add_field(name='**Установить минимальную оценку грамотности**', value='``set_literacy [минимальная_оценка_грамотности]``')
	embed.add_field(name='**Установить минимальную оценку активности**', value='``set_activity [минимальная_оценка_активности]``')
	embed.add_field(name='**Установить минимальную оценку токсичности**', value='``set_toxicity [минимальная_оценка_токсичности]``')
	embed.add_field(name='**ПЛАТНО!!! Установить определение термина**', value='``set_termin [термин]``')
	embed.add_field(name=' ', value = '**МАКСИМУМ 5 ПУНКТОВ**')
	embed.set_footer(text='''Created by wF#2016. Support author you can at https://www.donationalerts.com/r/petelinka''')
	await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="set_channel", description="Установить канал")
@app_commands.describe(channel1="Канал")
@app_commands.checks.has_permissions(manage_roles = True)
async def set_channel(interaction: discord.Interaction, channel1: discord.channel.TextChannel):
	await interaction.response.defer(ephemeral=True)

	c.execute('SELECT * FROM data WHERE serverName = ?', (interaction.guild.name, ))
	info = c.fetchone()
	if info is None:
		c.execute('INSERT INTO data VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (interaction.guild.name, None, None, None, None, None, None, channel1.id))
	else:
		c.execute('UPDATE data SET chatId = ? WHERE serverName = ?', (channel1.id, interaction.guild.name))
	conn.commit()

	embed = discord.Embed(color = discord.Color.orange())
	embed.add_field(name='**Заполнить анкету**', value='Нажмите на кнопку ниже, чтобы заполнить анкету')
	await channel1.send(view = MyView(), embed = embed)

	await interaction.followup.send(f'Канал для проверки успешно установлен!', ephemeral=True)

@bot.tree.command(name="set_age", description="Установить минимальный возраст")
@app_commands.describe(age="Возраст")
@app_commands.checks.has_permissions(manage_roles = True)
async def set_age(interaction: discord.Interaction, age: int = 0):
	await interaction.response.defer(ephemeral=True)

	c.execute('SELECT * FROM data WHERE serverName = ?', (interaction.guild.name, ))
	info = c.fetchone()
	if info is None:
		c.execute('INSERT INTO data VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (interaction.guild.name, age, None, None, None, None, None, None))
	else:
		c.execute('UPDATE data SET age = ? WHERE serverName = ?', (age, interaction.guild.name))
	conn.commit()
	await interaction.followup.send(f'Минимальный возраст успешно установлен!', ephemeral=True)

@bot.tree.command(name="set_adequacy", description="Установить минимальную адекватность")
@app_commands.describe(adekvat="Адекватность")
@app_commands.checks.has_permissions(manage_roles = True)
async def set_adequacy(interaction: discord.Interaction, adekvat: int = 0):
	await interaction.response.defer(ephemeral=True)

	c.execute('SELECT * FROM data WHERE serverName = ?', (interaction.guild.name, ))
	info = c.fetchone()
	if info is None:
		c.execute('INSERT INTO data VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (interaction.guild.name, None, adekvat, None, None, None, None, None))
	else:
		c.execute('UPDATE data SET adekvat = ? WHERE serverName = ?', (adekvat, interaction.guild.name))
	conn.commit()
	await interaction.followup.send(f'Минимальная оценка адекватности успешно установлена!', ephemeral=True)

@bot.tree.command(name="set_literacy", description="Установить минимальную грамотность")
@app_commands.describe(gramotnost="Грамотность")
@app_commands.checks.has_permissions(manage_roles = True)
async def set_literacy(interaction: discord.Interaction, gramotnost: int = 0):
	await interaction.response.defer(ephemeral=True)

	c.execute('SELECT * FROM data WHERE serverName = ?', (interaction.guild.name, ))
	info = c.fetchone()
	if info is None:
		c.execute('INSERT INTO data VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (interaction.guild.name, None, None,gramotnost, None, None, None, None))
	else:
		c.execute('UPDATE data SET gramotnost = ? WHERE serverName = ?', (gramotnost, interaction.guild.name))
	conn.commit()
	await interaction.followup.send(f'Минимальная оценка грамотности успешно установлена!', ephemeral=True)

@bot.tree.command(name="set_activity", description="Установить минимальную активность")
@app_commands.describe(activity="Активность")
@app_commands.checks.has_permissions(manage_roles = True)
async def set_activity(interaction: discord.Interaction, activity: int = 0):
	await interaction.response.defer(ephemeral=True)

	c.execute('SELECT * FROM data WHERE serverName = ?', (interaction.guild.name, ))
	info = c.fetchone()
	if info is None:
		c.execute('INSERT INTO data VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (interaction.guild.name, None, None, None, activity, None, None, None))
	else:
		c.execute('UPDATE data SET activity = ? WHERE serverName = ?', (activity, interaction.guild.name))
	conn.commit()
	await interaction.followup.send(f'Минимальная оценка активности успешно установлена!', ephemeral=True)

@bot.tree.command(name="set_toxicity", description="Установить максимальную токсичность")
@app_commands.describe(toxic="Токсичность")
@app_commands.checks.has_permissions(manage_roles = True)
async def set_toxicity(interaction: discord.Interaction, toxic: int = 0):
	await interaction.response.defer(ephemeral=True)

	c.execute('SELECT * FROM data WHERE serverName = ?', (interaction.guild.name, ))
	info = c.fetchone()
	if info is None:
		c.execute('INSERT INTO data VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (interaction.guild.name, None, None, None, None, toxic, None, None))
	else:
		c.execute('UPDATE data SET toxic = ? WHERE serverName = ?', (toxic, interaction.guild.name))
	conn.commit()
	await interaction.followup.send(f'Максимальная оценка токсичности успешно установлена!', ephemeral=True)

@bot.tree.command(name="set_termin", description="Установить термин")
@app_commands.describe(termin="Термин")
@app_commands.checks.has_permissions(manage_roles = True)
async def set_termin(interaction: discord.Interaction, termin: str = None):
	await interaction.response.defer(ephemeral=True)

	mySrv = bot.get_guild(1540981782977970188)
	prem_role = mySrv.get_role(1553850599747887146)
	if interaction.user not in prem_role.members:
		embed = discord.Embed(color=discord.Color.red())
		embed.add_field(name='**Ошибка!**', value='У вас нет премиума! Чтобы его получить, зайдите на сервер и напишите разработчику в личные сообщения\nhttps://discord.gg/5PzDUgV8sm\n<@949821041566445608>')
		await interaction.followup.send(embed=embed, ephemeral=True)
		return

	c.execute('SELECT * FROM data WHERE serverName = ?', (interaction.guild.name, ))
	info = c.fetchone()
	if info is None:
		c.execute('INSERT INTO data VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (interaction.guild.name, None, None, None, None, None, termin, None))
	else:
		c.execute('UPDATE data SET termin = ? WHERE serverName = ?', (termin, interaction.guild.name))
	conn.commit()
	await interaction.followup.send(f'Термин успешно установлен!', ephemeral=True)

bot.run(config['token'])