#--------Импорт нужных библиотек--------#
import discord # api discord
import requests # нужен для discord.py

from discord.ext import commands # команды с префиксом
from discord import app_commands # слэш-команды

from openai import OpenAI # требуется для одной из функций (проверка определения термина)

import sqlite3 #база данных

#--------Создание переменных для базы данных--------#

conn = sqlite3.connect('data.db') # подключение к основной базе данных
c = conn.cursor() # установка курсора

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

#--------Настройки бота. Можно ввести только токен--------#

config = {
	'token': 'token',
	'bot': 'AutoStaff',
	'id': 'botId'
}

bot = commands.Bot(command_prefix = '!', intents=discord.Intents.all()) # создание бота. установка префикса и всех разрешений
bot.remove_command('help') # убираем дефолтную команду help для настройки своей

#--------Проверка разрешений--------#

def can_send_messages(channel: discord.TextChannel) -> bool: # проверка возможности писать в канал, в котором должна быть кнопка для анкеты
	perms = channel.permissions_for(channel.guild.me)
	return perms.send_messages and perms.embed_links and perms.view_channel

#--------Проверка определения через нейронку--------#

def askAI(termin, meaning):
	client = OpenAI(
		base_url="https://api.orcarouter.ai/v1",
		api_key='api-key', # сюда вводим свой api-ключ
	)
	response = client.chat.completions.create(
		model="orcarouter/free",
		messages=[{"role": "user", "content": f'Данное определение хоть частично соответсвует определению термина "{termin}": {meaning}? Ответь 0, если да или 1, если нет'}],
	)
	# если нейросеть ответила 0 - значит "да, верно" и возвращаем True. 1 - "не верно", возвращаем False
	if '0' in response.choices[0].message.content:
		return True 
	else:
		return False

#--------Создание модального диалога со всеми пунктами--------#

class MyModal(discord.ui.Modal, title='Анкета'):
	def __init__(self, serverName, *args, **kwargs): # инициализация всех переменных
		super().__init__(*args, **kwargs)
		self.serverName = serverName # Название сервера, на котором был вызван модал
		self.params = dict() # params - словарь с параметром (ограничителем) и минимальным/максимальным значением из базы данных. пример - {'age': 16}
		self.texts = list() # texts - словарь, в котором находятся индексы для всех параметров. например, возраст у нас установлен, адекватность не установлена, грамотность установлена: [0, None, 1, None, None, None]

		c.execute('SELECT * FROM data WHERE serverName = ?', (self.serverName, )) # извлекаем все параметры, установленные на сервере, из базы данных
		data = c.fetchone() # записываем параметры в переменную

		#--------Создание инпутов для каждого из параметров--------#

		if data[1] != None: # если возраст установлен, то создаем
			self.add_item(discord.ui.TextInput(label="Возраст", placeholder='Число в диапазоне от 0 до 100'))
			self.params['age'] = data[1]
			self.texts.append(0) # запись значения из бд в словарь params и индекса возраста в texts
		else:
			self.texts.append(None) # если возраст не был установлен
		if data[2] != None: # если адекватность установлена, то создаем
			self.add_item(discord.ui.TextInput(label="Оцените вашу адекватность", placeholder='Число в диапазоне от 0 до 10'))
			self.params['adequacy'] = data[2]
			self.params['age'] = data[1]

			if self.texts[0] == None:
				self.texts.append(0)
			else:
				self.texts.append(1)
			# запись значения из бд в словарь params и индекса возраста в texts
		else:
			self.texts.append(None) # если адекватность не была установлена
		if data[3] != None: # если грамотность установлена, то создаем
			self.add_item(discord.ui.TextInput(label="Оцените вашу грамотность", placeholder='Число в диапазоне от 0 до 10'))
			self.params['literacy'] = data[3]
			notNone = None
			for i in range(len(self.texts)):
				if self.texts[i] != None:
					notNone = i
			if notNone == None:
				self.texts.append(0)
			else:
				self.texts.append(notNone+1)

			# запись значения из бд в словарь params и индекса возраста в texts
		else:
			self.texts.append(None) # если грамотность не была установлена
		if data[4] != None: # если активность установлена, то создаем
			self.add_item(discord.ui.TextInput(label="Оцените вашу активность", placeholder='Число в диапазоне от 0 до 10'))
			self.params['activity'] = data[4]
			notNone = None
			for i in range(len(self.texts)):
				if self.texts[i] != None:
					notNone = i
			if notNone == None:
				self.texts.append(0)
			else:
				self.texts.append(notNone+1)
			# запись значения из бд в словарь params и индекса возраста в texts
		else:
			self.texts.append(None) # если активность не была установлена
			
		if data[5] != None: # если токсичность установлена, то создаем
			self.add_item(discord.ui.TextInput(label="Оцените вашу токсичность", placeholder='Число в диапазоне от 0 до 10'))
			self.params['toxicity'] = data[5]
			notNone = None
			for i in range(len(self.texts)):
				if self.texts[i] != None:
					notNone = i
			if notNone == None:
				self.texts.append(0)
			else:
				self.texts.append(notNone+1)
			# запись значения из бд в словарь params и индекса возраста в texts
		else:
			self.texts.append(None) # если токсичность не была установлена

		if data[6] != None: # если термин установлен, то создаем
			self.add_item(discord.ui.TextInput(label=f'Обоснуйте термин "{data[6]}"', style=discord.TextStyle.long, placeholder='Объясните данный термин, можно коротко'))
			self.params['termin'] = data[6]
			notNone = None
			for i in range(len(self.texts)):
				if self.texts[i] != None:
					notNone = self.texts[i]
			if notNone == None:
				self.texts.append(0)
			else:
				self.texts.append(notNone+1)
			# запись значения из бд в словарь params и индекса возраста в texts
		else:
			self.texts.append(None) # если термин не был установлен

	#--------Отправка формы--------#

	async def on_submit(self, interaction: discord.Interaction):
		await interaction.response.defer()
		self.incorrect = 0 # создаем переменную для неподходящих значений
		self.wrong_answer = 0 # создаем переменную для значений, которые не попадают в доступный диапазон

		#--------Проверка значений--------#

		if 'age' in self.params:
			if int(str(self.children[self.texts[0]])) < 0 or int(str(self.children[self.texts[0]])) > 100: # проверка на вход в диапазон значений
				self.wrong_answer += 1 # если не входит, то +1
			if self.params['age'] > int(str(self.children[self.texts[0]])): # проверка на вход в ограничения из бд
				self.incorrect+=1 # если не входит, то +1
		if 'adequacy' in self.params:
			if int(str(self.children[self.texts[1]])) < 0 or int(str(self.children[self.texts[1]])) > 10: # проверка на вход в диапазон значений
				self.wrong_answer += 1 # если не входит, то +1
			if self.params['adequacy'] > int(str(self.children[self.texts[1]])): # проверка на вход в ограничения из бд
				self.incorrect+=1 # если не входит, то +1
		if 'literacy' in self.params:
			if int(str(self.children[self.texts[2]])) < 0 or int(str(self.children[self.texts[2]])) > 10: # проверка на вход в диапазон значений
				self.wrong_answer += 1 # если не входит, то +1
			if self.params['literacy'] > int(str(self.children[self.texts[2]])): # проверка на вход в ограничения из бд
				self.incorrect+=1 # если не входит, то +1
		if 'activity' in self.params:
			if int(str(self.children[self.texts[3]])) < 0 or int(str(self.children[self.texts[3]])) > 10: # проверка на вход в диапазон значений
				self.wrong_answer += 1 # если не входит, то +1
			if self.params['activity'] > int(str(self.children[self.texts[3]])): # проверка на вход в ограничения из бд
				self.incorrect+=1 # если не входит, то +1
		if 'toxicity' in self.params:
			if int(str(self.children[self.texts[4]])) < 0 or int(str(self.children[self.texts[4]])) > 10: # проверка на вход в диапазон значений
				self.wrong_answer += 1 # если не входит, то +1
			if self.params['toxicity'] < int(str(self.children[self.texts[4]])): # проверка на вход в ограничения из бд
				self.incorrect+=1 # если не входит, то +1
		if 'termin' in self.params:
			result = askAI(self.params['termin'], str(self.children[self.texts[5]])) # запуск функции с нейросетью и запись значения (bool) в переменную
			if not result: # если False
				self.incorrect+=1 # +1, т.к. определение не подходит

		#--------Соотношение--------#

		if self.wrong_answer > 0: # если хоть один пункт вышел за рамки диапазона
			await interaction.followup.send(f'Вы не прошли, так как вы указали неправильные значения', file = discord.File('orig-1-1.gif'), ephemeral=True)
			return

		if self.incorrect == 0: # если все пункты подошли под ограничения из бд
			channel2 = await interaction.guild.create_voice_channel(name=f'Опрос {interaction.user.display_name}') # создание войс-канала
			try: # пробуем перенести пользователя в войс
				await interaction.user.move_to(channel2)
				await interaction.followup.send(f'Вы прошли! Ожидайте захода проверяющего состава в голосовой канал!', file = discord.File('AD6J8Sd-2-1.gif'), ephemeral=True)
			except discord.errors.HTTPException: # если пользователь не был в войсе до этого/у бота нет нужных разрешений
				await interaction.followup.send(f'Вы прошли! Зайдите в <#{channel2.id}> и ожидайте захода проверяющего состава в голосовой канал!', file = discord.File('AD6J8Sd-2-1.gif'), ephemeral=True)
			return
		
		else: # если хоть один пункт не подошел под ограничения из бд
			await interaction.followup.send(f'Вы не прошли, так как вы не соответсвуете критериям отбора', file = discord.File('orig-1-1.gif'), ephemeral=True)
			return

#--------Создание кнопки для открытия модального диалога--------#

class OpenModalButton(discord.ui.Button):
	def __init__(self): # инициализация
		super().__init__(
			label="Анкета", # название кнопки
			style=discord.ButtonStyle.green, # цвет
			custom_id="open_modal_button", # данный параметр дает возможность бесконечно использовать одну кнопку для открытия модального диалога, даже если он был изменен или бот был перезапущен
		)

	async def callback(self, interaction: discord.Interaction): # при нажатии на кнпоку
		try:
			await interaction.response.send_modal(MyModal(serverName=interaction.guild.name)) # открытие модала и передача ему названия сервера
		except Exception as err:
			await interaction.response.send_message('Бот не настроен. Ожидайте объявлений от администрации', ephemeral = True) # если до этого не было установлено ни одного ограничения

class MyView(discord.ui.View): # данный класс требуется для добавления к сообщению кнопки
	def __init__(self):
		# timeout=None делает view постоянным (бесконечным)
		super().__init__(timeout=None)
		self.add_item(OpenModalButton()) # добавление кнопки

@bot.event
async def on_ready():
	print('ERRORS ARE SUCK!(maybe) )')
	await bot.change_presence(status=discord.Status.idle, activity=discord.Game(name = '''/help\nBot created by wF#2016''')) # установка статуса боту
	await bot.tree.sync() # синхронизация слэш-команд
	print("Слэш-команды синхронизированы!")	 
	bot.add_view(MyView()) # добавление класса с кнопкой

#--------Слэш-команды--------#
#-------- 1. Справка --------#
@bot.tree.command(name="help", description="Показать справку по боту")
@app_commands.checks.has_permissions(manage_roles = True)
async def help(interaction: discord.Interaction):
	await interaction.response.defer(ephemeral=True)

	embed = discord.Embed(color = discord.Color.orange())
	embed.add_field(name='**Установить канал**', value='``set_channel [упоминание канала]``; ')
	embed.add_field(name='**Установить минимальный возраст**', value='``set_age [минимальный_возраст]`` Для сброса ``0``')
	embed.add_field(name='**Установить минимальную оценку адекватности**', value='``set_adequacy [минимальная_оценка_адекватности]`` Для сброса ``0``')
	embed.add_field(name='**Установить минимальную оценку грамотности**', value='``set_literacy [минимальная_оценка_грамотности]`` Для сброса ``0``')
	embed.add_field(name='**Установить минимальную оценку активности**', value='``set_activity [минимальная_оценка_активности]`` Для сброса ``0``')
	embed.add_field(name='**Установить минимальную оценку токсичности**', value='``set_toxicity [минимальная_оценка_токсичности]`` Для сброса ``0``')
	embed.add_field(name='**ПЛАТНО!!! Установить определение термина**', value='``set_termin [термин]`` Для сброса ``reset``')
	embed.add_field(name='**Ограничение**', value = 'МАКСИМУМ 5 ПУНКТОВ')
	embed.set_footer(text='''Created by wF#2016. Support author you can at https://www.donationalerts.com/r/petelinka''')
	await interaction.followup.send(embed=embed, ephemeral=True)

#-------- 2. Установить канал и отправить туда сообщение с кнопкой --------#	

@bot.tree.command(name="set_channel", description="Установить канал")
@app_commands.describe(channel1="Канал")
@app_commands.checks.has_permissions(manage_roles = True)
async def set_channel(interaction: discord.Interaction, channel1: discord.channel.TextChannel):
	await interaction.response.defer(ephemeral=True)

	if not can_send_messages(channel1): # проверка возможности писать в канал
		await interaction.followup.send(f'У меня нет доступа к каналу <#{channel1.id}>!', ephemeral=True)
		return

	c.execute('SELECT * FROM data WHERE serverName = ?', (interaction.guild.name, )) # подгружаем данные из дб и записвыем их в переменную
	info = c.fetchone()

	if info is None: # если сервера не было до этого в бд, то создаем новую строку
		c.execute('INSERT INTO data VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (interaction.guild.name, None, None, None, None, None, None, channel1.id))
	else: # если был, то просто обновляем столбцы
		c.execute('UPDATE data SET chatId = ? WHERE serverName = ?', (channel1.id, interaction.guild.name))
	conn.commit() # сохраняем

	embed = discord.Embed(color = discord.Color.orange())
	embed.add_field(name='**Заполнить анкету**', value='Нажмите на кнопку ниже, чтобы заполнить анкету')
	await channel1.send(view = MyView(), embed = embed) 

	await interaction.followup.send(f'Канал для проверки успешно установлен!', ephemeral=True)

#-------- 3. Установить возраст --------#

@bot.tree.command(name="set_age", description="Установить минимальный возраст")
@app_commands.describe(age="Возраст")
@app_commands.checks.has_permissions(manage_roles = True)
async def set_age(interaction: discord.Interaction, age: int = 0):
	await interaction.response.defer(ephemeral=True)

	c.execute('SELECT * FROM data WHERE serverName = ?', (interaction.guild.name, )) # получаем данные из бд и записываем в переменную
	info = c.fetchone()

	if age == 0: # выставляем условие для сброса ограничителя
		if info is None: # проверка на наличие записей для сервера
			await interaction.followup.send(f'У вас не установлено ни одно ограничение', ephemeral=True)
		else:
			c.execute('UPDATE data SET age = ? WHERE serverName = ?', (None, interaction.guild.name)) # обновляем столбец возраста для строки сервера
			conn.commit() # сохраняем
			await interaction.followup.send(f'Ограничение успешно сброшено!', ephemeral=True)
		return

	if age < 0 or age > 100: # проверка на вход параметра в диапазон допустимых значений
		await interaction.followup.send(f'Нельзя ставить такие числа (допустимый диапазон от 0 до 100)', ephemeral=True)
		return

	if info is None: # если записей не было, создаем строку сервера со столбцом возраста
		c.execute('INSERT INTO data VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (interaction.guild.name, age, None, None, None, None, None, None))
	else: # если запись была
		# ----------
		not_none = 0
		for i in range(len(info)): 
			if info[i] != None:
				not_none += 1
		if not_none >= 7: # ограничители + название сервера + айди чата
			await interaction.followup.send(f'Достигнут лимит', ephemeral=True)
			return
		# ^^^^^^^^^^^ проверка достижения лимита по ограничителям. если опустить данный блок, то будет ошибка, т.к. дискорд не дает создавать модалы с числом итемов > 5
		c.execute('UPDATE data SET age = ? WHERE serverName = ?', (age, interaction.guild.name)) # обновляем стобец возраста для строки сервера
	conn.commit() # сохраняем изменения
	await interaction.followup.send(f'Минимальный возраст успешно установлен!', ephemeral=True)

#-------- 4. Установить адекватность --------#

@bot.tree.command(name="set_adequacy", description="Установить минимальную адекватность")
@app_commands.describe(adekvat="Адекватность")
@app_commands.checks.has_permissions(manage_roles = True)
async def set_adequacy(interaction: discord.Interaction, adekvat: int = 0):
	await interaction.response.defer(ephemeral=True)

	c.execute('SELECT * FROM data WHERE serverName = ?', (interaction.guild.name, )) # получаем данные из бд и записываем в переменную
	info = c.fetchone()

	if adekvat == 0: # выставляем условие для сброса ограничителя
		if info is None: # проверка на наличие записей для сервера
			await interaction.followup.send(f'У вас не установлено ни одно ограничение', ephemeral=True)
		else:
			c.execute('UPDATE data SET adekvat = ? WHERE serverName = ?', (None, interaction.guild.name)) # обновляем столбец адекватности для строки сервера
			conn.commit() # сохраняем
			await interaction.followup.send(f'Ограничение успешно сброшено!', ephemeral=True)
		return

	if adekvat < 0 or adekvat > 10: # проверка на вход параметра в диапазон допустимых значений
		await interaction.followup.send(f'Нельзя ставить такие числа (допустимый диапазон от 0 до 10)', ephemeral=True)
		return

	if info is None: # если записей не было, создаем строку сервера со столбцом адекватности
		c.execute('INSERT INTO data VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (interaction.guild.name, None, adekvat, None, None, None, None, None))
	else:# если запись была
		# ----------
		not_none = 0
		for i in range(len(info)):
			if info[i] != None:
				not_none += 1
		if not_none >= 7: # ограничители + название сервера + айди чата
			await interaction.followup.send(f'Достигнут лимит', ephemeral=True)
			return
		# ^^^^^^^^^^^ проверка достижения лимита по ограничителям. если опустить данный блок, то будет ошибка, т.к. дискорд не дает создавать модалы с числом итемов > 5
		c.execute('UPDATE data SET adekvat = ? WHERE serverName = ?', (adekvat, interaction.guild.name)) # обновляем стобец адекватности для строки сервера
	conn.commit() # сохраняем изменения
	await interaction.followup.send(f'Минимальная оценка адекватности успешно установлена!', ephemeral=True)

#-------- 5. Установить грамотность --------#

@bot.tree.command(name="set_literacy", description="Установить минимальную грамотность")
@app_commands.describe(gramotnost="Грамотность")
@app_commands.checks.has_permissions(manage_roles = True)
async def set_literacy(interaction: discord.Interaction, gramotnost: int = 0):
	await interaction.response.defer(ephemeral=True)

	c.execute('SELECT * FROM data WHERE serverName = ?', (interaction.guild.name, )) # получаем данные из бд и записываем в переменную
	info = c.fetchone()

	if gramotnost == 0: # выставляем условие для сброса ограничителя
		if info is None: # проверка на наличие записей для сервера
			await interaction.followup.send(f'У вас не установлено ни одно ограничение', ephemeral=True)
		else:
			c.execute('UPDATE data SET gramotnost = ? WHERE serverName = ?', (None, interaction.guild.name)) # обновляем столбец грамотности для строки сервера
			conn.commit() # сохраняем
			await interaction.followup.send(f'Ограничение успешно сброшено!', ephemeral=True)
		return

	if gramotnost < 0 or gramotnost > 10: # проверка на вход параметра в диапазон допустимых значений
		await interaction.followup.send(f'Нельзя ставить такие числа (допустимый диапазон от 0 до 10)', ephemeral=True)
		return

	if info is None: # если записей не было, создаем строку сервера со столбцом грамотности
		c.execute('INSERT INTO data VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (interaction.guild.name, None, None,gramotnost, None, None, None, None))
	else:# если запись была
		# ----------
		not_none = 0
		for i in range(len(info)):
			if info[i] != None:
				not_none += 1
		if not_none >= 7: # ограничители + название сервера + айди чата
			await interaction.followup.send(f'Достигнут лимит', ephemeral=True)
			return
		# ^^^^^^^^^^^ проверка достижения лимита по ограничителям. если опустить данный блок, то будет ошибка, т.к. дискорд не дает создавать модалы с числом итемов > 5
		c.execute('UPDATE data SET gramotnost = ? WHERE serverName = ?', (gramotnost, interaction.guild.name)) # обновляем стобец грамотности для строки сервера
	conn.commit() # сохраняем изменения
	await interaction.followup.send(f'Минимальная оценка грамотности успешно установлена!', ephemeral=True)

#-------- 6. Установить активность --------#

@bot.tree.command(name="set_activity", description="Установить минимальную активность")
@app_commands.describe(activity="Активность")
@app_commands.checks.has_permissions(manage_roles = True)
async def set_activity(interaction: discord.Interaction, activity: int = 0):
	await interaction.response.defer(ephemeral=True)

	c.execute('SELECT * FROM data WHERE serverName = ?', (interaction.guild.name, )) # получаем данные из бд и записываем в переменную
	info = c.fetchone()

	if activity == 0: # выставляем условие для сброса ограничителя
		if info is None: # проверка на наличие записей для сервера
			await interaction.followup.send(f'У вас не установлено ни одно ограничение', ephemeral=True)
		else:
			c.execute('UPDATE data SET activity = ? WHERE serverName = ?', (None, interaction.guild.name)) # обновляем столбец активности для строки сервера
			conn.commit() # сохраняем
			await interaction.followup.send(f'Ограничение успешно сброшено!', ephemeral=True)
		return

	if activity < 0 or activity > 10: # проверка на вход параметра в диапазон допустимых значений
		await interaction.followup.send(f'Нельзя ставить такие числа (допустимый диапазон от 0 до 10)', ephemeral=True)
		return

	if info is None: # если записей не было, создаем строку сервера со столбцом активности
		c.execute('INSERT INTO data VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (interaction.guild.name, None, None, None, activity, None, None, None))
	else:# если запись была
		# ----------
		not_none = 0
		for i in range(len(info)):
			if info[i] != None:
				not_none += 1
		if not_none >= 7: # ограничители + название сервера + айди чата
			await interaction.followup.send(f'Достигнут лимит', ephemeral=True)
			return
		# ^^^^^^^^^^^ проверка достижения лимита по ограничителям. если опустить данный блок, то будет ошибка, т.к. дискорд не дает создавать модалы с числом итемов > 5
		c.execute('UPDATE data SET activity = ? WHERE serverName = ?', (activity, interaction.guild.name)) # обновляем стобец активности для строки сервера
	conn.commit() # сохраняем изменения
	await interaction.followup.send(f'Минимальная оценка активности успешно установлена!', ephemeral=True)

#-------- 7. Установить токсичность --------#

@bot.tree.command(name="set_toxicity", description="Установить максимальную токсичность")
@app_commands.describe(toxic="Токсичность")
@app_commands.checks.has_permissions(manage_roles = True)
async def set_toxicity(interaction: discord.Interaction, toxic: int = 0):
	await interaction.response.defer(ephemeral=True)

	c.execute('SELECT * FROM data WHERE serverName = ?', (interaction.guild.name, )) # получаем данные из бд и записываем в переменную
	info = c.fetchone()

	if toxic == 0: # выставляем условие для сброса ограничителя
		if info is None: # проверка на наличие записей для сервера
			await interaction.followup.send(f'У вас не установлено ни одно ограничение', ephemeral=True)
		else:
			c.execute('UPDATE data SET toxic = ? WHERE serverName = ?', (None, interaction.guild.name)) # обновляем столбец токсичности для строки сервера
			conn.commit() # сохраняем
			await interaction.followup.send(f'Ограничение успешно сброшено!', ephemeral=True)
		return

	if toxic < 0 or toxic > 10: # проверка на вход параметра в диапазон допустимых значений
		await interaction.followup.send(f'Нельзя ставить такие числа (допустимый диапазон от 0 до 10)', ephemeral=True)
		return

	if info is None: # если записей не было, создаем строку сервера со столбцом токсичности
		c.execute('INSERT INTO data VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (interaction.guild.name, None, None, None, None, toxic, None, None))
	else:# если запись была
		# ----------
		not_none = 0
		for i in range(len(info)):
			if info[i] != None:
				not_none += 1
		if not_none >= 7: # ограничители + название сервера + айди чата
			await interaction.followup.send(f'Достигнут лимит', ephemeral=True)
			return
		# ^^^^^^^^^^^ проверка достижения лимита по ограничителям. если опустить данный блок, то будет ошибка, т.к. дискорд не дает создавать модалы с числом итемов > 5
		c.execute('UPDATE data SET toxic = ? WHERE serverName = ?', (toxic, interaction.guild.name)) # обновляем стобец токсичности для строки сервера
	conn.commit() # сохраняем изменения
	await interaction.followup.send(f'Максимальная оценка токсичности успешно установлена!', ephemeral=True)

#-------- 8. Установить термин --------#

@bot.tree.command(name="set_termin", description="Установить термин")
@app_commands.describe(termin="Термин")
@app_commands.checks.has_permissions(manage_roles = True)
async def set_termin(interaction: discord.Interaction, termin: str = None):
	await interaction.response.defer(ephemeral=True)

	# ------------ Для платных функций ------------ #
	mySrv = bot.get_guild(1540981782977970188) # получаем сервер
	prem_role = mySrv.get_role(1553850599747887146) # получаем роль
	if interaction.user not in prem_role.members: # соотносим пользователя и пользователей-носителей роли
		embed = discord.Embed(color=discord.Color.red())
		embed.add_field(name='**Ошибка!**', value='У вас нет премиума! Чтобы его получить, зайдите на сервер и напишите разработчику в личные сообщения\nhttps://discord.gg/5PzDUgV8sm\n<@949821041566445608>')
		await interaction.followup.send(embed=embed, ephemeral=True)
		return

	c.execute('SELECT * FROM data WHERE serverName = ?', (interaction.guild.name, )) # получаем данные из бд и записываем в переменную
	info = c.fetchone()

	if termin == 'reset': # выставляем условие для сброса ограничителя
		if info is None: # проверка на наличие записей для сервера
			await interaction.followup.send(f'У вас не установлено ни одно ограничение', ephemeral=True)
		else:
			c.execute('UPDATE data SET termin = ? WHERE serverName = ?', (None, interaction.guild.name)) # обновляем столбец термина для строки сервера
			conn.commit() # сохраняем
			await interaction.followup.send(f'Ограничение успешно сброшено!', ephemeral=True)
		return

	if info is None: # если записей не было, создаем строку сервера со столбцом термина
		c.execute('INSERT INTO data VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (interaction.guild.name, None, None, None, None, None, termin, None))
	else:# если запись была
		# ----------
		not_none = 0
		for i in range(len(info)):
			if info[i] != None:
				not_none += 1
		if not_none >= 7: # ограничители + название сервера + айди чата
			await interaction.followup.send(f'Достигнут лимит', ephemeral=True)
			return
		# ^^^^^^^^^^^ проверка достижения лимита по ограничителям. если опустить данный блок, то будет ошибка, т.к. дискорд не дает создавать модалы с числом итемов > 5
		c.execute('UPDATE data SET termin = ? WHERE serverName = ?', (termin, interaction.guild.name)) # обновляем стобец термина для строки сервера
	conn.commit() # сохраняем изменения
	await interaction.followup.send(f'Термин успешно установлен!', ephemeral=True)

bot.run(config['token'])