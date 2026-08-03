from src.services.calculations import calculate_strength


def test_happy_path_matches_worked_example():
    result = calculate_strength(
        pred_tek_min=898.0,
        vrem_sopr_min=981.0,
        p_rab_mpa=39.0,
        p_gidro=59.0,
        d_vnutr=411.0,
        s_isp=28.0,
        p_pnevma=45.0,
        p_rab=39.0,
    )
    assert result.sigma == 408.8
    assert result.sigma_gidro == 816.4
    assert result.s_rasch == 21.3
    assert result.s_rasch_gidro == 16.3
    assert result.s_max_rasch == 21.3
    assert result.p_dop == 50.4
    assert result.p_pnevma_kgs == 459
    assert result.p_rab_025 == 10
    assert result.p_rab_05 == 20
    assert result.p_rab_075 == 29


def test_sigma_limited_by_yield_strength_branch():
    # pred_tek_min / 1.5 < vrem_sopr_min / 2.4 -> предел текучести лимитирует
    result = calculate_strength(
        pred_tek_min=300.0,
        vrem_sopr_min=981.0,
        p_rab_mpa=39.0,
        p_gidro=59.0,
        d_vnutr=411.0,
        s_isp=28.0,
        p_pnevma=45.0,
        p_rab=39.0,
    )
    assert result.sigma == round(300.0 / 1.5, 1)


def test_sigma_limited_by_ultimate_strength_branch():
    # vrem_sopr_min / 2.4 < pred_tek_min / 1.5 -> временное сопротивление лимитирует
    result = calculate_strength(
        pred_tek_min=898.0,
        vrem_sopr_min=300.0,
        p_rab_mpa=39.0,
        p_gidro=59.0,
        d_vnutr=411.0,
        s_isp=28.0,
        p_pnevma=45.0,
        p_rab=39.0,
    )
    assert result.sigma == round(300.0 / 2.4, 1)


def test_s_max_rasch_takes_larger_of_two_branches():
    result = calculate_strength(
        pred_tek_min=898.0,
        vrem_sopr_min=981.0,
        p_rab_mpa=39.0,
        p_gidro=59.0,
        d_vnutr=411.0,
        s_isp=28.0,
        p_pnevma=45.0,
        p_rab=39.0,
    )
    assert result.s_max_rasch == max(result.s_rasch, result.s_rasch_gidro)


def test_p_pnevma_kgs_is_int_type():
    result = calculate_strength(
        pred_tek_min=898.0,
        vrem_sopr_min=981.0,
        p_rab_mpa=39.0,
        p_gidro=59.0,
        d_vnutr=411.0,
        s_isp=28.0,
        p_pnevma=45.0,
        p_rab=39.0,
    )
    assert isinstance(result.p_pnevma_kgs, int)
    assert isinstance(result.p_rab_025, int)
