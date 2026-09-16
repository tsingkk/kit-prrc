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
  - **交互体验保护**：在 Darby 3K 模式下，管件 K 值列自动设为只读并在计算后回填动态实际 K 值；切换至经典 1K 模式时恢复自由编辑。
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

## 三、 适用范围与不适用边界说明 (未覆盖但属合理范畴的功能)

本工具旨在为工程常用工况提供快速、高保真且稳定的水力阻力计算。以下物理场景属于超出本工具适用范围的合理范畴，工程核算时需特别注意：

1. **气液两相流（Two-Phase Flow）**：
   - 本工具仅适用于单相流体（单一均相液体或气体）的流动阻力计算。
   - 不适用于存在剧烈闪蒸、凝结或气液混输的两相流动（如未内置 Lockhart-Martinelli、Chisholm 等两相分相流阻力倍增模型）。
2. **动量变化与加速度压降（Acceleration Pressure Drop）**：
   - 本工具基于恒定管径和单相恒密度不可压缩/弱可压缩稳态流动假设，流体进出口流速相等，加速度压降 $\Delta P_{acc} = G^2 (1/\rho_{out} - 1/\rho_{in})$ 恒为 0。
   - 若流体沿管道有剧烈相变、大温差膨胀或密度显著衰变，需额外计入流体动量增量引起的附加压力降。
3. **复杂变径与管网系统（Network & Reducer Systems）**：
   - 本工具面向单一恒定管径管段进行核算。
   - 若管路系统包含大小头急扩/急缩变径段、多分支分配管路或环状闭合管网，需逐段拆分计算或使用专用管网水力平差软件。
4. **高压降大膨胀气体流动（Compressible Gas Flow with Large $\Delta P$）**：
   - 当气体输送压降较小（$\Delta P < 10\% P_{in}$）时，可采用本工具的平均密度法进行工程近视计算。
   - 当压降较大（$\Delta P \ge 10\% P_{in}$）时，气体膨胀显著，密度与流速沿程急剧变化，常规 Darcy-Weisbach 公式不再适用，需采用完全可压缩流动等温或绝热微分方程进行数值积分。
5. **非牛顿流体流动（Non-Newtonian Fluids）**：
   - 本工具所有雷诺数与摩擦因子公式均建立在牛顿流体（剪切应力与剪切速率呈线性关系）基础之上。
   - 对高聚物熔体、聚合物浆料、钻井泥浆、污泥胶体等非牛顿流体（假塑性、胀塑性、宾汉流体），需依据流变本构方程修正广义雷诺数与阻力系数。

---

## 四、 安装与运行指南

### 1. 从 GitHub Releases 直接下载运行（推荐，开箱即用）

若无需修改源码或进行二次开发，可直接下载已打包的 Windows 单一可执行程序：

1. 前往本项目的 **[GitHub Releases](https://github.com/tsingkk/kit-prrc/releases)** 页面。
2. 在最新版本的 **Assets** 列表中下载 `kit-prrc.exe`。
3. 双击 `kit-prrc.exe` 即可直接启动图形计算界面（目标机器无需预装 Python 环境或任何第三方依赖）。

### 2. 从源码运行（开发者模式）

本项目严格采用现代 Python 包管理工具 **[uv](https://github.com/astral-sh/uv)** 进行环境隔离与依赖管理。

#### (1) 环境准备
确保已安装 Python 3.12+ 以及 uv：
```bash
# 安装 uv (如果尚未安装)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### (2) 同步项目环境与依赖
进入项目根目录后执行：
```bash
uv sync
```

#### (3) 启动图形计算界面
```bash
uv run python gui.py
```

---

## 五、 开发与测试规范

项目遵循严格的代码质量规范，请使用 `uv run` 执行相关工具：

```bash
# 运行自动化单元测试
uv run pytest -v test_core.py

# 静默运行测试
uv run pytest -q

# 执行静态类型检查 (mypy)
uv run mypy core.py models.py gui.py test_core.py

# 代码格式化与检查
uv run ruff check .
uv run ruff format .

# 打包构建 Windows 单一可执行程序 (输出为 dist/kit-prrc.exe)
pwsh -File .\scripts\build_windows_onefile.ps1
```

---

## 六、 项目结构说明

```
pipeline_resistance/
├── core.py                   # 物理计算核心引擎 (Churchill, Colebrook, Darby 3K等)
├── models.py                 # 数据类定义、管件参数数据库及计算配置
├── gui.py                    # 基于 Tkinter 的四栏桌面图形界面交互层
├── test_core.py              # 自动化单元测试套件 (覆盖物理精度、边界条件与防回归测试)
├── scripts/
│   └── build_windows_onefile.ps1 # 基于 Nuitka 的 Windows 单一可执行程序自动化打包脚本
├── pyproject.toml            # 项目元数据与依赖管理配置
├── uv.lock                   # uv 依赖确定性锁定文件
├── .gitignore                # Git 忽略文件规则
└── README.md                 # 项目详细说明文档
```


---

## 七、 许可证与作者

- **作者**: tsingkk (<bodekangk@gmail.com>)
- **版权声明**: 本项目遵循开源规范，欢迎提交 Issue 与改进建议。
