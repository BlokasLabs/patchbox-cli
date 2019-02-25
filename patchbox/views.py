import sys
import urwid


class DialogExit(Exception):
    pass


class DialogDisplay:
    palette_org = [
        ('body', 'black', 'light gray', 'standout'),
        ('border', 'black', 'dark blue'),
        ('shadow', 'white', 'black'),
        ('selectable', 'black', 'dark cyan'),
        ('focus', 'white', 'dark blue', 'bold'),
        ('focustext', 'light gray', 'dark blue'),
    ]

    palette = [
        ('body','white','black'),
        ('focustext', 'black','yellow'),
        ('field', 'white', 'dark gray'),
        ('love', 'light red, bold', 'black'),
        ('title', 'white, bold', 'black'),
        ('selectable', 'white', 'black'),
        ('focus', 'white', 'dark blue', 'bold'),
    ]

    def __init__(self, text, body=None):
        width = ('relative', 80)
        height = ('relative', 80)

        self.body = body
        if body is None:
            # fill space with nothing
            body = urwid.Filler(urwid.Divider(), 'top')
        
        footer_text = 'by Blokas Community! ESC to EXIT'
        self.frame = urwid.Frame(body, focus_part='footer')

        if text is not None:
            self.frame.header = urwid.Pile([urwid.Text(text),
                                            urwid.Divider()])
        
        self.frame.footer = urwid.Text(['\nwith', ('love', ' love '), footer_text])

        w = self.frame

        # pad area around listbox
        w = urwid.Padding(w, 'center', ('relative', 70))
        w = urwid.Filler(w, 'middle', ('relative', 70))
        w = urwid.AttrMap(w, 'body')

        self.view = w

    def add_buttons(self, buttons):
        l = []
        for name, exitcode in buttons:
            b = urwid.Button(name, self.button_press)
            b.exitcode = exitcode
            b = urwid.AttrWrap(b, 'selectable', 'focus')
            l.append(b)
        self.buttons = urwid.GridFlow(l, 10, 3, 1, 'center')
        self.frame.footer = urwid.Pile([urwid.Divider(),
                                        self.buttons], focus_item=1)

    def button_press(self, button):
        raise DialogExit(button.exitcode)

    def unhandled_key(self, k):
        pass

    def main(self):
        self.loop = urwid.MainLoop(self.view, self.palette, unhandled_input=self.unhandled_key)
        try:
            self.loop.run()
        except DialogExit as e:
            return self.on_exit(e.args[0])

    def on_exit(self, exitcode):
        return exitcode, ""


class InputDialogDisplay(DialogDisplay):
    def __init__(self, text):
        self.edit = urwid.Edit()
        body = urwid.ListBox([self.edit])
        body = urwid.AttrWrap(body, 'selectable', 'focustext')

        DialogDisplay.__init__(self, text, body)

        self.frame.set_focus('body')

    def unhandled_key(self, k):
        if k in ('up', 'page up'):
            self.frame.set_focus('body')
        if k in ('down', 'page down'):
            self.frame.set_focus('footer')
        if k == 'enter':
            # pass enter to the "ok" button
            self.frame.set_focus('footer')
            # self.view.keypress(size, k)

    def on_exit(self, exitcode):
        return exitcode, self.edit.get_edit_text()


class ListDialogDisplay(DialogDisplay):
    def __init__(self, text, constr, items, has_default=False):
        l = []
        self.items = []
        for item in items:
            w = constr(item)
            self.items.append(w)
            if isinstance(item, dict) and item.get('description'):
                w = urwid.Columns([('fixed', 12, w),
                                urwid.Text(item.get('description'))], 2)
            w = urwid.AttrWrap(w, 'selectable', 'focus')
            l.append(w)

        lb = urwid.ListBox(l)
        lb = urwid.AttrWrap(lb, "selectable")
        DialogDisplay.__init__(self, text, lb)

        self.frame.set_focus('body')

    def unhandled_key(self, k):
        if k in ('up', 'page up'):
            self.frame.set_focus('body')
        if k in ('down', 'page down'):
            self.frame.set_focus('footer')
        if k == 'enter':
            # pass enter to the "ok" button
            self.frame.set_focus('footer')
            self.buttons.set_focus(0)
            # self.view.keypress(size, k)
        if k == 'esc':
            raise DialogExit(1)

    def on_exit(self, exitcode):
        """Print the tag of the item selected."""
        if exitcode != 0:
            return exitcode, ""
        s = ""
        for i in self.items:
            if i.get_state():
                s = i.item
                break
        return exitcode, s


class CheckListDialogDisplay(ListDialogDisplay):
    def on_exit(self, exitcode):
        """
        Mimic dialog(1)'s --checklist exit.
        Put each checked item in double quotes with a trailing space.
        """
        if exitcode != 0:
            return exitcode, ""
        l = []
        for i in self.items:
            if i.get_state():
                l.append(i.get_label())
        return exitcode, "".join(['"'+tag+'" ' for tag in l])


class MenuItem(urwid.Text):
    """A custom widget for the --menu option"""

    def __init__(self, item):
        self.item = item
        if isinstance(item, dict):
            if item.get('title'):
                self.label = item.get('title')
            elif item.get('value'):
                self.label = item.get('value')
            else:
                self.label = 'UNKNOWN'
        else:
            self.label = item
        urwid.Text.__init__(self, self.label)
        self.state = False

    def selectable(self):
        return True

    def keypress(self, size, key):
        if key == "enter":
            self.state = True
            raise DialogExit(0)
        return key

    def mouse_event(self, size, event, button, col, row, focus):
        if event == 'mouse release':
            self.state = True
            raise DialogExit(0)
        return False

    def get_state(self):
        return self.state

    def get_label(self):
        text, attr = self.get_text()
        return text


def do_checklist(text, *items):
    def constr(tag, state):
        return urwid.CheckBox(tag, state)
    d = CheckListDialogDisplay(text, constr, items, True)
    d.add_buttons([("OK", 0), ("Cancel", 1)])
    return d.main()


def do_inputbox(text):
    d = InputDialogDisplay(text)
    d.add_buttons([("OK", 0), ("Cancel", 1)])
    return d.main()


def do_menu(text, items, ok=None, cancel=None):
    def constr(item):
        return MenuItem(item)
    d = ListDialogDisplay(text, constr, items, False)
    buttons = []
    if ok:
        buttons.append((ok, 0))
    if cancel:
        buttons.append((cancel, 1))
    d.add_buttons(buttons)
    return d.main()


def do_msgbox(text):
    d = DialogDisplay(text)
    d.add_buttons([("OK", 0)])
    return d.main()


def do_radiolist(text, *items):
    radiolist = []

    def constr(tag, state, radiolist=radiolist):
        return urwid.RadioButton(radiolist, tag, state)
    d = ListDialogDisplay(text, height, width, constr, items, True)
    d.add_buttons([("OK", 0), ("Cancel", 1)])
    return d.main()


def do_yesno(text, yes="Yes", no="No"):
    d = DialogDisplay(text)
    d.add_buttons([(yes, 0), (no, 1)])
    return d.main()