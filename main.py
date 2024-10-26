try:
    import pyautogui
except ImportError:
    print("Ошибка: библиотека 'pyautogui' не установлена. Пожалуйста, установите её командой 'pip install pyautogui'.")
    sys.exit(1)

try:
    import pytesseract
except ImportError:
    print("Ошибка: библиотека 'pytesseract' не установлена. Пожалуйста, установите её командой 'pip install pytesseract'.")
    sys.exit(1)

from PIL import Image, ImageDraw
import os
from datetime import datetime
import tempfile
import sys
import tkinter as tk
from tkinter import simpledialog
import time
import threading
from pynput import keyboard

# Глобальные переменные для управления горячими клавишами
start_selection = False
terminate_script = False

def get_region_with_mouse(delay=1):
    """
    Позволяет пользователю выделить область экрана с помощью мыши.
    """
    print("Выберите область для скриншота... (Перетащите мышью для выделения области)")
    time.sleep(delay)  # Задержка перед началом выбора области (настраиваемая)

    # Создаем окно для отображения выделения области
    root = tk.Tk()
    root.attributes('-fullscreen', True)
    root.attributes('-alpha', 0.3)  # Прозрачность окна
    root.configure(bg='gray')
    root.overrideredirect(True)  # Убираем заголовок окна

    # Координаты начала и конца выделения
    start_x, start_y = None, None
    end_x, end_y = None, None
    rect_id = None

    def on_mouse_down(event):
        nonlocal start_x, start_y, rect_id
        start_x, start_y = event.x, event.y
        if rect_id:
            canvas.delete(rect_id)
        rect_id = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline='red', width=2)

    def on_mouse_drag(event):
        nonlocal rect_id
        if rect_id:
            canvas.coords(rect_id, start_x, start_y, event.x, event.y)

    def on_mouse_up(event):
        nonlocal end_x, end_y
        end_x, end_y = event.x, event.y
        root.quit()

    # Создаем Canvas для отображения выделения
    canvas = tk.Canvas(root, bg='gray', highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)
    canvas.bind('<ButtonPress-1>', on_mouse_down)
    canvas.bind('<B1-Motion>', on_mouse_drag)
    canvas.bind('<ButtonRelease-1>', on_mouse_up)

    root.mainloop()
    try:
        root.destroy()
    except tk.TclError:
        pass  # Игнорируем ошибку, если окно уже уничтожено

    # Определение координат и размеров выделенной области
    left, top, width, height = 0, 0, 0, 0
    if start_x is not None and end_x is not None:
        left = min(start_x, end_x)
        top = min(start_y, end_y)
        width = abs(end_x - start_x)
        height = abs(end_y - start_y)
    region = (left, top, width, height)

    return region

def capture_screenshot(region=None):
    """
    Делает скриншот экрана.
    Если передан регион (координаты x, y, ширина, высота), то захватывает эту область.
    """
    try:
        if region is None:
            screenshot = pyautogui.screenshot()
        else:
            screenshot = pyautogui.screenshot(region=region)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            screenshot_path = temp_file.name
            screenshot.save(screenshot_path)
        return screenshot_path
    except Exception as e:
        print(f"Ошибка при сохранении скриншота: {e}")
        return None

def extract_text_from_image(image_path):
    """
    Извлекает текст из изображения, используя pytesseract.
    """
    try:
        image = Image.open(image_path)
        # Преобразование изображения для повышения точности OCR
        image = image.convert('L')  # Преобразование в оттенки серого
        text = pytesseract.image_to_string(image, lang='jpn+rus+eng')
        return text
    except pytesseract.pytesseract.TesseractError as e:
        print("Ошибка при распознавании текста:", e)
        return ""
    except Exception as e:
        print(f"Ошибка при открытии изображения: {e}")
        return ""

def write_text_to_file(text, output_file):
    """
    Записывает извлеченный текст в файл.
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as file:
            # Пытаемся записать текст в файл и обрабатываем возможные ошибки с символами
            file.write(text.replace('\n\n', '\n'))
    except UnicodeEncodeError as e:
        print(f"Ошибка при записи текста в файл: {e}")

def listen_for_hotkeys():
    """
    Функция для прослушивания горячих клавиш в отдельном потоке.
    """
    def on_press(key):
        global start_selection, terminate_script
        try:
            if key == keyboard.Key.f9:
                start_selection = True
            if key == keyboard.Key.esc:
                terminate_script = True
        except AttributeError:
            pass

    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

def main():
    global start_selection, terminate_script

    # Запуск потока для прослушивания горячих клавиш
    hotkey_thread = threading.Thread(target=listen_for_hotkeys, daemon=True)
    hotkey_thread.start()

    print("Нажмите 'F9' для начала выделения области экрана.")
    print("Нажмите 'Esc' для завершения работы скрипта.")

    while True:
        if start_selection:
            start_selection = False
            # Получение области, выбранной пользователем с помощью мыши
            delay = simpledialog.askinteger("Input", "Введите задержку в секундах перед выделением области (0 для мгновенного выделения):", initialvalue=1)
            region = get_region_with_mouse(delay=delay)
            screenshot_path = capture_screenshot(region=region)

            if screenshot_path:
                print(f"Скриншот сохранен в файл: {screenshot_path}")
                
                # Извлечение текста из изображения
                extracted_text = extract_text_from_image(screenshot_path)
                
                # Запись текста в файл
                output_file = "extracted_text.txt"
                write_text_to_file(extracted_text, output_file)
                print(f"Текст из скриншота записан в файл: {output_file}")

                # Удаление временного изображения
                try:
                    if os.path.exists(screenshot_path):
                        os.remove(screenshot_path)
                        print("Временное изображение удалено.")
                except Exception as e:
                    print(f"Ошибка при удалении временного файла: {e}")

        if terminate_script:
            print("Завершение работы скрипта.")
            break

if __name__ == "__main__":
    main()
