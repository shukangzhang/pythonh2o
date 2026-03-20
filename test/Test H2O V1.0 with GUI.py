import tkinter as tk
from tkinter import simpledialog, filedialog, messagebox
import pandas as pd
import os
import matplotlib.pyplot as plt
import datetime
import numpy as np

def run_processing():
    start_time = entry_start.get() # get start time from entry
    end_time = entry_end.get() # get end time from entry

    if not start_time or not end_time:
        messagebox.showerror("error", "please input start and end time")
        return

    # 选择文件
    file_path = filedialog.askopenfilename(
    title="choose a CSV file",
    filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )

    root = tk.Tk()
    root.withdraw()

    t_start = pd.to_timedelta(start_time)
    t_end   = pd.to_timedelta(end_time)


    # 读取数据
    df = pd.read_csv(
        file_path,
        sep="[ ;]",  # 如果分隔符是空格、分号
        engine="python",     # 必须配合 sep=None
        encoding="utf-8",    # 或 "utf-8-sig" / "latin1"
        skip_blank_lines=True,
        comment="#",         # 如果文件里有注释行
        on_bad_lines="skip", # 遇到坏行跳过
        )

    df.columns = ["year", "time", "H2O [ppm]", "errors"]  # 给列命名，方便后续处理

    # 将第二列转换为 timedelta，先替换逗号为点, repare_new_col1 stores the converted timedelta values
    prepare_new_col1 = pd.to_timedelta(df["time"].str.replace(",", "."))  

    # calculate time difference in seconds, new_col1 stores the time difference in seconds
    t0 = prepare_new_col1.iloc[0]
    new_col1 = (prepare_new_col1 - t0).dt.total_seconds()
    df["time [s]"] = new_col1   # 写入 df 的新列 "time [s]"

    # check col3, clear errors, and convert to numeric
    df["H2O [ppm]"] = (
        df["H2O [ppm]"].replace("RegexOERROR", pd.NA)   # 替换错误值
            .ffill()                                     # 用上一行填补
            .str.replace(",", ".")                       # 把逗号换成点
        )

    # 转成真正的 float, new_col2 stores the numeric values of H2O [ppm]
    new_col2 = pd.to_numeric(df["H2O [ppm]"])
    df["H2O [ppm]"] = new_col2   # 写入 df 的新列 "H2O [ppm]"

    # 找到 >= 输入时间的第一个 index
    start_idx = df.index[prepare_new_col1 >= t_start][0]
    end_idx   = df.index[prepare_new_col1 >= t_end][0]
    df_cut = df.loc[start_idx:end_idx].copy()  # 注意要 copy 一份切片，否则后续修改会有 SettingWithCopyWarning
    # 时间重新从 0 开始
    df_cut["time [s]"] = df_cut["time [s]"] - df_cut["time [s]"].iloc[0]
    # 重置 index，让所有列从第 0 行开始排
    df_cut = df_cut.reset_index(drop=True)

    # 从切片 df_cut 中提取时间和 H2O 列，分别存到 new_col3 和 new_col4
    new_col3 = df_cut["time [s]"]
    new_col4 = df_cut["H2O [ppm]"]

    # ---------构建新 df----------
    df_new = pd.DataFrame({
        "time [s]": new_col1,
        "H2O [ppm]": new_col2,
        "cut_time [s]": new_col3,
        "cut_H2O [ppm]": new_col4,
    })

    #-------calculate full H2O production-------
    df_clean = df_new.dropna(subset=["cut_time [s]", "cut_H2O [ppm]"]).reset_index(drop=True)
    x = df_clean["cut_time [s]"].to_numpy()
    y = df_clean["cut_H2O [ppm]"].to_numpy()
    x0, y0 = x[0], y[0]
    x1, y1 = x[-1], y[-1]
    baseline = y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    diff = (y - baseline).clip(min=0) # 只保留高于基线的部分，负值置零
    # add baseline and diff to df_new
    valid_idx = df_new.dropna(subset=["cut_time [s]", "cut_H2O [ppm]"]).index
    df_new.loc[valid_idx, "baseline"] = baseline
    df_new.loc[valid_idx, "diff"] = diff

    area = np.trapezoid(diff, x)
    H2O_production = area * (2/60)  # 转换为 µL
    df_new.loc[0, "H2O_production [µL]"] = H2O_production


    # 生成时间戳 + export df_new to excel
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    save_dir = os.path.dirname(file_path)
    # ceate output folder path
    filename = os.path.basename(file_path)
    # 限制最大长度，例如 50 字符
    MAX_LEN = 50
    filename_short = filename[:MAX_LEN]
    output_folder = os.path.join(save_dir, f"processed_results_V1.0_{filename_short}")
    # make sure output folder exists
    os.makedirs(output_folder, exist_ok=True)
    save_path = os.path.join(output_folder, f"processed_output_{timestamp}.xlsx")
    df_new.to_excel(save_path, index=False)

    messagebox.showinfo("finished", f"处理完成！文件已保存到：\n{save_path}")

    # -------plot---------
    # plot overall data
    plt.figure(figsize=(12, 6))
    plt.plot(df_new["time [s]"], df_new["H2O [ppm]"], linewidth=1)
    plt.xlabel("Time [s]")
    plt.ylabel("Measurement")
    plt.xlim(left=0)
    plt.ylim(bottom=0)
    plt.title("Measurement vs Time")
    plt.grid(True)
    svg_path = os.path.join(output_folder, "overall_plot.svg")
    plt.savefig(svg_path, format="svg")

    # -------plot cut data----------
    plt.figure(figsize=(12, 6))
    # 曲线
    plt.plot(x, y, label="Cut Curve", linewidth=1)

    # 基线
    plt.plot(x, baseline, label="Baseline", linestyle="--", color="red",linewidth=1)

    # 填充面积（只填充 y > baseline 的部分）
    plt.fill_between(x, y, baseline, where=(y > baseline), alpha=0.3, color="orange", zorder=1)

    plt.xlim(left=0)
    plt.ylim(bottom=0)
    plt.xlabel("Time [s]")
    plt.ylabel("H2O [ppm]")
    plt.title("Cut Curve with Baseline and Area")
    plt.grid(True)
    plt.legend()

    cut_svg_path = os.path.join(output_folder, "cut_plot.svg")
    plt.savefig(cut_svg_path, format="svg")

    #plt.show()

# ---------------- GUI ----------------

root = tk.Tk()
root.title("python GUI for H2O sensor data processing")
root.geometry("350x180")

# build label and entry for start time
label_start = tk.Label(root, text="Start time (HH:MM:SS):")
label_start.pack(pady=5)
entry_start = tk.Entry(root, width=20)
entry_start.pack()

# build label and entry for end time
label_end = tk.Label(root, text="End time (HH:MM:SS):")
label_end.pack(pady=5)
entry_end = tk.Entry(root, width=20)
entry_end.pack()

# build run button
btn_run = tk.Button(root, text="Run", command=run_processing, width=15)
btn_run.pack(pady=15)

root.mainloop()
