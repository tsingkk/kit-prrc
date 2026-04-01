from dataclasses import dataclass, field
from typing import Optional, List, Dict


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
    Q_m3_h: Optional[float] = None
    v_m_s: Optional[float] = None
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


LOCAL_RESISTANCE_COMPONENTS = [
    ("90°标准弯头", 0.85),
    ("90°长半径弯头", 0.3),
    ("45°标准弯头", 0.35),
    ("180°回弯头", 2.0),
    ("三通(直通)", 0.3),
    ("三通(侧流)", 1.5),
    ("三通(汇流)", 1.8),
    ("闸阀(全开)", 0.2),
    ("闸阀(1/2开)", 2.2),
    ("闸阀(1/4开)", 25.0),
    ("截止阀(全开)", 10.0),
    ("球阀(全开)", 0.08),
    ("蝶阀(全开)", 0.4),
    ("止回阀(旋启式)", 2.5),
    ("止回阀(升降式)", 10.0),
    ("底阀(带滤网)", 15.0),
    ("突然扩大", 0.75),
    ("突然缩小", 0.5),
    ("管道入口(锐边)", 0.5),
    ("管道入口(倒角)", 0.2),
    ("管道出口", 1.0),
]


@dataclass
class LocalResistanceData:
    K_total: float = 0.0
    components: List[LocalResistanceComponent] = field(default_factory=list)

    def calculate_K_total(self) -> float:
        if self.components:
            self.K_total = sum(c.total_K for c in self.components)
        return self.K_total


@dataclass
class CalculationStep:
    name: str
    formula: str
    input_values: Dict[str, float]
    result: float
    unit: str = ""


@dataclass
class CalculationOptions:
    include_static_head: bool = False
    friction_correlation: str = "auto"


@dataclass
class CalculationResult:
    dp_major_Pa: float
    dp_minor_Pa: float
    dp_static_Pa: float
    dp_total_Pa: float
    dp_total_kPa: float
    velocity_m_s: float
    Re: float
    flow_regime: str
    friction_factor: float
    area_m2: float
    rho_used_kg_m3: float
    mu_used_Pa_s: float
    epsilon_over_D: float
    warnings: List[str]
    calculation_steps: List[CalculationStep] = field(default_factory=list)
    formulas_used: Dict[str, str] = field(default_factory=dict)
