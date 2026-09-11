from dataclasses import dataclass, field


@dataclass
class PipeData:
    D_mm: float
    L_m: float
    epsilon_mm: float = 0.045


@dataclass
class FluidData:
    rho_kg_m3: float
    mu_mPa_s: float


@dataclass
class OperatingConditions:
    Q_m3_h: float | None = None
    v_m_s: float | None = None
    z_in_m: float = 0.0
    z_out_m: float = 0.0
    use_flow_rate: bool = True


@dataclass
class LocalResistanceComponent:
    name: str
    K: float
    count: int = 0

    @property
    def total_K(self) -> float:
        return self.K * self.count


@dataclass
class Fitting3K:
    name: str
    K1: float  # 层流粘性影响系数
    K_inf: float  # 湍流惯性极限阻力系数
    Kd: float  # 几何尺寸非线性缩放因子 (以英寸为基准)
    classic_K: float  # 传统推荐的参考 1K 值 (用于回退或经典模式)

    def calc_k(self, Re: float, D_mm: float) -> float:
        """根据雷诺数和内径(mm)计算 Darby 3K 实际局部阻力系数"""
        if Re <= 0 or D_mm <= 0:
            return self.classic_K
        D_in = D_mm / 25.4  # 转换为英寸 (Darby 3K 经验公式必须以英寸为单位)
        D_in = max(D_in, 0.1)  # 避免管径极小时分母异常
        return (self.K1 / Re) + self.K_inf * (1.0 + self.Kd / (D_in**0.3))


# 标准管件数据库（包含经典 1K 值与 Darby 3K 参数）
FITTINGS_3K_DATABASE: list[Fitting3K] = [
    Fitting3K("90°标准弯头(法兰/焊接)", 800.0, 0.091, 4.0, 0.85),
    Fitting3K("90°标准弯头(螺纹)", 800.0, 0.140, 4.0, 1.20),
    Fitting3K("90°长半径弯头(R/D=1.5)", 800.0, 0.056, 3.9, 0.30),
    Fitting3K("45°标准弯头", 500.0, 0.071, 4.2, 0.35),
    Fitting3K("180°回弯头", 1000.0, 0.120, 4.0, 2.00),
    Fitting3K("三通(直通)", 150.0, 0.050, 4.0, 0.30),
    Fitting3K("三通(侧流/分流)", 500.0, 0.274, 4.0, 1.50),
    Fitting3K("三通(支管汇流)", 800.0, 0.350, 4.0, 1.80),
    Fitting3K("闸阀(全开)", 300.0, 0.037, 3.9, 0.20),
    Fitting3K("闸阀(1/2开)", 1000.0, 0.850, 3.9, 2.20),
    Fitting3K("闸阀(1/4开)", 2500.0, 12.000, 3.9, 25.00),
    Fitting3K("截止阀(全开)", 1500.0, 1.700, 3.6, 10.00),
    Fitting3K("球阀(全开)", 300.0, 0.017, 3.5, 0.08),
    Fitting3K("蝶阀(全开)", 800.0, 0.250, 4.0, 0.40),
    Fitting3K("止回阀(旋启式)", 1500.0, 0.460, 4.0, 2.50),
    Fitting3K("止回阀(升降式)", 2000.0, 2.000, 3.8, 10.00),
    Fitting3K("底阀(带滤网)", 2500.0, 3.000, 3.5, 15.00),
    Fitting3K("管道入口(锐边)", 160.0, 0.500, 0.0, 0.50),
    Fitting3K("管道入口(倒角/圆角)", 160.0, 0.200, 0.0, 0.20),
    Fitting3K("管道出口", 0.0, 1.000, 0.0, 1.00),
]

# 保留与旧代码的兼容列表 (管件名称, 经典K值)
LOCAL_RESISTANCE_COMPONENTS = [(f.name, f.classic_K) for f in FITTINGS_3K_DATABASE]


@dataclass
class LocalResistanceData:
    K_total: float = 0.0
    components: list[LocalResistanceComponent] = field(default_factory=list)

    def calculate_K_total(self) -> float:
        if self.components:
            self.K_total = sum(c.total_K for c in self.components)
        return self.K_total


@dataclass
class CalculationStep:
    name: str
    formula: str
    input_values: dict[str, float]
    result: float
    unit: str = ""


@dataclass
class CalculationOptions:
    include_static_head: bool = False
    friction_correlation: str = (
        "churchill"  # "churchill", "swamee_jain", "colebrook_white", "haaland"
    )
    local_resistance_method: str = "darby_3k"  # "darby_3k", "constant_k"


@dataclass
class CalculationResult:
    dp_major_Pa: float
    dp_minor_Pa: float
    dp_friction_loss_Pa: float  # 流动摩擦阻力总损失 (沿程+局部，恒>=0)
    dp_friction_loss_kPa: float
    dp_static_Pa: float  # 高程静压差 (+: 克服爬坡阻力所需附加压差; -: 自流升压)
    dp_total_Pa: float  # 系统进出口总压差 (dp_friction_loss + dp_static)
    dp_total_kPa: float
    velocity_m_s: float
    Re: float
    flow_regime: str
    friction_factor: float
    area_m2: float
    rho_used_kg_m3: float
    mu_used_Pa_s: float
    epsilon_over_D: float
    warnings: list[str]
    friction_model_used: str = "Churchill (1977)"
    local_method_used: str = "Darby 3K"
    calculation_steps: list[CalculationStep] = field(default_factory=list)
    formulas_used: dict[str, str] = field(default_factory=dict)
