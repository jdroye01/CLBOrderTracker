import os, sys
import sqlite3
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import pandas as pd
from datetime import datetime
PRIORITY_OPTIONS = ["High", "Medium", "Low"]

APP_FOLDER = os.path.join("C:\\Order Management")
DB_FILE = os.path.join(APP_FOLDER, "company_data.db")

# Create the folder if it doesn't exist
if not os.path.exists(APP_FOLDER):
    try:
        os.makedirs(APP_FOLDER)
    except Exception as e:
        messagebox.showerror("Startup Error", f"Could not create folder:\n{APP_FOLDER}\n\n{e}")
        sys.exit(1)

# Connect to SQLite
db_exists = os.path.exists(DB_FILE)
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

if not db_exists:
    cursor.execute("CREATE TABLE IF NOT EXISTS tabs (name TEXT PRIMARY KEY)")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS column_settings (
            tab TEXT,
            column_name TEXT,
            input_type TEXT,  -- "text" or "dropdown"
            options TEXT      -- comma-separated list if dropdown
        )
    """)
    conn.commit()



def resource_path(relative_path):
    try:
        # When bundled by PyInstaller
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname( os.path.abspath(sys.argv[0]))

    return os.path.join(base_path, relative_path)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        import os
        self.iconbitmap(resource_path("CLB_Logo.ico"))
        self.title("Order Tracker")
        self.state('zoomed')  # Windows fullscreen
        self.admin_mode = tk.BooleanVar(value=True)
        self.selected_tab = tk.StringVar()
        self.setup_ui()
        self.auto_load_first_tab()

    def setup_ui(self):
        top_frame = tk.Frame(self)
        top_frame.pack(fill="x")

        tk.Checkbutton(top_frame, text="Admin Mode", variable=self.admin_mode).pack(side="left")
        tk.Button(top_frame, text="New Tab", command=self.create_tab).pack(side="left")
        tk.Button(top_frame, text="Add Row", command=self.add_row).pack(side="left")
        tk.Button(top_frame, text="Edit Row", command=self.edit_row).pack(side="left")
        tk.Button(top_frame, text="Delete Row", command=self.delete_row).pack(side="left")
        tk.Button(top_frame, text="Delete Tab", command=self.delete_tab).pack(side="left")
        tk.Button(top_frame, text="Settings", command=self.open_settings).pack(side="left")

        self.tab_menu = ttk.Combobox(top_frame, textvariable=self.selected_tab, postcommand=self.refresh_tabs)
        self.tab_menu.pack(side="left", padx=10)
        tk.Button(top_frame, text="Load Tab", command=self.load_tab).pack(side="left")

        self.tree = ttk.Treeview(self)
        self.tree.pack(fill="both", expand=True)

    def open_settings(self):
        if not self.admin_mode.get():
            return
        
        self.load_tab()

        settings_win = tk.Toplevel(self)
        settings_win.title("Column Settings")
        settings_win.geometry("600x400")

        # Tab selection dropdown
        tk.Label(settings_win, text="Select Tab:").pack(pady=5)
        selected_tab = tk.StringVar(value=self.selected_tab.get())
        tab_combo = ttk.Combobox(settings_win, values=self.tab_menu["values"], textvariable=selected_tab, state="readonly")
        tab_combo.pack(pady=5)

        frame = tk.Frame(settings_win)
        frame.pack(fill="both", expand=True)

        def load_columns():
            for widget in frame.winfo_children():
                widget.destroy()

            tab = selected_tab.get()
            if not tab:
                return

            cursor.execute(f"PRAGMA table_info({tab})")
            columns = [row[1] for row in cursor.fetchall() if row[1] not in ("ID", "Created_At", "Last_Updated")]

            for row_index, col in enumerate(columns):
                tk.Label(frame, text=col).grid(row=row_index, column=0, padx=5, pady=5, sticky="w")

                # Input type selector
                input_type_var = tk.StringVar(value="text")
                type_combo = ttk.Combobox(frame, values=["text", "dropdown"], state="readonly", textvariable=input_type_var)
                type_combo.grid(row=row_index, column=1, padx=5, pady=5)

                # Dropdown options entry
                options_entry = tk.Entry(frame)
                options_entry.grid(row=row_index, column=2, padx=5, pady=5)

                # Load any existing config
                cursor.execute("SELECT input_type, options FROM column_settings WHERE tab=? AND column_name=?", (tab, col))
                existing = cursor.fetchone()
                if existing:
                    input_type, options = existing
                    input_type_var.set(input_type or "text")
                    options_entry.delete(0, tk.END)
                    options_entry.insert(0, options or "")
                else:
                    input_type_var.set("text")  # default

                # Tag widgets with column name so they can be saved
                type_combo.column_name = col
                options_entry.column_name = col

        def save_settings():
            tab = selected_tab.get()
            if not tab:
                return

            cursor.execute("DELETE FROM column_settings WHERE tab=?", (tab,))

            for row in range(len(frame.grid_slaves()) // 3):
                try:
                    input_type_widget = frame.grid_slaves(row=row, column=1)[0]
                    options_widget = frame.grid_slaves(row=row, column=2)[0]
                    column_name = input_type_widget.column_name
                    input_type = input_type_widget.get()
                    options = options_widget.get() if input_type == "dropdown" else ""
                    cursor.execute("INSERT INTO column_settings (tab, column_name, input_type, options) VALUES (?, ?, ?, ?)",
                                (tab, column_name, input_type, options))
                except Exception as e:
                    print(f"Failed to save column settings: {e}")

            conn.commit()
            messagebox.showinfo("Saved", "Settings saved successfully.")

        tk.Button(settings_win, text="Load Columns", command=load_columns).pack(pady=10)
        tk.Button(settings_win, text="Save Settings", command=save_settings).pack(pady=5)
    
        load_columns() # ✅ Auto-load current tab's settings

    def refresh_tabs(self):
        cursor.execute("SELECT name FROM tabs")
        tabs = [row[0] for row in cursor.fetchall()]
        self.tab_menu["values"] = tabs
    
    def auto_load_first_tab(self):
        cursor.execute("SELECT name FROM tabs ORDER BY name ASC")
        result = cursor.fetchone()
        if result:
            first_tab = result[0]
            self.selected_tab.set(first_tab)
            self.load_tab()

    def create_tab(self):
        if not self.admin_mode.get():
            return
        tab_name = simpledialog.askstring("Tab Name", "Enter new tab name:")
        if not tab_name:
            return
        col_input = simpledialog.askstring("Columns", "Enter column names (comma-separated, include 'Priority' and 'Order_Date')(Example: Customer, OrderID, Priority, Order_Date):")
        if not col_input:
            return
        columns = [c.strip() for c in col_input.split(",")]
        columns += ["Created_At", "Last_Updated"]
        try:
            col_defs = ", ".join(f"{col} TEXT" for col in columns)
            cursor.execute(f"CREATE TABLE {tab_name} (ID INTEGER PRIMARY KEY AUTOINCREMENT, {col_defs})")
            cursor.execute("INSERT INTO tabs (name) VALUES (?)", (tab_name,))
            conn.commit()
            messagebox.showinfo("Success", f"Tab '{tab_name}' created.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def load_tab(self):
        tab = self.selected_tab.get()
        if not tab:
            return
        try:
            df = pd.read_sql_query(f"SELECT * FROM {tab}", conn)
            self.tree.delete(*self.tree.get_children())
            self.tree["columns"] = list(df.columns)
            self.tree["show"] = "headings"
            for col in df.columns:
                self.tree.heading(col, text=col, command=lambda c=col: self.sort_by_column(c))

                self.tree.column(col, width=120, anchor="center")
            for index, row in df.iterrows():
                Priority = row["Priority"] if "Priority" in row else "Low"
                # Add zebra striping: even/odd tags
                row_tag = f"{Priority}_even" if index % 2 == 0 else f"{Priority}_odd"
                self.tree.insert("", "end", values=list(row), tags=(row_tag,))
            # Priority + zebra striping styles
            self.tree.tag_configure("High_even", background="#ffb3b3")      # light red
            self.tree.tag_configure("High_odd", background="#ff9999")       # slightly darker red

            self.tree.tag_configure("Medium_even", background="#fff2b3")    # light gold
            self.tree.tag_configure("Medium_odd", background="#ffe680")     # slightly darker gold

            self.tree.tag_configure("Low_even", background="#d6f5d6")       # light green
            self.tree.tag_configure("Low_odd", background="#b3ffb3")        # slightly darker green

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def add_row(self):
        if not self.admin_mode.get():
            return
        tab = self.selected_tab.get()
        if not tab:
            return
        cursor.execute(f"PRAGMA table_info({tab})")
        columns = [row[1] for row in cursor.fetchall() if row[1] not in ("ID", "Created_At", "Last_Updated")]
        values = []
        for col in columns:
            # Get setting for this column
            cursor.execute("SELECT input_type, options FROM column_settings WHERE tab=? AND column_name=?", (tab, col))
            setting = cursor.fetchone()

            if setting and setting[0] == "dropdown":
                # Show dropdown
                top = tk.Toplevel(self)
                top.title(f"{col} - Select Option")
                tk.Label(top, text=f"Select value for '{col}':").pack(pady=5)
                var = tk.StringVar()
                combo = ttk.Combobox(top, values=[x.strip() for x in (setting[1] or "").split(",")], textvariable=var, state="readonly")
                combo.pack(pady=5)
                tk.Button(top, text="OK", command=top.destroy).pack(pady=5)
                self.wait_window(top)
                values.append(var.get())
            else:
                val = simpledialog.askstring("Input", f"Enter value for '{col}':")
                values.append(val)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        values += [now, now]
        cursor.execute(f"INSERT INTO {tab} ({','.join(columns)}, Created_At, Last_Updated) VALUES ({','.join(['?'] * len(values))})", values)
        conn.commit()
        self.load_tab()

    def edit_row(self):
        if not self.admin_mode.get():
            return
        tab = self.selected_tab.get()
        if not tab:
            return
        selected = self.tree.selection()
        if not selected:
            return

        row_values = self.tree.item(selected[0])["values"]
        row_id = row_values[0]

        cursor.execute(f"PRAGMA table_info({tab})")
        all_columns = [row[1] for row in cursor.fetchall()]
        editable_columns = [col for col in all_columns if col not in ("ID", "Created_At", "Last_Updated")]

        # Show dropdown window to select column
        def on_confirm():
            column_to_edit = combo.get()
            if column_to_edit not in editable_columns:
                messagebox.showerror("Error", "Invalid column selected.")
                top.destroy()
                return

            # Check if this column is configured as a dropdown
            cursor.execute("SELECT input_type, options FROM column_settings WHERE tab=? AND column_name=?", (tab, column_to_edit))
            setting = cursor.fetchone()

            if setting and setting[0] == "dropdown":
                top2 = tk.Toplevel(self)
                top2.title(f"{column_to_edit} - Select New Value")
                tk.Label(top2, text=f"Select new value for '{column_to_edit}':").pack(pady=5)
                var = tk.StringVar()
                combo2 = ttk.Combobox(top2, values=[x.strip() for x in (setting[1] or "").split(",")], textvariable=var, state="readonly")
                combo2.pack(pady=5)
                combo2.set(row_values[self.tree["columns"].index(column_to_edit)])
                tk.Button(top2, text="OK", command=top2.destroy).pack(pady=5)
                self.wait_window(top2)
                new_value = var.get()
            else:
                new_value = simpledialog.askstring("New Value", f"Enter new value for '{column_to_edit}':")
            if new_value is None:
                top.destroy()
                return

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                cursor.execute(f"UPDATE {tab} SET {column_to_edit} = ?, Last_Updated = ? WHERE ID = ?", (new_value, now, row_id))
                conn.commit()
                self.load_tab()
            except Exception as e:
                messagebox.showerror("Error", str(e))
            top.destroy()

        top = tk.Toplevel(self)
        top.title("Select Column to Edit")
        top.geometry("300x100")
        tk.Label(top, text="Select column to edit:").pack(pady=5)
        combo = ttk.Combobox(top, values=editable_columns, state="readonly")
        combo.pack(pady=5)
        tk.Button(top, text="Confirm", command=on_confirm).pack(pady=5)

    def delete_row(self):
        if not self.admin_mode.get():
            return
        tab = self.selected_tab.get()
        selected = self.tree.selection()
        if not selected:
            return
        row_id = self.tree.item(selected[0])["values"][0]
        cursor.execute(f"DELETE FROM {tab} WHERE ID = ?", (row_id,))
        conn.commit()
        self.load_tab()
    
    def delete_tab(self):
        if not self.admin_mode.get():
            return
        tab = self.selected_tab.get()
        if not tab:
            return

        confirm = messagebox.askyesno("Delete Tab", f"Are you sure you want to delete tab '{tab}'? This cannot be undone.")
        if confirm:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {tab}")
                cursor.execute("DELETE FROM tabs WHERE name = ?", (tab,))
                conn.commit()
                self.refresh_tabs()
                self.selected_tab.set("")
                self.tree.delete(*self.tree.get_children())
                messagebox.showinfo("Success", f"Tab '{tab}' deleted.")
            except Exception as e:
                messagebox.showerror("Error", str(e))


    def sort_by_column(self, col):
        tab = self.selected_tab.get()
        if not tab:
            return

        # Toggle sort direction
        if hasattr(self, 'last_sort_column') and self.last_sort_column == col:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_ascending = True
            self.last_sort_column = col

        try:
            df = pd.read_sql_query(f"SELECT * FROM {tab}", conn)
            df = df.sort_values(by=col, ascending=self.sort_ascending, na_position='last')
            self.tree.delete(*self.tree.get_children())
            for _, row in df.iterrows():
                Priority = row["Priority"] if "Priority" in row else "Low"
                self.tree.insert("", "end", values=list(row), tags=(Priority,))
        except Exception as e:
            messagebox.showerror("Sort Error", str(e))


if __name__ == "__main__":
    app = App()
    app.mainloop()
