import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image

# 웹 페이지 타이틀
img = Image.open("image/sample.png")
st.set_page_config(
    layout="wide", page_title="복지패널 데이터분석 시각화 대시보드", page_icon=img)

job_code = pd.read_excel('data/welfare_2015_codebook.xlsx',
                         sheet_name = '직종코드')
# job_list = pd.read_excel('D:\streamlit\data\welfare_2015_codebook.xlsx', sheet_name = 1)
job_code.head()


# 한글 폰트 지정
plt.rc("font", family="Malgun Gothic")
# 마이너스 기호 깨짐 방지
plt.rcParams["axes.unicode_minus"] = False

# 데이터 로드 함수
# 캐시
@st.cache_data
def load_welfare(sav_path: str):
    raw_welfare = pd.read_csv(sav_path)
    welfare = raw_welfare.copy()
    welfare = welfare.rename(
        columns={
            "h10_g3": "sex",  #  성별
            "h10_g4": "birth_year",  #  태어난 연도
            "h10_g10": "marital_status",  #  혼인 상태
            "h10_g11": "religion",  #  종교
            "h10_eco9": "job_code",  #  직업 코드
            "p1002_8aq1": "income",  #  월급
            "h10_reg7": "region_code",
        }
    )  #  지역 코드

    # 전처리
    if "sex" in welfare.columns:
        welfare["sex"] = welfare["sex"].replace(9, np.nan)
        welfare["sex"] = welfare["sex"].map({1: "male", 2: "female"})

    if "income" in welfare.columns:
        welfare["income"] = welfare["income"].replace(9999, np.nan)
        welfare["income"] = np.where(welfare["income"] == 0, np.nan, welfare["income"])

    def age_group(age):
        if pd.isnull(age):
            return np.nan
        elif age >= 60:
            return 'old'
        elif age >= 30:
            return 'middle'
        else:
            return 'young'

    if "birth_year" in welfare.columns:
        welfare["birth_year"] = welfare["birth_year"].replace(9999, np.nan)
        welfare["age"] = 2015 - welfare["birth_year"] + 1
        welfare['age_group'] = welfare['age'].apply(age_group)

    if "job_code" in welfare.columns:
        welfare['job_code'] = np.where(welfare['job_code'] == 9999, np.nan, welfare['job_code'])

    return welfare


# 사이드바
st.sidebar.title("데이터 로드")
data_path = st.sidebar.text_input("데이터 파일 경로", value="data/welfare_2015.csv")

if st.sidebar.button("데이터 로드"):
    st.rerun()

# 메인
st.title("한국복지패널 대시보드")
st.markdown("데이터 출처: 복지패널 데이터 (로컬에 csv 파일 필요)")

# 데이터 로드
try:
    welfare = load_welfare(data_path)
    st.success("데이터 로드 완료: {}행 {}열".format(welfare.shape[0], welfare.shape[1]))
except Exception as e:
    st.error(f"데이터를 불러오는 데 실패했습니다. 경로와 파일을 확인하세요.\n에러: {e}")
    st.stop()

# 대시보드 레이아웃
# 필터
st.sidebar.header("필터")

# 성별 필터
if "sex" in welfare.columns:
    value_list = ["All"] + sorted(welfare["sex"].dropna().unique().tolist())
    select_sex = st.sidebar.selectbox("성별", value_list, index=0)
else:
    select_sex = "All"

# 연령 범위 필터
if "age" in welfare.columns:
    min_age = int(welfare["age"].dropna().min())
    max_age = int(welfare["age"].dropna().max())
    slider_range = st.sidebar.slider(
        "연령 범위", min_value=min_age, max_value=max_age, value=(min_age, max_age)
    )
    filter_button = st.sidebar.button("필터 적용")
else:
    slider_range = None

# 연령대 필터
# 여러 개 선택할 수 있는 multiselect
if "age_group" in welfare.columns:
    value_list = ["All"] + sorted(welfare["age_group"].dropna().unique().tolist())
    select_multi_age_group = st.sidebar.multiselect(
        "확인하고 싶은 연령대를 선택하세요(복수 선택 가능)",
        value_list,
    )
else:
    select_multi_age_group = "All"


# 성별에 따른 월급 차이 - '성별에 따라 월급이 다를까?'
st.subheader("1. 성별에 따른 월급 차이 - '성별에 따라 월급이 다를까?'")

if select_sex != "All" and "sex" in welfare.columns:
    tmp_welfare = welfare[welfare["sex"] == select_sex]
    st.write("필터로 선택한 데이터 첫 5행")
    st.table(tmp_welfare.head())

col1, col2 = st.columns([2, 1])
with col1:
    if "sex" in welfare.columns and "income" in welfare.columns:
        sex_income = (
            welfare.dropna(subset=["sex", "income"])
            .groupby("sex", as_index=False)
            .agg(mean_income=("income", "mean"))
        )
        # 시각화
        fig1, ax1 = plt.subplots()
        sns.barplot(x="sex", y="mean_income", data=sex_income, ax=ax1)
        plt.title("성별에 따른 평균 월급 막대 그래프")
        plt.xlabel("성별")
        plt.ylabel("평균 월급")
        for i, j in enumerate(sex_income["mean_income"]):
            ax1.annotate(
                round(j),
                (i, j),
                xytext=(0, 2),
                textcoords="offset points",
                fontsize=8,
                ha="center",
                color="black",
            )
        st.pyplot(fig1)
    else:
        st.info("성별/월급 변수가 없어 해당 그래프를 표시할 수 없습니다.")
with col2:
    st.markdown("테이블")
    if "sex" in welfare.columns and "income" in welfare.columns:
        st.write(sex_income)
    else:
        st.write("변수 없음")

# 나이와 월급의 관계 - '몇 살 때 월급을 가장 많이 받을까?'
st.subheader("2. 나이와 월급의 관계 - '몇 살 때 월급을 가장 많이 받을까?'")

if filter_button:
    tmp_welfare = welfare[
        (welfare["age"] >= slider_range[0]) & (welfare["age"] <= slider_range[1])
    ]
    st.write("필터로 선택한 데이터 첫 5행")
    st.table(tmp_welfare.head())

col1, col2 = st.columns([2, 1])
with col1:
    if "age" in welfare.columns and "income" in welfare.columns:
        age_income = (
            welfare.dropna(subset=["age", "income"])
            .groupby("age", as_index=False)
            .agg(mean_income=("income", "mean"))
        )
        # 시각화
        fig2, ax2 = plt.subplots()
        sns.lineplot(x="age", y="mean_income", data=age_income, ax=ax2)
        plt.title("나이에 따른 평균 월급 선 그래프")
        plt.xlabel("나이")
        plt.ylabel("평균 월급")
        st.pyplot(fig2)
    else:
        st.info("나이/월급 변수가 없어 해당 그래프를 표시할 수 없습니다.")
with col2:
    st.markdown("테이블")
    if "age" in welfare.columns and "income" in welfare.columns:
        st.write(age_income)
    else:
        st.write("변수 없음")

# 나머지 주제는 여러분들이 직접 만들어 보아요!
# 연령대에 따른 월급 차이 - 어떤 연령대의 월급이 가장 많을까?
st.subheader("3. 연령대에 따른 월급 차이 - 어떤 연령대의 월급이 가장 많을까?")

if select_multi_age_group != "All" and "age_group" in welfare.columns:
    tmp_welfare = welfare[welfare["age_group"].isin(select_multi_age_group)]
    st.write("필터로 선택한 데이터 첫 5행")
    st.table(tmp_welfare.head())

col1, col2 = st.columns([2, 1])
with col1:
    if "age_group" in welfare.columns and "income" in welfare.columns:
        age_group_income = (
            welfare.dropna(subset=["age_group", "income"])
                   .groupby("age_group", as_index=False)
                   .agg(mean_income=("income", "mean"))
        )
        # 시각화
        fig3, ax3 = plt.subplots()
        sns.barplot(
            x="age_group",
            y="mean_income",
            data=age_group_income,
            ax=ax3,
            order=["young", "middle", "old"],
        )
        plt.title("연령대에 따른 평균 월급 막대 그래프")
        plt.xlabel("연령대")
        plt.ylabel("평균 월급")
        st.pyplot(fig1)
    else:
        st.info("연령대/월급 변수가 없어 해당 그래프를 표시할 수 없습니다.")
with col2:
    st.markdown("테이블")
    if "age_group" in welfare.columns and "income" in welfare.columns:
        st.write(age_group_income)
    else:
        st.write("변수 없음")

# 연령대 및 성별 월급 차이 - 성별 월급 차이는 연령대별로 다를까?
st.subheader("4. 연령대 및 성별 월급 차이 - 성별 월급 차이는 연령대별로 다를까?")

if (
    select_sex != "All"
    and select_multi_age_group != "All"
    and "age_group" in welfare.columns
):
    tmp_welfare = welfare[
        (welfare["sex"] == select_sex)
        & (welfare["age_group"].isin(select_multi_age_group))
    ]
    st.write("필터로 선택한 데이터 첫 5행")
    st.table(tmp_welfare.head())

col1, col2 = st.columns([2, 1])
with col1:
    if (
        "sex" in welfare.columns
        and "age_group" in welfare.columns
        and "income" in welfare.columns
    ):
        age_group_sex_income = (
            welfare.dropna(subset=["age_group", "sex", "income"])
            .groupby(["age_group", "sex"], as_index=False)
            .agg(mean_income=("income", "mean"))
        )
        # 시각화
        fig4, ax4 = plt.subplots()
        sns.barplot(
            x="age_group",
            y="mean_income",
            hue="sex",
            data=age_group_sex_income,
            order=["young", "middle", "old"],
            ax=ax4,
        )
        plt.title("연령대 및 성별에 따른 평균 월급 막대 그래프")
        plt.xlabel("연령대 및 성별")
        plt.ylabel("평균 월급")
        st.pyplot(fig4)
    else:
        st.info("연령대/성별/월급 변수가 없어 해당 그래프를 표시할 수 없습니다.")
with col2:
    st.markdown("테이블")
    if (
        "sex" in welfare.columns
        and "age_group" in welfare.columns
        and "income" in welfare.columns
    ):
        st.write(age_group_sex_income)
    else:
        st.write("변수 없음")


# 직업별 월급 차이 - 어떤 직업이 월급을 가장 많이 받을까?
st.subheader("5. 직업별 월급 차이 - 어떤 직업이 월급을 가장 많이 받을까?")
if select_sex != "All" and "job_code" in welfare.columns:
    tmp_welfare = welfare[welfare["job_code"] == select_sex]
    st.write("필터로 선택한 데이터 첫 5행")
    st.table(tmp_welfare.head())

col1, col2 = st.columns([2, 1])
with col1:
    if "job_code" in welfare.columns and "income" in welfare.columns:
        sex_income = (
            welfare.dropna(subset=["sex", "income"])
            .groupby("sex", as_index=False)
            .agg(mean_income=("income", "mean"))
        )
        # 시각화
        fig1, ax1 = plt.subplots()
        sns.barplot(x="sex", y="mean_income", data=sex_income, ax=ax1)
        plt.title("성별에 따른 평균 월급 막대 그래프")
        plt.xlabel("성별")
        plt.ylabel("평균 월급")
        for i, j in enumerate(sex_income["mean_income"]):
            ax1.annotate(
                round(j),
                (i, j),
                xytext=(0, 2),
                textcoords="offset points",
                fontsize=8,
                ha="center",
                color="black",
            )
        st.pyplot(fig1)
    else:
        st.info("직업/월급 변수가 없어 해당 그래프를 표시할 수 없습니다.")
with col2:
    st.markdown("테이블")
    if "job_code" in welfare.columns and "income" in welfare.columns:
        st.write(sex_income)
    else:
        st.write("변수 없음")

# 성별 직업 빈도 - 성별로 어떤 직업이 가장 많을까?
st.subheader("6. 성별 직업 빈도 - 성별로 어떤 직업이 가장 많을까?")


# 종교 유무에 따른 이혼율 - 종교가 있으면 이혼을 덜 할까?
st.subheader("7. 종교 유무에 따른 이혼율 - 종교가 있으면 이혼을 덜 할까?")

# 지역별 연령대 비율 - 어느 지역에 노년층이 많을까?
st.subheader("8. 지역별 연령대 비율 - 어느 지역에 노년층이 많을까?")


# 끝
