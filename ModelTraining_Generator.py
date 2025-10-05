# ModelTraining_Generator.py
import os, sys, json, logging, shutil, threading, argparse
import tkinter as tk
import tensorflow as tf
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime

from core.utils import get_app_root
sys.path.append(get_app_root())

os.environ["OMP_NUM_THREADS"] = "1"  # 解决KMeans内存泄漏
os.environ["LOKY_MAX_CPU_COUNT"] = "16"  # 根据物理核心数设置
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

from core.model_trainer import ModelTrainer
from core.config import CONFIG, TUNING_CONFIG


class TextRedirector:
    """重定向到文本框"""
    def __init__(self, widget, tag=""):
        self.widget = widget
        self.tag = tag

    def write(self, text):
        self.widget.configure(state='normal')
        self.widget.insert('end', text, (self.tag,))
        self.widget.configure(state='disabled')
        self.widget.see('end')

    def flush(self):
        pass


class AnimatedProgressBar(tk.Canvas):
    """进度条"""
    def __init__(self, parent, width=300, height=20):
        super().__init__(parent, width=width, height=height, highlightthickness=0)
        self.width = width
        self.height = height
        self.value = 0
        self.max_value = 100
        self.text_visible = True
        self.setup_ui()

    def setup_ui(self):
        # 创建进度条背景
        self.create_rectangle(0, 0, self.width, self.height, fill="#e0e0e0", outline="#c0c0c0")

        # 创建进度条前景
        self.progress_rect = self.create_rectangle(0, 0, 0, self.height, fill="#4a90e2", outline="#4a90e2")

        # 创建文本
        self.text = self.create_text(self.width/2, self.height/2, text="0%", fill="black", font=("Arial", 8))

    def setRange(self, min_val, max_val):
        self.max_value = max_val

    def setValue(self, value):
        self.value = max(0, min(value, self.max_value))
        self.update_progress()

    def setTextVisible(self, visible):
        self.text_visible = visible
        if not visible:
            self.itemconfig(self.text, text="")

    def update_progress(self):
        # 更新进度条
        progress_width = (self.value / self.max_value) * self.width if self.max_value > 0 else 0
        self.coords(self.progress_rect, 0, 0, progress_width, self.height)

        # 更新文本
        if self.text_visible:
            percentage = int((self.value / self.max_value) * 100) if self.max_value > 0 else 0
            self.itemconfig(self.text, text=f"{percentage}%")


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


class OptimizationMethodDialog:
    """基于 tkinter 的优化方法选择对话框"""
    def __init__(self, parent, user_role=None):
        self.parent = parent
        self.user_role = user_role
        self.root = tk.Toplevel(parent.root)
        self.center_window()
        self.root.title("选择训练参数")
        self.root.resizable(False, False)
        self.root.iconbitmap(CONFIG["icon"])
        self.root.transient(parent.root)
        self.root.grab_set()
        self.result = None

        # 默认方法
        self.optimization_method = "hybrid"
        self.clustering_method = "kmeans"

        self.setup_ui()

    def center_window(self):
        """将窗口居中显示"""
        self.root.withdraw()
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.root.winfo_screenheight() // 2) - (400 // 2)
        self.root.geometry(f"500x400+{x}+{y}")
        self.root.deiconify()

    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 优化方法选择组
        optimization_group = ttk.LabelFrame(main_frame, text="超参数优化方法:", padding="10")
        optimization_group.pack(fill=tk.X, pady=(0, 10))

        # 优化方法选择
        self.optimization_var = tk.StringVar()

        # 根据用户角色设置可选项
        if self.user_role and self.user_role.get("value") == "basic":
            # 普通用户只能使用optuna优化
            optimization_options = ["Optuna优化 (默认)"]
            self.optimization_var.set("Optuna优化 (默认)")
            self.optimization_combo_state = "disabled"
        else:
            # 高级用户和管理员可以使用所有选项
            optimization_options = [
                "混合优化 (贝叶斯优化 + Optuna) - 推荐",
                "贝叶斯优化",
                "Optuna优化"
            ]
            optimization_method = TUNING_CONFIG.get("optimization_method", "hybrid")
            if optimization_method == "bayesian":
                self.optimization_var.set("贝叶斯优化")
            elif optimization_method == "optuna":
                self.optimization_var.set("Optuna优化")
            else:
                self.optimization_var.set("混合优化 (贝叶斯优化 + Optuna) - 推荐")
            self.optimization_combo_state = "normal"

        self.optimization_combo = ttk.Combobox(
            optimization_group,
            textvariable=self.optimization_var,
            values=optimization_options,
            state=self.optimization_combo_state
        )
        self.optimization_combo.pack(fill=tk.X, pady=(0, 10))

        # 说明文本
        optimization_info = ttk.Label(
            optimization_group,
            text="混合优化结合了贝叶斯优化的全局搜索能力和Optuna的局部优化能力，\n通常能获得更好的优化效果。",
            wraplength=450,
        )
        optimization_info.pack(fill=tk.X)

        # 聚类方法选择组
        clustering_group = ttk.LabelFrame(main_frame, text="聚类方法:", padding="10")
        clustering_group.pack(fill=tk.X, pady=(0, 10))

        # 聚类方法选择
        self.clustering_var = tk.StringVar()

        # 根据用户角色设置可选项
        if self.user_role and self.user_role.get("value") == "basic":
            # 普通用户只能使用kmeans聚类
            self.kmeans_radio = ttk.Radiobutton(
                clustering_group,
                text="K-Means聚类 (默认)",
                variable=self.clustering_var,
                value="K-Means聚类 (默认)"
            )
            self.som_radio = ttk.Radiobutton(
                clustering_group,
                text="SOM神经网络聚类",
                variable=self.clustering_var,
                value="SOM神经网络聚类",
                state="disabled"
            )
            self.clustering_var.set("K-Means聚类 (默认)")
        else:
            # 高级用户和管理员可以使用所有选项
            self.kmeans_radio = ttk.Radiobutton(
                clustering_group,
                text="K-Means聚类 (默认)",
                variable=self.clustering_var,
                value="K-Means聚类 (默认)"
            )
            self.som_radio = ttk.Radiobutton(
                clustering_group,
                text="SOM神经网络聚类",
                variable=self.clustering_var,
                value="SOM神经网络聚类"
            )

            clustering_method = TUNING_CONFIG.get("clustering_method", "kmeans")
            if clustering_method == "som":
                self.clustering_var.set("SOM神经网络聚类")
            else:
                self.clustering_var.set("K-Means聚类 (默认)")

        self.kmeans_radio.pack(anchor=tk.W)
        self.som_radio.pack(anchor=tk.W, pady=(5, 10))

        # SOM说明文本
        som_info = ttk.Label(
            clustering_group,
            text="SOM(自组织映射)是一种无监督神经网络聚类方法，\n能够更好地发现数据中的非线性结构，但训练时间较长。",
            wraplength=450,
        )
        som_info.pack(fill=tk.X)

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        # 使用自定义样式按钮
        self.cancel_button = StyledButton(
            button_frame,
            text="取消",
            width=80,
            height=30,
            bg_color="#dc3545",
            hover_color="#c82333",
            pressed_color="#bd2130",
            command=self.on_cancel
        )
        self.ok_button = StyledButton(
            button_frame,
            text="确定",
            width=80,
            height=30,
            bg_color="#28a745",
            hover_color="#218838",
            pressed_color="#1e7e34",
            command=self.on_ok
        )

        self.cancel_button.pack(side=tk.RIGHT, padx=(5, 0))
        self.ok_button.pack(side=tk.RIGHT)

    def on_ok(self):
        self.result = "ok"
        self.root.destroy()

    def on_cancel(self):
        self.result = "cancel"
        self.root.destroy()

    def show(self):
        self.root.wait_window()
        return self.result == "ok"

    def get_selected_methods(self):
        """获取选择的优化方法和聚类方法"""
        # 根据用户角色确定实际使用的方法
        if self.user_role and self.user_role.get("value") == "basic":
            # 普通用户固定使用optuna+kmeans
            optimization_method = "optuna"
            clustering_method = "kmeans"
        else:
            # 高级用户和管理员使用选择的选项
            opt_text = self.optimization_var.get()
            if "混合优化" in opt_text:
                optimization_method = "hybrid"
            elif "贝叶斯优化" in opt_text:
                optimization_method = "bayesian"
            elif "Optuna优化" in opt_text:
                optimization_method = "optuna"
            else:
                optimization_method = "hybrid"

            clustering_method = "som" if self.clustering_var.get() == "SOM神经网络聚类" else "kmeans"

        return optimization_method, clustering_method


class TrainingApp:
    """训练主应用"""
    def __init__(self, config_file=None):
        self.config_file = config_file
        self.root = tk.Tk()

        # 居中显示主窗口
        self.center_main_window()
        self.root.title("OptiSVR分光计折射率预测系统 · 模型训练器")
        self.root.iconbitmap(CONFIG["icon"])

        # 初始化变量
        self.tuning_config = TUNING_CONFIG.copy()
        self.model_dir = None
        self.stop_training_flag = False
        self.training_in_progress = False
        self.user_role = None  # 添加用户角色属性
        self.current_user_id = None  # 添加用户ID属性
        self.current_username = None  # 添加用户名属性

        # 设置日志
        self.logger = logging.getLogger("TrainingApp")
        self.logger.setLevel(logging.INFO)

        # 如果提供了配置文件，加载配置
        if self.config_file and os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    user_info = config.get("user_info", {})
                    self.user_role = config.get("user_role")  # 正确保存用户角色到实例变量
                    self.current_user_id = user_info.get("user_id")
                    self.current_username = user_info.get("username")
                    self.user_role = user_info.get("user_role")  # 正确保存用户角色到实例变量
                    self.tuning_config = config.get("tuning_config", TUNING_CONFIG)
            except Exception as e:
                self.logger.error(f"加载配置文件时出错: {e}")
        else:
            self.user_role = {"value": "basic", "label": "普通用户"}

        self.setup_ui()

        # 添加窗口关闭事件处理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 重定向标准输出
        sys.stdout = TextRedirector(self.output_text)
        sys.stderr = TextRedirector(self.output_text, "error")

        # 配置文本标签
        self.output_text.tag_config("error", foreground="red")

        # 创建临时文件路径
        self.temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
        self.temp_file = os.path.join(self.temp_dir, "training_status.json")

    def center_main_window(self):
        """将主窗口居中显示"""
        self.root.withdraw()
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (725 // 2)
        y = (self.root.winfo_screenheight() // 2) - (900 // 2)
        self.root.geometry(f"725x900+{x}+{y}")
        self.root.resizable(False, False)
        self.root.deiconify()

    def setup_ui(self):
        """设置主界面"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(main_frame, text="OptiSVR分光计折射率预测系统 · 模型训练器", font=("Microsoft YaHei", 16, "bold"))
        title_label.pack(pady=(0, 20))

        # 控制按钮框架
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 20))

        # 使用自定义样式按钮
        self.start_button = StyledButton(
            control_frame,
            text="开始训练",
            width=100,
            height=35,
            command=self.start_training
        )
        self.stop_button = StyledButton(
            control_frame,
            text="停止训练",
            width=100,
            height=35,
            bg_color="#dc3545",
            hover_color="#c82333",
            pressed_color="#bd2130",
            command=self.stop_training
        )
        self.stop_button.config(state=tk.DISABLED)

        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))

        # 阶段标签
        self.phase_label = ttk.Label(main_frame, text="准备训练...", anchor=tk.CENTER, font=("Microsoft YaHei", 12))
        self.phase_label.pack(fill=tk.X, pady=(10, 5))

        # 总体进度条
        total_progress_frame = ttk.Frame(main_frame)
        total_progress_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(total_progress_frame, text="总体进度:",font=("Microsoft YaHei", 10)).pack(anchor=tk.W)
        self.total_progress_bar = AnimatedProgressBar(total_progress_frame, width=700)
        self.total_progress_bar.pack(fill=tk.X, pady=(2, 0))
        self.total_progress_bar.setRange(0, 100)
        self.total_progress_bar.setValue(0)
        self.total_progress_bar.setTextVisible(True)

        # 当前阶段进度标签
        current_phase_frame = ttk.Frame(main_frame)
        current_phase_frame.pack(fill=tk.X, pady=(10, 5))

        ttk.Label(current_phase_frame, text="当前阶段进度:",font=("Microsoft YaHei", 10)).pack(anchor=tk.W)
        self.current_phase_progress_bar = AnimatedProgressBar(current_phase_frame, width=700)
        self.current_phase_progress_bar.pack(fill=tk.X, pady=(2, 0))
        self.current_phase_progress_bar.setRange(0, 100)
        self.current_phase_progress_bar.setValue(0)
        self.current_phase_progress_bar.setTextVisible(True)

        # 详细信息标签
        self.detail_label = ttk.Label(main_frame, text="", anchor=tk.CENTER, wraplength=750)
        self.detail_label.pack(fill=tk.X, pady=(10, 10))

        # 输出文本框
        output_frame = ttk.LabelFrame(main_frame, text="训练输出", padding="5")
        output_frame.pack(fill=tk.BOTH, expand=True)

        self.output_text = scrolledtext.ScrolledText(output_frame, state='disabled',font=("Microsoft YaHei", 12))
        self.output_text.pack(fill=tk.BOTH, expand=True)

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, pady=(10, 0))

    def start_training(self):
        """开始训练"""
        if self.training_in_progress:
            messagebox.showwarning("警告", "训练已在进行中", parent=self.root)
            return

        self.send_message_to_temp_file({
                "type": "start",
                "message": "训练开始",
                "timestamp": datetime.now().isoformat()
        })

        self.stop_training_flag = False

        # 显示优化方法选择对话框，传入用户角色
        dialog = OptimizationMethodDialog(self, self.user_role)  # 传入实际的用户角色
        if dialog.show():
            # 获取用户选择的优化方法和聚类方法
            optimization_method, clustering_method = dialog.get_selected_methods()
            # 更新配置
            self.tuning_config["optimization_method"] = optimization_method
            self.tuning_config["clustering_method"] = clustering_method

            # 发送配置更新消息给主应用
            self.send_message_to_temp_file({
                "type": "config_update",
                "optimization_method": optimization_method,
                "clustering_method": clustering_method,
                "timestamp": datetime.now().isoformat()
            })

            # 开始训练
            self.training_in_progress = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_var.set("正在训练...")

            # 在新线程中运行训练
            training_thread = threading.Thread(target=self.run_training, daemon=True)
            training_thread.start()
        else:
            # 用户取消了训练
            self.send_message_to_temp_file({
                "type": "cancelled",
                "message": "用户取消了训练",
                "timestamp": datetime.now().isoformat()
            })
            self.root.quit()

    def run_training(self):
        """执行训练过程"""
        try:
            if not os.path.exists(CONFIG["data_path"]):
                os.makedirs(CONFIG["data_path"])
                self.logger.info(f"创建数据目录: {CONFIG['data_path']}")
                print(f"创建数据目录: {CONFIG['data_path']}")

            # 调用训练主函数
            self.trainer = ModelTrainer(
                app=self,
                training_worker=self,
                tuning_config=self.tuning_config
            )

            # 连接进度信号到UI更新方法
            self.trainer.progress_signal.progress_updated.connect(self.update_progress)

            # 设置阶段更新回调
            if hasattr(self.trainer, 'app'):
                self.trainer.app.trainer_phase_signal = self.update_phase
                self.trainer.app.trainer_progress_signal = self.update_progress
                self.trainer.app.trainer_total_progress_signal = self.update_total_progress

            self.model_dir = self.trainer.run_training

            if self.stop_training_flag:
                message = "训练已被用户中断"
                self.logger.info(message)
                print(message)

                # 删除中断训练生成的模型目录
                self._delete_model_dir()

                # 释放GPU资源
                self.release_gpu_resources()
                self.send_message_to_temp_file({
                    "type": "cancelled",
                    "success": False,
                    "model_dir": "",
                    "message": "训练已被用户中断",
                    "timestamp": datetime.now().isoformat()
                })
            else:
                message = f"训练完成！模型已保存至 {self.model_dir} 目录"
                self.logger.info("训练完成！模型已保存至 %s 目录", self.model_dir)
                print(message)

                self.send_message_to_temp_file({
                    "type": "completion",
                    "success": True,
                    "model_dir": self.model_dir,
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                })
                self.root.quit()
                self.root.destroy()

        except Exception as e:
            if not self.stop_training_flag:
                error_msg = f"训练过程中发生错误: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                print(error_msg)

                # 删除训练失败生成的模型目录
                self._delete_model_dir()

                self.send_message_to_temp_file({
                    "type": "error",
                    "success": False,
                    "model_dir": "",
                    "message": error_msg,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                # 异常情况删除模型目录
                message = "训练已被用户中断"
                self.logger.info(message)
                print(message)

                # 删除中断训练生成的模型目录
                self._delete_model_dir()
                self.release_gpu_resources()

                self.send_message_to_temp_file({
                    "type": "cancelled",
                    "success": False,
                    "model_dir": "",
                    "message": "训练已被用户中断",
                    "timestamp": datetime.now().isoformat()
                })
        finally:
            # 恢复按钮状态
            self.training_in_progress = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.status_var.set("训练完成")

    def _delete_model_dir(self):
        """删除模型目录的辅助方法"""
        model_dir_to_delete = self.model_dir

        if not model_dir_to_delete and hasattr(self, 'trainer') and self.trainer:
            model_dir_to_delete = self.trainer.model_dir

        self.logger.info(f"尝试删除模型目录: {model_dir_to_delete}")
        print(f"尝试删除模型目录: {model_dir_to_delete}")

        if model_dir_to_delete and os.path.exists(model_dir_to_delete):
            try:
                shutil.rmtree(model_dir_to_delete)
                msg = f"已删除中断训练生成的模型目录: {model_dir_to_delete}"
                self.logger.info(msg)
                print(msg)
            except Exception as e:
                msg = f"删除中断训练生成的模型目录失败: {str(e)}"
                self.logger.error(msg, exc_info=True)
                print(msg)
        elif model_dir_to_delete:
            msg = f"模型目录不存在: {model_dir_to_delete}"
            self.logger.warning(msg)
            print(msg)
        else:
            msg = "未找到需要删除的模型目录"
            self.logger.warning(msg)
            print(msg)

    def release_gpu_resources(self):
        """释放GPU资源"""
        try:
            # 清理TensorFlow GPU资源
            try:
                # 清空Keras会话
                try:
                    tf.keras.backend.clear_session()
                except:
                    pass

                # 重置默认图
                try:
                    tf.compat.v1.reset_default_graph()
                except:
                    pass

                print("TensorFlow GPU资源已释放")
            except ImportError:
                pass
            except Exception as e:
                msg = f"释放TensorFlow GPU资源时出错: {str(e)}"
                print(msg)

        except Exception as e:
            msg = f"释放GPU资源时发生错误: {str(e)}"
            self.logger.error(msg)
            print(msg)

    def stop_training(self):
        """停止训练"""
        if self.training_in_progress:
            self.stop_training_flag = True
            self.status_var.set("已停止训练...")
            self.training_in_progress = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            # 发送停止训练信号给主应用
            self._delete_model_dir()
            self.release_gpu_resources()
            self.send_message_to_temp_file({"type": "cancelled", "timestamp": datetime.now().isoformat()})

    def update_progress(self, current, total, description):
        """更新进度条"""
        if total > 0 and self.current_phase_progress_bar:
            try:
                percentage = (current / total) * 100
                self.current_phase_progress_bar.setValue(percentage)
                self.detail_label.config(text=description)
                self.root.update()
            except Exception as e:
                pass

    def update_phase(self, phase_text):
        """更新阶段文本"""
        if self.phase_label:
            try:
                self.phase_label.config(text=phase_text)
                self.root.update()
            except Exception as e:
                pass

    def update_total_progress(self, percentage):
        """更新总体进度"""
        if self.total_progress_bar:
            try:
                self.total_progress_bar.setValue(percentage)
                self.root.update()
            except Exception as e:
                pass

    def send_message_to_temp_file(self, data):
        """将消息写入临时JSON文件"""
        try:
            # 添加时间戳
            data["timestamp"] = data.get("timestamp", datetime.now().isoformat())

            # 写入临时文件
            with open(self.temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"写入临时文件时出错: {e}")

    def run(self):
        """运行应用"""
        self.root.mainloop()

    def on_closing(self):
        """处理窗口关闭事件"""
        # 如果训练正在进行中，发送停止训练信号
        if self.training_in_progress:
            self.stop_training_flag = True
            self.send_message_to_temp_file({"type": "cancelled", "timestamp": datetime.now().isoformat()})
            self._delete_model_dir()
            self.release_gpu_resources()

        # 发送取消信号
        self.send_message_to_temp_file({
            "type": "cancelled",
            "message": "用户关闭了训练窗口",
            "timestamp": datetime.now().isoformat()
        })

        # 销毁窗口
        self.root.quit()
        self.root.destroy()


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser()
    parser.add_argument("config_file", nargs="?", default=None, help="配置文件路径")
    args = parser.parse_args()

    try:
        app = TrainingApp(config_file=args.config_file)
        app.run()
    except Exception as e:
        try:
            data = {
                "type": "error",
                "message": f"训练应用运行出错: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            # 写入临时文件
            temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            temp_file = os.path.join(temp_dir, "training_status.json")

            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except:
            pass


if __name__ == "__main__":
    main()
