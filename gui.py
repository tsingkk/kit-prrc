import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, List
from models import (
    PipeData,
    FluidData,
    OperatingConditions,
    LocalResistanceData,
    LocalResistanceComponent,
    LOCAL_RESISTANCE_COMPONENTS,
    CalculationOptions,
    CalculationResult,
)
from core import calc_pressure_drop


ROUGHNESS_DATA = [
    ("钢管(无缝)", "0.02-0.05"),
    ("钢管(焊接)", "0.05-0.1"),
    ("镀锌钢管", "0.15"),
    ("铸铁管", "0.26"),
    ("不锈钢管", "0.015-0.045"),
    ("PVC管", "0.0015-0.007"),
    ("PE管", "0.003-0.007"),
    ("玻璃管", "0.001"),
    ("混凝土管", "0.3-3.0"),
    ("橡胶软管", "0.01-0.03"),
]


class PipelineResistanceGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Kit管道阻力降计算工具")
        self.root.geometry("1500x800")
        self.root.minsize(1400, 700)

        self.component_entries: List[tk.Entry] = []
        self.component_K_entries: List[tk.Entry] = []
        self.component_K_labels: List[ttk.Label] = []

        self.create_scrollbar()
        self.create_widgets()
        self.set_default_values()

    def create_scrollbar(self):
        self.canvas = tk.Canvas(self.root, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(
            self.root, orient="vertical", command=self.canvas.yview
        )
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self._update_scroll_region(),
        )

        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.root.bind_all("<MouseWheel>", self._on_mousewheel)
        self.root.bind_all("<Button-4>", self._on_mousewheel)
        self.root.bind_all("<Button-5>", self._on_mousewheel)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_canvas_configure(self, event):
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)

    def _update_scroll_region(self):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_mousewheel(self, event):
        scroll_region = self.canvas.bbox("all")
        if scroll_region:
            canvas_height = self.canvas.winfo_height()
            content_height = scroll_region[3] - scroll_region[1]
            if content_height > canvas_height:
                if event.num == 4:
                    self.canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    self.canvas.yview_scroll(1, "units")
                elif event.delta:
                    self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_comp_mousewheel(self, event):
        scroll_region = self.canvas_comp.bbox("all")
        if scroll_region:
            canvas_height = self.canvas_comp.winfo_height()
            content_height = scroll_region[3] - scroll_region[1]
            if content_height > canvas_height:
                if event.num == 4:
                    self.canvas_comp.yview_scroll(-1, "units")
                elif event.num == 5:
                    self.canvas_comp.yview_scroll(1, "units")
                elif event.delta:
                    self.canvas_comp.yview_scroll(
                        int(-1 * (event.delta / 120)), "units"
                    )

    def create_widgets(self):
        main_frame = ttk.Frame(self.scrollable_frame, padding="5")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.scrollable_frame.columnconfigure(0, weight=1)
        self.scrollable_frame.rowconfigure(0, weight=1)

        main_frame.columnconfigure(0, weight=1, minsize=280)
        main_frame.columnconfigure(1, weight=1, minsize=200)
        main_frame.columnconfigure(2, weight=1, minsize=250)
        main_frame.columnconfigure(3, weight=1, minsize=380)
        main_frame.rowconfigure(1, weight=1)

        header_frame = ttk.Frame(main_frame)
        header_frame.grid(
            row=0, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 5)
        )
        header_frame.columnconfigure(0, weight=1)
        header_frame.columnconfigure(1, weight=1)
        header_frame.columnconfigure(2, weight=1)

        title_label = ttk.Label(
            header_frame, text="Kit管道阻力降计算助手", font=("Arial", 18, "bold")
        )
        title_label.grid(row=0, column=1)

        author_label = ttk.Label(header_frame, text="by tsingkk", font=("Arial", 10))
        author_label.grid(row=0, column=2, sticky="e", padx=5)

        self.create_input_column(main_frame)
        self.create_reference_column(main_frame)
        self.create_output_column(main_frame)
        self.create_formula_column(main_frame)

    def create_input_column(self, parent):
        left_frame = ttk.Frame(parent)
        left_frame.grid(
            row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=3, pady=5
        )
        left_frame.columnconfigure(0, weight=1)

        param_frame = ttk.LabelFrame(left_frame, text="输入参数", padding="5")
        param_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        param_frame.columnconfigure(1, weight=1)

        row = 0

        ttk.Label(param_frame, text="【管道参数】", font=("Arial", 9, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 2)
        )
        row += 1

        ttk.Label(param_frame, text="管内径 D (mm):").grid(
            row=row, column=0, sticky=tk.W, pady=1
        )
        self.entry_D = ttk.Entry(param_frame, width=15)
        self.entry_D.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=1)
        row += 1

        ttk.Label(param_frame, text="管道长度 L (m):").grid(
            row=row, column=0, sticky=tk.W, pady=1
        )
        self.entry_L = ttk.Entry(param_frame, width=15)
        self.entry_L.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=1)
        row += 1

        ttk.Label(param_frame, text="粗糙度 ε (mm):").grid(
            row=row, column=0, sticky=tk.W, pady=1
        )
        self.entry_epsilon = ttk.Entry(param_frame, width=15)
        self.entry_epsilon.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=1)
        row += 1

        ttk.Separator(param_frame, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5
        )
        row += 1

        ttk.Label(param_frame, text="【流体参数】", font=("Arial", 9, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 2)
        )
        row += 1

        ttk.Label(param_frame, text="密度 ρ (kg/m³):").grid(
            row=row, column=0, sticky=tk.W, pady=1
        )
        self.entry_rho = ttk.Entry(param_frame, width=15)
        self.entry_rho.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=1)
        row += 1

        ttk.Label(param_frame, text="黏度 μ (mPa·s):").grid(
            row=row, column=0, sticky=tk.W, pady=1
        )
        self.entry_mu = ttk.Entry(param_frame, width=15)
        self.entry_mu.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=1)
        row += 1

        ttk.Separator(param_frame, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5
        )
        row += 1

        ttk.Label(param_frame, text="【工况参数】", font=("Arial", 9, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 2)
        )
        row += 1

        self.use_flow_rate_var = tk.BooleanVar(value=True)
        ttk.Radiobutton(
            param_frame,
            text="流量 Q (m³/h)",
            variable=self.use_flow_rate_var,
            value=True,
            command=self.toggle_input_mode,
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W)
        row += 1

        self.entry_Q = ttk.Entry(param_frame, width=15)
        self.entry_Q.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=1)
        ttk.Label(param_frame, text="Q:").grid(row=row, column=0, sticky=tk.W)
        row += 1

        ttk.Radiobutton(
            param_frame,
            text="流速 v (m/s)",
            variable=self.use_flow_rate_var,
            value=False,
            command=self.toggle_input_mode,
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W)
        row += 1

        self.entry_v = ttk.Entry(param_frame, width=15, state="disabled")
        self.entry_v.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=1)
        ttk.Label(param_frame, text="v:").grid(row=row, column=0, sticky=tk.W)
        row += 1

        ttk.Label(param_frame, text="进口高程 z_in (m):").grid(
            row=row, column=0, sticky=tk.W, pady=1
        )
        self.entry_z_in = ttk.Entry(param_frame, width=15)
        self.entry_z_in.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=1)
        row += 1

        ttk.Label(param_frame, text="出口高程 z_out (m):").grid(
            row=row, column=0, sticky=tk.W, pady=1
        )
        self.entry_z_out = ttk.Entry(param_frame, width=15)
        self.entry_z_out.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=1)
        row += 1

        ttk.Separator(param_frame, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5
        )
        row += 1

        self.include_static_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            param_frame, text="叠加静压差", variable=self.include_static_var
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W)
        row += 1

        local_frame = ttk.LabelFrame(left_frame, text="局部阻力输入", padding="5")
        local_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        header_frame = ttk.Frame(local_frame)
        header_frame.pack(fill=tk.X)
        ttk.Label(header_frame, text="管件名称", width=12).pack(side=tk.LEFT, padx=2)
        ttk.Label(header_frame, text="K值", width=5).pack(side=tk.LEFT, padx=2)
        ttk.Label(header_frame, text="数量", width=5).pack(side=tk.LEFT, padx=2)
        ttk.Label(header_frame, text="K×n", width=5).pack(side=tk.LEFT, padx=2)

        list_frame = ttk.Frame(local_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas_comp = tk.Canvas(list_frame, height=180, highlightthickness=0)
        scrollbar_comp = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.canvas_comp.yview
        )
        comp_inner_frame = ttk.Frame(self.canvas_comp)

        comp_inner_frame.bind(
            "<Configure>",
            lambda e: self.canvas_comp.configure(
                scrollregion=self.canvas_comp.bbox("all")
            ),
        )
        self.canvas_comp.create_window((0, 0), window=comp_inner_frame, anchor="nw")
        self.canvas_comp.configure(yscrollcommand=scrollbar_comp.set)

        for i, (name, k_value) in enumerate(LOCAL_RESISTANCE_COMPONENTS):
            ttk.Label(comp_inner_frame, text=name, width=12).grid(
                row=i, column=0, padx=2, pady=1, sticky=tk.W
            )
            k_entry = ttk.Entry(comp_inner_frame, width=6)
            k_entry.insert(0, f"{k_value}")
            k_entry.grid(row=i, column=1, padx=2, pady=1)
            k_entry.bind(
                "<KeyRelease>", lambda e, idx=i: self.update_K_total_display(idx)
            )

            entry = ttk.Entry(comp_inner_frame, width=5)
            entry.insert(0, "0")
            entry.grid(row=i, column=2, padx=2, pady=1)
            entry.bind(
                "<KeyRelease>", lambda e, idx=i: self.update_K_total_display(idx)
            )

            total_label = ttk.Label(comp_inner_frame, text="0", width=6)
            total_label.grid(row=i, column=3, padx=2, pady=1)

            self.component_K_entries.append(k_entry)
            self.component_entries.append(entry)
            self.component_K_labels.append(total_label)

        self.canvas_comp.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_comp.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas_comp.bind("<MouseWheel>", self._on_comp_mousewheel)
        self.canvas_comp.bind("<Button-4>", self._on_comp_mousewheel)
        self.canvas_comp.bind("<Button-5>", self._on_comp_mousewheel)

        total_frame = ttk.Frame(local_frame)
        total_frame.pack(fill=tk.X, pady=5)
        ttk.Label(total_frame, text="总K值:", font=("Arial", 9, "bold")).pack(
            side=tk.LEFT, padx=5
        )
        self.lbl_K_total = ttk.Label(
            total_frame, text="0.00", font=("Arial", 9, "bold")
        )
        self.lbl_K_total.pack(side=tk.LEFT)

        control_frame = ttk.Frame(left_frame)
        control_frame.pack(fill=tk.X, pady=5)

        self.btn_calculate = ttk.Button(
            control_frame, text="计算", command=self.calculate, width=8
        )
        self.btn_calculate.pack(side=tk.LEFT, padx=2)

        self.btn_reset = ttk.Button(
            control_frame, text="重置", command=self.reset, width=8
        )
        self.btn_reset.pack(side=tk.LEFT, padx=2)

        self.btn_example1 = ttk.Button(
            control_frame, text="示例1:湍流", command=self.load_example1, width=10
        )
        self.btn_example1.pack(side=tk.LEFT, padx=2)

        self.btn_example2 = ttk.Button(
            control_frame, text="示例2:层流", command=self.load_example2, width=10
        )
        self.btn_example2.pack(side=tk.LEFT, padx=2)

    def update_K_total_display(self, changed_idx=None):
        total = 0.0
        for i in range(len(LOCAL_RESISTANCE_COMPONENTS)):
            try:
                k_value = float(self.component_K_entries[i].get() or 0)
            except ValueError:
                k_value = 0
            try:
                count = int(self.component_entries[i].get() or 0)
            except ValueError:
                count = 0
            sub_total = k_value * count
            self.component_K_labels[i].config(text=f"{sub_total:.2f}")
            total += sub_total
        self.lbl_K_total.config(text=f"{total:.2f}")

    def create_reference_column(self, parent):
        center_frame = ttk.Frame(parent)
        center_frame.grid(
            row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=3, pady=5
        )
        center_frame.columnconfigure(0, weight=1)

        roughness_frame = ttk.LabelFrame(
            center_frame, text="管道粗糙度参考值 (mm)", padding="5"
        )
        roughness_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        columns = ("type", "epsilon")
        self.roughness_tree = ttk.Treeview(
            roughness_frame, columns=columns, show="headings", height=8
        )
        self.roughness_tree.heading("type", text="管材类型")
        self.roughness_tree.heading("epsilon", text="粗糙度ε")
        self.roughness_tree.column("type", width=90)
        self.roughness_tree.column("epsilon", width=70)

        for item in ROUGHNESS_DATA:
            self.roughness_tree.insert("", "end", values=item)

        roughness_scroll = ttk.Scrollbar(
            roughness_frame, orient="vertical", command=self.roughness_tree.yview
        )
        self.roughness_tree.configure(yscrollcommand=roughness_scroll.set)
        self.roughness_tree.pack(side=tk.LEFT, fill="both", expand=True)
        roughness_scroll.pack(side=tk.RIGHT, fill="y")

        k_value_frame = ttk.LabelFrame(
            center_frame, text="局部阻力系数K值参考", padding="5"
        )
        k_value_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("component", "k_value")
        self.k_tree = ttk.Treeview(
            k_value_frame, columns=columns, show="headings", height=8
        )
        self.k_tree.heading("component", text="管件类型")
        self.k_tree.heading("k_value", text="K值")
        self.k_tree.column("component", width=90)
        self.k_tree.column("k_value", width=70)

        for item in LOCAL_RESISTANCE_COMPONENTS:
            self.k_tree.insert("", "end", values=item)

        k_scroll = ttk.Scrollbar(
            k_value_frame, orient="vertical", command=self.k_tree.yview
        )
        self.k_tree.configure(yscrollcommand=k_scroll.set)
        self.k_tree.pack(side=tk.LEFT, fill="both", expand=True)
        k_scroll.pack(side=tk.RIGHT, fill="y")

    def create_output_column(self, parent):
        right_frame = ttk.Frame(parent)
        right_frame.grid(
            row=1, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=3, pady=5
        )
        right_frame.columnconfigure(0, weight=1)

        results_frame = ttk.LabelFrame(right_frame, text="计算结果", padding="5")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        results_frame.columnconfigure(1, weight=1)

        row = 0

        ttk.Label(results_frame, text="【最终结果】", font=("Arial", 9, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 2)
        )
        row += 1

        ttk.Label(results_frame, text="沿程压降 (Pa):").grid(
            row=row, column=0, sticky=tk.W, pady=1
        )
        self.lbl_dp_major = ttk.Label(results_frame, text="--", width=12, anchor="e")
        self.lbl_dp_major.grid(row=row, column=1, sticky=tk.E, pady=1)
        row += 1

        ttk.Label(results_frame, text="局部压降 (Pa):").grid(
            row=row, column=0, sticky=tk.W, pady=1
        )
        self.lbl_dp_minor = ttk.Label(results_frame, text="--", width=12, anchor="e")
        self.lbl_dp_minor.grid(row=row, column=1, sticky=tk.E, pady=1)
        row += 1

        ttk.Label(results_frame, text="静压差 (Pa):").grid(
            row=row, column=0, sticky=tk.W, pady=1
        )
        self.lbl_dp_static = ttk.Label(results_frame, text="--", width=12, anchor="e")
        self.lbl_dp_static.grid(row=row, column=1, sticky=tk.E, pady=1)
        row += 1

        ttk.Separator(results_frame, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=3
        )
        row += 1

        ttk.Label(results_frame, text="总压降 (Pa):", font=("Arial", 9, "bold")).grid(
            row=row, column=0, sticky=tk.W, pady=1
        )
        self.lbl_dp_total = ttk.Label(
            results_frame, text="--", width=12, anchor="e", font=("Arial", 9, "bold")
        )
        self.lbl_dp_total.grid(row=row, column=1, sticky=tk.E, pady=1)
        row += 1

        ttk.Label(results_frame, text="总压降 (kPa):").grid(
            row=row, column=0, sticky=tk.W, pady=1
        )
        self.lbl_dp_total_kpa = ttk.Label(
            results_frame, text="--", width=12, anchor="e"
        )
        self.lbl_dp_total_kpa.grid(row=row, column=1, sticky=tk.E, pady=1)
        row += 1

        ttk.Separator(results_frame, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=3
        )
        row += 1

        ttk.Label(results_frame, text="【中间量】", font=("Arial", 9, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 2)
        )
        row += 1

        intermediate_items = [
            ("流速 v (m/s):", "lbl_velocity"),
            ("雷诺数 Re:", "lbl_Re"),
            ("流型:", "lbl_flow_regime"),
            ("摩擦因子 f:", "lbl_friction"),
            ("截面积 A (m²):", "lbl_area"),
            ("相对粗糙度 ε/D:", "lbl_epsilon_D"),
        ]

        for label_text, attr_name in intermediate_items:
            ttk.Label(results_frame, text=label_text).grid(
                row=row, column=0, sticky=tk.W, pady=1
            )
            lbl = ttk.Label(results_frame, text="--", width=12, anchor="e")
            lbl.grid(row=row, column=1, sticky=tk.E, pady=1)
            setattr(self, attr_name, lbl)
            row += 1

        warnings_frame = ttk.LabelFrame(right_frame, text="警告信息", padding="5")
        warnings_frame.pack(fill=tk.BOTH, expand=True)

        self.text_warnings = tk.Text(
            warnings_frame, height=6, width=30, state="disabled", font=("Arial", 9)
        )
        warnings_scroll = ttk.Scrollbar(
            warnings_frame, orient="vertical", command=self.text_warnings.yview
        )
        self.text_warnings.configure(yscrollcommand=warnings_scroll.set)
        self.text_warnings.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        warnings_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def create_formula_column(self, parent):
        formula_frame = ttk.Frame(parent)
        formula_frame.grid(
            row=1, column=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=3, pady=5
        )
        formula_frame.columnconfigure(0, weight=1)

        steps_frame = ttk.LabelFrame(formula_frame, text="计算公式与步骤", padding="5")
        steps_frame.pack(fill=tk.BOTH, expand=True)

        self.text_steps = tk.Text(
            steps_frame, height=35, width=45, state="disabled", font=("Consolas", 9)
        )
        steps_scroll = ttk.Scrollbar(
            steps_frame, orient="vertical", command=self.text_steps.yview
        )
        self.text_steps.configure(yscrollcommand=steps_scroll.set)
        self.text_steps.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        steps_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def set_default_values(self):
        self.entry_epsilon.insert(0, "0.045")
        self.entry_z_in.insert(0, "0")
        self.entry_z_out.insert(0, "0")

    def toggle_input_mode(self):
        if self.use_flow_rate_var.get():
            self.entry_Q.config(state="normal")
            self.entry_v.config(state="disabled")
        else:
            self.entry_Q.config(state="disabled")
            self.entry_v.config(state="normal")

    def get_float(
        self, entry: ttk.Entry, field_name: str, allow_empty: bool = False
    ) -> float:
        value_str = entry.get().strip()
        if allow_empty and value_str == "":
            return 0.0
        try:
            return float(value_str)
        except ValueError:
            raise ValueError(f"无效的 {field_name}，请输入数值")

    def get_local_resistance_components(self) -> LocalResistanceData:
        components = []
        for i, (name, _) in enumerate(LOCAL_RESISTANCE_COMPONENTS):
            try:
                k_value = float(self.component_K_entries[i].get() or 0)
            except ValueError:
                k_value = 0
            try:
                count = int(self.component_entries[i].get() or 0)
            except ValueError:
                count = 0
            if count > 0:
                components.append(
                    LocalResistanceComponent(name=name, K=k_value, count=count)
                )

        local_resistance = LocalResistanceData(components=components)
        if components:
            local_resistance.calculate_K_total()
        return local_resistance

    def calculate(self):
        try:
            D = self.get_float(self.entry_D, "管内径")
            L = self.get_float(self.entry_L, "管道长度")
            epsilon = self.get_float(self.entry_epsilon, "绝对粗糙度")

            rho = self.get_float(self.entry_rho, "流体密度")
            mu = self.get_float(self.entry_mu, "动力黏度")

            use_flow_rate = self.use_flow_rate_var.get()
            Q = None
            v = None

            if use_flow_rate:
                Q = self.get_float(self.entry_Q, "体积流量")
            else:
                v = self.get_float(self.entry_v, "流速")

            z_in = self.get_float(self.entry_z_in, "进口高程", allow_empty=True)
            z_out = self.get_float(self.entry_z_out, "出口高程", allow_empty=True)

            pipe_data = PipeData(D_mm=D, L_m=L, epsilon_mm=epsilon)
            fluid_data = FluidData(rho_kg_m3=rho, mu_mPa_s=mu)
            operating_conditions = OperatingConditions(
                Q_m3_h=Q,
                v_m_s=v,
                z_in_m=z_in,
                z_out_m=z_out,
                use_flow_rate=use_flow_rate,
            )
            local_resistance = self.get_local_resistance_components()
            options = CalculationOptions(
                include_static_head=self.include_static_var.get()
            )

            result = calc_pressure_drop(
                pipe_data, fluid_data, operating_conditions, local_resistance, options
            )

            self.display_result(result)

        except ValueError as e:
            messagebox.showerror("输入错误", str(e))
        except Exception as e:
            messagebox.showerror("计算错误", str(e))

    def display_result(self, result: CalculationResult):
        self.lbl_dp_major.config(text=f"{result.dp_major_Pa:.4f}")
        self.lbl_dp_minor.config(text=f"{result.dp_minor_Pa:.4f}")
        self.lbl_dp_static.config(text=f"{result.dp_static_Pa:.4f}")
        self.lbl_dp_total.config(text=f"{result.dp_total_Pa:.4f}")
        self.lbl_dp_total_kpa.config(text=f"{result.dp_total_kPa:.6f}")

        self.lbl_velocity.config(text=f"{result.velocity_m_s:.4f}")
        self.lbl_Re.config(text=f"{result.Re:.2f}")

        flow_regime_text = {
            "laminar": "层流",
            "transition": "过渡流",
            "turbulent": "湍流",
        }
        self.lbl_flow_regime.config(
            text=flow_regime_text.get(result.flow_regime, result.flow_regime)
        )
        self.lbl_friction.config(text=f"{result.friction_factor:.6f}")
        self.lbl_area.config(text=f"{result.area_m2:.6f}")
        self.lbl_epsilon_D.config(text=f"{result.epsilon_over_D:.6f}")

        self.text_steps.config(state="normal")
        self.text_steps.delete(1.0, tk.END)

        self.text_steps.insert(tk.END, "═══════════════════════════════\n")
        self.text_steps.insert(tk.END, "         所 用 公 式\n")
        self.text_steps.insert(tk.END, "═══════════════════════════════\n\n")
        for name, formula in result.formulas_used.items():
            self.text_steps.insert(tk.END, f"【{name}】\n")
            for line in formula.split("\n"):
                self.text_steps.insert(tk.END, f"  {line}\n")
            self.text_steps.insert(tk.END, "\n")

        self.text_steps.insert(tk.END, "═══════════════════════════════\n")
        self.text_steps.insert(tk.END, "         计 算 步 骤\n")
        self.text_steps.insert(tk.END, "═══════════════════════════════\n")
        for step in result.calculation_steps:
            self.text_steps.insert(tk.END, f"\n▶ {step.name}\n")
            self.text_steps.insert(tk.END, f"  公式: {step.formula}\n")
            inputs_str = ", ".join(
                [f"{k}={v:.6g}" for k, v in step.input_values.items()]
            )
            self.text_steps.insert(tk.END, f"  输入: {inputs_str}\n")
            unit_str = f" {step.unit}" if step.unit else ""
            self.text_steps.insert(tk.END, f"  结果: {step.result:.6g}{unit_str}\n")

        self.text_steps.config(state="disabled")

        self.text_warnings.config(state="normal")
        self.text_warnings.delete(1.0, tk.END)
        if result.warnings:
            for warning in result.warnings:
                self.text_warnings.insert(tk.END, f"⚠ {warning}\n")
        else:
            self.text_warnings.insert(tk.END, "✓ 无警告信息")
        self.text_warnings.config(state="disabled")

    def reset(self):
        self.entry_D.delete(0, tk.END)
        self.entry_L.delete(0, tk.END)
        self.entry_epsilon.delete(0, tk.END)
        self.entry_epsilon.insert(0, "0.045")
        self.entry_rho.delete(0, tk.END)
        self.entry_mu.delete(0, tk.END)
        self.entry_Q.delete(0, tk.END)
        self.entry_v.delete(0, tk.END)
        self.entry_z_in.delete(0, tk.END)
        self.entry_z_in.insert(0, "0")
        self.entry_z_out.delete(0, tk.END)
        self.entry_z_out.insert(0, "0")

        self.use_flow_rate_var.set(True)
        self.include_static_var.set(False)
        self.toggle_input_mode()

        for i, (name, k_value) in enumerate(LOCAL_RESISTANCE_COMPONENTS):
            self.component_K_entries[i].delete(0, tk.END)
            self.component_K_entries[i].insert(0, f"{k_value}")
            self.component_entries[i].delete(0, tk.END)
            self.component_entries[i].insert(0, "0")
        self.update_K_total_display()

        self.lbl_dp_major.config(text="--")
        self.lbl_dp_minor.config(text="--")
        self.lbl_dp_static.config(text="--")
        self.lbl_dp_total.config(text="--")
        self.lbl_dp_total_kpa.config(text="--")
        self.lbl_velocity.config(text="--")
        self.lbl_Re.config(text="--")
        self.lbl_flow_regime.config(text="--")
        self.lbl_friction.config(text="--")
        self.lbl_area.config(text="--")
        self.lbl_epsilon_D.config(text="--")

        self.text_steps.config(state="normal")
        self.text_steps.delete(1.0, tk.END)
        self.text_steps.config(state="disabled")

        self.text_warnings.config(state="normal")
        self.text_warnings.delete(1.0, tk.END)
        self.text_warnings.config(state="disabled")

    def load_example1(self):
        self.entry_D.delete(0, tk.END)
        self.entry_D.insert(0, "50")
        self.entry_L.delete(0, tk.END)
        self.entry_L.insert(0, "100")
        self.entry_epsilon.delete(0, tk.END)
        self.entry_epsilon.insert(0, "0.045")
        self.entry_rho.delete(0, tk.END)
        self.entry_rho.insert(0, "1000")
        self.entry_mu.delete(0, tk.END)
        self.entry_mu.insert(0, "1.0")
        self.entry_Q.delete(0, tk.END)
        self.entry_Q.insert(0, "10")
        self.entry_z_in.delete(0, tk.END)
        self.entry_z_in.insert(0, "0")
        self.entry_z_out.delete(0, tk.END)
        self.entry_z_out.insert(0, "0")

        for i, (name, k_value) in enumerate(LOCAL_RESISTANCE_COMPONENTS):
            self.component_K_entries[i].delete(0, tk.END)
            self.component_K_entries[i].insert(0, f"{k_value}")
            self.component_entries[i].delete(0, tk.END)
            self.component_entries[i].insert(0, "0")
        self.component_entries[0].delete(0, tk.END)
        self.component_entries[0].insert(0, "10")
        self.component_entries[11].delete(0, tk.END)
        self.component_entries[11].insert(0, "1")
        self.update_K_total_display()

        self.use_flow_rate_var.set(True)
        self.toggle_input_mode()

    def load_example2(self):
        self.entry_D.delete(0, tk.END)
        self.entry_D.insert(0, "25")
        self.entry_L.delete(0, tk.END)
        self.entry_L.insert(0, "10")
        self.entry_epsilon.delete(0, tk.END)
        self.entry_epsilon.insert(0, "0.045")
        self.entry_rho.delete(0, tk.END)
        self.entry_rho.insert(0, "900")
        self.entry_mu.delete(0, tk.END)
        self.entry_mu.insert(0, "500")
        self.entry_Q.delete(0, tk.END)
        self.entry_Q.insert(0, "0.1")
        self.entry_z_in.delete(0, tk.END)
        self.entry_z_in.insert(0, "0")
        self.entry_z_out.delete(0, tk.END)
        self.entry_z_out.insert(0, "0")

        for i, (name, k_value) in enumerate(LOCAL_RESISTANCE_COMPONENTS):
            self.component_K_entries[i].delete(0, tk.END)
            self.component_K_entries[i].insert(0, f"{k_value}")
            self.component_entries[i].delete(0, tk.END)
            self.component_entries[i].insert(0, "0")
        self.update_K_total_display()

        self.use_flow_rate_var.set(True)
        self.toggle_input_mode()


def run_gui():
    root = tk.Tk()
    app = PipelineResistanceGUI(root)
    root.mainloop()


if __name__ == "__main__":
    run_gui()
