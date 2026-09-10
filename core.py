import math
from typing import Optional, Tuple
from models import (
    PipeData,
    FluidData,
    OperatingConditions,
    LocalResistanceData,
    CalculationOptions,
    CalculationResult,
    CalculationStep,
    FITTINGS_3K_DATABASE,
)

G = 9.80665

RE_LAMINAR上限 = 2300
RE_TURBULENT下限 = 4000
RE_SWAMEE_JAIN_MIN = 5000
RE_SWAMEE_JAIN_MAX = 1e8
EPSILON_OVER_D_MIN = 1e-6
EPSILON_OVER_D_MAX = 1e-2

# 建立 3K 快速映射表
_FITTINGS_3K_MAP = {f.name: f for f in FITTINGS_3K_DATABASE}


def calc_pressure_drop(
    pipe_data: PipeData,
    fluid_data: FluidData,
    operating_conditions: OperatingConditions,
    local_resistance: LocalResistanceData,
    options: Optional[CalculationOptions] = None,
) -> CalculationResult:
    if options is None:
        options = CalculationOptions()

    warnings = []
    calculation_steps = []
    formulas_used = {}

    D_m = pipe_data.D_mm / 1000.0
    epsilon_m = pipe_data.epsilon_mm / 1000.0
    L_m = pipe_data.L_m

    formulas_used["单位转换"] = (
        "D_m = D_mm / 1000\nε_m = ε_mm / 1000\nQ_m³/s = Q_m³/h / 3600\nμ_Pa·s = μ_mPa·s / 1000"
    )

    # 几何与物理边界严格校验
    if D_m <= 0:
        raise ValueError("管内径必须为正数")
    if L_m < 0:
        raise ValueError("管道长度不能为负数")
    if epsilon_m < 0:
        raise ValueError("绝对粗糙度不能为负数")
    if epsilon_m >= D_m:
        raise ValueError(
            f"绝对粗糙度 ({pipe_data.epsilon_mm} mm) 不能大于或等于管内径 ({pipe_data.D_mm} mm)"
        )

    rho = fluid_data.rho_kg_m3
    mu_Pa_s = fluid_data.mu_mPa_s / 1000.0

    if rho <= 0:
        raise ValueError("流体密度必须为正数")
    if mu_Pa_s <= 0:
        raise ValueError("动力黏度必须为正数")

    A_m2 = math.pi * D_m**2 / 4.0
    calculation_steps.append(
        CalculationStep(
            name="截面积计算",
            formula="A = πD²/4",
            input_values={"D": D_m},
            result=A_m2,
            unit="m²",
        )
    )
    formulas_used["截面积"] = "A = πD²/4"

    # 计算体积流量
    Q_m3_s = None
    if operating_conditions.use_flow_rate:
        if operating_conditions.Q_m3_h is not None:
            if operating_conditions.Q_m3_h < 0:
                raise ValueError("流量不能为负数")
            Q_m3_s = operating_conditions.Q_m3_h / 3600.0
    else:
        v_input = operating_conditions.v_m_s
        if v_input is not None:
            if v_input < 0:
                raise ValueError("流速不能为负数")
            Q_m3_s = v_input * A_m2

    if Q_m3_s is None:
        raise ValueError("必须提供体积流量或流速")

    epsilon_over_D = epsilon_m / D_m

    # 边界情况：零流量处理
    if Q_m3_s == 0.0:
        v_m_s = 0.0
        Re = 0.0
        f = 0.0
        flow_regime = "laminar"
        dp_major_Pa = 0.0
        dp_minor_Pa = 0.0
        dp_friction_loss_Pa = 0.0
        dp_friction_loss_kPa = 0.0

        dp_static_Pa = 0.0
        if options.include_static_head:
            z_in = operating_conditions.z_in_m
            z_out = operating_conditions.z_out_m
            dp_static_Pa = rho * G * (z_out - z_in)
            calculation_steps.append(
                CalculationStep(
                    name="静压差计算",
                    formula="ΔP_static = ρg(z_out - z_in)",
                    input_values={"ρ": rho, "g": G, "z_out": z_out, "z_in": z_in},
                    result=dp_static_Pa,
                    unit="Pa",
                )
            )
            formulas_used["静压差"] = "ΔP_static = ρg(z_out - z_in)"

        dp_total_Pa = dp_friction_loss_Pa + dp_static_Pa
        dp_total_kPa = dp_total_Pa / 1000.0
        warnings.append("流量为0，流体处于静止状态，沿程与局部摩擦阻力均为0")

        return CalculationResult(
            dp_major_Pa=0.0,
            dp_minor_Pa=0.0,
            dp_friction_loss_Pa=0.0,
            dp_friction_loss_kPa=0.0,
            dp_static_Pa=dp_static_Pa,
            dp_total_Pa=dp_total_Pa,
            dp_total_kPa=dp_total_kPa,
            velocity_m_s=0.0,
            Re=0.0,
            flow_regime=flow_regime,
            friction_factor=0.0,
            area_m2=A_m2,
            rho_used_kg_m3=rho,
            mu_used_Pa_s=mu_Pa_s,
            epsilon_over_D=epsilon_over_D,
            warnings=warnings,
            friction_model_used=options.friction_correlation,
            local_method_used=options.local_resistance_method,
            calculation_steps=calculation_steps,
            formulas_used=formulas_used,
        )

    # 正常流动计算
    v_m_s = Q_m3_s / A_m2
    calculation_steps.append(
        CalculationStep(
            name="流速计算",
            formula="v = Q/A",
            input_values={"Q": Q_m3_s, "A": A_m2},
            result=v_m_s,
            unit="m/s",
        )
    )
    formulas_used["流速"] = "v = Q/A"

    # 流速过高工程预警
    if rho >= 500 and v_m_s > 5.0:
        warnings.append(
            f"管内流速 {v_m_s:.2f} m/s 偏高（液体推荐流速通常在 1.0~3.0 m/s 之间，流速过大易导致剧烈磨损与高阻力）"
        )
    elif rho < 500 and v_m_s > 40.0:
        warnings.append(
            f"气相流速 {v_m_s:.2f} m/s 偏高，请注意检查噪音与压降损耗"
        )

    try:
        Re = rho * v_m_s * D_m / mu_Pa_s
        if not math.isfinite(Re) or Re < 0:
            raise ValueError("雷诺数计算结果无效")
    except (OverflowError, ValueError) as e:
        raise ValueError(f"雷诺数计算错误: {e}")

    calculation_steps.append(
        CalculationStep(
            name="雷诺数计算",
            formula="Re = ρvD/μ",
            input_values={"ρ": rho, "v": v_m_s, "D": D_m, "μ": mu_Pa_s},
            result=Re,
            unit="",
        )
    )
    formulas_used["雷诺数"] = "Re = ρvD/μ"

    # 流态判定
    if Re < RE_LAMINAR上限:
        flow_regime = "laminar"
    elif Re < RE_TURBULENT下限:
        flow_regime = "transition"
        warnings.append(
            f"雷诺数 Re={Re:.1f} 处于临界过渡流区 (2300≤Re<4000)，流动存在层流与湍流交替脉动，计算结果具有一定不确定性"
        )
    else:
        flow_regime = "turbulent"

    # 计算摩擦因子
    f, f_formula, model_name = calculate_friction_factor(
        Re, D_m, epsilon_m, options, warnings
    )
    calculation_steps.append(
        CalculationStep(
            name=f"摩擦因子计算 ({model_name})",
            formula=f_formula,
            input_values={"Re": Re, "D": D_m, "ε": epsilon_m, "ε/D": epsilon_over_D},
            result=f,
            unit="",
        )
    )
    formulas_used["摩擦因子"] = f_formula

    # 动压计算
    dynamic_pressure = rho * v_m_s**2 / 2.0
    calculation_steps.append(
        CalculationStep(
            name="动压计算",
            formula="P_dyn = ρv²/2",
            input_values={"ρ": rho, "v": v_m_s},
            result=dynamic_pressure,
            unit="Pa",
        )
    )
    formulas_used["动压"] = "P_dyn = ρv²/2"

    # 沿程阻力压降
    dp_major_Pa = f * (L_m / D_m) * dynamic_pressure
    calculation_steps.append(
        CalculationStep(
            name="沿程阻力压降",
            formula="ΔP_major = f·(L/D)·(ρv²/2)",
            input_values={"f": f, "L": L_m, "D": D_m, "ρv²/2": dynamic_pressure},
            result=dp_major_Pa,
            unit="Pa",
        )
    )
    formulas_used["沿程阻力压降"] = "ΔP_major = f·(L/D)·(ρv²/2)"

    # 局部阻力计算 (支持 Darby 3K 与 经典 1K)
    dp_minor_Pa, K_total, local_method_desc = calculate_minor_loss(
        local_resistance=local_resistance,
        Re=Re,
        D_mm=pipe_data.D_mm,
        dynamic_pressure=dynamic_pressure,
        options=options,
        warnings=warnings,
    )
    calculation_steps.append(
        CalculationStep(
            name=f"局部阻力压降 ({local_method_desc})",
            formula="ΔP_minor = Σ(K_i·n_i)·(ρv²/2)",
            input_values={"等效总K值": K_total, "ρv²/2": dynamic_pressure},
            result=dp_minor_Pa,
            unit="Pa",
        )
    )
    formulas_used["局部阻力压降"] = f"ΔP_minor = Σ(K_i·n_i)·(ρv²/2) [{local_method_desc}]"

    # 水力流动总摩擦损失 (不可逆能耗，恒为非负)
    dp_friction_loss_Pa = dp_major_Pa + dp_minor_Pa
    dp_friction_loss_kPa = dp_friction_loss_Pa / 1000.0
    calculation_steps.append(
        CalculationStep(
            name="水力摩擦总损失",
            formula="ΔP_friction = ΔP_major + ΔP_minor",
            input_values={"ΔP_major": dp_major_Pa, "ΔP_minor": dp_minor_Pa},
            result=dp_friction_loss_Pa,
            unit="Pa",
        )
    )
    formulas_used["水力摩擦总损失"] = "ΔP_friction = ΔP_major + ΔP_minor"

    # 高程静压差
    dp_static_Pa = 0.0
    if options.include_static_head:
        z_in = operating_conditions.z_in_m
        z_out = operating_conditions.z_out_m
        dp_static_Pa = rho * G * (z_out - z_in)
        calculation_steps.append(
            CalculationStep(
                name="高程静压差",
                formula="ΔP_static = ρg(z_out - z_in)",
                input_values={"ρ": rho, "g": G, "z_out": z_out, "z_in": z_in},
                result=dp_static_Pa,
                unit="Pa",
            )
        )
        formulas_used["高程静压差"] = "ΔP_static = ρg(z_out - z_in)"

        if z_out < z_in:
            warnings.append(
                f"出口高程(z_out={z_out}m)低于进口(z_in={z_in}m)，重力位能转为静压（自流升压 {-dp_static_Pa/1000.0:.3f} kPa）"
            )

    # 进出口所需总压差
    dp_total_Pa = dp_friction_loss_Pa + dp_static_Pa
    dp_total_kPa = dp_total_Pa / 1000.0

    calculation_steps.append(
        CalculationStep(
            name="系统总压差计算",
            formula="ΔP_total = ΔP_friction + ΔP_static",
            input_values={
                "ΔP_friction": dp_friction_loss_Pa,
                "ΔP_static": dp_static_Pa,
            },
            result=dp_total_Pa,
            unit="Pa",
        )
    )
    formulas_used["系统总压差"] = "ΔP_total = ΔP_friction + ΔP_static"

    return CalculationResult(
        dp_major_Pa=dp_major_Pa,
        dp_minor_Pa=dp_minor_Pa,
        dp_friction_loss_Pa=dp_friction_loss_Pa,
        dp_friction_loss_kPa=dp_friction_loss_kPa,
        dp_static_Pa=dp_static_Pa,
        dp_total_Pa=dp_total_Pa,
        dp_total_kPa=dp_total_kPa,
        velocity_m_s=v_m_s,
        Re=Re,
        flow_regime=flow_regime,
        friction_factor=f,
        area_m2=A_m2,
        rho_used_kg_m3=rho,
        mu_used_Pa_s=mu_Pa_s,
        epsilon_over_D=epsilon_over_D,
        warnings=warnings,
        friction_model_used=model_name,
        local_method_used=local_method_desc,
        calculation_steps=calculation_steps,
        formulas_used=formulas_used,
    )


def calculate_friction_factor(
    Re: float, D_m: float, epsilon_m: float, options: CalculationOptions, warnings: list
) -> Tuple[float, str, str]:
    """根据雷诺数、相对粗糙度与用户配置计算达西摩擦系数 f"""
    epsilon_over_D = epsilon_m / D_m
    correlation = (options.friction_correlation or "churchill").lower()

    # 1. 优先推荐：Churchill (1977) 全流态连续显式方程 (无断点、无除零、处处光滑可导)
    if correlation in ("churchill", "auto"):
        f, formula = churchill_1977(Re, epsilon_over_D)
        return f, formula, "Churchill (1977)"

    # 2. 分段模型：层流哈根-泊肃叶定律
    if Re < RE_LAMINAR上限:
        f = 64.0 / Re
        formula = "f = 64/Re (层流 Hagen-Poiseuille)"
        return f, formula, "层流公式 (64/Re)"

    # 3. 分段模型：过渡流区 (2300 <= Re < 4000)
    elif Re < RE_TURBULENT下限:
        f_laminar_end = 64.0 / RE_LAMINAR上限
        # 在湍流端点 Re=4000 计算湍流摩擦因子
        if correlation == "colebrook_white":
            f_turb_end, _ = colebrook_white_solve(RE_TURBULENT下限, epsilon_over_D)
        elif correlation == "haaland":
            f_turb_end, _ = haaland(RE_TURBULENT下限, epsilon_over_D)
        else:
            f_turb_end, _ = swamee_jain(RE_TURBULENT下限, epsilon_over_D)

        # 正确计算线性插值权重 alpha, 严防除零错误
        delta_re = RE_TURBULENT下限 - RE_LAMINAR上限
        alpha = (Re - RE_LAMINAR上限) / delta_re
        f = f_laminar_end + alpha * (f_turb_end - f_laminar_end)
        formula = (
            f"f = f_laminar + α·(f_turbulent - f_laminar), "
            f"α=({Re:.1f}-2300)/1700={alpha:.4f} (过渡流端点插值)"
        )
        return f, formula, "过渡流线性插值"

    # 4. 分段模型：湍流区 (Re >= 4000)
    else:
        if correlation == "colebrook_white":
            f, formula = colebrook_white_solve(Re, epsilon_over_D)
            return f, formula, "Colebrook-White"
        elif correlation == "haaland":
            f, formula = haaland(Re, epsilon_over_D)
            return f, formula, "Haaland"
        else:
            # 默认 Swamee-Jain
            if Re < RE_SWAMEE_JAIN_MIN or Re > RE_SWAMEE_JAIN_MAX:
                warnings.append(
                    f"雷诺数 Re={Re:.0f} 超出Swamee-Jain公式推荐范围(5000 < Re < 10⁸)"
                )
            if (
                epsilon_over_D < EPSILON_OVER_D_MIN
                or epsilon_over_D > EPSILON_OVER_D_MAX
            ):
                if epsilon_over_D > 0:
                    warnings.append(
                        f"相对粗糙度 ε/D={epsilon_over_D:.6f} 超出Swamee-Jain推荐范围(10⁻⁶ < ε/D < 10⁻²)"
                    )
            f, formula = swamee_jain(Re, epsilon_over_D)
            return f, formula, "Swamee-Jain"


def churchill_1977(Re: float, epsilon_over_D: float) -> Tuple[float, str]:
    """Stuart Churchill (1977) 全流态连续显式达西摩擦系数模型"""
    if Re <= 0:
        return 0.0, "f = 0"
    term_laminar = (8.0 / Re) ** 12

    # 保护对数定义域
    inner_log = (7.0 / Re) ** 0.9 + 0.27 * epsilon_over_D
    inner_log = max(inner_log, 1e-15)

    A = (2.457 * math.log(1.0 / inner_log)) ** 16
    B = (37530.0 / Re) ** 16

    term_turbulent = (A + B) ** (-1.5)
    f = 8.0 * (term_laminar + term_turbulent) ** (1.0 / 12.0)
    formula = (
        "f = 8·[(8/Re)¹² + (A + B)⁻¹.⁵]¹/¹²\n"
        "A = [2.457·ln(1/((7/Re)⁰·⁹ + 0.27·(ε/D)))]¹⁶\n"
        "B = (37530/Re)¹⁶ (Churchill 1977 全流态连续公式)"
    )
    return f, formula


def swamee_jain(Re: float, epsilon_over_D: float) -> Tuple[float, str]:
    """Swamee-Jain 显式湍流摩擦系数模型"""
    try:
        term1 = epsilon_over_D / 3.7
        term2 = 5.74 / (Re**0.9)
        inner = max(term1 + term2, 1e-15)
        denominator = math.log10(inner)
        if denominator == 0:
            raise ValueError("Swamee-Jain公式分母为零")
        f = 0.25 / (denominator**2)
        return f, "f = 0.25 / [log₁₀(ε/(3.7D) + 5.74/Re⁰·⁹)]²"
    except (ValueError, ZeroDivisionError, OverflowError) as e:
        raise ValueError(f"无法计算摩擦因子: {e}")


def haaland(Re: float, epsilon_over_D: float) -> Tuple[float, str]:
    """Haaland (1983) 显式湍流摩擦系数模型"""
    try:
        term1 = (epsilon_over_D / 3.7) ** 1.11
        term2 = 6.9 / Re
        inner = max(term1 + term2, 1e-15)
        denominator = -1.8 * math.log10(inner)
        if denominator == 0:
            raise ValueError("Haaland公式分母为零")
        f = (1.0 / denominator) ** 2
        return f, "1/√f = -1.8·log₁₀[(ε/(3.7D))¹·¹¹ + 6.9/Re] (Haaland)"
    except (ValueError, ZeroDivisionError, OverflowError) as e:
        raise ValueError(f"Haaland计算错误: {e}")


def colebrook_white_solve(
    Re: float, epsilon_over_D: float, max_iter: int = 40, tol: float = 1e-8
) -> Tuple[float, str]:
    """Colebrook-White 隐式超越方程高精度牛顿-拉夫逊法迭代求解"""
    if Re <= 0:
        return 0.0, "f = 0"

    # 使用 Haaland 公式作为优良初值
    f_init, _ = haaland(Re, epsilon_over_D)
    x = 1.0 / math.sqrt(max(f_init, 1e-10))  # x = 1 / sqrt(f)

    # 求解 F(x) = x + 2.0 * log10(ε/(3.7D) + 2.51*x/Re) = 0
    ln10 = math.log(10.0)
    for _ in range(max_iter):
        arg = epsilon_over_D / 3.7 + (2.51 / Re) * x
        if arg <= 0:
            arg = 1e-15
        fx = x + 2.0 * math.log10(arg)
        # 导数 F'(x) = 1 + (2 / ln10) * (2.51 / Re) / arg
        dfx = 1.0 + (2.0 / ln10) * (2.51 / Re) / arg
        dx = fx / dfx
        x -= dx
        if abs(dx) < tol:
            break

    f = 1.0 / (x**2)
    formula = "1/√f = -2.0·log₁₀[ε/(3.7D) + 2.51/(Re·√f)] (Colebrook-White 隐式迭代求解)"
    return f, formula


def calculate_minor_loss(
    local_resistance: LocalResistanceData,
    Re: float,
    D_mm: float,
    dynamic_pressure: float,
    options: CalculationOptions,
    warnings: list,
) -> Tuple[float, float, str]:
    """计算局部阻力损失，支持 Darby 3K 高保真模型与经典 1K 常数法"""
    method = (options.local_resistance_method or "darby_3k").lower()

    if not local_resistance.components:
        return 0.0, 0.0, "无管件"

    total_k = 0.0
    if method == "darby_3k":
        # Darby 3K 动态求解
        desc = "Darby 3K 动态模型"
        for comp in local_resistance.components:
            if comp.count <= 0:
                continue
            fitting_def = _FITTINGS_3K_MAP.get(comp.name)
            if fitting_def is not None:
                k_i = fitting_def.calc_k(Re, D_mm)
            else:
                k_i = comp.K
            total_k += k_i * comp.count

        if Re < RE_LAMINAR上限 and total_k > sum(
            c.total_K for c in local_resistance.components
        ):
            warnings.append(
                "低雷诺数下触发 Darby 3K 粘性增强修正，管件实际局部阻力系数已自动放大"
            )
    else:
        # 经典 1K 常数相加法
        desc = "经典 1K 恒定常数法"
        total_k = sum(c.total_K for c in local_resistance.components)

    dp_minor_Pa = total_k * dynamic_pressure
    return dp_minor_Pa, total_k, desc
