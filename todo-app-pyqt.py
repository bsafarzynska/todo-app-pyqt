import sys
import sqlite3
from datetime import datetime, date
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QDateEdit, QScrollArea, QMessageBox, QCheckBox, QComboBox,
    QInputDialog
)
from PyQt5.QtCore import Qt, QDate

DB_FILE = "tasks.db"

class TaskWidget(QWidget):
    def __init__(self, task, on_change_callback):
        super().__init__()
        self.task = task
        self.on_change_callback = on_change_callback
        self.initUI()

    def initUI(self):
        layout = QHBoxLayout()
        self.desc_label = QLabel(self.task['description'])
        added_label = QLabel(f"Created: {self.task['created']}")

        self.deadline_label = QLabel(f"Deadline: {self.task['deadline']}")
        deadline_date = datetime.strptime(self.task['deadline'], "%Y-%m-%d").date()
        if deadline_date < date.today():
            self.deadline_label.setStyleSheet("color: red")

        complete_button = QPushButton("✔")
        complete_button.setToolTip("Mark as completed")
        complete_button.clicked.connect(self.mark_completed)

        edit_button = QPushButton("✎")
        edit_button.setToolTip("Edit task")
        edit_button.clicked.connect(self.edit_task)

        delete_button = QPushButton("🗑")
        delete_button.setToolTip("Delete task")
        delete_button.clicked.connect(self.delete_task)

        layout.addWidget(self.desc_label)
        layout.addWidget(added_label)
        layout.addWidget(self.deadline_label)
        layout.addWidget(complete_button)
        layout.addWidget(edit_button)
        layout.addWidget(delete_button)
        self.setLayout(layout)

    def mark_completed(self):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("UPDATE tasks SET completed = 1 WHERE id = ?", (self.task['id'],))
        conn.commit()
        conn.close()
        self.on_change_callback()

    def edit_task(self):
        new_desc, ok1 = QInputDialog.getText(self, "Edit task", "New description:", text=self.task['description'])
        new_deadline, ok2 = QInputDialog.getText(self, "Edit deadline", "New deadline (YYYY-MM-DD):", text=self.task['deadline'])

        if ok1 and ok2 and new_desc.strip() and new_deadline.strip():
            try:
                datetime.strptime(new_deadline.strip(), "%Y-%m-%d")
            except ValueError:
                QMessageBox.warning(self, "Error", "Invalid date format. Use YYYY-MM-DD.")
                return
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("UPDATE tasks SET description = ?, deadline = ? WHERE id = ?", (new_desc.strip(), new_deadline.strip(), self.task['id']))
            conn.commit()
            conn.close()
            self.task['description'] = new_desc.strip()
            self.task['deadline'] = new_deadline.strip()
            self.desc_label.setText(self.task['description'])
            self.deadline_label.setText(f"Deadline: {self.task['deadline']}")
            if datetime.strptime(new_deadline.strip(), "%Y-%m-%d").date() < date.today():
                self.deadline_label.setStyleSheet("color: red")
            else:
                self.deadline_label.setStyleSheet("")

    def delete_task(self):
        confirm = QMessageBox.question(self, "Confirm deletion", "Are you sure you want to delete this task?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("DELETE FROM tasks WHERE id = ?", (self.task['id'],))
            conn.commit()
            conn.close()
            self.on_change_callback()

class TodoApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TODO List - PyQt")
        self.resize(700, 500)
        self.init_db()
        self.initUI()
        self.load_tasks()

    def init_db(self):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        description TEXT,
                        created TEXT,
                        deadline TEXT,
                        completed INTEGER DEFAULT 0
                    )''')
        conn.commit()
        conn.close()

    def initUI(self):
        self.layout = QVBoxLayout()

        # Form to add task
        form_layout = QHBoxLayout()
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("Enter task description...")
        self.deadline_input = QDateEdit()
        self.deadline_input.setCalendarPopup(True)
        self.deadline_input.setDate(QDate.currentDate())
        add_button = QPushButton("Add task")
        add_button.clicked.connect(self.add_task)

        form_layout.addWidget(self.task_input)
        form_layout.addWidget(self.deadline_input)
        form_layout.addWidget(add_button)
        self.layout.addLayout(form_layout)

        # Extra options
        options_layout = QHBoxLayout()
        self.show_completed_checkbox = QCheckBox("Show completed")
        self.show_completed_checkbox.stateChanged.connect(self.load_tasks)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Sort by creation date", "Sort by deadline"])
        self.sort_combo.currentIndexChanged.connect(self.load_tasks)

        options_layout.addWidget(self.show_completed_checkbox)
        options_layout.addWidget(self.sort_combo)
        self.layout.addLayout(options_layout)

        # Scroll area for tasks
        self.scroll_area = QScrollArea()
        self.task_container = QWidget()
        self.task_layout = QVBoxLayout()
        self.task_container.setLayout(self.task_layout)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.task_container)
        self.layout.addWidget(self.scroll_area)

        self.setLayout(self.layout)

    def add_task(self):
        desc = self.task_input.text().strip()
        deadline = self.deadline_input.date().toString("yyyy-MM-dd")
        created = datetime.today().strftime("%Y-%m-%d")

        if not desc:
            QMessageBox.warning(self, "Error", "Task description cannot be empty.")
            return

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO tasks (description, created, deadline) VALUES (?, ?, ?)", (desc, created, deadline))
        conn.commit()
        conn.close()

        self.task_input.clear()
        self.load_tasks()

    def load_tasks(self):
        for i in reversed(range(self.task_layout.count())):
            self.task_layout.itemAt(i).widget().setParent(None)

        show_completed = self.show_completed_checkbox.isChecked()
        sort_by_deadline = self.sort_combo.currentIndex() == 1

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        query = "SELECT id, description, created, deadline FROM tasks"
        if not show_completed:
            query += " WHERE completed = 0"

        if sort_by_deadline:
            query += " ORDER BY deadline ASC"
        else:
            query += " ORDER BY created DESC"

        c.execute(query)
        tasks = c.fetchall()
        conn.close()

        for task in tasks:
            task_data = {
                'id': task[0],
                'description': task[1],
                'created': task[2],
                'deadline': task[3]
            }
            task_widget = TaskWidget(task_data, self.load_tasks)
            self.task_layout.addWidget(task_widget)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    todo = TodoApp()
    todo.show()
    sys.exit(app.exec_())