def prochnost(p_rab_MPa, p_gidro, p_pnevma, d_vnutr, pred_tek_min, vrem_sopr_min, s_isp):
    sigma = 1.0 * min(pred_tek_min / 1.5, vrem_sopr_min / 2.4)
    sigma_gidro = pred_tek_min / 1.1

    s_rasch = round(((d_vnutr + (s_isp * 2)) * p_rab_MPa) / (2 * sigma + p_rab_MPa), 1)
    s_rasch_gidro = round(((d_vnutr + (s_isp * 2)) * p_gidro) / (2 * sigma_gidro + p_gidro), 1)
    s_max_rasch = max(s_rasch, s_rasch_gidro)
    return s_rasch, s_rasch_gidro, s_max_rasch

# p_rab_MPa = 39
# p_gidro = 59
# p_pnevma = 45
# d_vnutr = 411
# pred_tek_min = 898
# vrem_sopr_min = 981
# s_isp = 28


if __name__ == "__main__":
    print(prochnost(39, 59, 45, 411, 898, 981, 28))