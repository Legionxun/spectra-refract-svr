# Model_Comparator.py
import os, logging, traceback, csv, json, math, sys, queue
import tkinter as tk
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tkinter import ttk, messagebox, filedialog, scrolledtext
from threading import Thread, Lock
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from core.utils import get_app_root
sys.path.append(get_app_root())
os.environ["OMP_NUM_THREADS"] = "1"  # 解决KMeans内存泄漏
os.environ["LOKY_MAX_CPU_COUNT"] = "16"  # 根据物理核心数设置

from core.config import CONFIG
from core.predictor import RefractiveIndexPredictor

plt.rc("font", family='Microsoft YaHei')
plt.rcParams['axes.unicode_minus'] = False


class BufferedTextRedirector:
    """带缓冲的文本重定向器，减少GUI更新频率"""
    def __init__(self, widget, tag="", buffer_size=20):
        self.widget = widget
        self.tag = tag
        self.buffer = []
        self.buffer_size = buffer_size
        self.lock = Lock()

    def write(self, text):
        with self.lock:
            self.buffer.append(text)
            # 当缓冲区达到指定大小或包含换行符时，刷新到GUI
            if len(self.buffer) >= self.buffer_size or '\n' in text:
                self._flush_buffer()

    def _flush_buffer(self):
        if self.buffer:
            text_to_insert = ''.join(self.buffer)
            self.widget.configure(state='normal')
            self.widget.insert('end', text_to_insert, (self.tag,))
            self.widget.configure(state='disabled')
            self.widget.see('end')
            self.buffer = []

    def flush(self):
        with self.lock:
            self._flush_buffer()


class TkinterProgressBar(ttk.Frame):
    """仿照 AnimatedProgressBar 样式的 Tkinter 进度条，带百分比显示"""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        # 创建进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self,
            variable=self.progress_var,
            maximum=100,
            length=300
        )
        self.progress_bar.pack(fill=tk.X, expand=True, pady=5)

        # 创建一个框架来包含百分比和文本标签
        self.text_frame = ttk.Frame(self)
        self.text_frame.pack(fill=tk.X, pady=5)

        # 进度百分比标签（只显示百分比）
        self.percent_label = tk.Label(self.text_frame, text="0.0%", font=("Microsoft YaHei", 9, "bold"))
        self.percent_label.pack(side=tk.LEFT)

        # 进度文本标签（只显示文本）
        self.progress_label = tk.Label(self.text_frame, text="准备评估模型...")
        self.progress_label.pack(side=tk.LEFT, padx=(10, 0))

    def set_progress(self, value, text=""):
        """设置进度值和文本"""
        self.progress_var.set(value)
        # 更新百分比显示
        self.percent_label.config(text=f"{value:.1f}%")
        # 更新文本显示
        if text:
            self.progress_label.config(text=text)
        self.update_idletasks()


class StyledButton(tk.Canvas):
    """带有悬停、按压效果和圆角的按钮"""
    def __init__(self, parent, text="", command=None, width=120, height=35,
                 bg_color="#4a90e2", hover_color="#357abd", pressed_color="#2c5f96",
                 text_color="white", font=("Microsoft YaHei", 10, "bold"), corner_radius=15):
        super().__init__(parent, width=width, height=height, highlightthickness=0, bd=0)

        self.width = width
        self.height = height
        self.corner_radius = corner_radius
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.pressed_color = pressed_color
        self.text_color = text_color
        self.font = font
        self.command = command
        self.text = text
        self.state = "normal"
        self.enabled = True

        # 创建按钮元素
        self.button_bg = self.create_rounded_rectangle(0, 0, width, height, corner_radius, fill=bg_color, outline="")
        self.button_text = self.create_text(width/2, height/2, text=text, fill=text_color, font=font)

        # 绑定事件
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_release)

        # 绑定文本元素的事件到整个Canvas
        self.tag_bind(self.button_text, "<Enter>", self.on_enter)
        self.tag_bind(self.button_text, "<Leave>", self.on_leave)
        self.tag_bind(self.button_text, "<Button-1>", self.on_press)
        self.tag_bind(self.button_text, "<ButtonRelease-1>", self.on_release)

    def create_rounded_rectangle(self, x1, y1, x2, y2, radius, **kwargs):
        """创建圆角矩形"""
        points = [
            x1+radius, y1,
            x2-radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1+radius,
            x1, y1
        ]

        return self.create_polygon(points, smooth=True, **kwargs)

    def on_enter(self, event):
        """鼠标悬停事件"""
        if self.state == "normal" and self.enabled:
            self.itemconfig(self.button_bg, fill=self.hover_color)

    def on_leave(self, event):
        """鼠标离开事件"""
        if self.state == "normal" and self.enabled:
            self.itemconfig(self.button_bg, fill=self.bg_color)

    def on_press(self, event):
        """鼠标按下事件"""
        if self.enabled:
            self.state = "pressed"
            self.itemconfig(self.button_bg, fill=self.pressed_color)

    def on_release(self, event):
        """鼠标释放事件"""
        if self.enabled:
            self.state = "normal"
            self.itemconfig(self.button_bg, fill=self.bg_color)
            if self.command:
                self.command()

    def config(self, **kwargs):
        """配置按钮属性"""
        if "state" in kwargs:
            state = kwargs["state"]
            if state == tk.DISABLED:
                self.enabled = False
                self.itemconfig(self.button_bg, fill="#bdc3c7")
                self.itemconfig(self.button_text, fill="#ecf0f1")
            elif state == tk.NORMAL:
                self.enabled = True
                self.itemconfig(self.button_bg, fill=self.bg_color)
                self.itemconfig(self.button_text, fill=self.text_color)
        if "text" in kwargs:
            self.itemconfig(self.button_text, text=kwargs["text"])
            self.text = kwargs["text"]


class ModelEvaluationWorker:
    """模型评估工作线程"""
    def __init__(self, app, models_list, template_images, progress_callback=None, result_callback=None, temp_file_path=None):
        self.logger = logging.getLogger("ModelEvaluationWorker")
        self.app = app
        self.models_list = models_list
        self.template_images = template_images
        self.progress_callback = progress_callback
        self.result_callback = result_callback
        self.temp_file_path = temp_file_path
        self.stop_flag = False
        # 模型缓存字典
        self.model_cache = {}

    def stop_evaluation(self):
        """停止评估"""
        self.stop_flag = True

    def get_cached_predictor(self, model_path):
        """获取缓存的预测器，如果不存在则创建新的"""
        if model_path not in self.model_cache:
            self.model_cache[model_path] = RefractiveIndexPredictor(model_path)
        return self.model_cache[model_path]

    def close_all_predictors(self):
        """关闭所有缓存的预测器"""
        for predictor in self.model_cache.values():
            try:
                predictor.close()
            except:
                pass
        self.model_cache.clear()

    def send_message_to_temp_file(self, data):
        """通过临时文件发送消息到主应用"""
        try:
            if self.temp_file_path:
                # 读取现有内容
                existing_data = []
                if os.path.exists(self.temp_file_path):
                    with open(self.temp_file_path, 'r', encoding='utf-8') as f:
                        try:
                            existing_data = json.load(f)
                            if not isinstance(existing_data, list):
                                existing_data = []
                        except json.JSONDecodeError:
                            existing_data = []

                # 添加新数据
                existing_data.append(data)

                # 写入文件
                with open(self.temp_file_path, 'w', encoding='utf-8') as f:
                    json.dump(existing_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            pass

    def run_evaluation(self, force_recalculate=False):
        """运行模型评估"""
        try:
            # 发送开始消息
            self.send_message_to_temp_file({
                "type": "start",
                "message": "模型比较开始"
            })

            model_data = []
            total_models = len(self.models_list)

            # 检查是否需要停止
            if self.stop_flag:
                if self.result_callback:
                    self.result_callback("evaluation_stopped", None)
                return

            # 检查是否已存在模型比较结果文件且不需要强制重新计算
            comparison_csv_path = os.path.join(CONFIG["history_dir"], "model_comparison_results.csv")
            if not force_recalculate and os.path.exists(comparison_csv_path):
                self._update_progress(100, "已存在模型比较结果")
                try:
                    # 尝试从已有的CSV文件加载数据
                    df = pd.read_csv(comparison_csv_path)
                    if len(df) >= len(self.models_list):
                        for _, row in df.iterrows():
                            # 检查是否需要停止
                            if self.stop_flag:
                                if self.result_callback:
                                    self.result_callback("evaluation_stopped", None)
                                return

                            model_result = {
                                "name": row["模型名称"],
                                "training_time": row.get("训练时长(s)", 0),
                                "mae": row["MAE"],
                                "rmse": row["RMSE"],
                                "median_ae": row.get("MedAE", 0),
                                "sse": row.get("SSE", 0),
                                "r2": row.get("R²", 0),
                                "accuracy": row.get("准确度(±0.001)(%)", 0),
                                "model_size": row.get("模型大小(MB)", 0)
                            }
                            model_data.append(model_result)
                            if self.result_callback:
                                self.result_callback("model_evaluated", model_result)
                        if self.result_callback:
                            self.result_callback("evaluation_finished", model_data)
                        return
                except Exception as e:
                    print(f"加载现有评估数据失败: {str(e)}")

            # 用于存储所有模型的预测结果
            actual_values = []
            # 首先解析所有图片的实际值（只做一次）
            for img_path in self.template_images:
                # 检查是否需要停止
                if self.stop_flag:
                    if self.result_callback:
                        self.result_callback("evaluation_stopped", None)
                    return

                # 从文件名中提取实际折射率值
                filename = os.path.basename(img_path)
                try:
                    name_str = filename.split('_')[1]
                    actual_rn = float(name_str.split('.')[0]) + float(name_str.split('.')[1]) * round(math.pow(0.1, len(name_str.split('.')[1])), len(name_str.split('.')[1]))
                    actual_values.append(actual_rn)
                except Exception as e:
                    print(f"解析文件名失败: {filename}, 错误: {str(e)}")
                    actual_values.append(0)
            actual_values = np.array(actual_values)

            # 定义准确度计算的±
            ACCURACY_THRESHOLD = 0.001

            # 计算总的进度单位
            total_units = total_models * (2 + len(self.template_images))  # 2表示加载和计算步骤，每个模板图像一个步骤
            completed_units = 0

            for i, model_info in enumerate(self.models_list):
                # 检查是否需要停止
                if self.stop_flag:
                    if self.result_callback:
                        self.result_callback("evaluation_stopped", None)
                    return

                # 更新进度
                progress = int((completed_units / total_units) * 100)
                self._update_progress(progress, f"正在加载模型: {model_info['name']} ({i + 1}/{total_models})")

                # 加载模型性能数据
                metrics_path = os.path.join(model_info["path"], "metrics.json")
                metrics = {}
                # 如果存在`metrics.json`文件，先加载它
                if os.path.exists(metrics_path):
                    try:
                        with open(metrics_path, 'r') as f:
                            metrics = json.load(f)
                    except Exception as e:
                        print(f"加载模型 {model_info['name']} 的指标失败: {str(e)}")

                completed_units += 1
                progress = int((completed_units / total_units) * 100)
                self._update_progress(progress, f"加载模型 {model_info['name']} 完成")

                # 使用template图片评估模型
                predictor = None
                try:
                    # 检查是否需要停止
                    if self.stop_flag:
                        if self.result_callback:
                            self.result_callback("evaluation_stopped", None)
                        return

                    # 使用缓存的预测器
                    predictor = self.get_cached_predictor(model_info["path"])
                    # 存储该模型对所有图片的预测结果
                    predictions = []
                    # 对每张图片进行预测
                    for j, img_path in enumerate(self.template_images):
                        # 检查是否需要停止
                        if self.stop_flag:
                            if self.result_callback:
                                self.result_callback("evaluation_stopped", None)
                            return

                        # 更新进度
                        completed_units += 1
                        progress = int((completed_units / total_units) * 100)
                        self._update_progress(progress,
                                              f"模型 {model_info['name']} 正在预测第 {j + 1}/{len(self.template_images)} 张图片")

                        # 使用模型预测
                        predicted_rn = predictor.predict(img_path)
                        if predicted_rn is not None:
                            predictions.append(predicted_rn)
                        else:
                            predictions.append(actual_values[j] if j < len(actual_values) else 0)
                            print(f"警告: 模型 {model_info['name']} 对 {img_path} 预测失败")

                    # 如果评估被停止，跳出循环
                    if self.stop_flag:
                        if self.result_callback:
                            self.result_callback("evaluation_stopped", None)
                        return

                    # 更新进度
                    completed_units += 1
                    progress = int((completed_units / total_units) * 100)
                    self._update_progress(progress, f"正在计算 {model_info['name']} 的评估指标")

                    # 计算评估指标
                    predictions = np.array(predictions)
                    # 确保数组长度一致
                    if len(predictions) != len(actual_values):
                        # 如果长度不一致，截取较短的长度
                        min_len = min(len(predictions), len(actual_values))
                        predictions = predictions[:min_len]
                        actual_values_subset = actual_values[:min_len]
                        print(f"警告: 预测值和实际值长度不一致，已截取为{min_len}")
                    else:
                        actual_values_subset = actual_values

                    # 计算各种评估指标
                    mae = np.mean(np.abs(predictions - actual_values_subset))  # 平均绝对误差
                    rmse = np.sqrt(np.mean((predictions - actual_values_subset) ** 2))  # 均方根误差
                    median_ae = np.median(np.abs(predictions - actual_values_subset))  # 中位数绝对误差
                    # 计算SSE (残差平方和)
                    sse = np.sum((actual_values_subset - predictions) ** 2)
                    # 计算SST (总平方和)
                    sst = np.sum((actual_values_subset - np.mean(actual_values_subset)) ** 2)
                    # 计算R² (决定系数)
                    r2 = 1 - (sse / sst) if sst != 0 else 0
                    # 计算绝对误差百分比
                    abs_error_percentage = np.abs((predictions - actual_values_subset) / actual_values_subset)
                    # 统计在±内的样本数
                    correct_count = np.sum(abs_error_percentage <= ACCURACY_THRESHOLD)
                    # 计算准确度百分比
                    accuracy = (correct_count / len(actual_values_subset)) * 100
                    # 获取模型文件大小
                    model_file_path = os.path.join(model_info["path"], "models", CONFIG["save_model"])
                    model_size = os.path.getsize(model_file_path) / (1024 * 1024) if os.path.exists(
                        model_file_path) else 0  # MB
                    # 获取训练时长
                    training_time = predictor.training_time

                    # 更新指标
                    metrics["mae"] = float(mae)
                    metrics["rmse"] = float(rmse)
                    metrics["median_ae"] = float(median_ae)
                    metrics["sse"] = float(sse)
                    metrics["r2"] = float(r2)
                    metrics["accuracy"] = float(accuracy)
                    metrics["model_size"] = float(model_size)
                    metrics["training_time"] = float(training_time)

                    # 保存更新后的指标
                    with open(metrics_path, 'w') as f:
                        json.dump(metrics, f, indent=2)

                    # 添加调试信息
                    print(f"模型 {model_info['name']} 评估结果:")
                    print(f"  预测值范围: {np.min(predictions):.4f} - {np.max(predictions):.4f}")
                    print(f"  实际值范围: {np.min(actual_values_subset):.4f} - {np.max(actual_values_subset):.4f}")
                    print(f"  MAE: {mae:.4f}, RMSE: {rmse:.4f}")
                    print(f"  SSE: {sse:.4f}, R²: {r2:.4f}")
                    print(f"  准确度(±0.001): {accuracy:.2f}%")
                    print(f"  训练时长: {training_time:.2f}s")

                    # 发送性能数据到主应用
                    performance_data = {
                        "model_name": model_info["name"],
                        "mae": float(mae),
                        "rmse": float(rmse),
                        "median_ae": float(median_ae),
                        "sse": float(sse),
                        "r2": float(r2),
                        "accuracy": float(accuracy),
                        "model_size": float(model_size),
                        "training_time": float(training_time)
                    }

                    self.send_message_to_temp_file({
                        "type": "model_performance",
                        "data": performance_data
                    })

                except Exception as e:
                    print(f"评估模型 {model_info['name']} 失败: {str(e)}")
                    traceback.print_exc()
                    # 使用默认值或从`metrics.json`中读取的值
                    if "mae" not in metrics:
                        metrics["mae"] = 0
                    if "rmse" not in metrics:
                        metrics["rmse"] = 0
                    if "median_ae" not in metrics:
                        metrics["median_ae"] = 0
                    if "sse" not in metrics:
                        metrics["sse"] = 0
                    if "r2" not in metrics:
                        metrics["r2"] = 0
                    if "accuracy" not in metrics:
                        metrics["accuracy"] = 0
                    if "model_size" not in metrics:
                        metrics["model_size"] = 0
                    if "training_time" not in metrics:
                        metrics["training_time"] = 0
                finally:
                    # 评估完一个模型后立即释放GPU资源
                    if predictor:
                        try:
                            predictor.close()
                            # 从缓存中移除已关闭的预测器
                            if model_info["path"] in self.model_cache:
                                del self.model_cache[model_info["path"]]
                        except Exception as e:
                            print(f"释放模型 {model_info['name']} 的GPU资源时出错: {str(e)}")

                # 保存数据用于绘图
                model_result = {
                    "name": model_info["name"],
                    "training_time": metrics.get("training_time", 0),
                    "mae": metrics.get("mae", 0),
                    "rmse": metrics.get("rmse", 0),
                    "median_ae": metrics.get("median_ae", 0),
                    "sse": metrics.get("sse", 0),
                    "r2": metrics.get("r2", 0),
                    "accuracy": metrics.get("accuracy", 0),
                    "model_size": metrics.get("model_size", 0)
                }
                model_data.append(model_result)

                # 发送单个模型评估完成信号
                if self.result_callback:
                    self.result_callback("model_evaluated", model_result)

            # 如果评估被停止，不发送完成信号
            if self.stop_flag:
                if self.result_callback:
                    self.result_callback("evaluation_stopped", None)
                return

            self._update_progress(100, "评估完成")
            if self.result_callback:
                self.result_callback("evaluation_finished", model_data)

        except Exception as e:
            if not self.stop_flag:
                error_msg = f"模型评估过程中发生错误: {str(e)}"
                print(error_msg)
                traceback.print_exc()
                self.send_message_to_temp_file({
                    "type": "error",
                    "message": error_msg
                })
                if self.result_callback:
                    self.result_callback("error_occurred", error_msg)
        finally:
            # 关闭所有缓存的预测器
            self.close_all_predictors()

    def _update_progress(self, value, text):
        """更新进度"""
        if self.progress_callback:
            self.progress_callback(value, text)


class ModelComparisonApp:
    """基于 tkinter 的模型比较应用"""
    def __init__(self, master, models_list, template_images, temp_file_path):
        self.master = master
        self.models_list = models_list
        self.template_images = template_images
        self.temp_file_path = temp_file_path
        self.model_data = []
        self.worker = None
        self.worker_thread = None

        # 创建输出队列用于异步处理GUI更新
        self.output_queue = queue.Queue()
        self.gui_update_thread = None
        self.gui_update_running = True

        self.master.title("模型性能比较")
        self.master.geometry("1050x600")
        self.master.minsize(800, 400)
        self.master.iconbitmap(CONFIG["icon"])

        # 将窗口居中显示
        self.center_window()

        self.create_widgets()
        self.start_evaluation()

        # 启动GUI更新线程
        self.start_gui_update_thread()

        # 重定向标准输出到带缓冲的文本框
        sys.stdout = BufferedTextRedirector(self.output_text)
        sys.stderr = BufferedTextRedirector(self.output_text, "error")

        # 配置文本标签
        self.output_text.tag_config("error", foreground="red")

    def start_gui_update_thread(self):
        """启动GUI更新线程"""
        self.gui_update_thread = Thread(target=self.process_gui_updates, daemon=True)
        self.gui_update_thread.start()

    def process_gui_updates(self):
        """处理GUI更新的线程函数"""
        while self.gui_update_running:
            try:
                # 从队列中获取更新任务
                func, args = self.output_queue.get(timeout=0.1)
                # 在主线程中执行GUI更新
                self.master.after(0, func, *args)
                self.output_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                pass

    def center_window(self):
        """将窗口居中显示在屏幕中央"""
        # 强制更新窗口以获取准确的尺寸
        self.master.update_idletasks()

        # 获取窗口尺寸
        width = self.master.winfo_width()
        height = self.master.winfo_height()

        # 获取屏幕尺寸
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()

        # 计算居中位置
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        # 设置窗口位置
        self.master.geometry(f"{width}x{height}+{x}+{y}")

    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.master)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 标题
        title_label = tk.Label(main_frame, text="模型性能比较", font=("Microsoft YaHei", 16, "bold"))
        title_label.pack(pady=(0, 10))

        # Notebook 选项卡
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 表格比较选项卡
        self.table_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.table_frame, text="表格比较")
        self.create_table_tab()

        # 图表比较选项卡
        self.plot_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.plot_frame, text="图表比较")
        self.plot_frame.columnconfigure(0, weight=1)
        self.plot_frame.rowconfigure(0, weight=1)

        # 雷达图比较选项卡
        self.radar_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.radar_frame, text="雷达图比较")
        self.radar_frame.columnconfigure(0, weight=1)
        self.radar_frame.rowconfigure(0, weight=1)

        # 综合评分选项卡
        self.score_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.score_frame, text="综合评分")
        self.score_frame.columnconfigure(0, weight=1)
        self.score_frame.rowconfigure(0, weight=1)

        # 输出文本框选项卡
        self.output_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.output_frame, text="系统输出")

        # 创建输出文本框
        output_container = ttk.Frame(self.output_frame)
        output_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.output_text = scrolledtext.ScrolledText(output_container, state='disabled', font=("Consolas", 10))
        self.output_text.pack(fill=tk.BOTH, expand=True)

        # 进度条区域
        self.progress_frame = ttk.Frame(self.table_frame)
        self.progress_frame.pack(fill=tk.X, pady=(10, 5))

        # 创建包含进度条和按钮的容器
        progress_container = ttk.Frame(self.progress_frame)
        progress_container.pack(fill=tk.X, expand=True)

        # 进度条框架
        progress_bar_frame = ttk.Frame(progress_container)
        progress_bar_frame.pack(fill=tk.X, expand=True, side=tk.LEFT)

        # 进度条
        self.progress_bar = TkinterProgressBar(progress_bar_frame)
        self.progress_bar.pack(fill=tk.X)

        # 停止评估按钮
        self.stop_btn = StyledButton(
            progress_container,
            text="停止评估",
            width=100,
            height=35,
            bg_color="#ffc107",
            hover_color="#e0a800",
            pressed_color="#d39e00",
            text_color="#212529",
            font=("Microsoft YaHei", 9, "bold"),
            command=self.stop_evaluation
        )
        self.stop_btn.pack(side=tk.RIGHT, padx=(10, 0))

        # 按钮区域
        self.button_frame = ttk.Frame(self.table_frame)
        self.button_frame.pack(fill=tk.X, pady=(5, 10))

        # 最佳模型标签
        self.best_model_label = tk.Label(
            self.button_frame,
            text="暂无最佳模型推荐",
            font=("Microsoft YaHei", 10, "bold"),
            fg="red"
        )
        self.best_model_label.pack(side=tk.LEFT, padx=(0, 10))

        # 按钮容器
        button_container = ttk.Frame(self.button_frame)
        button_container.pack(side=tk.RIGHT)

        # 使用自定义样式按钮
        self.load_best_btn = StyledButton(
            button_container,
            text="加载最佳模型",
            width=100,
            height=35,
            bg_color="#28a745",
            hover_color="#218838",
            pressed_color="#1e7e34",
            command=self.load_best_model
        )
        self.reevaluate_btn = StyledButton(
            button_container,
            text="重新评估",
            width=100,
            height=35,
            bg_color="#007bff",
            hover_color="#0069d9",
            pressed_color="#0062cc",
            command=self.reevaluate_models
        )
        self.export_btn = StyledButton(
            button_container,
            text="导出比较结果",
            width=100,
            height=35,
            bg_color="#17a2b8",
            hover_color="#138496",
            pressed_color="#117a8b",
            command=self.export_comparison
        )
        self.close_btn = StyledButton(
            button_container,
            text="关闭",
            width=100,
            height=35,
            bg_color="#dc3545",
            hover_color="#c82333",
            pressed_color="#bd2130",
            command=self.close_app
        )

        self.load_best_btn.pack(side=tk.LEFT, padx=5)
        self.reevaluate_btn.pack(side=tk.LEFT, padx=5)
        self.export_btn.pack(side=tk.LEFT, padx=5)
        self.close_btn.pack(side=tk.LEFT, padx=5)

    def create_table_tab(self):
        """创建表格选项卡"""
        # 创建表格框架
        table_container = ttk.Frame(self.table_frame)
        table_container.pack(fill=tk.BOTH, expand=True)

        # 创建表格
        self.tree = ttk.Treeview(
            table_container,
            columns=("模型名称", "训练时长(s)", "MAE", "RMSE", "MedAE", "SSE", "R²", "准确度(±0.001)(%)", "模型大小(MB)"),
            show="headings"
        )

        # 设置列标题
        self.tree.heading("模型名称", text="模型名称")
        self.tree.heading("训练时长(s)", text="训练时长(s)")
        self.tree.heading("MAE", text="MAE")
        self.tree.heading("RMSE", text="RMSE")
        self.tree.heading("MedAE", text="MedAE")
        self.tree.heading("SSE", text="SSE")
        self.tree.heading("R²", text="R²")
        self.tree.heading("准确度(±0.001)(%)", text="准确度(±0.001)(%)")
        self.tree.heading("模型大小(MB)", text="模型大小(MB)")

        # 设置列宽
        self.tree.column("模型名称", width=150)
        self.tree.column("训练时长(s)", width=100)
        self.tree.column("MAE", width=100)
        self.tree.column("RMSE", width=100)
        self.tree.column("MedAE", width=100)
        self.tree.column("SSE", width=100)
        self.tree.column("R²", width=100)
        self.tree.column("准确度(±0.001)(%)", width=120)
        self.tree.column("模型大小(MB)", width=100)

        # 添加滚动条
        v_scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(table_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # 布局
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")

        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)

    def start_evaluation(self, force_recalculate=False):
        """开始评估"""
        if len(self.models_list) < 2:
            messagebox.showinfo("提示", "至少需要两个模型才能进行比较")
            return

        # 检查template文件夹中是否有理论数据图片
        template_dir = os.path.join(CONFIG["base_dir"], "template")
        if not os.path.exists(template_dir):
            messagebox.showwarning("警告", "未找到template文件夹，请先生成理论数据")
            return

        # 查找template文件夹中的图片文件
        template_images = []
        for file in os.listdir(template_dir):
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                template_images.append(os.path.join(template_dir, file))
        if not template_images:
            messagebox.showwarning("警告", "template文件夹中没有找到图片文件，请先生成理论数据")
            return

        # 清空现有数据和表格
        self.model_data.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 创建并启动工作线程
        self.worker = ModelEvaluationWorker(
            self,
            self.models_list,
            template_images,
            progress_callback=self.update_progress,
            result_callback=self.handle_result,
            temp_file_path=self.temp_file_path
        )
        self.worker_thread = Thread(target=lambda: self.worker.run_evaluation(force_recalculate))
        self.worker_thread.start()

        # 启用停止按钮
        self.stop_btn.config(state=tk.NORMAL)

    def update_progress(self, value, text):
        """更新进度 - 通过队列异步更新GUI"""
        def _update_progress_gui(value, text):
            self.progress_bar.set_progress(value, text)
        self.output_queue.put((_update_progress_gui, (value, text)))

    def handle_result(self, event_type, data):
        """处理评估结果 - 通过队列异步更新GUI"""
        def _handle_result_gui(event_type, data):
            if event_type == "model_evaluated":
                self.on_model_evaluated(data)
            elif event_type == "evaluation_finished":
                self.on_evaluation_finished(data)
                # 评估完成后禁用停止按钮
                self.stop_btn.config(state=tk.DISABLED)
                # 发送完成消息
                self.worker.send_message_to_temp_file({
                    "type": "completion",
                    "message": "模型比较完成"
                })
            elif event_type == "evaluation_stopped":
                self.on_evaluation_stopped()
                # 停止后禁用停止按钮
                self.stop_btn.config(state=tk.DISABLED)
                # 发送停止消息
                self.worker.send_message_to_temp_file({
                    "type": "cancelled",
                    "message": "模型比较已取消"
                })
            elif event_type == "error_occurred":
                self.on_error(data)
                # 出错后禁用停止按钮
                self.stop_btn.config(state=tk.DISABLED)
        self.output_queue.put((_handle_result_gui, (event_type, data)))

    def on_model_evaluated(self, model_result):
        """单个模型评估完成"""
        # 添加到模型数据列表
        self.model_data.append(model_result)

        # 在表格中添加一行
        self.tree.insert("", "end", values=(
            model_result["name"],
            f"{model_result['training_time']:.2f}",
            f"{model_result['mae']:.4f}",
            f"{model_result['rmse']:.4f}",
            f"{model_result['median_ae']:.4f}",
            f"{model_result['sse']:.4f}",
            f"{model_result['r2']:.4f}",
            f"{model_result['accuracy']:.2f}",
            f"{model_result['model_size']:.2f}"
        ))

        # 更新最佳模型显示
        self.update_best_model_label()

    def on_evaluation_finished(self, model_data):
        """评估完成"""
        # 生成图表
        self.generate_charts()
        self.generate_score_chart()

        self.progress_frame.lift()
        self.button_frame.lift()

    def on_evaluation_stopped(self):
        """评估停止"""
        self.progress_bar.set_progress(0, "评估已停止")
        messagebox.showinfo("提示", "模型评估已停止")

    def on_error(self, error_msg):
        """处理错误"""
        self.progress_bar.set_progress(0, f"评估出错: {error_msg}")
        messagebox.showerror("错误", f"模型评估过程中发生错误: {error_msg}")

    def stop_evaluation(self):
        """停止评估"""
        if self.worker:
            self.worker.stop_evaluation()
            self.progress_bar.set_progress(0, "正在停止评估...")
            # 禁用停止按钮，避免重复点击
            self.stop_btn.config(state=tk.DISABLED)

    def populate_table(self):
        """填充表格"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        for data in self.model_data:
            self.tree.insert("", "end", values=(
                data["name"],
                f"{data['training_time']:.2f}",
                f"{data['mae']:.4f}",
                f"{data['rmse']:.4f}",
                f"{data['median_ae']:.4f}",
                f"{data['sse']:.4f}",
                f"{data['r2']:.4f}",
                f"{data['accuracy']:.2f}",
                f"{data['model_size']:.2f}"
            ))

    def generate_charts(self):
        """生成图表"""
        if not self.model_data:
            return

        try:
            # 清空图表区域
            for widget in self.plot_frame.winfo_children():
                widget.destroy()
            for widget in self.radar_frame.winfo_children():
                widget.destroy()

            # 为图表比较选项卡添加滚动和缩放功能
            # 创建主容器框架
            plot_main_container = ttk.Frame(self.plot_frame)
            plot_main_container.pack(fill=tk.BOTH, expand=True)

            # 创建画布和滚动条
            plot_canvas = tk.Canvas(plot_main_container)
            plot_scrollbar_y = ttk.Scrollbar(plot_main_container, orient="vertical", command=plot_canvas.yview)
            # 横向滚动条放在选项卡框架中，使其贯穿整个底部宽度
            plot_scrollbar_x = ttk.Scrollbar(self.plot_frame, orient="horizontal", command=plot_canvas.xview)

            # 创建可滚动框架
            plot_scrollable_frame = ttk.Frame(plot_canvas)
            plot_scrollable_frame.bind(
                "<Configure>",
                lambda e: plot_canvas.configure(
                    scrollregion=plot_canvas.bbox("all")
                )
            )

            plot_canvas.create_window((0, 0), window=plot_scrollable_frame, anchor="nw")
            plot_canvas.configure(yscrollcommand=plot_scrollbar_y.set, xscrollcommand=plot_scrollbar_x.set)

            # 创建图表框架
            fig, axes = plt.subplots(2, 4, figsize=(16, 8))

            # 训练时长比较图
            names = [d["name"] for d in self.model_data]
            training_time_values = [d["training_time"] for d in self.model_data]
            axes[0, 0].bar(names, training_time_values, color='cyan')
            axes[0, 0].set_title('训练时长', fontsize=10)
            axes[0, 0].set_ylabel('时间 (s)', fontsize=9)
            axes[0, 0].tick_params(axis='x', rotation=45, labelsize=8)

            # MAE 比较图
            mae_values = [d["mae"] for d in self.model_data]
            axes[0, 1].bar(names, mae_values, color='skyblue')
            axes[0, 1].set_title('平均绝对误差 (MAE)', fontsize=10)
            axes[0, 1].set_ylabel('MAE', fontsize=9)
            axes[0, 1].tick_params(axis='x', rotation=45, labelsize=8)

            # RMSE 比较图
            rmse_values = [d["rmse"] for d in self.model_data]
            axes[0, 2].bar(names, rmse_values, color='lightcoral')
            axes[0, 2].set_title('均方根误差 (RMSE)', fontsize=10)
            axes[0, 2].set_ylabel('RMSE', fontsize=9)
            axes[0, 2].tick_params(axis='x', rotation=45, labelsize=8)

            # SSE 比较图
            sse_values = [d["sse"] for d in self.model_data]
            axes[0, 3].bar(names, sse_values, color='lightgreen')
            axes[0, 3].set_title('残差平方和 (SSE)', fontsize=10)
            axes[0, 3].set_ylabel('SSE', fontsize=9)
            axes[0, 3].tick_params(axis='x', rotation=45, labelsize=8)

            # 中位数绝对误差比较图
            median_ae_values = [d["median_ae"] for d in self.model_data]
            axes[1, 0].bar(names, median_ae_values, color='gold')
            axes[1, 0].set_title('中位数绝对误差', fontsize=10)
            axes[1, 0].set_ylabel('MedAE', fontsize=9)
            axes[1, 0].tick_params(axis='x', rotation=45, labelsize=8)

            # R² 比较图
            r2_values = [d["r2"] for d in self.model_data]
            axes[1, 1].bar(names, r2_values, color='purple')
            axes[1, 1].set_title('决定系数 (R²)', fontsize=10)
            axes[1, 1].set_ylabel('R²', fontsize=9)
            axes[1, 1].set_ylim(0, 1)  # R²范围通常在0-1之间
            axes[1, 1].tick_params(axis='x', rotation=45, labelsize=8)

            # 模型大小比较图
            model_size_values = [d["model_size"] for d in self.model_data]
            axes[1, 2].bar(names, model_size_values, color='orange')
            axes[1, 2].set_title('模型大小', fontsize=10)
            axes[1, 2].set_ylabel('大小 (MB)', fontsize=9)
            axes[1, 2].tick_params(axis='x', rotation=45, labelsize=8)

            # 准确度比较图
            accuracy_values = [d["accuracy"] for d in self.model_data]
            axes[1, 3].bar(names, accuracy_values, color='violet')
            axes[1, 3].set_title('预测准确度 (%)', fontsize=10)
            axes[1, 3].set_ylabel('准确度(±0.001)(%)', fontsize=9)
            axes[1, 3].set_ylim(0, 100)
            axes[1, 3].tick_params(axis='x', rotation=45, labelsize=8)

            plt.tight_layout()

            # 显示图表并启用交互功能
            canvas = FigureCanvasTkAgg(fig, plot_scrollable_frame)
            canvas.draw()

            # 启用鼠标滚轮缩放和拖拽
            canvas.mpl_connect('scroll_event', lambda event: self.on_scroll(event, fig, canvas, plot_canvas))
            canvas.mpl_connect('button_press_event', self.on_press)
            canvas.mpl_connect('button_release_event', self.on_release)
            canvas.mpl_connect('motion_notify_event', lambda event: self.on_motion(event, fig, canvas, plot_canvas))

            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            # 布局 - 横向滚动条放在选项卡框架底部，使其贯穿整个宽度
            plot_canvas.pack(side="left", fill="both", expand=True)
            plot_scrollbar_y.pack(side="right", fill="y")
            plot_scrollbar_x.pack(side="bottom", fill="x")

            # 保存图表
            plot_path = os.path.join(CONFIG["temp_dir"], "model_comparison.png")
            plt.savefig(plot_path, dpi=100, bbox_inches='tight')
            plt.close()

        except Exception as e:
            print(f"生成模型比较图表失败: {str(e)}")
            traceback.print_exc()

        # 生成雷达图
        try:
            # 为雷达图选项卡添加滚动和缩放功能
            # 创建主容器框架
            radar_main_container = ttk.Frame(self.radar_frame)
            radar_main_container.pack(fill=tk.BOTH, expand=True)

            # 创建画布和滚动条
            radar_canvas = tk.Canvas(radar_main_container)
            radar_scrollbar_y = ttk.Scrollbar(radar_main_container, orient="vertical", command=radar_canvas.yview)
            # 横向滚动条放在选项卡框架中，使其贯穿整个底部宽度
            radar_scrollbar_x = ttk.Scrollbar(self.radar_frame, orient="horizontal", command=radar_canvas.xview)

            # 创建可滚动框架
            radar_scrollable_frame = ttk.Frame(radar_canvas)
            radar_scrollable_frame.bind(
                "<Configure>",
                lambda e: radar_canvas.configure(
                    scrollregion=radar_canvas.bbox("all")
                )
            )

            radar_canvas.create_window((0, 0), window=radar_scrollable_frame, anchor="nw")
            radar_canvas.configure(yscrollcommand=radar_scrollbar_y.set, xscrollcommand=radar_scrollbar_x.set)

            # 创建雷达图
            fig_radar = plt.figure(figsize=(14, 14))
            ax_radar = fig_radar.add_subplot(111, projection='polar')

            # 准备数据
            model_names = [d["name"] for d in self.model_data]
            training_time_values = np.array([d["training_time"] for d in self.model_data])
            mae_values = np.array([d["mae"] for d in self.model_data])
            rmse_values = np.array([d["rmse"] for d in self.model_data])
            sse_values = np.array([d["sse"] for d in self.model_data])
            median_ae_values = np.array([d["median_ae"] for d in self.model_data])
            r2_values = np.array([d["r2"] for d in self.model_data])
            accuracy_values = np.array([d["accuracy"] for d in self.model_data])
            model_size_values = np.array([d["model_size"] for d in self.model_data])

            # 提取标准值
            min_training_time = np.min(training_time_values)
            max_mae = 1 - np.min(mae_values)
            max_rmse = 1 - np.min(rmse_values)
            max_sse = 1 - np.min(sse_values)
            max_median_ae = 1 - np.min(median_ae_values)
            min_model_size = np.min(model_size_values)
            max_accuracy = 100  # 最大准确度是100%

            # 归一化数据
            normalized_training_time = (min_training_time / training_time_values) if min_training_time > 0 else np.ones_like(training_time_values)
            normalized_mae = ((1 - mae_values) / max_mae)
            normalized_rmse = ((1 - rmse_values) / max_rmse)
            normalized_sse = ((1 - sse_values) / max_sse)
            normalized_median_ae = ((1 - median_ae_values) / max_median_ae)
            normalized_r2 = r2_values
            normalized_accuracy = (accuracy_values / max_accuracy)
            normalized_model_size = (min_model_size / model_size_values)

            # 确保值在0-1范围内
            normalized_training_time = np.clip(normalized_training_time, 0, 1)
            normalized_mae = np.clip(normalized_mae, 0, 1)
            normalized_rmse = np.clip(normalized_rmse, 0, 1)
            normalized_sse = np.clip(normalized_sse, 0, 1)
            normalized_median_ae = np.clip(normalized_median_ae, 0, 1)
            normalized_r2 = np.clip(normalized_r2, 0, 1)  # R²
            normalized_accuracy = np.clip(normalized_accuracy, 0, 1)
            normalized_model_size = np.clip(normalized_model_size, 0, 1)

            # 角度设置
            num_metrics = 8
            metric_angles = np.linspace(0, 2 * np.pi, num_metrics, endpoint=False).tolist()
            metric_labels = ['训练时长', 'MAE', 'RMSE', 'SSE', 'MedAE', 'R²', '准确度(±0.001)', '模型大小']

            # 为每个模型绘制雷达图
            colors = plt.cm.Set1(np.linspace(0, 1, len(model_names)))
            for i, (name, color) in enumerate(zip(model_names, colors)):
                # 获取当前模型的各项指标数据
                training_time = normalized_training_time[i]
                mae = normalized_mae[i]
                rmse = normalized_rmse[i]
                sse = normalized_sse[i]
                median_ae = normalized_median_ae[i]
                r2 = normalized_r2[i]
                accuracy = normalized_accuracy[i]
                model_size = normalized_model_size[i]

                # 创建数据点
                data = [training_time, mae, rmse, sse, median_ae, r2, accuracy, model_size]
                data += data[:1]  # 闭合图形，添加第一个点到最后

                # 为每个模型创建角度
                model_angles = metric_angles.copy()
                model_angles += model_angles[:1]  # 闭合角度

                # 绘制
                ax_radar.plot(model_angles, data, linewidth=1.5, label=name, color=color)
                ax_radar.fill(model_angles, data, alpha=0.25, color=color)

            # 添加标签
            ax_radar.set_xticks(metric_angles)
            ax_radar.set_xticklabels(metric_labels, fontsize=9)
            ax_radar.set_ylim(0, 1)
            ax_radar.set_title('模型综合性能雷达图', pad=20, fontsize=12)
            ax_radar.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0), fontsize=8)

            plt.tight_layout()

            # 显示雷达图并启用交互功能
            canvas_radar = FigureCanvasTkAgg(fig_radar, radar_scrollable_frame)
            canvas_radar.draw()

            # 启用鼠标滚轮缩放和拖拽
            canvas_radar.mpl_connect('scroll_event', lambda event: self.on_scroll(event, fig_radar, canvas_radar, radar_canvas))
            canvas_radar.mpl_connect('button_press_event', self.on_press)
            canvas_radar.mpl_connect('button_release_event', self.on_release)
            canvas_radar.mpl_connect('motion_notify_event', lambda event: self.on_motion(event, fig_radar, canvas_radar, radar_canvas))

            canvas_radar.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            # 布局 - 横向滚动条放在选项卡框架底部，使其贯穿整个宽度
            radar_canvas.pack(side="left", fill="both", expand=True)
            radar_scrollbar_y.pack(side="right", fill="y")
            radar_scrollbar_x.pack(side="bottom", fill="x")

            # 保存雷达图
            radar_path = os.path.join(CONFIG["temp_dir"], "model_radar.png")
            plt.savefig(radar_path, bbox_inches='tight', dpi=300)
            plt.close()

            # 自动保存比较结果到CSV文件
            try:
                comparison_csv_path = os.path.join(CONFIG["history_dir"], "model_comparison_results.csv")
                with open(comparison_csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=["模型名称", "训练时长(s)", "MAE", "RMSE", "MedAE", "SSE",
                                                           "R²", "准确度(±0.001)(%)", "模型大小(MB)"])
                    writer.writeheader()
                    for record in self.model_data:
                        writer.writerow({
                            "模型名称": record["name"],
                            "训练时长(s)": record["training_time"],
                            "MAE": record["mae"],
                            "RMSE": record["rmse"],
                            "MedAE": record["median_ae"],
                            "SSE": record["sse"],
                            "R²": record["r2"],
                            "准确度(±0.001)(%)": record["accuracy"],
                            "模型大小(MB)": record["model_size"]
                        })
                print(f"模型比较结果已自动保存至: {comparison_csv_path}")
            except Exception as e:
                print(f"自动保存比较结果失败: {str(e)}")
                traceback.print_exc()

        except Exception as e:
            print(f"生成雷达图失败: {str(e)}")
            traceback.print_exc()

    def generate_score_chart(self):
        """生成综合评分图表"""
        if not self.model_data:
            return

        try:
            # 为综合评分选项卡添加滚动和缩放功能
            # 清空现有内容
            for widget in self.score_frame.winfo_children():
                widget.destroy()

            # 创建主容器框架
            score_main_container = ttk.Frame(self.score_frame)
            score_main_container.pack(fill=tk.BOTH, expand=True)

            # 创建画布和滚动条
            score_canvas = tk.Canvas(score_main_container)
            score_scrollbar_y = ttk.Scrollbar(score_main_container, orient="vertical", command=score_canvas.yview)
            # 横向滚动条放在选项卡框架中，使其贯穿整个底部宽度
            score_scrollbar_x = ttk.Scrollbar(self.score_frame, orient="horizontal", command=score_canvas.xview)

            # 创建可滚动框架
            score_scrollable_frame = ttk.Frame(score_canvas)
            score_scrollable_frame.bind(
                "<Configure>",
                lambda e: score_canvas.configure(
                    scrollregion=score_canvas.bbox("all")
                )
            )

            score_canvas.create_window((0, 0), window=score_scrollable_frame, anchor="nw")
            score_canvas.configure(yscrollcommand=score_scrollbar_y.set, xscrollcommand=score_scrollbar_x.set)

            # 计算综合评分（加权平均）
            scores = []
            model_names = []
            # 获取各项指标的最大值（用于归一化）
            max_training_time = max([d["training_time"] for d in self.model_data]) if any(
                d["training_time"] > 0 for d in self.model_data) else 1
            max_mae = max([d["mae"] for d in self.model_data]) if any(d["mae"] > 0 for d in self.model_data) else 1
            max_rmse = max([d["rmse"] for d in self.model_data]) if any(d["rmse"] > 0 for d in self.model_data) else 1
            max_sse = max([d["sse"] for d in self.model_data]) if any(d["sse"] > 0 for d in self.model_data) else 1
            max_model_size = max([d["model_size"] for d in self.model_data]) if any(
                d["model_size"] > 0 for d in self.model_data) else 1

            for data in self.model_data:
                # 标准化各项指标到0-1范围（越大越好）, 对于误差类指标需要反转
                # 训练时长越小越好，需要反转
                norm_training_time = 1 - (data["training_time"] / max_training_time) if max_training_time > 0 else 1
                norm_mae = 1 - (data["mae"] / max_mae) if max_mae > 0 else 1
                norm_rmse = 1 - (data["rmse"] / max_rmse) if max_rmse > 0 else 1
                norm_sse = 1 - (data["sse"] / max_sse) if max_sse > 0 else 1
                norm_model_size = 1 - (data["model_size"] / max_model_size) if max_model_size > 0 else 1
                norm_r2 = data["r2"]  # R²越大越好
                norm_accuracy = data["accuracy"] / 100
                # 计算加权综合评分（调整权重，增加R²和准确度权重）
                score = (
                                norm_training_time * 0.10 +  # 训练时长权重10%
                                norm_mae * 0.10 +  # MAE权重10%
                                norm_rmse * 0.10 +  # RMSE权重10%
                                norm_sse * 0.10 +  # SSE权重10%
                                norm_r2 * 0.20 +  # R²权重20%
                                norm_model_size * 0.05 +  # 模型大小权重5%
                                norm_accuracy * 0.35  # 准确度权重35%
                        ) * 100  # 转换为百分制
                scores.append(score)
                model_names.append(data["name"])

            # 创建综合评分图表
            fig, ax = plt.subplots(figsize=(14, 10))
            bars = ax.bar(model_names, scores, color=plt.cm.viridis(scores))

            # 突出显示最佳模型
            if model_names and scores:
                best_idx = scores.index(max(scores))
                bars[best_idx].set_color('gold')
                bars[best_idx].set_edgecolor('red')
                bars[best_idx].set_linewidth(2)

                # 在最佳模型上添加特殊标记
                ax.text(bars[best_idx].get_x() + bars[best_idx].get_width() / 2,
                        bars[best_idx].get_height() + 3,
                        '推荐', ha='center', va='bottom',
                        fontweight='bold', color='red', fontsize=10)

            # 添加数值标签
            for bar, score in zip(bars, scores):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                        f'{score:.1f}', ha='center', va='bottom', fontsize=9)

            ax.set_ylabel('综合评分', fontsize=10)
            ax.set_title('模型综合评分比较', fontsize=12)
            ax.set_ylim(0, 100)
            plt.xticks(rotation=45, ha='right', fontsize=9)
            plt.yticks(fontsize=9)
            plt.tight_layout()

            # 显示图表并启用交互功能
            canvas = FigureCanvasTkAgg(fig, score_scrollable_frame)
            canvas.draw()

            # 启用鼠标滚轮缩放和拖拽
            canvas.mpl_connect('scroll_event', lambda event: self.on_scroll(event, fig, canvas, score_canvas))
            canvas.mpl_connect('button_press_event', self.on_press)
            canvas.mpl_connect('button_release_event', self.on_release)
            canvas.mpl_connect('motion_notify_event', lambda event: self.on_motion(event, fig, canvas, score_canvas))

            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            # 布局 - 横向滚动条放在选项卡框架底部，使其贯穿整个宽度
            score_canvas.pack(side="left", fill="both", expand=True)
            score_scrollbar_y.pack(side="right", fill="y")
            score_scrollbar_x.pack(side="bottom", fill="x")

            # 保存图表
            score_path = os.path.join(CONFIG["temp_dir"], "model_scores.png")
            plt.savefig(score_path, dpi=100, bbox_inches='tight')
            plt.close()

        except Exception as e:
            print(f"生成综合评分图表失败: {str(e)}")
            traceback.print_exc()

    # 添加交互功能相关方法
    def on_scroll(self, event, fig, canvas, parent_canvas):
        """处理鼠标滚轮事件实现整个图表区域的缩放"""
        # 计算缩放因子
        scale_factor = 1.1 if event.button == 'up' else 0.9

        # 获取当前画布的宽度和高度
        current_width = parent_canvas.winfo_width()
        current_height = parent_canvas.winfo_height()

        # 计算新的尺寸
        new_width = int(current_width * scale_factor)
        new_height = int(current_height * scale_factor)

        # 限制最小和最大尺寸
        min_size = 200
        max_size = 5000
        new_width = max(min_size, min(max_size, new_width))
        new_height = max(min_size, min(max_size, new_height))

        # 调整父画布的滚动区域
        parent_canvas.configure(scrollregion=(0, 0, new_width, new_height))

        # 调整图表画布的尺寸
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.configure(width=new_width, height=new_height)

        # 重新绘制图表
        canvas.draw()

    def on_press(self, event):
        """处理鼠标按下事件"""
        self.press_event = event
        self._pan_start = (event.x, event.y)

    def on_release(self, event):
        """处理鼠标释放事件"""
        self.press_event = None
        self._pan_start = None

    def on_motion(self, event, fig, canvas, parent_canvas):
        """处理鼠标移动事件实现整个图表区域的拖拽"""
        # 检查是否有鼠标按下事件且是鼠标左键
        if hasattr(self, 'press_event') and self.press_event and self.press_event.button == 1:
            dx = event.x - self._pan_start[0] if hasattr(self, '_pan_start') and self._pan_start else 0
            dy = event.y - self._pan_start[1] if hasattr(self, '_pan_start') and self._pan_start else 0

            # 通过父画布的滚动条实现拖拽
            if hasattr(parent_canvas, 'xview_scroll') and hasattr(parent_canvas, 'yview_scroll'):
                scroll_dx = int(-dx / 2)
                scroll_dy = int(-dy / 2)

                # 执行滚动
                parent_canvas.xview_scroll(scroll_dx, "units")
                parent_canvas.yview_scroll(scroll_dy, "units")

            # 更新拖拽起始点
            self._pan_start = (event.x, event.y)

    def find_best_model(self):
        """找到最佳模型"""
        if not self.model_data:
            return None, 0

        # 获取各项指标的最大值（用于归一化）
        max_training_time = max([d["training_time"] for d in self.model_data]) if any(
            d["training_time"] > 0 for d in self.model_data) else 1
        max_mae = max([d["mae"] for d in self.model_data]) if any(d["mae"] > 0 for d in self.model_data) else 1
        max_rmse = max([d["rmse"] for d in self.model_data]) if any(d["rmse"] > 0 for d in self.model_data) else 1
        max_sse = max([d["sse"] for d in self.model_data]) if any(d["sse"] > 0 for d in self.model_data) else 1
        max_model_size = max([d["model_size"] for d in self.model_data]) if any(
            d["model_size"] > 0 for d in self.model_data) else 1

        scores = []
        model_names = []
        for data in self.model_data:
            # 标准化各项指标到0-1范围（越大越好），对于误差类指标需要反转；训练时长越小越好，需要反转
            norm_training_time = 1 - (data["training_time"] / max_training_time) if max_training_time > 0 else 1
            norm_mae = 1 - (data["mae"] / max_mae) if max_mae > 0 else 1
            norm_rmse = 1 - (data["rmse"] / max_rmse) if max_rmse > 0 else 1
            norm_sse = 1 - (data["sse"] / max_sse) if max_sse > 0 else 1
            norm_model_size = 1 - (data["model_size"] / max_model_size) if max_model_size > 0 else 1

            # R²越大越好
            norm_r2 = data["r2"]

            # 准确度已经是百分比，需要除以100归一化
            norm_accuracy = data["accuracy"] / 100

            # 计算加权综合评分（调整权重，增加R²和准确度权重）
            score = (
                            norm_training_time * 0.05 +  # 训练时长权重5%
                            norm_mae * 0.10 +  # MAE权重10%
                            norm_rmse * 0.10 +  # RMSE权重10%
                            norm_sse * 0.10 +  # SSE权重10%
                            norm_r2 * 0.20 +  # R²权重20%
                            norm_model_size * 0.05 +  # 模型大小权重5%
                            norm_accuracy * 0.40  # 准确度权重40%
                    ) * 100  # 转换为百分制
            scores.append(score)
            model_names.append(data["name"])

        if scores:
            best_idx = scores.index(max(scores))
            return model_names[best_idx], scores[best_idx]
        return None, 0

    def update_best_model_label(self):
        """更新最佳模型标签"""
        best_model_name, best_score = self.find_best_model()
        if best_model_name:
            best_model_text = f"最佳模型: {best_model_name} (综合评分: {best_score:.1f})"
            self.best_model_label.config(text=best_model_text, fg="green")
        else:
            self.best_model_label.config(text="暂无最佳模型推荐", fg="red")

    def load_best_model(self):
        """加载推荐的最佳模型"""
        best_model_name, _ = self.find_best_model()
        if best_model_name:
            try:
                model_path = None

                # 在[models_list](file://F:\Python学习\OptiSVR分光计折射率预测系统\OptiSVR分光计折射率预测系统%20v1.5.0\core\gui.py#L339-L339)中查找对应模型路径
                for model_info in self.models_list:
                    if model_info["name"] == best_model_name:
                        model_path = model_info["path"]
                        break

                if model_path:
                    # 将最佳模型路径写入临时文件
                    result_data = {
                        "action": "load_best_model",
                        "model_path": model_path,
                    }

                    with open(self.temp_file_path, 'w', encoding='utf-8') as f:
                        json.dump([result_data], f, ensure_ascii=False, indent=2)

                    # 退出应用
                    self.master.quit()
                else:
                    messagebox.showerror("错误", "无法找到推荐模型的路径")
            except Exception as e:
                print(f"加载推荐模型失败: {str(e)}")
                messagebox.showerror("错误", f"加载推荐模型失败: {str(e)}")
        else:
            messagebox.showinfo("提示", "暂无推荐模型")

    def export_comparison(self):
        """导出比较结果"""
        if not self.model_data:
            messagebox.showinfo("提示", "没有数据可导出")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx")]
        )

        if save_path:
            try:
                export_data = []
                for record in self.model_data:
                    export_data.append({
                        "模型名称": record["name"],
                        "训练时长(s)": record["training_time"],
                        "MAE": record["mae"],
                        "RMSE": record["rmse"],
                        "MedAE": record["median_ae"],
                        "SSE": record["sse"],
                        "R²": record["r2"],
                        "准确度(±0.001)(%)": record["accuracy"],
                        "模型大小(MB)": record["model_size"]
                    })

                if save_path.endswith('.xlsx'):
                    df = pd.DataFrame(export_data)
                    df.to_excel(save_path, index=False)
                else:
                    with open(save_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=["模型名称", "训练时长(s)", "MAE", "RMSE", "MedAE", "SSE",
                                                               "R²", "准确度(±0.001)(%)", "模型大小(MB)"])
                        writer.writeheader()
                        writer.writerows(export_data)
                messagebox.showinfo("成功", f"比较结果已导出至:\n{save_path}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {str(e)}")

    def reevaluate_models(self):
        """重新评估所有模型"""
        self.start_evaluation(force_recalculate=True)

    def close_app(self):
        """关闭应用"""
        self.gui_update_running = False

        result_data = {
            "action": "close"
        }

        # 读取现有内容
        existing_data = []
        if os.path.exists(self.temp_file_path):
            with open(self.temp_file_path, 'r', encoding='utf-8') as f:
                try:
                    existing_data = json.load(f)
                    if not isinstance(existing_data, list):
                        existing_data = []
                except json.JSONDecodeError:
                    existing_data = []

        # 添加新数据
        existing_data.append(result_data)

        # 写入文件
        with open(self.temp_file_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)

        self.master.quit()
        self.master.destroy()


def main():
    """主函数"""
    temp_file_path = sys.argv[1]

    # 从临时文件读取配置
    try:
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        models_list = config_data.get("models_list", [])
        template_images = config_data.get("template_images", [])

        # 创建 Tkinter 应用
        root = tk.Tk()
        app = ModelComparisonApp(root, models_list, template_images, temp_file_path)

        # 发送初始化完成消息
        init_message = [{
            "type": "start",
            "message": "模型比较应用初始化完成"
        }]
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            json.dump(init_message, f, ensure_ascii=False, indent=2)

        root.mainloop()

    except Exception as e:
        print(f"启动模型比较应用失败: {str(e)}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
