import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import cv2
import numpy as np
import subprocess


SUPPORTED_EXTENSIONS = ('.mp4', '.mov', '.avi', '.mkv', '.webm')

def find_video_files(root_dir):
    video_files = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith(SUPPORTED_EXTENSIONS):
                full_path = os.path.join(root, file)
                video_files.append(full_path)
    return video_files

def cut_video_ffmpeg(input_file, output_file, start_sec, end_sec):
    start_sec += 0.5
    end_sec -= 0.5
    if end_sec <= start_sec:
        print("⚠️ Фрагмент слишком короткий после обрезки.")
        return False

    cmd = [
        "ffmpeg", "-y",
        "-i", input_file,
        "-ss", str(start_sec),
        "-to", str(end_sec),
        "-c:v", "copy",
        "-c:a", "copy",
        output_file
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        print("❌ Ошибка при вырезке:", input_file)
        return False



def is_static_frame(prev_frame, current_frame, threshold=3.0):
    diff = cv2.absdiff(prev_frame, current_frame)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    mean_diff = np.mean(gray)
    return mean_diff < threshold

def find_static_segments(video_path, min_sec=5, max_sec=13, sensitivity=3.0):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    static_segments = []
    start_frame = None
    prev_frame = None

    for i in range(total_frames):
        ret, frame = cap.read()
        if not ret:
            break

        if prev_frame is not None:
            if is_static_frame(prev_frame, frame, threshold=sensitivity):
                if start_frame is None:
                    start_frame = i
            else:
                if start_frame is not None:
                    duration_sec = (i - start_frame) / fps
                    if min_sec <= duration_sec <= max_sec:
                        static_segments.append((start_frame, i))
                    start_frame = None
        prev_frame = frame

    if start_frame is not None:
        duration_sec = (total_frames - start_frame) / fps
        if min_sec <= duration_sec <= max_sec:
            static_segments.append((start_frame, total_frames))

    cap.release()
    return static_segments, fps

def select_input_folder():
    folder = filedialog.askdirectory(title="Выберите папку с видео")
    if folder:
        input_path_var.set(folder)

def select_output_folder():
    folder = filedialog.askdirectory(title="Выберите папку для сохранения")
    if folder:
        output_path_var.set(folder)

def start_processing():
    input_path = input_path_var.get()
    output_path = output_path_var.get()

    if not input_path or not output_path:
        messagebox.showerror("Ошибка", "Укажи обе папки!")
        return

    video_files = find_video_files(input_path)

    if not video_files:
        messagebox.showinfo("Нет видео", "В выбранной папке нет видеофайлов.")
        return

    total_videos = len(video_files)
    progress_bar['value'] = 0

    for idx_file, video in enumerate(video_files):
        print("\n▶️ Обработка файла:", os.path.basename(video))
        segments, fps = find_static_segments(video)

        if segments:
            print(f"  Найдено {len(segments)} статичных фрагментов:")
            for idx, (start, end) in enumerate(segments):
                duration = (end - start) / fps
                print(f"   {idx + 1}. Кадры: {start}–{end} ({duration:.2f} сек)")

                start_sec = start / fps
                end_sec = end / fps

                filename = os.path.splitext(os.path.basename(video))[0]
                ext = os.path.splitext(video)[1]
                final_fragment = os.path.join(output_path, f"{filename}_fragment{idx + 1}{ext}")

                print(f"  💾 Сохраняем: {final_fragment} ({duration:.2f} сек)")

                success = cut_video_ffmpeg(video, final_fragment, start_sec, end_sec)

                if not success:
                    print("    ❌ Не удалось сохранить.")
                    continue


        else:
            print("  Статичных участков не найдено.")

        progress_percent = ((idx_file + 1) / total_videos) * 100
        progress_var.set(progress_percent)
        root.update_idletasks()

    messagebox.showinfo("Готово", f"Обработка завершена. Всего файлов: {total_videos}")

root = tk.Tk()
root.title("Видео обрезка и стабилизация")
root.geometry("600x300")

input_path_var = tk.StringVar()
output_path_var = tk.StringVar()

# GUI элементы

tk.Label(root, text="Папка с исходными видео:").pack(pady=5)
tk.Entry(root, textvariable=input_path_var, width=70).pack()
tk.Button(root, text="Выбрать папку", command=select_input_folder).pack(pady=5)

tk.Label(root, text="Папка для сохранения видео:").pack(pady=5)
tk.Entry(root, textvariable=output_path_var, width=70).pack()
tk.Button(root, text="Выбрать папку", command=select_output_folder).pack(pady=5)

tk.Button(root, text="Старт обработки", command=start_processing, bg="green", fg="white", height=2).pack(pady=10)

progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=100)
progress_bar.pack(fill="x", padx=10, pady=10)

root.mainloop()
