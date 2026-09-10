# Kit 管道阻力降计算工具 (Pipeline Resistance Calculator)

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![Package Manager](https://img.shields.io/badge/managed%20by-uv-blueviolet.svg)](https://github.com/astral-sh/uv)
[![Code Style](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checked](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](https://mypy-lang.org/)

一款面向化工、给排水、动力工程及热能工程的桌面级管道水力学阻力压降计算工具。基于 **Python 3.12+** 与 **Tkinter** 架构开发，支持恒定内径、单相流体稳态流动条件下的沿程阻力损失、局部阻力损失以及高程静压差的综合高保真计算。

---

## 一、 核心特性与物理模型

### 1. 全流态摩擦系数（Darcy Friction Factor）多模型引擎
- **Churchill (1977) 全流态模型（默认推荐）**：
  - 显式解析方程，天然涵盖层流、临界过渡区、光滑管湍流与完全粗糙湍流全流态。
  - 数学上光滑、处处可导，彻底消除了分段判断带来的流态跳变断层与数值迭代不收敛问题。
- **Colebrook-White 隐式超越方程（工业基准）**：
  - 采用牛顿-拉夫逊法（Newton-Raphson）在湍流区进行高精度迭代求解。
- **Swamee-Jain 显式方程**：
  - 经典工程显式近似，并内置优化后的端点平滑线性插值算法。
- **Haaland 显式公式**：
  - 适用于工程快速估算的显式对数近似模型。

### 2. 高保真局部阻力（Minor Loss）模型 —— Darby 3K
- **解决层流与小管径阻力失真**：
  - 传统固定 $K$ 值法仅适用于高雷诺数水流工况，在低雷诺数/高粘度层流下会将管件局部阻力低估数百倍。
  - 内置 **Darby 3K 动态模型**：根据流动局部雷诺数 $Re$ 与管道公称内径（英寸）动态求解：
    $$K = \frac{K_1}{Re} + K_\infty \left( 1 + \frac{K_d}{D_{in}^{0.3}} \right)$$
  - 涵盖 90° 弯头、45° 弯头、三通、闸阀、截止阀、球阀、止回阀、底阀等标准工业管件。
- **经典 1K 常数法**：
  - 同时保留传统固定系数累加法，便于不同工程标准与文献对比。

### 3. 系统机械能守恒与水力能耗解耦
- **概念严谨划分**：
  - **水力摩擦总损失 $\Delta P_{friction}$**（$\Delta P_{major} + \Delta P_{minor}$）：反映流体流动过程中因粘性耗散造成的不可逆机械能损失，恒大于等于 0。
  - **高程静压差 $\Delta P_{static}$**：流体克服几何高程落差所需的附加位能压差。
  - **系统进出口总压差 $\Delta P_{total}$**：$\Delta P_{friction} + \Delta P_{static}$。针对下坡管道（$z_{out} < z_{in}$）自流升压工况，提供科学清晰的物理提示。

### 4. 严谨的物理边界保护
- **零流量工况安全处理**：当输入流量 $Q = 0$ 时，程序正常返回零流速与零摩擦阻力，保留有效静压差，避免异常中断。
- **水力光滑管自适应**：当绝对粗糙度 $\epsilon = 0$ 时自适应保护，避免数学定义域异常。
- **物理合理性校验**：严格拦截 $\epsilon \ge D$、内径非正、密度或粘度非正等非法输入。

---

## 二、 界面布局与交互设计

程序采用四栏式专业桌面布局：
1. **输入参数面板**：
   - 管道几何尺寸（管径 $D$、管长 $L$、粗糙度 $\epsilon$）。
   - 流体物性（密度 $\rho$、动力黏度 $\mu$）。
   - 工况条件（支持流量 $Q$ 与流速 $v$ 双向输入；进出口高程设置与静压差开关）。
   - 计算模型选择（摩擦因子模型、局部阻力计算方法下拉选项）。
2. **局部阻力配置与参考库**：
   - 标准管件输入列表（各管件数量及实时 $K \times n$ 显示）。
   - 管道材质粗糙度参考表（无缝钢管、焊接钢管、镀锌管、不锈钢、PVC/PE管等）。
   - 常见管件与阀门局部阻力系数参考表。
3. **计算结果展示区**：
   - 清晰输出沿程阻力、局部阻力、摩擦总损失、高程静压差、系统总压差（Pa / kPa）。
   - 呈现流速、雷诺数、流动状态、摩擦系数、截面积、相对粗糙度等关键物理中间量。
   - 实时警报与工程合规提示（如流速偏高、过渡流区波动提示、自流升压说明等）。
4. **公式与计算步骤推导区**：
   - 完整展示当前工况下所采用的物理方程表达式。
   - 分步列出截面积、流速、雷诺数、摩擦因子、动压、沿程阻力、局部阻力及总压差的计算输入与数值结果。

---

## 三、 安装与运行指南

本项目严格采用现代 Python 包管理工具 **[uv](https://github.com/astral-sh/uv)** 进行环境隔离与依赖管理。

### 1. 环境准备
确保已安装 Python 3.12+ 以及 uv：
```bash
# 安装 uv (如果尚未安装)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. 同步项目环境与依赖
进入项目根目录后执行：
```bash
uv sync
```

### 3. 启动图形计算界面
可通过以下任一命令直接启动桌面程序：
```bash
# 方式一：通过配置好的 CLI 脚本启动
uv run pipeline-resistance

# 方式二：直接运行 GUI 脚本
uv run python gui.py
```

---

## 四、 开发与测试规范

项目遵循严格的代码质量规范，请使用 `uv run` 执行相关工具：

```bash
# 运行自动化单元测试
uv run pytest -v

# 静默运行测试
uv run pytest -q

# 执行静态类型检查 (mypy)
uv run mypy core.py models.py gui.py src/pipeline_resistance

# 代码格式化与检查 (如已配置 ruff)
uv run ruff check .
uv run ruff format .
```

---

## 五、 项目结构说明

```
pipeline_resistance/
├── core.py                   # 物理计算核心引擎 (Churchill, Colebrook, Darby 3K等)
├── models.py                 # 数据类定义、管件参数数据库及计算配置
├── gui.py                    # 基于 Tkinter 的四栏桌面图形界面交互层
├── tests/                    # 自动化单元测试套件
│   └── test_core.py          # 水力模型物理精度、边界条件与Bug防回归测试
├── src/
│   └── pipeline_resistance/  # 打包与对外导入接口
│       └── __init__.py
├── pyproject.toml            # 项目元数据、依赖管理与 CLI 入口点配置
├── uv.lock                   # uv 依赖确定性锁定文件
├── .gitignore                # Git 忽略文件规则
└── README.md                 # 项目详细说明文档
```

---

## 六、 许可证与作者

- **作者**: tsingkk (<bodekangk@gmail.com>)
- **版权声明**: 本项目遵循开源规范，欢迎提交 Issue 与改进建议。
