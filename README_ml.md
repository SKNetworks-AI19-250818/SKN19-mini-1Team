# 플랜B

안녕하세요! 플랜B팀의 프로젝트 과정을 담았습니다.

<table>
  <tr>
    <td align="center">
      <strong>강지완</strong><br><br>
      <img src="assets/img/강지완.png" alt="강지완" width="140"><br>
      <a href="https://github.com/Maroco0109">
        <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" alt="강지완 GitHub" width="32">
      </a>
    </td>
    <td align="center">
      <strong>김성욱</strong><br><br>
      <img src="assets/img/김성욱.png" alt="김성욱" width="140"><br>
      <a href="https://github.com/souluk319">
        <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" alt="김성욱 GitHub" width="32">
      </a>
    </td>
    <td align="center">
      <strong>김소희</strong><br><br>
      <img src="assets/img/김소희.png" alt="김소희" width="140"><br>
      <a href="https://github.com/sosodoit">
        <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" alt="김소희 GitHub" width="32">
      </a>
    </td>
    <td align="center">
      <strong>박진형</strong><br><br>
      <img src="assets/img/박진형.png" alt="박진형" width="140"><br>
      <a href="https://github.com/vispi94">
        <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" alt="박진형 GitHub" width="32">
      </a>
    </td>
    <td align="center">
      <strong>이상민</strong><br><br>
      <img src="assets/img/이상민.png" alt="이상민" width="140"><br>
      <a href="https://github.com/ChocolateStrawberryYumYum">
        <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" alt="이상민 GitHub" width="32">
      </a>
    </td>
  </tr>
</table>

## 📂 필수 산출물

| 테이블 | 데이터(폴더) | ipynb |
| ----- | ----- | ----- |
| 통합데이터 | [통합데이터](https://github.com/SKNetworks-AI19-250818/SKN19-mini-1Team/tree/develop/integrated_data/prep_data) | [전처리](https://github.com/SKNetworks-AI19-250818/SKN19-mini-1Team/tree/develop/integrated_data/prep_notebook) |
| 여행마스터 | [여행마스터](https://github.com/SKNetworks-AI19-250818/SKN19-mini-1Team/blob/develop/integrated_data/prep_data/traveller_master.csv) | [전처리](https://github.com/SKNetworks-AI19-250818/SKN19-mini-1Team/blob/develop/integrated_data/prep_notebook/%EC%97%AC%ED%96%89%EA%B0%9D%EB%8D%B0%EC%9D%B4%ED%84%B0%EC%A0%84%EC%B2%98%EB%A6%AC.ipynb) |
| 숙박소비내역 | [숙박소비내역](https://github.com/SKNetworks-AI19-250818/SKN19-mini-1Team/blob/develop/integrated_data/prep_data/lodging_consumption.csv) | [전처리](https://github.com/SKNetworks-AI19-250818/SKN19-mini-1Team/blob/develop/integrated_data/prep_notebook/%EC%88%99%EB%B0%95%EC%86%8C%EB%B9%84%EB%82%B4%EC%97%AD_%EC%A0%84%EC%B2%98%EB%A6%AC.ipynb) |
| 방문지정보 | [방문지정보](https://github.com/SKNetworks-AI19-250818/SKN19-mini-1Team/blob/develop/integrated_data/prep_data/visit_area_base.csv) | [전처리](https://github.com/SKNetworks-AI19-250818/SKN19-mini-1Team/blob/develop/integrated_data/prep_notebook/%EC%97%AC%ED%96%89%EB%B0%A9%EB%AC%B8%EC%A7%80%EB%82%B4%EC%97%AD_%EC%A0%84%EC%B2%98%EB%A6%AC.ipynb) |
| 활동내역 | [활동내역](https://github.com/SKNetworks-AI19-250818/SKN19-mini-1Team/blob/develop/integrated_data/prep_data/activity_history.csv) | [전처리](https://github.com/SKNetworks-AI19-250818/SKN19-mini-1Team/blob/develop/integrated_data/prep_notebook/%ED%99%9C%EB%8F%99%EB%82%B4%EC%97%AD_%EC%A0%84%EC%B2%98%EB%A6%AC.ipynb) |
| 활동소비내역 | [활동소비내역](https://github.com/SKNetworks-AI19-250818/SKN19-mini-1Team/blob/develop/integrated_data/prep_data/activity_consumption.csv) | [전처리](https://github.com/SKNetworks-AI19-250818/SKN19-mini-1Team/blob/develop/integrated_data/prep_notebook/%ED%99%9C%EB%8F%99%EC%86%8C%EB%B9%84%EB%82%B4%EC%97%AD_%EC%A0%84%EC%B2%98%EB%A6%AC.ipynb) |

## 📂 프로젝트 구조

```
  SKN19-mini-1Team/
  ├── data/
  │ ├── tag_code/
  │ │ ├── training/
  │ │ └── validation/
  │ ├── training/
  │ │ ├── TL_csv/
  │ │ ├── final/
  │ │ └── preprocessing/
  │ └── validation/
  │   └── VL_csv/
  ├──integrated_data
  │ ├── prep_data/
  │ │ ├── activity_cosumption.csv
  │ │ ├── activity_history.csv
  │ │ ├── lodging_cosumption.csv
  │ │ ├── traveller_master.csv
  │ │ └── visit_area_base.csv
  │ ├── prep_notebook/
  │ │ ├── 숙박소비내역_전처리.ipynb
  │ │ ├── 여행객데이터전처리.ipynb
  │ │ ├── 여행방문지내역_EDA.ipynb
  │ │ ├── 여행방문지내역_전처리.ipynb
  │ │ ├── 활동내역_전처리.ipynb
  │ │ ├── 활동소비내역_CD_전처리.ipynb
  │ │ └── 활동소비내역_전처리.ipynb
  ├── assets/
  │ └──img/
  │ │ └── *.png
  ├── ppt/
  │ ├── 발표자료.pptx
  │ └── 슬라이드\*.JPG
  ├──  preprocessing/
  │ ├── merge_datasets.py
  │ ├── preprocessing.py
  │ ├── data/
  │ ├── img/
  │ └── notebook/
  ├── README.md
  └── requirements.txt
```

## 🔧 기술 스택

| 분류 | 사용 도구 |
| ----- | ----- |
| 언어 및 환경 | ![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) |
| 데이터 전처리 | ![Pandas](https://img.shields.io/badge/pandas-%23150458.svg?style=for-the-badge&logo=pandas&logoColor=white) ![NumPy](https://img.shields.io/badge/numpy-%23013243.svg?style=for-the-badge&logo=numpy&logoColor=white) |
| 시각화 | ![Seaborn](https://img.shields.io/badge/Seaborn-3776AB?style=for-the-badge&logo=seaborn&logoColor=white) ![Matplotlib](https://img.shields.io/badge/Matplotlib-%23ffffff.svg?style=for-the-badge&logo=Matplotlib&logoColor=black) ![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white) |
| 협업 | ![Git](https://img.shields.io/badge/git-%23F05033.svg?style=for-the-badge&logo=git&logoColor=white) ![GitHub](https://img.shields.io/badge/github-%23121011.svg?style=for-the-badge&logo=github&logoColor=white) ![Notion](https://img.shields.io/badge/Notion-%23000000.svg?style=for-the-badge&logo=notion&logoColor=white) ![Slack](https://img.shields.io/badge/Slack-4A154B?style=for-the-badge&logo=slack&logoColor=white) |

---
---

<br/>

## One Trip, Two Fates 👎👍

## 🔎 EDA 리마인드

## 💡 모델 선정 과정 및 이유

## 📖 데이터 튜닝

## 💪 최종성능결과 및 시연

## 🔫 트러블 슈팅팅

## 💬 한줄회고

<table style="width:100%, table-layout: fixed;">
  <tr>
    <th style="min-width: 100px;">이름</th>
    <th>회고 내용</th>
  </tr>
  <tr>
    <td style="width: 10%" align="center">강지완</td>
    <td></td>
  </tr>
  <tr>
    <td style="width: 10%" align="center">김성욱</td>
    <td></td>
  </tr>
  <tr>
    <td style="width: 10%" align="center">김소희</td>
    <td></td>
  </tr>
  <tr>
    <td style="width: 10%" align="center">박진형</td>
    <td></td>
  </tr>
  <tr>
    <td style="width: 10%" align="center">이상민</td>
    <td></td>
  </tr>
</table>

## 🚀 How to Use

This project includes a command-line interface (`main.py`) to handle data preprocessing and merging.

### 1. Preprocessing

To preprocess the data for a specific year and mode (training/validation), use the `preprocess` command.

**Usage:**
```bash
python main.py preprocess --year <YEAR> --mode <MODE>
```

**Examples:**

- Preprocess the 2022 training data:
  ```bash
  python main.py preprocess --year 2022 --mode train
  ```
- Preprocess the 2023 validation data:
  ```bash
  python main.py preprocess --year 2023 --mode validation
  ```

### 2. Merging

To merge the preprocessed data from all available years (2022, 2023) into a single final dataset, use the `merge` command.

**Usage:**
```bash
python main.py merge --mode <MODE>
```

**Examples:**

- Merge all preprocessed training data:
  ```bash
  python main.py merge --mode train
  ```
- Merge all preprocessed validation data:
  ```bash
  python main.py merge --mode validation
  ```

### 3. ML Preprocessing

To run the ML-specific preprocessing on the final dataset for a specific mode, use the `ml` command. This will generate a `travel_ml.csv` file in the corresponding `data/<mode>/final/` directory.

**Usage:**
```bash
python main.py ml --mode <MODE>
```

**Examples:**

- Preprocess the training data for ML:
  ```bash
  python main.py ml --mode train
  ```
- Preprocess the validation data for ML:
  ```bash
  python main.py ml --mode validation
  ```
