
class Menu:

    def __init__(self, id: int | str, title, function=None):
        self.id = self._normalise_id(id)
        self.title = title
        self.function = function
        self.sub_menus = []

    @staticmethod
    def _normalise_id(id: int | str) -> int | str:
        """`Menu(2)` and `Menu('2')` must name the same menu.

        `input()` only ever yields strings, so a menu registered under the
        string '2' would otherwise be impossible to choose.
        """
        if isinstance(id, str):
            return int(id) if id.isdigit() else id.lower()
        return id

    def add_sub_menu(self, sub_menu: 'Menu') -> None:
        self.sub_menus.append(sub_menu)

    def run(self) -> None:
        print(self)
        menu = self._wait_for_user()
        while menu.sub_menus:
            print(menu)
            menu = menu._wait_for_user()

        # invoke menu
        assert menu.function
        menu()

    def _wait_for_user(self):
        choice = self._normalise_id(input('Your choice: '))

        ids = [m.id for m in self.sub_menus]
        ids.append(self.id)
        if choice in ids:
            return self._get_menu_by_id(choice)
        else:
            print(f'Invalid menu id {choice}. Valid ids are {ids}')
            return self._wait_for_user()

    def _get_menu_by_id(self, id: int | str):
        if self.id == id:
            return self
        for menu in self.sub_menus:
            if menu.id == id:
                return menu

        ids = [m.id for m in self.sub_menus]
        ids.append(self.id)
        raise ValueError(f'Invalid menu id {id}. Valid ids are {ids}')

    def __repr__(self):
        return f'Menu({self.id}, {self.title})'

    def __str__(self):
        out = []
        out.append('********************************')
        out.append(self.title)
        out.append('********************************')
        for sub_menu in self.sub_menus:
            out.append(f'{sub_menu.id}: {sub_menu.title}')
        else:
            out.append('********************************')

        return '\n'.join(out)

    def __call__(self, *args, **kwargs):
        if self.function:
            self.function(*args, **kwargs)


# timcli for tschuppi's interactive menu for python console applications.
# it is tailored for creating interactive menus within a python
# console applications

if __name__ == '__main__':
    def s11():
        print('s11')

    def s12():
        print('s12')

    def s2():
        print('s2')

    m = Menu(1, 'Main Menu')
    s1 = Menu('S1', 'S1')
    s2 = Menu('S2', 'S2', s2)
    m.add_sub_menu(s1)
    m.add_sub_menu(s2)

    s11 = Menu('S11', 'S11', s11)
    s12 = Menu('S12', 'S12', s12)
    s1.add_sub_menu(s11)
    s1.add_sub_menu(s12)

    m.run()



