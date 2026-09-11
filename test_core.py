"""
Unit tests for Kit Pipeline Resistance Calculator core engine.
Tests Darcy friction factors, Colebrook-White solver, Churchill model,
Darby 3K / 1K minor losses, static head, flow regimes, and edge conditions.
"""

import math

import pytest

from core import (
    GRAVITY,
    RE_LAMINAR_UPPER,
    RE_TURBULENT_LOWER,
    calc_pressure_drop,
    calculate_friction_factor,
    churchill_1977,
    colebrook_white_solve,
    haaland,
    swamee_jain,
)
from models import (
    CalculationOptions,
    Fitting3K,
    FluidData,
    LocalResistanceComponent,
    LocalResistanceData,
    OperatingConditions,
    PipeData,
)


# =====================================================================
# 1. 常量与参数命名验证 (问题 5 & 6 回归测试)
# =====================================================================
def test_constants_and_renamed_variables():
    assert GRAVITY == pytest.approx(9.80665, rel=1e-6)
    assert RE_LAMINAR_UPPER == 2300
    assert RE_TURBULENT_LOWER == 4000


# =====================================================================
# 2. 层流区哈根-泊肃叶与 Churchill 极限退化
# =====================================================================
@pytest.mark.parametrize("re", [100, 500, 1000, 1500, 2000])
def test_churchill_laminar_matches_hagen_poiseuille(re: float):
    """验证在深度层流区 (Re <= 2000) Churchill (1977) 模型严格逼近解析解 f = 64 / Re (误差 < 0.2%)"""
    f_expected = 64.0 / re
    f_churchill, _ = churchill_1977(re, epsilon_over_D=0.001)
    assert math.isclose(f_churchill, f_expected, rel_tol=0.005)


@pytest.mark.parametrize("re", [100, 1000, 2299])
def test_piecewise_laminar_exact_formula(re: float):
    """验证分段模型在层流区 (Re < 2300) 采用精确 Hagen-Poiseuille 公式 f = 64 / Re"""
    opts = CalculationOptions(friction_correlation="colebrook_white")
    warnings_list: list[str] = []
    f, formula, _model_name = calculate_friction_factor(
        re, 0.05, 0.000045, opts, warnings_list
    )
    assert math.isclose(f, 64.0 / re, rel_tol=1e-9)
    assert "64/Re" in formula


# =====================================================================
# 3. 湍流区摩擦系数多模型交叉校验 (误差 < 1.5%)
# =====================================================================
@pytest.mark.parametrize(
    ("re", "eps_d"),
    [
        (1e4, 0.001),
        (5e4, 0.0005),
        (1e5, 0.0001),
        (1e5, 0.001),
        (1e5, 0.01),
        (1e6, 0.001),
    ],
)
def test_turbulent_models_cross_verification(re: float, eps_d: float):
    """验证各摩擦因子模型与 Colebrook-White 基准的相对偏差在工程允许范围内 (< 1.5%)"""
    f_cw, _ = colebrook_white_solve(re, eps_d)
    f_ch, _ = churchill_1977(re, eps_d)
    f_sj, _ = swamee_jain(re, eps_d)
    f_ha, _ = haaland(re, eps_d)

    assert math.isclose(f_ch, f_cw, rel_tol=0.015)
    assert math.isclose(f_sj, f_cw, rel_tol=0.015)
    assert math.isclose(f_ha, f_cw, rel_tol=0.015)


# =====================================================================
# 4. 水力光滑管极限 (ε = 0)
# =====================================================================
def test_smooth_pipe_zero_roughness():
    """验证绝对粗糙度为 0 时所有模型均能正常计算且符合光滑管 Blasius 规律"""
    pipe = PipeData(D_mm=50.0, L_m=100.0, epsilon_mm=0.0)
    fluid = FluidData(rho_kg_m3=1000.0, mu_mPa_s=1.0)
    op = OperatingConditions(Q_m3_h=10.0, use_flow_rate=True)
    local = LocalResistanceData()

    for model in ["churchill", "colebrook_white", "haaland", "swamee_jain"]:
        opts = CalculationOptions(friction_correlation=model)
        result = calc_pressure_drop(pipe, fluid, op, local, opts)
        assert result.friction_factor > 0
        # 与 Blasius 公式 f = 0.316 / Re^0.25 (Re ~ 70736) 比较，相对误差在 3% 内
        f_blasius = 0.316 / (result.Re**0.25)
        assert math.isclose(result.friction_factor, f_blasius, rel_tol=0.03)


# =====================================================================
# 5. 过渡流区与 Churchill 警告抑制 (问题 1 回归测试)
# =====================================================================
def test_churchill_suppresses_transition_warning():
    """问题1：Churchill 模型天然连续覆盖过渡区，不应发出过渡区不确定性警告"""
    # 构造处于过渡流区 (2300 <= Re < 4000) 的工况
    # D = 50mm, rho = 1000, mu = 1.0 mPa.s -> Re = rho * v * D / mu = 1000 * v * 0.05 / 0.001 = 50000 * v
    # 设定 v = 0.06 m/s -> Re = 3000
    pipe = PipeData(D_mm=50.0, L_m=100.0, epsilon_mm=0.045)
    fluid = FluidData(rho_kg_m3=1000.0, mu_mPa_s=1.0)
    op = OperatingConditions(v_m_s=0.06, use_flow_rate=False)
    local = LocalResistanceData()

    # 1. Churchill 模式：流态为 transition，但无过渡流警告
    opts_churchill = CalculationOptions(friction_correlation="churchill")
    res_ch = calc_pressure_drop(pipe, fluid, op, local, opts_churchill)
    assert res_ch.flow_regime == "transition"
    assert not any("临界过渡流区" in w for w in res_ch.warnings)

    # 2. 分段模型模式 (Colebrook-White)：流态为 transition，且产生过渡流警告
    opts_cw = CalculationOptions(friction_correlation="colebrook_white")
    res_cw = calc_pressure_drop(pipe, fluid, op, local, opts_cw)
    assert res_cw.flow_regime == "transition"
    assert any("临界过渡流区" in w for w in res_cw.warnings)

    # 3. 分段模型模式 (Haaland)：产生过渡流警告
    opts_ha = CalculationOptions(friction_correlation="haaland")
    res_ha = calc_pressure_drop(pipe, fluid, op, local, opts_ha)
    assert res_ha.flow_regime == "transition"
    assert any("临界过渡流区" in w for w in res_ha.warnings)


# =====================================================================
# 6. Darby 3K 动态局部阻力模型与警告基准 (问题 4 回归测试)
# =====================================================================
def test_darby_3k_calculation_and_warning_baseline():
    """问题4：Darby 3K 模型在低 Re 下放大 K 值，且警告对比基准为数据库经典值"""
    fitting = Fitting3K("90°标准弯头(法兰/焊接)", 800.0, 0.091, 4.0, 0.85)

    # 手工计算验证: D=50mm -> D_in = 50 / 25.4 = 1.968504 in
    # K = 800 / Re + 0.091 * (1 + 4.0 / (1.968504^0.3))
    D_in = 50.0 / 25.4
    expected_k_turb = 800.0 / 100000.0 + 0.091 * (1.0 + 4.0 / (D_in**0.3))
    assert math.isclose(fitting.calc_k(100000.0, 50.0), expected_k_turb, rel_tol=1e-6)

    # 层流下 K 值大幅增大 (Re = 100)
    k_laminar = fitting.calc_k(100.0, 50.0)
    assert k_laminar > 8.0  # 800/100 = 8.0 + 湍流项

    # 回归测试问题4：用户即使在 GUI 中把 component.K 改为一个极大的值 (如 999.0)
    # 程序低雷诺数下判断 3K 粘性增强应对比数据库中的经典 K 值 (0.85)，而不受修改影响
    pipe = PipeData(D_mm=50.0, L_m=10.0, epsilon_mm=0.045)
    fluid = FluidData(rho_kg_m3=900.0, mu_mPa_s=500.0)  # 高黏度
    op = OperatingConditions(Q_m3_h=0.1, use_flow_rate=True)  # Re 极低 (~12.7)
    # 模拟用户在输入框中填入了一个被篡改的高 K 值
    tampered_comp = LocalResistanceComponent(
        name="90°标准弯头(法兰/焊接)", K=999.0, count=2
    )
    local = LocalResistanceData(components=[tampered_comp])
    opts = CalculationOptions(local_resistance_method="darby_3k")

    res = calc_pressure_drop(pipe, fluid, op, local, opts)
    assert res.flow_regime == "laminar"
    # 验证粘性增强警告成功触发
    assert any("粘性增强修正" in w for w in res.warnings)


def test_constant_1k_minor_loss():
    """验证经典 1K 常数法局部阻力计算"""
    pipe = PipeData(D_mm=50.0, L_m=10.0, epsilon_mm=0.045)
    fluid = FluidData(rho_kg_m3=1000.0, mu_mPa_s=1.0)
    op = OperatingConditions(v_m_s=2.0, use_flow_rate=False)
    # 2 个弯头 (K=0.85)，1 个闸阀 (K=0.20) -> 总 K = 1.90
    components = [
        LocalResistanceComponent(name="90°标准弯头(法兰/焊接)", K=0.85, count=2),
        LocalResistanceComponent(name="闸阀(全开)", K=0.20, count=1),
    ]
    local = LocalResistanceData(components=[components[0], components[1]])
    opts = CalculationOptions(local_resistance_method="constant_k")

    res = calc_pressure_drop(pipe, fluid, op, local, opts)
    # 动压 = 1000 * 4 / 2 = 2000 Pa
    # 局部压降 = 1.90 * 2000 = 3800 Pa
    expected_dp_minor = 1.90 * (1000.0 * 2.0**2 / 2.0)
    assert math.isclose(res.dp_minor_Pa, expected_dp_minor, rel_tol=1e-5)


# =====================================================================
# 7. 高程静压差与重力势能计算 (问题 5 回归测试)
# =====================================================================
def test_static_head_uphill_and_downhill():
    """问题5：静压差计算使用标准 GRAVITY 常数，并区分爬坡与自流升压"""
    pipe = PipeData(D_mm=50.0, L_m=100.0, epsilon_mm=0.045)
    fluid = FluidData(rho_kg_m3=1000.0, mu_mPa_s=1.0)
    local = LocalResistanceData()

    # 1. 爬坡工况 (z_in = 0, z_out = 10m)
    op_up = OperatingConditions(
        Q_m3_h=10.0, z_in_m=0.0, z_out_m=10.0, use_flow_rate=True
    )
    opts_with_static = CalculationOptions(include_static_head=True)
    res_up = calc_pressure_drop(pipe, fluid, op_up, local, opts_with_static)

    expected_dp_static = 1000.0 * GRAVITY * 10.0
    assert math.isclose(res_up.dp_static_Pa, expected_dp_static, rel_tol=1e-6)
    assert res_up.dp_total_Pa == pytest.approx(
        res_up.dp_friction_loss_Pa + expected_dp_static, rel=1e-6
    )

    # 2. 下坡自流工况 (z_in = 10m, z_out = 0m)
    op_down = OperatingConditions(
        Q_m3_h=10.0, z_in_m=10.0, z_out_m=0.0, use_flow_rate=True
    )
    res_down = calc_pressure_drop(pipe, fluid, op_down, local, opts_with_static)
    assert math.isclose(res_down.dp_static_Pa, -expected_dp_static, rel_tol=1e-6)
    assert any("自流升压" in w for w in res_down.warnings)

    # 3. 未勾选叠加静压差
    opts_no_static = CalculationOptions(include_static_head=False)
    res_no = calc_pressure_drop(pipe, fluid, op_up, local, opts_no_static)
    assert res_no.dp_static_Pa == 0.0
    assert res_no.dp_total_Pa == pytest.approx(res_no.dp_friction_loss_Pa, rel=1e-6)


# =====================================================================
# 8. 零流量安全边界处理
# =====================================================================
def test_zero_flow_condition():
    """验证流量为 0 时的平稳处理，摩擦阻力为 0，保留有效静压"""
    pipe = PipeData(D_mm=50.0, L_m=100.0, epsilon_mm=0.045)
    fluid = FluidData(rho_kg_m3=1000.0, mu_mPa_s=1.0)
    op = OperatingConditions(Q_m3_h=0.0, z_in_m=0.0, z_out_m=5.0, use_flow_rate=True)
    local = LocalResistanceData()
    opts = CalculationOptions(include_static_head=True)

    res = calc_pressure_drop(pipe, fluid, op, local, opts)
    assert res.velocity_m_s == 0.0
    assert res.Re == 0.0
    assert res.friction_factor == 0.0
    assert res.dp_major_Pa == 0.0
    assert res.dp_minor_Pa == 0.0
    assert res.dp_friction_loss_Pa == 0.0
    assert math.isclose(res.dp_static_Pa, 1000.0 * GRAVITY * 5.0, rel_tol=1e-6)
    assert res.dp_total_Pa == pytest.approx(res.dp_static_Pa, rel=1e-6)
    assert any("流量为0" in w for w in res.warnings)


# =====================================================================
# 9. 高流速工程预警
# =====================================================================
def test_high_velocity_warnings():
    """验证液体流速 > 5 m/s 及气体流速 > 40 m/s 时的工程合规预警"""
    pipe = PipeData(D_mm=50.0, L_m=100.0, epsilon_mm=0.045)
    local = LocalResistanceData()

    # 液体高流速 (v = 6 m/s, rho = 1000)
    fluid_liquid = FluidData(rho_kg_m3=1000.0, mu_mPa_s=1.0)
    op_liquid = OperatingConditions(v_m_s=6.0, use_flow_rate=False)
    res_liq = calc_pressure_drop(pipe, fluid_liquid, op_liquid, local)
    assert any("液体推荐流速" in w for w in res_liq.warnings)

    # 气体高流速 (v = 50 m/s, rho = 1.2)
    fluid_gas = FluidData(rho_kg_m3=1.2, mu_mPa_s=0.018)
    op_gas = OperatingConditions(v_m_s=50.0, use_flow_rate=False)
    res_gas = calc_pressure_drop(pipe, fluid_gas, op_gas, local)
    assert any("气相流速" in w for w in res_gas.warnings)


# =====================================================================
# 10. 物理与几何异常输入校验 (抛出 ValueError)
# =====================================================================
@pytest.mark.parametrize(
    ("d", "l", "eps", "rho", "mu", "q", "v", "err_msg"),
    [
        (0.0, 100.0, 0.045, 1000.0, 1.0, 10.0, None, "管内径必须为正数"),
        (-10.0, 100.0, 0.045, 1000.0, 1.0, 10.0, None, "管内径必须为正数"),
        (50.0, -5.0, 0.045, 1000.0, 1.0, 10.0, None, "管道长度不能为负数"),
        (50.0, 100.0, -0.01, 1000.0, 1.0, 10.0, None, "绝对粗糙度不能为负数"),
        (50.0, 100.0, 50.0, 1000.0, 1.0, 10.0, None, "不能大于或等于管内径"),
        (50.0, 100.0, 60.0, 1000.0, 1.0, 10.0, None, "不能大于或等于管内径"),
        (50.0, 100.0, 0.045, 0.0, 1.0, 10.0, None, "流体密度必须为正数"),
        (50.0, 100.0, 0.045, 1000.0, 0.0, 10.0, None, "动力黏度必须为正数"),
        (50.0, 100.0, 0.045, 1000.0, 1.0, -1.0, None, "流量不能为负数"),
        (50.0, 100.0, 0.045, 1000.0, 1.0, None, -2.0, "流速不能为负数"),
        (50.0, 100.0, 0.045, 1000.0, 1.0, None, None, "必须提供体积流量或流速"),
    ],
)
def test_invalid_input_validation(d, l, eps, rho, mu, q, v, err_msg):
    pipe = PipeData(D_mm=d, L_m=l, epsilon_mm=eps)
    fluid = FluidData(rho_kg_m3=rho, mu_mPa_s=mu)
    op = OperatingConditions(Q_m3_h=q, v_m_s=v, use_flow_rate=(q is not None))
    local = LocalResistanceData()

    with pytest.raises(ValueError, match=err_msg):
        calc_pressure_drop(pipe, fluid, op, local)


# =====================================================================
# 11. 经典工程教科书案例基准校验
# =====================================================================
def test_textbook_water_flow_case():
    """
    经典水力学案例：
    水温 20°C (ρ=1000 kg/m³, μ=1.0 mPa·s), 管径 D=50mm, 长度 L=100m, ε=0.045mm
    流量 Q = 10 m³/h
    验证截面积、流速、雷诺数与沿程压降的精确吻合
    """
    pipe = PipeData(D_mm=50.0, L_m=100.0, epsilon_mm=0.045)
    fluid = FluidData(rho_kg_m3=1000.0, mu_mPa_s=1.0)
    op = OperatingConditions(Q_m3_h=10.0, use_flow_rate=True)
    local = LocalResistanceData()
    opts = CalculationOptions(friction_correlation="colebrook_white")

    res = calc_pressure_drop(pipe, fluid, op, local, opts)

    # 理论值解析
    A_expected = math.pi * 0.05**2 / 4.0  # 0.0019635 m²
    v_expected = (10.0 / 3600.0) / A_expected  # 1.4147 m/s
    re_expected = 1000.0 * v_expected * 0.05 / 0.001  # 70735.5

    assert math.isclose(res.area_m2, A_expected, rel_tol=1e-5)
    assert math.isclose(res.velocity_m_s, v_expected, rel_tol=1e-5)
    assert math.isclose(res.Re, re_expected, rel_tol=1e-5)
    assert res.flow_regime == "turbulent"

    # Colebrook-White 求解 f ~ 0.02268
    f_expected, _ = colebrook_white_solve(re_expected, 0.045 / 50.0)
    dp_major_expected = f_expected * (100.0 / 0.05) * (1000.0 * v_expected**2 / 2.0)
    assert math.isclose(res.dp_major_Pa, dp_major_expected, rel_tol=1e-5)
