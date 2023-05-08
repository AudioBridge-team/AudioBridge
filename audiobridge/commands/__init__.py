from .user import *

class Help(Command):
    """Общедоступная команда, которая выводит список всех доступных команд для пользователя в соответсвии с его ролью.

    Args:
        Command (_type_): Класс, описывающий структуру пользовательской команды.
    """
    name        = "help"
    description = "Список доступных команд"
    category    = CommandCategory.API

    def run(self, *args):
        user_role = args[1]
        cmd_list = "Доступные команды:\n\n"
        for category in CommandCategory:
            cmd_list += category.description + ":\n"
            # Сортировка команд по категориям, их порядок определён порядком инициализации переменных в CommandCategory
            for cmd in filter(lambda cmd_obj: cmd_obj.category is category, commands):
                if cmd.userRole > user_role: continue
                cmd_list += "/" + cmd.name + " — " + cmd.description + "\n"
            cmd_list += "\n"

        sayOrReply(args[0], cmd_list)

# Список всех команд
commands = [
    Help(),
    Start(),
    Stop(),
    Skip(),
    SetAgent()
]
