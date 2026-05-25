import streamlit as st
import math
import pandas as pd

# ===================== 工具函数 =====================
def dms2deg(dms_str: str) -> float:
    try:
        s = dms_str.strip().replace("°", " ").replace("'", " ").replace('"', "")
        d, m, sec = map(float, s.split())
        return d + m / 60 + sec / 3600
    except Exception:
        raise ValueError(f"格式错误，请输入：xx°xx'xx\"")

def deg2dms(deg: float) -> str:
    deg = deg % 360.0
    d = int(deg)
    rem = (deg - d) * 60
    m = int(rem)
    s = round((rem - m) * 60, 2)
    return f"{d}°{m}'{s}\""

def sec2deg(sec: float) -> float:
    return sec / 3600

# ===================== 页面初始化 =====================
st.set_page_config(page_title="附合导线通用计算器", layout="wide")
st.title("📐 附合导线内业计算程序（右角·自由输入版）")
st.info("可修改所有输入值，角度/边长可增删行数；格式：角度xx°xx'xx\"，边长纯数字")

# ===================== 1. 已知控制点输入 =====================
col1, col2 = st.columns(2)
with col1:
    alpha_start_str = st.text_input("起始方位角 α_AB", value="236°44'28\"")
    xB = st.number_input("B点 X(m)", value=1536.86, step=0.01, format="%.2f")
    yB = st.number_input("B点 Y(m)", value=837.54, step=0.01, format="%.2f")
with col2:
    alpha_end_str = st.text_input("终止方位角 α_CD", value="60°38'01\"")
    xC = st.number_input("C点 X(m)", value=1429.02, step=0.01, format="%.2f")
    yC = st.number_input("C点 Y(m)", value=1283.17, step=0.01, format="%.2f")

st.divider()

# ===================== 2. 批量观测数据 =====================
st.subheader("观测右角（每行一个）")
beta_text = st.text_area("", value="""205°36'48\"
290°40'54\"
202°47'08\"
167°21'56\"
175°31'25\"
214°09'33\"""", height=160)

st.subheader("对应水平边长(m)（行数必须和角度一致）")
dist_text = st.text_area("", value="""125.36
98.76
116.44
167.25
175.62
156.25""", height=160)

st.divider()

# ===================== 3. 数据解析 & 前置校验 =====================
try:
    beta_lines = [s.strip() for s in beta_text.splitlines() if s.strip()]
    dist_lines = [s.strip() for s in dist_text.splitlines() if s.strip()]
    dist_list = []
    for d in dist_lines:
        dist_list.append(float(d))

    n = len(beta_lines)
    if n != len(dist_list):
        st.error(f"❌ 角度数量{n} ≠ 边长数量{len(dist_list)}，行数必须一一对应！")
        st.stop()

    beta_deg = [dms2deg(b) for b in beta_lines]
    alpha_start = dms2deg(alpha_start_str)
    alpha_end_true = dms2deg(alpha_end_str)

except ValueError as e:
    st.error(f"输入解析失败：{str(e)}")
    st.stop()
except Exception as e:
    st.error(f"未知错误：{str(e)}")
    st.stop()

# ===================== 4. 角度闭合差计算 =====================
sum_beta = sum(beta_deg)
alpha_calc_end = alpha_start - sum_beta + n * 180.0
f_beta_sec = (alpha_calc_end - alpha_end_true) * 3600
f_beta_allow = 60 * math.sqrt(n)

st.subheader("一、角度闭合差验算")
col_a, col_b = st.columns(2)
with col_a:
    st.write(f"推算终止方位角：{deg2dms(alpha_calc_end)}")
    st.write(f"已知终止方位角：{alpha_end_str}")
with col_b:
    st.write(f"闭合差 fβ = {f_beta_sec:.2f} 秒")
    st.write(f"容许值：±{f_beta_allow:.1f} 秒")

if abs(f_beta_sec) > f_beta_allow:
    st.error("❌ 角度闭合差超限，数据不合格！")
    st.stop()
else:
    st.success("✅ 角度精度合格，自动分配改正数")

# 角度改正 & 逐边推算方位角
v_per_angle_sec = f_beta_sec / n
v_per_angle_deg = sec2deg(v_per_angle_sec)
beta_corr = [b + v_per_angle_deg for b in beta_deg]

azimuth_list = [alpha_start]
current_az = alpha_start
for b in beta_corr:
    current_az = (current_az - b + 180.0) % 360.0
    azimuth_list.append(current_az)

# ===================== 5. 坐标增量原始计算 =====================
sum_dist = sum(dist_list)
dx_raw = []
dy_raw = []
x_now = xB
y_now = yB
x_track = [x_now]
y_track = [y_now]

for i in range(n):
    az_rad = math.radians(azimuth_list[i+1])
    d = dist_list[i]
    dx = d * math.cos(az_rad)
    dy = d * math.sin(az_rad)
    dx_raw.append(dx)
    dy_raw.append(dy)
    x_now += dx
    y_now += dy
    x_track.append(x_now)
    y_track.append(y_now)

# 坐标闭合差
Wx = x_now - xC
Wy = y_now - yC
f_total = math.hypot(Wx, Wy)
rel_error = f_total / sum_dist if sum_dist > 1e-6 else 0

st.subheader("二、坐标闭合差验算")
col_c, col_d = st.columns(2)
with col_c:
    st.write(f"X闭合差 Wx = {Wx:.4f} m")
    st.write(f"Y闭合差 Wy = {Wy:.4f} m")
with col_d:
    st.write(f"全长闭合差 f = {f_total:.4f} m")
    if rel_error > 1e-9:
        st.write(f"相对闭合差：1 / {int(1/rel_error)}")
    else:
        st.write("相对闭合差：无穷小（完美闭合）")

# 按边长正比例分配坐标改正数
dx_corr = []
dy_corr = []
dx_fixed = []
dy_fixed = []
for idx, d in enumerate(dist_list):
    vx = -Wx * d / sum_dist
    vy = -Wy * d / sum_dist
    dx_corr.append(vx)
    dy_corr.append(vy)
    dx_fixed.append(dx_raw[idx] + vx)
    dy_fixed.append(dy_raw[idx] + vy)

# 改正后最终坐标校核
final_x = xB + sum(dx_fixed)
final_y = yB + sum(dy_fixed)

# ===================== 6. 构造成果表格 =====================
table_angle = []
for i in range(n):
    table_angle.append({
        "序号": i+1,
        "观测右角": beta_lines[i],
        "单角改正(秒)": round(v_per_angle_sec, 1),
        "改正后角度": deg2dms(beta_corr[i]),
        "坐标方位角": deg2dms(azimuth_list[i+1])
    })
df_angle = pd.DataFrame(table_angle)

table_coord = []
for i in range(n):
    table_coord.append({
        "边号": i+1,
        "边长(m)": round(dist_list[i], 2),
        "Δx计算值(m)": round(dx_raw[i], 4),
        "Δy计算值(m)": round(dy_raw[i], 4),
        "Δx改正数(m)": round(dx_corr[i], 4),
        "Δy改正数(m)": round(dy_corr[i], 4),
        "改正后Δx(m)": round(dx_fixed[i], 4),
        "改正后Δy(m)": round(dy_fixed[i], 4),
        "X坐标(m)": round(x_track[i+1], 2),
        "Y坐标(m)": round(y_track[i+1], 2)
    })
df_coord = pd.DataFrame(table_coord)

# ===================== 展示 =====================
st.divider()
st.subheader("📋 表1 角度推算成果")
st.dataframe(df_angle, use_container_width=True, hide_index=True)

st.subheader("📋 表2 坐标增量&点位成果")
st.dataframe(df_coord, use_container_width=True, hide_index=True)

st.info(f"校核：改正后终点 X={final_x:.2f} m，Y={final_y:.2f} m（应接近 {xC:.2f} , {yC:.2f}）")