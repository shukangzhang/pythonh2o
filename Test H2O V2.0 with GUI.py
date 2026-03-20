import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import os
import matplotlib.pyplot as plt
import datetime
import numpy as np

# ---------------- 文件处理逻辑 ----------------

def run_processing():
    start_time = entry_start.get()
    end_time = entry_end.get()

    if not start_time or not end_time:
        messagebox.showerror("error", "please input start and end time")
        return

    folder = folder_var.get()
    filename = selected_file_var.get()

    if not folder or not filename:
        messagebox.showerror("error", "please select a folder and a file")
        return

    file_path = os.path.join(folder, filename)

    # ---------------- 以下是你的原始数据处理代码（未改动） ----------------

    t_start = pd.to_timedelta(start_time)
    t_end   = pd.to_timedelta(end_time)

    df = pd.read_csv(
        file_path,
        sep="[ ;]",
        engine="python",
        encoding="utf-8",
        skip_blank_lines=True,
        comment="#",
        on_bad_lines="skip",
    )

    df.columns = ["year", "time", "H2O [ppm]", "errors"]

    prepare_new_col1 = pd.to_timedelta(df["time"].str.replace(",", "."))
    t0 = prepare_new_col1.iloc[0]
    new_col1 = (prepare_new_col1 - t0).dt.total_seconds()
    df["time [s]"] = new_col1

    df["H2O [ppm]"] = (
        df["H2O [ppm]"]
            .replace(["RegexOERROR", "timeoutO"], pd.NA)
            .ffill()
            .str.replace(",", ".")
    )

    new_col2 = pd.to_numeric(df["H2O [ppm]"])
    df["H2O [ppm]"] = new_col2

    start_idx = df.index[prepare_new_col1 >= t_start][0]
    end_idx   = df.index[prepare_new_col1 >= t_end][0]
    df_cut = df.loc[start_idx:end_idx].copy()
    df_cut["time [s]"] = df_cut["time [s]"] - df_cut["time [s]"].iloc[0]
    df_cut = df_cut.reset_index(drop=True)

    new_col3 = df_cut["time [s]"]
    new_col4 = df_cut["H2O [ppm]"]

    df_new = pd.DataFrame({
        "time [s]": new_col1,
        "H2O [ppm]": new_col2,
        "cut_time [s]": new_col3,
        "cut_H2O [ppm]": new_col4,
    })

    df_clean = df_new.dropna(subset=["cut_time [s]", "cut_H2O [ppm]"]).reset_index(drop=True)
    x = df_clean["cut_time [s]"].to_numpy()
    y = df_clean["cut_H2O [ppm]"].to_numpy()
    x0, y0 = x[0], y[0]
    x1, y1 = x[-1], y[-1]
    baseline = y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    diff = (y - baseline).clip(min=0)

    valid_idx = df_new.dropna(subset=["cut_time [s]", "cut_H2O [ppm]"]).index
    df_new.loc[valid_idx, "baseline"] = baseline
    df_new.loc[valid_idx, "diff"] = diff

    area = np.trapezoid(diff, x)
    H2O_production = area * (2/60)
    df_new.loc[0, "H2O_production [µL]"] = H2O_production

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    save_dir = os.path.dirname(file_path)

    # 去掉扩展名（可选）
    filename_no_ext = os.path.splitext(filename)[0].strip()
    filename_short = filename_no_ext[:20].strip()
    output_folder = os.path.join(save_dir, f"processed_V2.0_{filename_short}")
    os.makedirs(output_folder, exist_ok=True)

    save_path = os.path.join(output_folder, f"processed_{timestamp}.xlsx")
    df_new.to_excel(save_path, index=False)

    messagebox.showinfo("finished", f"Processing completed! File saved to:\n{save_path}")

    # -------plot---------
    plt.figure(figsize=(12, 6))
    plt.plot(df_new["time [s]"], df_new["H2O [ppm]"], linewidth=1)
    plt.xlabel("Time [s]")
    plt.ylabel("Measurement")
    plt.xlim(left=0)
    plt.ylim(bottom=0)
    plt.grid(True)
    svg_path = os.path.join(output_folder, "overall_plot.svg")
    plt.savefig(svg_path, format="svg")

    plt.figure(figsize=(12, 6))
    plt.plot(x, y, label="Cut Curve", linewidth=1)
    plt.plot(x, baseline, label="Baseline", linestyle="--", color="red", linewidth=1)
    plt.fill_between(x, y, baseline, where=(y > baseline), alpha=0.3, color="orange")
    plt.xlim(left=0)
    plt.ylim(bottom=0)
    plt.grid(True)
    plt.legend()
    cut_svg_path = os.path.join(output_folder, "cut_plot.svg")
    plt.savefig(cut_svg_path, format="svg")


# ---------------- GUI：文件夹 + 文件列表 ----------------

def choose_folder():
    folder = filedialog.askdirectory(title="Select Folder")
    if folder:
        folder_var.set(folder)
        update_file_list(folder)

def update_file_list(folder):
    listbox_files.delete(0, tk.END)
    try:
        for f in os.listdir(folder):
            if os.path.isfile(os.path.join(folder, f)):
                listbox_files.insert(tk.END, f)
    except Exception as e:
        messagebox.showerror("Error", str(e))

def on_file_select(event):
    selection = listbox_files.curselection()
    if selection:
        selected_file_var.set(listbox_files.get(selection[0]))


# ---------------- GUI 主界面 ----------------

root = tk.Tk()
root.title("python GUI for H2O sensor data processing @Shukang V2.0 2026.3.20")
root.geometry("500x420")

folder_var = tk.StringVar()
selected_file_var = tk.StringVar()

# 选择文件夹
frame_folder = tk.Frame(root)
frame_folder.pack(pady=5)
tk.Button(frame_folder, text="select folder", command=choose_folder).pack(side="left")
tk.Entry(frame_folder, textvariable=folder_var, width=40).pack(side="left", padx=10)

# 文件列表
tk.Label(root, text="File List:").pack()
listbox_files = tk.Listbox(root, height=10)
listbox_files.pack(fill="both", expand=True, padx=10)
listbox_files.bind("<<ListboxSelect>>", on_file_select)

tk.Label(root, textvariable=selected_file_var, fg="blue").pack(pady=5)

# 时间输入
tk.Label(root, text="Start time (HH:MM:SS):").pack()
entry_start = tk.Entry(root, width=20)
entry_start.pack()

tk.Label(root, text="End time (HH:MM:SS):").pack()
entry_end = tk.Entry(root, width=20)
entry_end.pack()

# Run 按钮
tk.Button(root, text="Run", command=run_processing, width=15).pack(pady=10)

root.mainloop()
