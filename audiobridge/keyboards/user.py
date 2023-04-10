from vk_api.keyboard import *
from .keyboard import keys, Keyboard


class Main(Keyboard):
    command: str = "main"

    def keyboard(self, *args):
        keyboard = VkKeyboard()

        keyboard.add_button("Управление очередью", color=VkKeyboardColor.PRIMARY, payload={ keys.cmd : Queue.command, keys.args : [Queue.executable] })
        keyboard.add_line()
        keyboard.add_button("Аккаунт", payload={ keys.cmd : Account.command, keys.args : [Account.executable] })
        keyboard.add_button("Прочее", payload={ keys.cmd : Other.command, keys.args : [Other.executable] })

        return keyboard.get_keyboard()

class Queue(Keyboard):
    command: str = "queue"

    def keyboard(self, *args):
        keyboard = VkKeyboard()

        keyboard.add_button("Остановить загрузку", payload={ keys.cmd : "stop" })
        keyboard.add_line()
        keyboard.add_button("Назад", color=VkKeyboardColor.PRIMARY, payload={ keys.cmd : "back", keys.args : [False, Main.command] })

        return keyboard.get_keyboard()


class Account(Keyboard):
    command: str = "account"

    def keyboard(self, *args):
        keyboard = VkKeyboard()

        keyboard.add_button("Назад", color=VkKeyboardColor.PRIMARY, payload={ keys.cmd : "back", keys.args : [False, Main.command] })

        return keyboard.get_keyboard()

class Other(Keyboard):
    command: str = "other"

    def keyboard(self, *args):
        keyboard = VkKeyboard()

        keyboard.add_button("Список команд", payload={ keys.cmd : "help" })
        keyboard.add_openlink_button("Инструкция", link=Manual.link, payload={ keys.cmd : Manual.command, keys.args : [Manual.executable] })
        keyboard.add_line()
        keyboard.add_button("Назад", color=VkKeyboardColor.PRIMARY, payload={ keys.cmd : "back", keys.args : [False, Main.command] })

        return keyboard.get_keyboard()

class Manual(Keyboard):
    command: str = "manual"
    link: str = "https://vk.com/saveaudio?w=page-212269992_56497954"
