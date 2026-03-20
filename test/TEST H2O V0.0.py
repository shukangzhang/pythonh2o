import tkinter as tk
from tkinter import simpledialog, filedialog, messagebox
import pandas as pd
import os
import matplotlib.pyplot as plt

file_path = filedialog.askopenfilename(
    title="choose a CSV file",
    filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )

root = tk.Tk()
root.withdraw()

start_time = simpledialog.askstring("输入开始时间", "请输入开始时间（格式：HH:MM:SS）")
end_time   = simpledialog.askstring("输入结束时间", "请输入结束时间（格式：HH:MM:SS）")
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

col1 = df.iloc[:, 0]   # 第一列
col2 = df.iloc[:, 1]   # 第二列
col3 = df.iloc[:, 2]   # 第三列

col4 = pd.to_timedelta(col2.str.replace(",", ".")) # 将第二列转换为 timedelta，先替换逗号为点 

# 构建新 df
df_new = pd.DataFrame({
    "time [s]": df["time [s]"],
    "H2O [ppm]": df["H2O [ppm]"],
})

df["time [s]"] = col4   # 再写入 timedelta
#df.columns.values[4] = "time [s]" # 重命名第五列

# calculate time difference in seconds
t0 = df["time [s]"].iloc[0]
df["time [s]"] = (df["time [s]"] - t0).dt.total_seconds()

# check col3, clear errors, and convert to numeric
df["H2O [ppm]"] = (
    col3.replace("RegexOERROR", pd.NA)   # 替换错误值
        .ffill()                            # 用上一行填补
        .str.replace(",", ".")              # 把逗号换成点
    )

# 转成真正的 float
df["H2O [ppm]"] = pd.to_numeric(df["H2O [ppm]"])

# 找到 >= 输入时间的第一个 index
start_idx = df.index[col4 >= t_start][0]
end_idx   = df.index[col4 >= t_end][0]
df_cut = df.loc[start_idx:end_idx]

# 在原 DataFrame 中添加新列，默认值为 NA
df["cut_time [s]"] = pd.NA
df["cut_H2O [ppm]"] = pd.NA
df.loc[start_idx:end_idx, "cut_time [s]"] = df.loc[start_idx:end_idx, "time [s]"]
df.loc[start_idx:end_idx, "cut_H2O [ppm]"] = df.loc[start_idx:end_idx, "H2O [ppm]"]

df.loc[start_idx:end_idx, "cut_H2O [ppm]"] = df.loc[start_idx:end_idx, df.columns[2]]

# 导出 CSV
save_dir = os.path.dirname(file_path)
save_path = os.path.join(save_dir, "processed_output.csv")
df.to_csv(save_path, index=False)

messagebox.showinfo("finished", f"处理完成！文件已保存到：\n{save_path}")

# -------plot---------
# plot overall data
plt.figure(figsize=(12, 6))
plt.plot(df["time [s]"], df["H2O [ppm]"], linewidth=1)
plt.xlabel("Time [s]")
plt.ylabel("Measurement")
plt.title("Measurement vs Time")
plt.grid(True)
svg_path = os.path.join(save_dir, "overall_plot.svg")
plt.savefig(svg_path, format="svg")

# plot cut data
plt.figure(figsize=(12, 6))
plt.plot(df_cut["time [s]"], df_cut["H2O [ppm]"], color="red", linewidth=1.2)
plt.xlabel("Time [s]")
plt.ylabel("H2O [ppm]")
plt.title("Cut Measurement vs Time")
plt.grid(True)

cut_svg_path = os.path.join(save_dir, "cut_plot.svg")
plt.savefig(cut_svg_path, format="svg")

plt.show()
