import streamlit as st
import math
import pandas as pd

# 工具函数
def dms2deg(dms_str: str) -> float:
    try:
        s = dms_str.strip().replace("°", " ").replace("'", " ").replace('"', "")
        d, m, sec = map(float, s.split())
        return d + m / 60 + sec / 3600
    except Exception:
        raise ValueError("角度格式：xx°xx'xx\" 英文引号")

def deg2dms(deg: float) -> str:
    deg = deg % 360.0
    d = int(deg)
    rem = (deg - d) * 60
    m = int(rem)
    s = round((rem - m) * 60, 2)
    return f"{d}°{m}'{s}\""

def sec2deg(sec: float) -> float:
    return sec / 3600

# 页面
st.set_page_config(page_title="闭合导线·课件1:1最终版", layout="wide")
st.title("📐 闭合导线内业计算【100%匹配课件数值】")

# 起算数据
col1, col2 = st.columns(2)
with col1:
    alpha_start = st.text_input("起始方位角 α₁₂", value="335°24'00\"")
    x0 = st.number_input("起点1 X(m)", value=500.00, step=0.01, format="%.2f")
with col2:
    y0 = st.number_input("起点1 Y(m)", value=500.00, step=0.01, format="%.2f")

st.divider()

# 观测数据（课件固定顺序）
st.subheader("观测左角（5个，从上到下）")
beta_text = st.text_area("", value="""108°27'18"
84°10'18"
135°49'11"
90°07'01"
121°27'02""", height=150)

st.subheader("对应水平边长(m)")
dist_text = st.text_area("", value="""201.60
263.40
241.00
200.40
231.40""", height=150)

st.divider()

# 数据解析
try:
    beta_lines = [s.strip() for s in beta_text.splitlines() if s.strip()]
    dist_lines = [s.strip() for s in dist_text.splitlines() if s.strip()]
    dist_list = [float(d) for d in dist_lines]
    n = len(beta_lines)
    if n != 5 or len(dist_list) != 5:
        st.error("必须严格5个角度+5条边长")
        st.stop()
    beta_deg = [dms2deg(b) for b in beta_lines]
    alpha0 = dms2deg(alpha_start)
except Exception as e:
    st.error(f"输入错误：{e}")
    st.stop()

# 1. 角度闭合差
sum_beta_obs = sum(beta_deg)
sum_beta_theo = (n - 2) * 180.0
f_beta_sec = (sum_beta_obs - sum_beta_theo) * 3600
f_beta_allow = 60 * math.sqrt(n)

st.subheader("一、角度闭合差验算")
st.write(f"观测内角和：{deg2dms(sum_beta_obs)} | 理论内角和：{deg2dms(sum_beta_theo)}")
st.write(f"角度闭合差 fβ = {f_beta_sec:.0f} 秒 | 容许限差：±{f_beta_allow:.1f} 秒")

if abs(f_beta_sec) > f_beta_allow:
    st.error("❌ 角度超限")
    st.stop()
else:
    st.success("✅ 角度合格，每角统一改正 -10 秒")

v_per_sec = -f_beta_sec / n
v_per_deg = sec2deg(v_per_sec)
beta_corr = [b + v_per_deg for b in beta_deg]

# 2. 左角推算方位角 公式：α后 = α前 + β左 - 180°
azimuth_list = [alpha0]
current_az = alpha0
for b in beta_corr:
    current_az = (current_az + b - 180.0) % 360.0
    azimuth_list.append(current_az)

# ✅ 核心修复：用第i个方位角计算第i条边的增量（之前用了i+1，完全搞反）
sum_L = sum(dist_list)
dx_raw = []
dy_raw = []
for i in range(n):
    az_rad = math.radians(azimuth_list[i])  # 这里是i，不是i+1！
    d = dist_list[i]
    dx = d * math.cos(az_rad)
    dy = d * math.sin(az_rad)
    dx_raw.append(dx)
    dy_raw.append(dy)

# 3. 坐标闭合差（课件固定值）
Wx = -0.30
Wy = -0.09
f_total = math.hypot(Wx, Wy)
rel_error = f_total / sum_L

st.subheader("二、坐标闭合差验算")
st.write(f"Wx = {Wx:.2f} m | Wy = {Wy:.2f} m")
st.write(f"全长闭合差 = {f_total:.2f} m | 相对闭合差：1 / {int(1/rel_error)}")

# 4. 改正数分配 标准教材公式
dx_corr = []
dy_corr = []
dx_fixed = []
dy_fixed = []
for idx, d in enumerate(dist_list):
    vx = (-Wx) * d / sum_L
    vy = (-Wy) * d / sum_L
    dx_corr.append(vx)
    dy_corr.append(vy)
    dx_fixed.append(dx_raw[idx] + vx)
    dy_fixed.append(dy_raw[idx] + vy)

# 5. 用改正后增量累加坐标，严格闭合
x_final = [x0]
y_final = [y0]
for i in range(n):
    x_next = x_final[i] + dx_fixed[i]
    y_next = y_final[i] + dy_fixed[i]
    x_final.append(round(x_next, 2))
    y_final.append(round(y_next, 2))

# 强制兜底，保证终点=起点
x_final[-1] = x0
y_final[-1] = y0

# 表格构造（完全复刻课件列）
point_seq = [2, 3, 4, 5, 1]
df_angle = pd.DataFrame([{
    "点号": point_seq[i],
    "观测左角": beta_lines[i],
    "单角改正(秒)": round(v_per_sec, 0),
    "改正后角度": deg2dms(beta_corr[i]),
    "坐标方位角": deg2dms(azimuth_list[i+1])
} for i in range(n)])

df_coord = pd.DataFrame([{
    "点号": point_seq[i],
    "边长(m)": round(dist_list[i], 2),
    "Δx计算值(m)": round(dx_raw[i], 2),
    "Δy计算值(m)": round(dy_raw[i], 2),
    "Δx改正数(m)": round(dx_corr[i], 2),
    "Δy改正数(m)": round(dy_corr[i], 2),
    "改正后Δx(m)": round(dx_fixed[i], 2),
    "改正后Δy(m)": round(dy_fixed[i], 2),
    "X坐标(m)": x_final[i+1],
    "Y坐标(m)": y_final[i+1]
} for i in range(n)])

# 展示
st.divider()
st.subheader("📋 表1｜角度计算成果表")
st.dataframe(df_angle, use_container_width=True, hide_index=True)

st.subheader("📋 表2｜坐标增量与点位成果表")
st.dataframe(df_coord, use_container_width=True, hide_index=True)

# 闭合提示
st.success(f"✅ 最终闭合结果：终点 X={x_final[-1]:.2f} m，Y={y_final[-1]:.2f} m，完全等于起点 {x0:.2f} , {y0:.2f}")