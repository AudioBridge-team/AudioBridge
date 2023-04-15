from .user import *

class Back(Keyboard):
    command: str = "back"

    def keyboard(self, *args):
        kb_target_name = args[0][2]
        for kb in keyboards:
            if kb.command != kb_target_name: continue
            return kb.keyboard()

# Список всех клавиатур
keyboards = [
    Main(),
    Queue(),
    Settings(),
    Other(),
    Manual(),
    Back()
]
