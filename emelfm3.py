#!/usr/bin/env python3
# emelFM3 - Lightweight orthodox dual-pane file manager for Linux
# Copyright (C) 2026 legacy-craft
# Licensed under the GNU General Public License v3.0 (GPL-3.0)

import os, shutil, subprocess, stat, datetime, getpass, socket, gi, sys, pwd, grp, json, fnmatch
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Gio, Pango

class EmelFM(Gtk.Window):
    def __init__(self):
        super().__init__(title="emelFM3 - Orthodox File Manager")
        self.set_default_size(1000, 650)
        
        self.left_path = os.path.expanduser("~")
        self.right_path = os.path.expanduser("~")
        self.active_side = "left"
        self.left_show_hidden = False
        self.right_show_hidden = False
        self.left_filter = "*"
        self.right_filter = "*"
        
        self.bookmarks_file = os.path.expanduser("~/.config/emelfm3/bookmarks.json")
        old_bookmarks_file = os.path.expanduser("~/.config/emelfm_gtk/bookmarks.json")
        if not os.path.exists(self.bookmarks_file) and os.path.exists(old_bookmarks_file):
            try:
                os.makedirs(os.path.dirname(self.bookmarks_file), exist_ok=True)
                shutil.copy2(old_bookmarks_file, self.bookmarks_file)
            except:
                pass
                
        self.load_bookmarks()
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(main_box)
        
        # Menu Bar (centered above central action column)
        menu_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        menubar = Gtk.MenuBar()
        menubar.set_halign(Gtk.Align.CENTER)
        menu_box.pack_start(menubar, True, False, 0)
        main_box.pack_start(menu_box, False, False, 0)
        
        # Bookmarks Menu
        bm_item = Gtk.MenuItem(label="Bookmarks")
        menubar.append(bm_item)
        self.bm_menu = Gtk.Menu()
        bm_item.set_submenu(self.bm_menu)
        self.build_bookmarks_menu()
        
        # Filters Menu
        fl_item = Gtk.MenuItem(label="Filters")
        menubar.append(fl_item)
        fl_menu = Gtk.Menu()
        fl_item.set_submenu(fl_menu)
        
        f_all = Gtk.MenuItem(label="All files (*)")
        f_all.connect("activate", self.on_filter_selected, "*")
        fl_menu.append(f_all)
        
        f_img = Gtk.MenuItem(label="Images (*.png, *.jpg, *.jpeg, *.webp, *.svg)")
        f_img.connect("activate", self.on_filter_selected, "*.png,*.jpg,*.jpeg,*.webp,*.svg")
        fl_menu.append(f_img)
        
        f_arc = Gtk.MenuItem(label="Archives (*.zip, *.tar*, *.7z, *.rar)")
        f_arc.connect("activate", self.on_filter_selected, "*.zip,*.tar*,*.7z,*.rar")
        fl_menu.append(f_arc)
        
        f_doc = Gtk.MenuItem(label="CAD / Documents (*.step, *.stp, *.pdf, *.txt, *.md)")
        f_doc.connect("activate", self.on_filter_selected, "*.step,*.stp,*.pdf,*.txt,*.md")
        fl_menu.append(f_doc)
        
        fl_menu.append(Gtk.SeparatorMenuItem())
        
        f_custom = Gtk.MenuItem(label="Custom filter... (Ctrl+G)")
        f_custom.connect("activate", lambda w: self.on_custom_filter())
        fl_menu.append(f_custom)
        
        # Help Menu
        hp_item = Gtk.MenuItem(label="Help")
        menubar.append(hp_item)
        hp_menu = Gtk.Menu()
        hp_item.set_submenu(hp_menu)
        
        h_shortcuts = Gtk.MenuItem(label="Keyboard shortcuts (Ctrl+?)")
        h_shortcuts.connect("activate", lambda w: self.show_shortcuts_help())
        hp_menu.append(h_shortcuts)
        
        self.paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        self.paned.set_position(420)
        main_box.pack_start(self.paned, True, True, 0)
        
        top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, homogeneous=False, spacing=0)
        self.paned.pack1(top_box, True, False)
        
        self.left_panel = self.create_file_panel("left")
        self.right_panel = self.create_file_panel("right")
        
        size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        size_group.add_widget(self.left_panel["scrolled"])
        size_group.add_widget(self.right_panel["scrolled"])
        
        top_box.pack_start(self.left_panel["container"], True, True, 0)
        
        center_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        center_box.set_size_request(110, -1)
        center_box.set_halign(Gtk.Align.CENTER)
        center_box.set_margin_start(2)
        center_box.set_margin_end(2)
        center_box.set_margin_top(2)
        center_box.set_margin_bottom(2)
        
        central_btns = [
            ("F1 Refresh", self.on_refresh_btn),
            ("F2 Info", self.on_info_btn),
            ("F3 Find", self.on_find_btn),
            ("F4 View", self.on_view_btn),
            ("F5 Copy", self.on_copy),
            ("F6 Move", self.on_move),
            ("F7 MkDir", self.on_new_dir),
            ("F8 Delete", self.on_delete),
        ]
        for label, cb in central_btns:
            b = Gtk.Button(label=label)
            b.connect("clicked", cb)
            center_box.pack_start(b, False, False, 0)
            
        center_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 4)
        
        extra_btns = [
            ("New File", self.on_new_file_btn),
            ("Rename", self.on_rename),
            ("SymLink", self.on_symlink),
            ("Open With", self.on_open_with),
            ("Sync", self.on_sync),
        ]
        for label, cb in extra_btns:
            b = Gtk.Button(label=label)
            b.connect("clicked", cb)
            center_box.pack_start(b, False, False, 0)
            
        top_box.pack_start(center_box, False, False, 0)
        top_box.pack_start(self.right_panel["container"], True, True, 0)
        
        self.bottom_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.paned.pack2(self.bottom_box, False, True)
        
        self.term_textview = Gtk.TextView()
        self.term_textview.set_editable(False)
        self.term_textview.set_monospace(True)
        term_scrolled = Gtk.ScrolledWindow()
        term_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        term_scrolled.add(self.term_textview)
        self.bottom_box.pack_start(term_scrolled, True, True, 0)
        
        cmd_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        cmd_box.set_margin_start(4)
        cmd_box.set_margin_end(4)
        cmd_box.set_margin_top(2)
        cmd_box.set_margin_bottom(2)
        self.bottom_box.pack_start(cmd_box, False, False, 0)
        
        prompt_str = f"{getpass.getuser()}@{socket.gethostname()} $ "
        self.prompt_label = Gtk.Label(label=prompt_str)
        cmd_box.pack_start(self.prompt_label, False, False, 0)
        
        self.cmd_entry = Gtk.Entry()
        self.cmd_entry.set_hexpand(True)
        self.cmd_entry.connect("activate", self.on_command_activate)
        cmd_box.pack_start(self.cmd_entry, True, True, 0)
        
        for qcmd in ["du", "df", "free"]:
            qb = Gtk.Button(label=qcmd)
            qb.connect("clicked", self.on_quick_cmd, qcmd)
            cmd_box.pack_start(qb, False, False, 0)
            
        x_btn = Gtk.Button(label="X")
        x_btn.set_tooltip_text("Open external terminal here")
        x_btn.connect("clicked", self.on_terminal)
        cmd_box.pack_start(x_btn, False, False, 0)
            
        self.status_bar = Gtk.Statusbar()
        main_box.pack_start(self.status_bar, False, False, 0)
        self.status_context = self.status_bar.get_context_id("main")
        
        self.connect("key-press-event", self.on_key_press)
        
        self.load_directory("left", self.left_path)
        self.load_directory("right", self.right_path)
        self.update_active_visuals()
        self.update_status_bar()
        self.left_panel["tree"].grab_focus()

    def load_bookmarks(self):
        default_bookmarks = [
            ("Home (~)", os.path.expanduser("~")),
            ("Root (/)", "/")
        ]
        try:
            if os.path.exists(self.bookmarks_file):
                with open(self.bookmarks_file, 'r', encoding='utf-8') as f:
                    self.bookmarks = json.load(f)
            else:
                self.bookmarks = default_bookmarks
                self.save_bookmarks()
        except:
            self.bookmarks = default_bookmarks

    def save_bookmarks(self):
        try:
            os.makedirs(os.path.dirname(self.bookmarks_file), exist_ok=True)
            with open(self.bookmarks_file, 'w', encoding='utf-8') as f:
                json.dump(self.bookmarks, f, indent=2)
        except Exception as e:
            self.show_error(str(e))

    def build_bookmarks_menu(self):
        children = self.bm_menu.get_children()
        for child in children:
            self.bm_menu.remove(child)
            
        for name, path in self.bookmarks:
            item = Gtk.MenuItem(label=name)
            item.connect("activate", lambda w, p=path: self.load_directory(self.active_side, p))
            self.bm_menu.append(item)
            
        self.bm_menu.append(Gtk.SeparatorMenuItem())
        
        add_item = Gtk.MenuItem(label="Add current folder (Ctrl+B)")
        add_item.connect("activate", lambda w: self.add_current_bookmark())
        self.bm_menu.append(add_item)
        
        manage_item = Gtk.MenuItem(label="Manage bookmarks...")
        manage_item.connect("activate", lambda w: self.manage_bookmarks_dialog())
        self.bm_menu.append(manage_item)
        
        self.bm_menu.show_all()

    def add_current_bookmark(self):
        curr_path = self.left_path if self.active_side == "left" else self.right_path
        name = os.path.basename(curr_path) or curr_path
        self.bookmarks.append((name, curr_path))
        self.save_bookmarks()
        self.build_bookmarks_menu()

    def manage_bookmarks_dialog(self):
        dialog = Gtk.Dialog(title="Manage Bookmarks", transient_for=self, flags=0)
        dialog.add_button("Close", Gtk.ResponseType.CLOSE)
        
        box = dialog.get_content_area()
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_size_request(400, 250)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        store = Gtk.ListStore(str, str)
        for name, path in self.bookmarks:
            store.append([name, path])
            
        tree = Gtk.TreeView(model=store)
        tree.append_column(Gtk.TreeViewColumn("Name", Gtk.CellRendererText(), text=0))
        tree.append_column(Gtk.TreeViewColumn("Path", Gtk.CellRendererText(), text=1))
        scrolled.add(tree)
        box.pack_start(scrolled, True, True, 0)
        
        remove_btn = Gtk.Button(label="Remove Selected")
        remove_btn.set_margin_start(10)
        remove_btn.set_margin_end(10)
        remove_btn.set_margin_top(10)
        remove_btn.set_margin_bottom(10)
        
        def on_remove_clicked(btn):
            sel = tree.get_selection()
            model, paths = sel.get_selected_rows()
            for p in paths:
                iter_ = model.get_iter(p)
                path_val = model.get_value(iter_, 1)
                self.bookmarks = [b for b in self.bookmarks if b[1] != path_val]
            self.save_bookmarks()
            self.build_bookmarks_menu()
            dialog.destroy()
            self.manage_bookmarks_dialog()
            
        remove_btn.connect("clicked", on_remove_clicked)
        box.pack_start(remove_btn, False, False, 0)
        
        dialog.show_all()
        dialog.run()
        dialog.destroy()

    def on_filter_selected(self, widget, pattern):
        if self.active_side == "left":
            self.left_filter = pattern
            self.load_directory("left", self.left_path)
        else:
            self.right_filter = pattern
            self.load_directory("right", self.right_path)
        self.update_status_bar()

    def on_custom_filter(self):
        dialog = Gtk.Dialog(title="Custom Filter", transient_for=self, flags=0)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("OK", Gtk.ResponseType.OK)
        
        box = dialog.get_content_area()
        curr_pat = self.left_filter if self.active_side == "left" else self.right_filter
        entry = Gtk.Entry()
        entry.set_text(curr_pat)
        entry.set_margin_start(10)
        entry.set_margin_end(10)
        entry.set_margin_top(10)
        entry.set_margin_bottom(10)
        box.pack_start(entry, True, True, 0)
        dialog.show_all()
        
        response = dialog.run()
        pat = entry.get_text()
        dialog.destroy()
        
        if response == Gtk.ResponseType.OK and pat:
            self.on_filter_selected(None, pat)

    def show_shortcuts_help(self):
        shortcuts_text = (
            "emelFM3 - Orthodox File Manager Shortcuts:\n\n"
            "F1 / Ctrl+L : Refresh both panels\n"
            "F2 : File Info details\n"
            "F3 / Ctrl+F : Find files recursively\n"
            "Shift+F4 : Create New File\n"
            "F4 : View file content\n"
            "F5 / Ctrl+C : Copy selected items\n"
            "F6 / Ctrl+M : Move selected items\n"
            "F7 / Ctrl+D : Create new directory (MkDir)\n"
            "F8 / Delete : Delete selected items\n"
            "Return / KP_Enter / Right : Enter directory or open file\n"
            "BackSpace / Left : Go to parent directory (..)\n"
            "Tab / Space : Switch active panel\n"
            "Insert / Ctrl+T : Select current item & move down\n"
            "Home : Go to user Home directory\n"
            "Ctrl+R : Rename selected item\n"
            "Ctrl+S : Create Symbolic Link\n"
            "Ctrl+X : Sync active to destination\n"
            "Ctrl+H : Toggle hidden files\n"
            "Ctrl+W : Show/Hide terminal output box\n"
            "Ctrl+Z : Focus command entry bar\n"
            "Ctrl+B : Add current folder to bookmarks\n"
            "Ctrl+G : Apply custom file filter\n"
            "Escape : Return focus from Entry to TreeView\n"
            "Ctrl+? : Show this help\n"
            "Ctrl+Q : Quit application"
        )
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=shortcuts_text
        )
        dialog.run()
        dialog.destroy()

    def update_status_bar(self):
        panel = self.left_panel if self.active_side == "left" else self.right_panel
        model, paths = panel["tree"].get_selection().get_selected_rows()
        count = len(paths)
        filt = self.left_filter if self.active_side == "left" else self.right_filter
        msg = f"Selected: {count} item(s) in {self.active_side} panel | Filter: {filt}"
        self.status_bar.pop(self.status_context)
        self.status_bar.push(self.status_context, msg)

    def custom_sort_func(self, model, iter1, iter2, user_data):
        name1 = model.get_value(iter1, 1)
        name2 = model.get_value(iter2, 1)
        
        sort_column_id, order = model.get_sort_column_id()
        
        if name1 == "..":
            return -1 if order == Gtk.SortType.ASCENDING else 1
        if name2 == "..":
            return 1 if order == Gtk.SortType.ASCENDING else -1
            
        is_dir1 = model.get_value(iter1, 6)
        is_dir2 = model.get_value(iter2, 6)
        
        if is_dir1 and not is_dir2:
            return -1
        if not is_dir1 and is_dir2:
            return 1
            
        res = 0
        if sort_column_id == 2:
            e1 = model.get_value(iter1, 2).lower()
            e2 = model.get_value(iter2, 2).lower()
            res = (e1 > e2) - (e1 < e2)
        elif sort_column_id == 3:
            val1 = model.get_value(iter1, 7)
            val2 = model.get_value(iter2, 7)
            res = (val1 > val2) - (val1 < val2)
        elif sort_column_id == 4:
            val1 = model.get_value(iter1, 8)
            val2 = model.get_value(iter2, 8)
            res = (val1 > val2) - (val1 < val2)
        else:
            n1 = name1.lower()
            n2 = name2.lower()
            res = (n1 > n2) - (n1 < n2)
            
        if res == 0:
            n1 = name1.lower()
            n2 = name2.lower()
            res = (n1 > n2) - (n1 < n2)
            
        if order == Gtk.SortType.DESCENDING:
            return -res
        return res

    def create_file_panel(self, side):
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        container.set_margin_start(2)
        container.set_margin_end(2)
        container.set_margin_top(2)
        container.set_margin_bottom(2)
        
        path_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        container.pack_start(path_box, False, False, 0)
        
        home_btn = Gtk.Button()
        home_img = Gtk.Image.new_from_icon_name("go-home-symbolic", Gtk.IconSize.BUTTON)
        home_btn.set_image(home_img)
        home_btn.set_tooltip_text("Home")
        home_btn.connect("clicked", lambda w: self.load_directory(side, os.path.expanduser("~")))
        path_box.pack_start(home_btn, False, False, 0)
        
        up_btn = Gtk.Button()
        up_img = Gtk.Image.new_from_icon_name("go-up-symbolic", Gtk.IconSize.BUTTON)
        up_btn.set_image(up_img)
        up_btn.set_tooltip_text("Parent folder")
        up_btn.connect("clicked", lambda w: self.on_up_clicked(side))
        path_box.pack_start(up_btn, False, False, 0)
        
        entry = Gtk.Entry()
        entry.connect("activate", self.on_path_activate, side)
        path_box.pack_start(entry, True, True, 0)
        
        h_btn = Gtk.ToggleButton(label="H")
        h_btn.set_tooltip_text("Show/Hide Hidden Files (Ctrl+H)")
        h_btn.connect("toggled", self.on_hidden_toggled, side)
        path_box.pack_start(h_btn, False, False, 0)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_width(250)
        container.pack_start(scrolled, True, True, 0)
        
        # model: icon_name(0), name(1), ext(2), size_str(3), modified(4), fullpath(5), is_dir(6), raw_size(7), raw_mtime(8)
        store = Gtk.ListStore(str, str, str, str, str, str, bool, int, float)
        store.set_sort_func(1, self.custom_sort_func, None)
        store.set_sort_func(2, self.custom_sort_func, None)
        store.set_sort_func(3, self.custom_sort_func, None)
        store.set_sort_func(4, self.custom_sort_func, None)
        store.set_sort_column_id(1, Gtk.SortType.ASCENDING)
        
        tree = Gtk.TreeView(model=store)
        tree.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        tree.get_selection().connect("changed", self.on_selection_changed, side)
        tree.connect("row-activated", self.on_row_activated, side)
        tree.connect("button-press-event", self.on_tree_button_press, side)
        
        # 1. Icon + Filename
        col_name = Gtk.TreeViewColumn("Filename")
        col_name.set_expand(True)
        col_name.set_min_width(140)
        col_name.set_clickable(True)
        col_name.set_sort_column_id(1)
        
        renderer_icon = Gtk.CellRendererPixbuf()
        col_name.pack_start(renderer_icon, False)
        col_name.add_attribute(renderer_icon, "icon-name", 0)
        
        renderer_name = Gtk.CellRendererText()
        renderer_name.set_property("ellipsize", Pango.EllipsizeMode.END)
        col_name.pack_start(renderer_name, True)
        col_name.add_attribute(renderer_name, "text", 1)
        
        tree.append_column(col_name)
        
        # 2. Ext
        renderer_ext = Gtk.CellRendererText()
        col_ext = Gtk.TreeViewColumn("Ext", renderer_ext, text=2)
        col_ext.set_clickable(True)
        col_ext.set_sort_column_id(2)
        tree.append_column(col_ext)
        
        # 3. Size
        renderer_size = Gtk.CellRendererText()
        renderer_size.set_property("xalign", 1.0)
        col_size = Gtk.TreeViewColumn("Size", renderer_size, text=3)
        col_size.set_clickable(True)
        col_size.set_sort_column_id(3)
        tree.append_column(col_size)
        
        # 4. Modified
        renderer_mod = Gtk.CellRendererText()
        col_mod = Gtk.TreeViewColumn("Modified", renderer_mod, text=4)
        col_mod.set_clickable(True)
        col_mod.set_sort_column_id(4)
        tree.append_column(col_mod)
        
        scrolled.add(tree)
        
        return {
            "container": container,
            "path_entry": entry,
            "h_btn": h_btn,
            "scrolled": scrolled,
            "tree": tree,
            "store": store
        }

    def on_up_clicked(self, side):
        current = self.left_path if side == "left" else self.right_path
        parent = os.path.dirname(current)
        if parent and os.path.isdir(parent):
            self.load_directory(side, parent)
            self.set_active_side(side)

    def get_other_side(self, side):
        return "right" if side == "left" else "left"

    def set_active_side(self, side):
        if self.active_side != side:
            self.active_side = side
            self.update_active_visuals()
            self.update_status_bar()

    def update_active_visuals(self):
        if self.active_side == "left":
            self.left_panel["path_entry"].set_state_flags(Gtk.StateFlags.SELECTED, True)
            self.right_panel["path_entry"].unset_state_flags(Gtk.StateFlags.SELECTED)
        else:
            self.right_panel["path_entry"].set_state_flags(Gtk.StateFlags.SELECTED, True)
            self.left_panel["path_entry"].unset_state_flags(Gtk.StateFlags.SELECTED)

    def on_tree_button_press(self, widget, event, side):
        self.set_active_side(side)
        return False

    def on_selection_changed(self, selection, side):
        if side != self.active_side:
            return
        self.update_status_bar()

    def format_size(self, size):
        for unit in ['', 'K', 'M', 'G', 'T']:
            if size < 1024.0:
                return f"{size:.1f}{unit}" if unit else f"{int(size)}"
            size /= 1024.0
        return f"{size:.1f}P"

    def on_hidden_toggled(self, btn, side):
        active = btn.get_active()
        if side == "left":
            self.left_show_hidden = active
            self.load_directory("left", self.left_path)
        else:
            self.right_show_hidden = active
            self.load_directory("right", self.right_path)

    def matches_filter(self, filename, filt_str):
        if not filt_str or filt_str == "*":
            return True
        patterns = [p.strip() for p in filt_str.split(",")]
        for p in patterns:
            if fnmatch.fnmatch(filename, p):
                return True
        return False

    def load_directory(self, side, path):
        panel = self.left_panel if side == "left" else self.right_panel
        show_hidden = self.left_show_hidden if side == "left" else self.right_show_hidden
        filt = self.left_filter if side == "left" else self.right_filter
        
        if side == "left":
            self.left_path = path
        else:
            self.right_path = path
            
        panel["path_entry"].set_text(path)
        panel["h_btn"].set_active(show_hidden)
        store = panel["store"]
        store.clear()
        
        try:
            items = os.listdir(path)
        except Exception as e:
            self.show_error(str(e))
            return
            
        store.append(["folder-symbolic", "..", "", "", "", os.path.dirname(path), True, 0, 0.0])
        
        dirs = []
        files = []
        for item in items:
            if not show_hidden and item.startswith('.'):
                continue
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                dirs.append(item)
            else:
                if self.matches_filter(item, filt):
                    files.append(item)
                
        dirs.sort()
        files.sort()
        
        for d in dirs:
            full_path = os.path.join(path, d)
            try:
                st = os.stat(full_path)
                mtime_str = datetime.datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M')
                raw_mtime = float(st.st_mtime)
            except:
                mtime_str = ""
                raw_mtime = 0.0
            store.append(["folder-symbolic", d, "", "", mtime_str, full_path, True, 0, raw_mtime])
            
        for f in files:
            full_path = os.path.join(path, f)
            ext = os.path.splitext(f)[1].lstrip(".").lower()
            try:
                st = os.stat(full_path)
                raw_size = int(st.st_size)
                size_str = self.format_size(raw_size)
                mtime_str = datetime.datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M')
                raw_mtime = float(st.st_mtime)
            except:
                raw_size = 0
                size_str = ""
                mtime_str = ""
                raw_mtime = 0.0
            store.append(["text-x-generic-symbolic", f, ext, size_str, mtime_str, full_path, False, raw_size, raw_mtime])

    def on_path_activate(self, entry, side):
        path = entry.get_text()
        if os.path.isdir(path):
            self.load_directory(side, os.path.abspath(path))
            self.set_active_side(side)
        else:
            self.show_error("Directory does not exist")

    def on_row_activated(self, tree_view, path, column, side):
        model = tree_view.get_model()
        iter_ = model.get_iter(path)
        full_path = model.get_value(iter_, 5)
        if os.path.isdir(full_path):
            self.load_directory(side, full_path)
            self.set_active_side(side)
        else:
            try:
                gfile = Gio.File.new_for_path(full_path)
                Gio.AppInfo.launch_default_for_uri(gfile.get_uri(), None)
            except Exception as e:
                self.show_error(str(e))

    def get_selected_paths(self, side):
        panel = self.left_panel if side == "left" else self.right_panel
        tree = panel["tree"]
        model, paths = tree.get_selection().get_selected_rows()
        res = []
        for p in paths:
            iter_ = model.get_iter(p)
            name = model.get_value(iter_, 1)
            if name == "..":
                continue
            full_path = model.get_value(iter_, 5)
            res.append(full_path)
        return res

    def refresh_both(self):
        self.load_directory("left", self.left_path)
        self.load_directory("right", self.right_path)

    def show_error(self, msg):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=msg
        )
        dialog.run()
        dialog.destroy()

    def on_refresh_btn(self, btn):
        self.refresh_both()

    def on_info_btn(self, btn):
        src_side = self.active_side
        selected = self.get_selected_paths(src_side)
        if len(selected) != 1:
            self.show_error("Please select exactly one item.")
            return
        item = selected[0]
        try:
            st = os.stat(item)
            size = st.st_size
            perms_text = stat.filemode(st.st_mode)
            try:
                owner = pwd.getpwuid(st.st_uid).pw_name
            except:
                owner = str(st.st_uid)
            try:
                group = grp.getgrgid(st.st_gid).gr_name
            except:
                group = str(st.st_gid)
            mtime = datetime.datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            atime = datetime.datetime.fromtimestamp(st.st_atime).strftime('%Y-%m-%d %H:%M:%S')
            
            info_text = (f"Path: {item}\n"
                         f"Size: {size} bytes ({self.format_size(size)})\n"
                         f"Permissions: {perms_text}\n"
                         f"Owner: {owner}:{group}\n"
                         f"Modified: {mtime}\n"
                         f"Accessed: {atime}")
            
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=info_text
            )
            dialog.run()
            dialog.destroy()
        except Exception as e:
            self.show_error(str(e))

    def on_find_btn(self, btn):
        dialog = Gtk.Dialog(title="Find Files", transient_for=self, flags=0)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("OK", Gtk.ResponseType.OK)
        
        box = dialog.get_content_area()
        entry = Gtk.Entry()
        entry.set_text("")
        entry.set_margin_start(10)
        entry.set_margin_end(10)
        entry.set_margin_top(10)
        entry.set_margin_bottom(10)
        box.pack_start(entry, True, True, 0)
        dialog.show_all()
        
        response = dialog.run()
        pattern = entry.get_text()
        dialog.destroy()
        
        if response == Gtk.ResponseType.OK and pattern:
            src_dir = self.left_path if self.active_side == "left" else self.right_path
            found = []
            for root, dirs, files in os.walk(src_dir):
                for name in dirs + files:
                    if pattern in name:
                        found.append(os.path.join(root, name))
            
            buf = self.term_textview.get_buffer()
            end_iter = buf.get_end_iter()
            out = f"Find '{pattern}' in {src_dir}:\n" + "\n".join(found) + "\n----end-of-output----\n"
            buf.insert(end_iter, out)
            adj = self.term_textview.get_vadjustment()
            adj.set_value(adj.get_upper())

    def on_view_btn(self, btn):
        src_side = self.active_side
        selected = self.get_selected_paths(src_side)
        if len(selected) != 1:
            self.show_error("Please select exactly one file to view.")
            return
        item = selected[0]
        if os.path.isdir(item):
            self.show_error("Cannot view directory.")
            return
        try:
            with open(item, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            win = Gtk.Window(title=f"View: {os.path.basename(item)}")
            win.set_default_size(600, 400)
            tv = Gtk.TextView()
            tv.set_editable(False)
            tv.set_monospace(True)
            tv.get_buffer().set_text(content)
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            scrolled.add(tv)
            win.add(scrolled)
            win.show_all()
        except Exception as e:
            self.show_error(str(e))

    def on_new_file_btn(self, btn=None):
        src_dir = self.left_path if self.active_side == "left" else self.right_path
        
        dialog = Gtk.Dialog(title="New File", transient_for=self, flags=0)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("OK", Gtk.ResponseType.OK)
        
        box = dialog.get_content_area()
        entry = Gtk.Entry()
        entry.set_text("new_file.txt")
        entry.set_margin_start(10)
        entry.set_margin_end(10)
        entry.set_margin_top(10)
        entry.set_margin_bottom(10)
        box.pack_start(entry, True, True, 0)
        dialog.show_all()
        
        response = dialog.run()
        filename = entry.get_text()
        dialog.destroy()
        
        if response == Gtk.ResponseType.OK and filename:
            try:
                filepath = os.path.join(src_dir, filename)
                with open(filepath, 'w') as f:
                    pass
                self.refresh_both()
                gfile = Gio.File.new_for_path(filepath)
                Gio.AppInfo.launch_default_for_uri(gfile.get_uri(), None)
            except Exception as e:
                self.show_error(str(e))

    def on_copy(self, btn=None):
        src_side = self.active_side
        dst_side = self.get_other_side(src_side)
        dst_dir = self.left_path if dst_side == "left" else self.right_path
        selected = self.get_selected_paths(src_side)
        if not selected:
            return
        try:
            for item in selected:
                base = os.path.basename(item)
                dst = os.path.join(dst_dir, base)
                if os.path.isdir(item):
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(item, dst)
                else:
                    shutil.copy2(item, dst)
            self.refresh_both()
        except Exception as e:
            self.show_error(str(e))

    def on_move(self, btn=None):
        src_side = self.active_side
        dst_side = self.get_other_side(src_side)
        dst_dir = self.left_path if dst_side == "left" else self.right_path
        selected = self.get_selected_paths(src_side)
        if not selected:
            return
        try:
            for item in selected:
                base = os.path.basename(item)
                dst = os.path.join(dst_dir, base)
                shutil.move(item, dst)
            self.refresh_both()
        except Exception as e:
            self.show_error(str(e))

    def on_delete(self, btn=None):
        src_side = self.active_side
        selected = self.get_selected_paths(src_side)
        if not selected:
            return
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Delete {len(selected)} item(s)?"
        )
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.YES:
            try:
                for item in selected:
                    if os.path.isdir(item):
                        shutil.rmtree(item)
                    else:
                        os.remove(item)
                self.refresh_both()
            except Exception as e:
                self.show_error(str(e))

    def on_rename(self, btn=None):
        src_side = self.active_side
        selected = self.get_selected_paths(src_side)
        if len(selected) != 1:
            self.show_error("Please select exactly one item to rename.")
            return
        item = selected[0]
        old_name = os.path.basename(item)
        
        dialog = Gtk.Dialog(title="Rename", transient_for=self, flags=0)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("OK", Gtk.ResponseType.OK)
        
        box = dialog.get_content_area()
        entry = Gtk.Entry()
        entry.set_text(old_name)
        entry.set_margin_start(10)
        entry.set_margin_end(10)
        entry.set_margin_top(10)
        entry.set_margin_bottom(10)
        box.pack_start(entry, True, True, 0)
        dialog.show_all()
        
        response = dialog.run()
        new_name = entry.get_text()
        dialog.destroy()
        
        if response == Gtk.ResponseType.OK and new_name:
            try:
                parent = os.path.dirname(item)
                new_path = os.path.join(parent, new_name)
                os.rename(item, new_path)
                self.refresh_both()
            except Exception as e:
                self.show_error(str(e))

    def on_symlink(self, btn=None):
        src_side = self.active_side
        dst_side = self.get_other_side(src_side)
        dst_dir = self.left_path if dst_side == "left" else self.right_path
        selected = self.get_selected_paths(src_side)
        if len(selected) != 1:
            self.show_error("Please select exactly one item to symlink.")
            return
        item = selected[0]
        try:
            base = os.path.basename(item)
            dst = os.path.join(dst_dir, "symlink_to_" + base)
            os.symlink(item, dst)
            self.refresh_both()
        except Exception as e:
            self.show_error(str(e))

    def on_new_dir(self, btn=None):
        src_dir = self.left_path if self.active_side == "left" else self.right_path
        
        dialog = Gtk.Dialog(title="New Directory", transient_for=self, flags=0)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("OK", Gtk.ResponseType.OK)
        
        box = dialog.get_content_area()
        entry = Gtk.Entry()
        entry.set_text("new_folder")
        entry.set_margin_start(10)
        entry.set_margin_end(10)
        entry.set_margin_top(10)
        entry.set_margin_bottom(10)
        box.pack_start(entry, True, True, 0)
        dialog.show_all()
        
        response = dialog.run()
        dirname = entry.get_text()
        dialog.destroy()
        
        if response == Gtk.ResponseType.OK and dirname:
            try:
                os.makedirs(os.path.join(src_dir, dirname))
                self.refresh_both()
            except Exception as e:
                self.show_error(str(e))

    def on_open_with(self, btn=None):
        src_side = self.active_side
        selected = self.get_selected_paths(src_side)
        if len(selected) != 1:
            self.show_error("Please select exactly one file.")
            return
        item = selected[0]
        if os.path.isdir(item):
            return
        try:
            gfile = Gio.File.new_for_path(item)
            content_type, _ = Gio.content_type_guess(item, None)
            chooser = Gtk.AppChooserDialog.new_for_content_type(self, 0, content_type)
            response = chooser.run()
            if response == Gtk.ResponseType.OK:
                app_info = chooser.get_app_info()
                if app_info:
                    app_info.launch([gfile], None)
            chooser.destroy()
        except Exception as e:
            self.show_error(str(e))

    def on_terminal(self, btn=None):
        src_dir = self.left_path if self.active_side == "left" else self.right_path
        terms = ["kitty", "alacritty", "konsole", "xfce4-terminal", "gnome-terminal", "foot", "xterm"]
        chosen = None
        for t in terms:
            if shutil.which(t):
                chosen = t
                break
        if not chosen:
            self.show_error("No supported terminal emulator found.")
            return
        try:
            subprocess.Popen([chosen], cwd=src_dir)
        except Exception as e:
            self.show_error(str(e))

    def on_sync(self, btn=None):
        src_side = self.active_side
        dst_side = self.get_other_side(src_side)
        src_dir = self.left_path if src_side == "left" else self.right_path
        dst_dir = self.left_path if dst_side == "left" else self.right_path
        try:
            for item in os.listdir(src_dir):
                src_item = os.path.join(src_dir, item)
                dst_item = os.path.join(dst_dir, item)
                if os.path.isdir(src_item):
                    continue
                should_copy = False
                if not os.path.exists(dst_item):
                    should_copy = True
                else:
                    if os.path.getmtime(src_item) > os.path.getmtime(dst_item):
                        should_copy = True
                if should_copy:
                    shutil.copy2(src_item, dst_item)
            self.refresh_both()
        except Exception as e:
            self.show_error(str(e))

    def on_command_activate(self, entry):
        cmd = entry.get_text()
        entry.set_text("")
        if not cmd.strip():
            return
        src_dir = self.left_path if self.active_side == "left" else self.right_path
        self.run_shell_command(cmd, src_dir)

    def on_quick_cmd(self, btn, cmd):
        src_dir = self.left_path if self.active_side == "left" else self.right_path
        self.run_shell_command(cmd, src_dir)

    def run_shell_command(self, cmd, cwd):
        try:
            res = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
            out = res.stdout + res.stderr
        except Exception as e:
            out = str(e)
            
        buf = self.term_textview.get_buffer()
        end_iter = buf.get_end_iter()
        prompt_str = f"{getpass.getuser()}@{socket.gethostname()} $ {cmd}\n"
        buf.insert(end_iter, prompt_str + out + "\n----end-of-output----\n")
        
        adj = self.term_textview.get_vadjustment()
        adj.set_value(adj.get_upper())
        
        self.refresh_both()

    def on_key_press(self, widget, event):
        focused = self.get_focus()
        keyval = Gdk.keyval_to_lower(event.keyval)
        state = event.state & Gtk.accelerator_get_default_mod_mask()
        ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)
        shift = bool(state & Gdk.ModifierType.SHIFT_MASK)
        
        if isinstance(focused, Gtk.Entry):
            if keyval == Gdk.KEY_Escape:
                panel = self.left_panel if self.active_side == "left" else self.right_panel
                panel["tree"].grab_focus()
                return True
            if not ctrl and not shift and keyval in [Gdk.KEY_F1, Gdk.KEY_F2, Gdk.KEY_F3, Gdk.KEY_F5, Gdk.KEY_F6, Gdk.KEY_F7, Gdk.KEY_F8]:
                pass
            else:
                return False

        panel = self.left_panel if self.active_side == "left" else self.right_panel
        tree = panel["tree"]
        selection = tree.get_selection()
        model, paths = selection.get_selected_rows()
        
        if keyval == Gdk.KEY_Escape:
            tree.grab_focus()
            return True
        elif keyval == Gdk.KEY_F1 or (ctrl and keyval == Gdk.KEY_l):
            self.refresh_both()
            return True
        elif keyval == Gdk.KEY_F2:
            self.on_info_btn(None)
            return True
        elif keyval == Gdk.KEY_F3 or (ctrl and keyval == Gdk.KEY_f):
            self.on_find_btn(None)
            return True
        elif keyval == Gdk.KEY_F4 and shift:
            self.on_new_file_btn(None)
            return True
        elif keyval == Gdk.KEY_F4:
            self.on_view_btn(None)
            return True
        elif keyval == Gdk.KEY_F5 or (ctrl and keyval == Gdk.KEY_c):
            self.on_copy()
            return True
        elif keyval == Gdk.KEY_F6 or (ctrl and keyval == Gdk.KEY_m):
            self.on_move()
            return True
        elif keyval == Gdk.KEY_F7 or (ctrl and keyval == Gdk.KEY_d):
            self.on_new_dir()
            return True
        elif keyval == Gdk.KEY_F8 or keyval == Gdk.KEY_Delete or keyval == Gdk.KEY_KP_Delete:
            self.on_delete()
            return True
        elif keyval == Gdk.KEY_Return or keyval == Gdk.KEY_KP_Enter or keyval == Gdk.KEY_Right:
            if paths:
                iter_ = model.get_iter(paths[0])
                full_path = model.get_value(iter_, 5)
                if os.path.isdir(full_path):
                    self.load_directory(self.active_side, full_path)
                else:
                    try:
                        gfile = Gio.File.new_for_path(full_path)
                        Gio.AppInfo.launch_default_for_uri(gfile.get_uri(), None)
                    except Exception as e:
                        self.show_error(str(e))
            return True
        elif keyval == Gdk.KEY_BackSpace or keyval == Gdk.KEY_Left:
            current = self.left_path if self.active_side == "left" else self.right_path
            parent = os.path.dirname(current)
            if parent and os.path.isdir(parent):
                self.load_directory(self.active_side, parent)
            return True
        elif keyval == Gdk.KEY_Tab or keyval == Gdk.KEY_space:
            new_side = self.get_other_side(self.active_side)
            self.set_active_side(new_side)
            other_tree = self.left_panel["tree"] if new_side == "left" else self.right_panel["tree"]
            other_tree.grab_focus()
            return True
        elif keyval == Gdk.KEY_Insert or (ctrl and keyval == Gdk.KEY_t):
            if paths:
                tree.get_selection().select_path(paths[0])
                path_str = paths[0].to_string()
                indices = [int(x) for x in path_str.split(':')]
                indices[-1] += 1
                new_path = Gtk.TreePath.new_from_indices(indices)
                try:
                    if model.get_iter(new_path):
                        tree.get_selection().select_path(new_path)
                        tree.set_cursor(new_path, None, False)
                except ValueError:
                    pass
            return True
        elif keyval == Gdk.KEY_Home:
            self.load_directory(self.active_side, os.path.expanduser("~"))
            return True
        elif ctrl and keyval == Gdk.KEY_r:
            self.on_rename()
            return True
        elif ctrl and keyval == Gdk.KEY_s:
            self.on_symlink()
            return True
        elif ctrl and keyval == Gdk.KEY_x:
            self.on_sync()
            return True
        elif ctrl and keyval == Gdk.KEY_h:
            h_btn = self.left_panel["h_btn"] if self.active_side == "left" else self.right_panel["h_btn"]
            h_btn.set_active(not h_btn.get_active())
            return True
        elif ctrl and keyval == Gdk.KEY_w:
            visible = self.bottom_box.get_visible()
            self.bottom_box.set_visible(not visible)
            return True
        elif ctrl and keyval == Gdk.KEY_z:
            self.cmd_entry.grab_focus()
            return True
        elif ctrl and keyval == Gdk.KEY_b:
            self.add_current_bookmark()
            return True
        elif ctrl and keyval == Gdk.KEY_g:
            self.on_custom_filter()
            return True
        elif ctrl and keyval == Gdk.KEY_question or (ctrl and shift and keyval == Gdk.KEY_slash):
            self.show_shortcuts_help()
            return True
        elif ctrl and keyval == Gdk.KEY_q:
            Gtk.main_quit()
            return True
            
        return False

def main():
    screenshot = None
    if "--screenshot" in sys.argv:
        idx = sys.argv.index("--screenshot")
        if idx + 1 < len(sys.argv):
            screenshot = sys.argv[idx + 1]
    
    app = EmelFM()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    
    if screenshot:
        def take_screenshot():
            while Gtk.events_pending():
                Gtk.main_iteration()
            window = app.get_window()
            if window:
                pixbuf = Gdk.pixbuf_get_from_window(window, 0, 0, window.get_width(), window.get_height())
                if pixbuf:
                    os.makedirs(os.path.dirname(os.path.abspath(screenshot)), exist_ok=True)
                    pixbuf.savev(screenshot, "png", [], [])
            Gtk.main_quit()
        GLib = gi.repository.GLib
        GLib.timeout_add(500, take_screenshot)
        
    Gtk.main()

if __name__ == "__main__":
    main()
