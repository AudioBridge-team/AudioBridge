from vk_api.keyboard import *
from .keyboard import keys, Keyboard


class Main(Keyboard):
    command: str = "main"

    def keyboard(self, *args):
        keyboard = VkKeyboard()

        keyboard.add_button("Управление очередью", color=VkKeyboardColor.PRIMARY, payload={ keys.CMD : Queue.command, keys.ARGS : [Queue.executable] })
        keyboard.add_line()
        keyboard.add_button("Настройки", payload={ keys.CMD : Settings.command, keys.ARGS : [Settings.executable] })
        keyboard.add_button("Прочее", payload={ keys.CMD : Other.command, keys.ARGS : [Other.executable] })

        return keyboard.get_keyboard()

class Queue(Keyboard):
    command: str = "queue"

    def keyboard(self, *args):
        keyboard = VkKeyboard()

        keyboard.add_button("Остановить загрузку", color=VkKeyboardColor.NEGATIVE, payload={ keys.CMD : "stop" })
        keyboard.add_line()
        keyboard.add_button("Назад", color=VkKeyboardColor.PRIMARY, payload={ keys.CMD : "back", keys.ARGS : [False, Main.command] })

        return keyboard.get_keyboard()


class Settings(Keyboard):
    command: str = "settings"

    def keyboard(self, *args):
        keyboard = VkKeyboard()

        keyboard.add_button("Назад", color=VkKeyboardColor.PRIMARY, payload={ keys.CMD : "back", keys.ARGS : [False, Main.command] })

        return keyboard.get_keyboard()

class Other(Keyboard):
    command: str = "other"

    def keyboard(self, *args):
        keyboard = VkKeyboard()

        keyboard.add_button("Список команд", payload={ keys.CMD : "help" })
        keyboard.add_openlink_button("Инструкция", link=Manual.link, payload={ keys.CMD : Manual.command, keys.ARGS : [Manual.executable] })
        keyboard.add_line()
        keyboard.add_button("Назад", color=VkKeyboardColor.PRIMARY, payload={ keys.CMD : "back", keys.ARGS : [False, Main.command] })

        return keyboard.get_keyboard()

class Manual(Keyboard):
    command: str = "manual"
    link: str = "https://vk.com/saveaudio?w=page-212269992_56497954"
