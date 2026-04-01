import math
from typing import Optional
from models import (
    PipeData,
    FluidData,
    OperatingConditions,
    LocalResistanceData,
    CalculationOptions,
    CalculationResult,
    CalculationStep,
)

G = 9.80665

RE_LAMINAR上限 = 2300
RE_TURBULENT下限 = 4000
RE_SWAMEE_JAIN_MIN = 5000
RE_SWAMEE_JAIN_MAX = 1e8
EPSILON_OVER_D_MIN = 1e-6
EPSILON_OVER_D_MAX = 1e-2


def calc_pressure_drop(
    pipe_data: PipeData,
    fluid_data: FluidData,
    operating_conditions: OperatingConditions,
    local_resistance: LocalResistanceData,
    options: CalculationOptions,
) -> CalculationResult:
    warnings = []
    calculation_steps = []
    formulas_used = {}

    D_m = pipe_data.D_mm / 1000.0
    epsilon_m = pipe_data.epsilon_mm / 1000.0
    L_m = pipe_data.L_m

    formulas_used["单位转换"] = (
        "D_m = D_mm / 1000\nε_m = ε_mm / 1000\nQ_m³/s = Q_m³/h / 3600\nμ_Pa·s = μ_mPa·s / 1000"
    )

    if D_m <= 0:
        raise ValueError("管内径必须为正数")
    if L_m < 0:
        raise ValueError("管道长度不能为负数")
    if epsilon_m < 0:
        raise ValueError("绝对粗糙度不能为负数")

    Q_m3_s = None
    if operating_conditions.use_flow_rate:
        if operating_conditions.Q_m3_h is not None:
            Q_m3_s = operating_conditions.Q_m3_h / 3600.0
    else:
        v_input = operating_conditions.v_m_s
        if v_input is not None:
            A_temp = math.pi * (D_m**2) / 4.0
            Q_m3_s = v_input * A_temp

    rho = fluid_data.rho_kg_m3
    mu_Pa_s = fluid_data.mu_mPa_s / 1000.0

    if rho <= 0:
        raise ValueError("流体密度必须为正数")
    if mu_Pa_s <= 0:
        raise ValueError("动力黏度必须为正数")
    if Q_m3_s is None or Q_m3_s <= 0:
        raise ValueError("流量必须为正数")

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

    try:
        Re = rho * v_m_s * D_m / mu_Pa_s
        if not math.isfinite(Re) or Re <= 0:
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

    if Re < RE_LAMINAR上限:
        flow_regime = "laminar"
        regime_text = "层流"
    elif Re < RE_TURBULENT下限:
        flow_regime = "transition"
        regime_text = "过渡流"
        warnings.append(
            f"雷诺数 {Re:.2f} 处于过渡流区(2300≤Re<4000)，计算结果具有较大不确定性"
        )
    else:
        flow_regime = "turbulent"
        regime_text = "湍流"

    f, f_formula = calculate_friction_factor(Re, D_m, epsilon_m, options, warnings)
    calculation_steps.append(
        CalculationStep(
            name="摩擦因子计算",
            formula=f_formula,
            input_values={"Re": Re, "D": D_m, "ε": epsilon_m},
            result=f,
            unit="",
        )
    )

    epsilon_over_D = epsilon_m / D_m
    calculations_valid = True

    if flow_regime == "turbulent":
        if Re < RE_SWAMEE_JAIN_MIN or Re > RE_SWAMEE_JAIN_MAX:
            warnings.append(
                f"雷诺数 Re={Re:.0f} 超出Swamee-Jain公式推荐范围(5000 < Re < 10⁸)"
            )
        if epsilon_over_D < EPSILON_OVER_D_MIN or epsilon_over_D > EPSILON_OVER_D_MAX:
            warnings.append(
                f"相对粗糙度 ε/D={epsilon_over_D:.6f} 超出Swamee-Jain公式推荐范围(10⁻⁶ < ε/D < 10⁻²)"
            )

    dynamic_pressure = rho * v_m_s**2 / 2.0
    calculation_steps.append(
        CalculationStep(
            name="动压头计算",
            formula="P_dyn = ρv²/2",
            input_values={"ρ": rho, "v": v_m_s},
            result=dynamic_pressure,
            unit="Pa",
        )
    )
    formulas_used["动压头"] = "P_dyn = ρv²/2"

    dp_major_Pa = f * (L_m / D_m) * dynamic_pressure
    calculation_steps.append(
        CalculationStep(
            name="沿程压降计算",
            formula="ΔP_major = f·(L/D)·(ρv²/2)",
            input_values={"f": f, "L": L_m, "D": D_m, "ρv²/2": dynamic_pressure},
            result=dp_major_Pa,
            unit="Pa",
        )
    )
    formulas_used["沿程压降"] = "ΔP_major = f·(L/D)·(ρv²/2)"

    K_total = local_resistance.K_total
    if local_resistance.components:
        K_total = local_resistance.calculate_K_total()

    dp_minor_Pa = K_total * dynamic_pressure
    calculation_steps.append(
        CalculationStep(
            name="局部压降计算",
            formula="ΔP_minor = Σ(K_i·n_i)·(ρv²/2)",
            input_values={"ΣKi": K_total, "ρv²/2": dynamic_pressure},
            result=dp_minor_Pa,
            unit="Pa",
        )
    )
    formulas_used["局部压降"] = "ΔP_minor = Σ(K_i·n_i)·(ρv²/2)"

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

    dp_total_Pa = dp_major_Pa + dp_minor_Pa + dp_static_Pa
    calculation_steps.append(
        CalculationStep(
            name="总压降计算",
            formula="ΔP_total = ΔP_major + ΔP_minor + ΔP_static",
            input_values={
                "ΔP_major": dp_major_Pa,
                "ΔP_minor": dp_minor_Pa,
                "ΔP_static": dp_static_Pa,
            },
            result=dp_total_Pa,
            unit="Pa",
        )
    )
    formulas_used["总压降"] = "ΔP_total = ΔP_major + ΔP_minor + ΔP_static"

    dp_total_kPa = dp_total_Pa / 1000.0

    return CalculationResult(
        dp_major_Pa=dp_major_Pa,
        dp_minor_Pa=dp_minor_Pa,
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
        calculation_steps=calculation_steps,
        formulas_used=formulas_used,
    )


def calculate_friction_factor(
    Re: float, D_m: float, epsilon_m: float, options: CalculationOptions, warnings: list
) -> tuple:
    epsilon_over_D = epsilon_m / D_m

    if Re < RE_LAMINAR上限:
        f = 64.0 / Re
        formula = "f = 64/Re (层流)"
        return f, formula

    elif Re < RE_TURBULENT下限:
        f_laminar = 64.0 / RE_LAMINAR上限
        f_turbulent, _ = swamee_jain(Re, epsilon_over_D)
        alpha = (Re - RE_LAMINAR上限) / (RE_TURBULENT下限 - RE_LAMINAR上限)
        f = f_laminar + alpha * (f_turbulent - f_laminar)
        formula = f"f = f_laminar + α(f_turbulent - f_laminar), α={(RE_TURBULENT下限 - RE_LAMINAR上限) / (Re - RE_LAMINAR上限):.4f} (过渡流插值)"
        return f, formula

    else:
        f, _ = swamee_jain(Re, epsilon_over_D)
        formula = "f = 0.25 / [log₁₀(ε/(3.7D) + 5.74/Re^0.9)]² (Swamee-Jain)"
        return f, formula


def swamee_jain(Re: float, epsilon_over_D: float) -> tuple:
    try:
        term1 = epsilon_over_D / 3.7
        term2 = 5.74 / (Re**0.9)
        denominator = math.log10(term1 + term2)
        if denominator == 0:
            raise ValueError("Swamee-Jain公式分母为零")
        f = 0.25 / (denominator**2)
        return f, "f = 0.25 / [log₁₀(ε/(3.7D) + 5.74/Re^0.9)]²"
    except (ValueError, ZeroDivisionError, OverflowError) as e:
        raise ValueError(f"无法计算摩擦因子: {e}")
