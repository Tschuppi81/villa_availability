from unittest.mock import Mock

import pytest

from src.villa_availabitlity.t_menu import Menu


@pytest.fixture
def answer(monkeypatch):
    """Feed `input()` a scripted sequence of answers.

    Running out of answers means the menu kept re-prompting, which is a real
    failure -- so say that rather than leaking a bare StopIteration.
    """

    def _answer(*answers):
        remaining = iter(answers)

        def fake_input(_prompt=''):
            try:
                return next(remaining)
            except StopIteration:
                raise AssertionError(
                    f'menu asked for more input than the {len(answers)} '
                    f'answer(s) given: {answers}') from None

        monkeypatch.setattr('builtins.input', fake_input)

    return _answer


def test_normalises_ids_so_2_and_str_2_are_the_same_menu():
    assert Menu(2, 'x').id == Menu('2', 'x').id == 2


def test_lowercases_string_ids():
    assert Menu('M2', 'x').id == 'm2'


def test_repr_and_str_show_the_menu_and_its_children():
    menu = Menu('root', 'Main Menu')
    menu.add_sub_menu(Menu(1, 'First'))

    assert repr(menu) == 'Menu(root, Main Menu)'
    assert 'Main Menu' in str(menu)
    assert '1: First' in str(menu)


def test_calling_a_menu_without_a_function_is_a_no_op():
    Menu(1, 'x')()  # must not raise


def test_runs_the_function_of_a_single_menu(capsys, answer):
    function = Mock()
    answer('1')

    Menu(1, 'The Menu', function).run()

    assert 'The Menu' in capsys.readouterr().out
    function.assert_called_once()


def test_runs_the_chosen_sibling_only(capsys, answer):
    first, second = Mock(), Mock()

    menu = Menu(1, 'Main Menu')
    menu.add_sub_menu(Menu('M1', 'Main 1', first))
    menu.add_sub_menu(Menu('M2', 'Main 2', second))

    answer('M2')
    menu.run()

    out = capsys.readouterr().out
    assert 'Main 1' in out and 'Main 2' in out
    first.assert_not_called()
    second.assert_called_once()


def test_string_ids_are_matched_case_insensitively(answer):
    function = Mock()

    menu = Menu('root', 'Main Menu')
    menu.add_sub_menu(Menu('M2', 'Main 2', function))

    answer('m2')
    menu.run()

    function.assert_called_once()


def test_digit_ids_given_as_strings_are_selectable(answer):
    """Regression: `Menu('2')` used to be impossible to choose, because
    `input()` returns '2' which was coerced to int and never matched."""
    function = Mock()

    menu = Menu('root', 'Main Menu')
    menu.add_sub_menu(Menu('2', 'Main 2', function))

    answer('2')
    menu.run()

    function.assert_called_once()


def test_descends_into_a_sub_menu(capsys, answer):
    sub, other = Mock(), Mock()

    menu = Menu('root', 'Main Menu')
    branch = Menu('2', 'Main 2')
    menu.add_sub_menu(Menu('1', 'Main 1', other))
    menu.add_sub_menu(branch)
    branch.add_sub_menu(Menu('21', 'Sub 21', sub))

    answer('2', '21')
    menu.run()

    assert 'Sub 21' in capsys.readouterr().out
    sub.assert_called_once()
    other.assert_not_called()


def test_reprompts_on_an_unknown_choice_and_reports_what_was_typed(capsys,
                                                                   answer):
    function = Mock()

    menu = Menu('root', 'Main Menu')
    menu.add_sub_menu(Menu(1, 'Main 1', function))

    answer('9', 'nope', '1')
    menu.run()

    out = capsys.readouterr().out
    assert 'Invalid menu id 9.' in out  # the choice, not the parent's id
    assert 'Invalid menu id nope.' in out
    function.assert_called_once()


def test_get_menu_by_id_rejects_an_unknown_id():
    menu = Menu('root', 'Main Menu')
    menu.add_sub_menu(Menu(1, 'Main 1'))

    with pytest.raises(ValueError, match='Invalid menu id 7'):
        menu._get_menu_by_id(7)


def test_choosing_a_leaf_without_a_function_fails_loudly(answer):
    menu = Menu(1, 'Dead End')  # no function attached

    answer('1')
    with pytest.raises(AssertionError):
        menu.run()
