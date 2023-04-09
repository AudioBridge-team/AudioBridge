from audiobridge.utils.sayOrReply import sayOrReply

from .user import *

class Help(Command):
    """Общедоступная команда, которая выводит список всех доступных команд для пользователя в соответсвии с его ролью.

    Args:
        Command (_type_): Класс, описывающий структуру пользовательской команды.
    """
    def __init__(self):
        """Описание команды.
        """
        super().__init__(
            name        = "help",
            description = "Список доступных команд",
            category    = CommandCategory.API,
            adminOnly   = False
        )

    def run(self, *args):
        # Обращение к бд за ролью
        is_admin = False
        cmd_list = "Доступные команды:\n\n"
        for category in CommandCategory:
            cmd_list += category.description + ":\n"
            # Сортировка команд по категориям, их порядок определён порядком инициализации переменных в CommandCategory
            for cmd in filter(lambda cmd_obj: cmd_obj.category is category, commands):
                if cmd.adminOnly > is_admin: continue
                cmd_list += "/" + cmd.name + " — " + cmd.description + "\n"
            cmd_list += "\n"

        sayOrReply(*args, cmd_list)

# Список всех команд
commands = [
    Help(),
    Stop(),
]
