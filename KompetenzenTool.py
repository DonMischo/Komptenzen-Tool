import ui_components as ui
from student_loader import sync_students

sync_students()

result = ui.run_ui()
