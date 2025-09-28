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

---

## 신규 타겟: SUCCESS_SCORE (구현)

기존의 이진 분류 타겟인 `IS_FAILED_TRIP` 대신, 여행의 질을 종합적으로 평가하는 회귀(regression) 타겟인 `SUCCESS_SCORE`를 새롭게 정의합니다. 점수는 0점에서 50점 사이의 값을 가집니다.

점수는 현재 사용 가능한 데이터를 바탕으로 다음 두 가지 항목의 조합으로 계산됩니다.

### (A) 주관 만족 축 (최대 40점)

여행자가 각 방문지에서 평가한 만족도, 재방문 의향, 추천 의향 점수의 평균을 사용합니다.

- **계산 방식:**
  1. 각 여행(`TRAVEL_ID`)에 포함된 모든 방문지의 만족도(`DGSTFN_AVG`), 재방문 의향(`REVISIT_AVG`), 추천 의향(`RCMDTN_AVG`) 점수의 평균을 계산합니다.
  2. 세 가지 평균 점수를 다시 평균내어 '종합 만족도 평균'을 구합니다. (각 점수는 1~5점 척도로 가정)
  3. 이 종합 만족도 평균을 0점에서 40점 사이의 점수로 변환합니다.
     - `점수 = ((종합 만족도 평균 - 1) / 4) * 40`

### (D) 경험 다양성 축 (최대 10점)

한 여행에서 얼마나 다양한 활동을 했는지를 측정합니다.

- **계산 방식:**
  1. 각 여행(`TRAVEL_ID`)에서 경험한 고유한 활동 유형(`ACTIVITY_TYPE_CD`)의 개수를 계산합니다.
  2. 활동 개수에 따라 점수를 부여하며, 최대 5개의 활동까지만 점수에 반영하여 10점 만점으로 변환합니다.
     - `점수 = min(고유 활동 개수, 5) * 2`

### 최종 성공 점수

`SUCCESS_SCORE` = (A) 주관 만족 점수 + (D) 경험 다양성 점수

---

## 결측치 처리

데이터 병합 및 피처 생성 과정에서 발생할 수 있는 결측치(null 값)는 모델 학습 오류를 방지하고 데이터의 일관성을 유지하기 위해 다음과 같이 처리합니다.

- **문자열(Object) 타입 컬럼:** '정보없음'이라는 특정 문자열로 값을 채웁니다.
- **숫자(Numeric) 타입 컬럼:** 해당 컬럼의 중앙값(median)으로 값을 채웁니다. 중앙값은 평균(mean)에 비해 극단적인 값(outlier)의 영향을 덜 받기 때문에 더 안정적인 대푯값으로 사용됩니다.

---

## ML/01_CatBoost.ipynb 학습 요약 및 타겟 정의

본 절은 `ML/01_CatBoost.ipynb`의 모델 학습 구성(데이터, 타겟 정의, 특징 컬럼, 최적화/파라미터, 평가/산출물)을 정리합니다. 특히 타겟 변수 생성 로직을 상세히 기록합니다.

### 1) 데이터 소스

- 입력 경로: `../data/training/final/travel_insight_pruned.csv`
- 학습/검증 분할: `train_test_split(test_size=0.3, random_state=42)`
- 출력 디렉터리: `ML/outputs/01_Catboost`

### 2) 타겟 변수 정의(중요)

- 이 노트북은 회귀형 `SUCCESS_SCORE`를 기반으로 이진 타겟 `IS_FAILED_TRIP`을 생성하여 분류 문제로 학습합니다.
- 생성 로직: `travel['IS_FAILED_TRIP'] = (travel['SUCCESS_SCORE'] < 35).astype(int)`
  - 의미: `SUCCESS_SCORE < 35`인 경우 실패(1), 그 외 성공(0)
  - 주의: 코드 셀 주석에는 “30점 미만”이라고 적혀 있으나, 실제 조건은 35 미만입니다. 재현 시 혼선을 피하기 위해 문구(주석)와 조건(35)을 일치시키는 것을 권장합니다.
- 최종 사용 타겟: `BINARY_CLASSIFICATION_TARGET = 'IS_FAILED_TRIP'`

### 3) 특징 컬럼(Features)

- 사용 목록: `BINARY_CLASSIFICATION_FEATURES = [
  'TRIP_DAYS', 'MOVE_CNT', 'activity_payment_sum', 'activity_history_rows',
  'ACTIVITY_TYPE_CD', 'payment_persona', 'GENDER', 'AGE_GRP', 'HOUSE_INCOME',
  'TRAVEL_MOTIVE_1', 'TRAVEL_STATUS_ACCOMPANY', 'TRAVEL_COMPANIONS_NUM',
  'RESIDENCE_SGG_CD', 'move_cnt_per_day', 'activity_payment_sum_per_day',
  'activity_history_rows_per_day'
]`

### 4) 전처리: 범주형 지정 방식(CatBoost `cat_features`)

- 객체(Object) 타입 컬럼을 스캔하여 다음 규칙 적용:
  - 숫자 형변환 성공률이 95% 이상이면 숫자열로 강제 변환(`pd.to_numeric(errors='coerce')`).
  - 그 외는 문자열로 캐스팅하여 범주형으로 유지.
- 추가 수동 지정: `manual_cat = ['TRAVEL_SEASON', 'activity_type_catboost']`(존재하는 경우에 한해 병합)
- 최종 범주형 목록: `cat_cols = sorted(set(cat_auto).union(manual_cat))`
- 레이블 타입 안전화: `y_train`이 `bool`이면 `int`로, `object`면 고유값 매핑하여 0/1로 변환.

### 5) 최적화(Optuna) 목적함수와 탐색 공간

- 교차검증: `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`
- 평가 지표: 평균 PR-AUC(`average_precision_score`) 최대화
- 조기 종료: `early_stopping_rounds = 100`
- 클래스 불균형 처리: `auto_class_weights='Balanced'` (CatBoost 내부 자동 가중치)
- 공통 고정 파라미터: `loss_function='Logloss'`, `eval_metric='PRAUC'`, `random_seed=42`, `verbose=False`
- 탐색 공간(주요 하이퍼파라미터):
  - `depth`: 1~6(정수)
  - `iterations`: 800~2000(정수)
  - `learning_rate`: 1e-3~0.2(로그 스케일, 실수)
  - `l2_leaf_reg`: 1.0~12.0(실수)
  - `min_data_in_leaf`: 10~64(정수)
  - `border_count`: 64~254(정수)
  - `rsm`: 0.7~1.0(실수)
  - `bootstrap_type`: {'Bayesian', 'Bernoulli'}
    - if `Bayesian`: `bagging_temperature` 0.0~3.0(실수)
    - else(`Bernoulli`): `subsample` 0.6~1.0(실수)
- 탐색 횟수: `n_trials = 100`

### 6) 최적 파라미터 적용 및 최종 학습

- Optuna의 `best_trial.params`를 다음 딕셔너리에 병합하여 최종 파라미터 구성:
  - `final_params = {
  'loss_function': 'Logloss', 'eval_metric': 'PRAUC',
  'random_seed': 42, 'verbose': False, 'auto_class_weights': 'Balanced',
  **best_trial.params
}`
- `CatBoostClassifier(**final_params)`로 학습하며, `Pool(X_train, y_train, cat_features=cat_cols)`를 사용하고 조기 종료(100) 적용.
- 노트북 실행 예시에서의 Best 값(참고): `Best PR-AUC ≈ 0.3846`, `depth=4`, `iterations≈1240`, `learning_rate≈0.147`, `l2_leaf_reg≈3.39`, `min_data_in_leaf≈16`, `border_count≈205`, `bootstrap_type='Bernoulli'`, `rsm≈0.887`, `subsample≈0.883`.

### 7) 검증 및 임계값 처리

- 내부 K-Fold 검증 블록: `StratifiedKFold(n_splits=5)`에서 fold별 모델을 학습하고, 고정 임계값 0.5로 분류 지표/PR-AUC를 출력. PR-AUC가 가장 높은 fold의 모델을 `best_model`로 채택.
- 최종 Train/Test 평가 블록: 확률 예측 후 고정 임계값 0.4로 이진 분류를 산출하여 지표를 출력.
  - 비고: 그림 제목은 `@0.5`로 표기되지만, 코드 상 예측은 0.4 임계값을 사용합니다. 문구/코드 일치화가 필요합니다.

### 8) 산출물(Artifacts)

- 혼동행렬 이미지: `ML/outputs/01_Catboost/confusion_matrix.png`
- 특성중요도 그래프: `ML/outputs/01_Catboost/feature_importances_top.png`
- True Positive 샘플: `ML/outputs/01_Catboost/TP_traveler_catboost.csv`
- True Negative 샘플: `ML/outputs/01_Catboost/TN_traveler_catboost.csv`
- 학습 모델 파일: `ML/outputs/01_Catboost/catboost_best_model.joblib`
- 경량(4피처) 학습 모델 파일: `ML/outputs/01_Catboost/catboost_best_model_lite.joblib`

### 9) 재현 요약(Checklist)

- `data/training/final/travel_insight_pruned.csv` 존재 확인 후 노트북 실행
- 타겟 생성 셀에서 `SUCCESS_SCORE < 35` 조건 확인(주석과 수치 일치 여부 점검)
- CatBoost 설치 및 동일 버전 권장, `random_seed=42` 유지 시 유사 결과 재현 가능

### 10) 저장된 모델 사용 방법

- 경로: `ML/outputs/01_Catboost/catboost_best_model.joblib`
- 예시 코드:

  ```python
  import pandas as pd
  import joblib

  # 1) 모델 로드
  model_path = 'ML/outputs/01_Catboost/catboost_best_model.joblib'
  model = joblib.load(model_path)

  # 2) 입력 데이터 준비 (학습 시 사용한 동일 피처 스키마)
  BINARY_CLASSIFICATION_FEATURES = [
      'TRIP_DAYS','MOVE_CNT','activity_payment_sum','activity_history_rows',
      'ACTIVITY_TYPE_CD','payment_persona','GENDER','AGE_GRP','HOUSE_INCOME',
      'TRAVEL_MOTIVE_1','TRAVEL_STATUS_ACCOMPANY','TRAVEL_COMPANIONS_NUM',
      'RESIDENCE_SGG_CD','move_cnt_per_day','activity_payment_sum_per_day',
      'activity_history_rows_per_day'
  ]

  df = pd.read_csv('path/to/your_input.csv')
  X = df[BINARY_CLASSIFICATION_FEATURES].copy()

  # 3) 범주형 컬럼 형 맞추기(학습 로직과 동일하게 object→string 캐스팅 권장)
  obj_cols = X.select_dtypes(include=['object']).columns
  X[obj_cols] = X[obj_cols].astype(str)

  # 4) 예측 확률 및 이진 예측
  proba = model.predict_proba(X)[:, 1]
  # 노트북에서는 0.4/0.5 임계값을 혼용하여 평가했습니다. 기본 0.5를 권장합니다.
  y_pred = (proba >= 0.5).astype(int)
  ```

- 참고: CatBoost는 학습 시 `cat_features` 정보를 가진 상태로 저장되므로, 피처 이름과 순서를 동일하게 맞추면 `predict_proba` 호출 시 별도 `cat_features` 지정 없이 동작합니다. 다만, 학습 시 문자열로 처리한 범주형은 예측 시에도 문자열이어야 합니다.

### 11) 4개 피처만으로 예측하는 경량 모델 사용

- 경로: `ML/outputs/01_Catboost/catboost_best_model_lite.joblib`
- 입력 스키마: `['TRIP_DAYS', 'GENDER', 'AGE_GRP', 'ACTIVITY_TYPE_CD']`
- 예시 코드(배치/단일 모두 가능):

  ```python
  import pandas as pd
  import joblib

  model = joblib.load('ML/outputs/01_Catboost/catboost_best_model_lite.joblib')

  LITE_FEATURES = ['TRIP_DAYS','GENDER','AGE_GRP','ACTIVITY_TYPE_CD']

  # 1) 배치 예측 예시
  df = pd.read_csv('path/to/input_minimal.csv')  # 해당 4컬럼만 존재하면 됨
  X = df[LITE_FEATURES].copy()
  obj_cols = X.select_dtypes(include=['object']).columns
  X[obj_cols] = X[obj_cols].astype(str)
  proba = model.predict_proba(X)[:, 1]
  y_pred = (proba >= 0.5).astype(int)

  # 2) 단일 샘플 예시
  sample = {
      'TRIP_DAYS': 3,
      'GENDER': 'F',        # 문자열 권장(범주형)
      'AGE_GRP': '30대',     # 데이터에 맞는 표기 사용
      'ACTIVITY_TYPE_CD': 'A01'  # 활동 코드 예시
  }
  X1 = pd.DataFrame([sample], columns=LITE_FEATURES)
  X1[X1.select_dtypes(include=['object']).columns] = X1.select_dtypes(include=['object']).astype(str)
  p1 = model.predict_proba(X1)[:, 1][0]
  y1 = int(p1 >= 0.5)
  print('proba=', p1, 'pred=', y1)
  ```

- 주의사항
  - `GENDER`, `AGE_GRP`, `ACTIVITY_TYPE_CD`는 학습 시 문자열 범주형으로 처리될 수 있으므로 문자열 입력을 권장합니다.
  - 임계값은 기본 0.5 권장(노트북에는 0.4/0.5 혼용 지점이 있으므로 일관되게 0.5 사용 권장).

ACTIVITY_TYPE 입력 가이드(라벨→코드 매핑)
- CLI에서 아래 한글 라벨을 직접 입력할 수 있으며 내부적으로 ACT 코드로 변환합니다.
- 라벨 목록 및 매핑:
  - 취식 → 1
  - 쇼핑(쇼핑/구매) → 2
  - 체험(입장/관람 포함) → 3
  - 산책(단순 구경/걷기 포함) → 4
  - 휴식 → 5
  - 기타 → 6
  - 이동(환승/경유) → 7
  - 없음 → 99
- 또한 코드 직접 입력도 허용: '1'..'7','99' 또는 'A01'.. 형태(예: A03 → 3)

CLI 예측 스크립트(model_test.py)

- 경량 모델을 사용한 단일 사용자 입력 예측을 CLI로 지원합니다.
- 실행 예시:

  - 비대화형: `python model_test.py --trip-days 3 --gender F --age-grp 30대 --activity-type A01 --threshold 0.5`
  - 대화형(인자 생략 시 프롬프트): `python model_test.py`

입력 정규화와 오류 해결
- GENDER: 'M'/'F' 또는 '남'/'여' 입력을 각각 1/2로 자동 매핑합니다. 숫자 입력도 허용합니다.
- AGE_GRP: '30대' 같은 표기는 30으로 파싱합니다. 숫자 입력도 허용합니다.
- ACTIVITY_TYPE: 위 라벨을 코드로 자동 변환합니다. 미인식 시 '없음'(99)로 대체합니다.
- 위 정규화로 인해 CatBoost의 "Cannot convert 'M' to float" 오류를 방지합니다(GENDER/AGE_GRP를 숫자로 변환하여 모델 학습 스키마와 일치시킴).

  ### 12) LITE 모델 메커니즘(동작 원리)

- 목적: 입력 스키마를 최소화(TRIP_DAYS, GENDER, AGE_GRP, ACTIVITY_TYPE_CD)하여 간편 추론을 지원하는 분류기 추가 제공.
- 타겟: 본 모델도 동일하게 `IS_FAILED_TRIP`(= `SUCCESS_SCORE < 35` → 1, else 0)을 예측합니다.
- 데이터 분할: `train_test_split(test_size=0.3, random_state=42)`로 학습/테스트 분리.
- 피처 세트: `LITE_FEATURES = ['TRIP_DAYS','GENDER','AGE_GRP','ACTIVITY_TYPE_CD']`
  - TRIP_DAYS: 연속형(숫자)로 사용.
  - GENDER/AGE_GRP/ACTIVITY_TYPE_CD: 범주형으로 사용(문자열 권장).
- 전처리 로직(간단 규칙):
  - 학습 세트의 object 컬럼에 대해 숫자 변환 성공률이 95% 이상이면 숫자형으로 강제 변환, 그렇지 않으면 문자열로 캐스팅하여 범주형 유지.
  - 최종 범주형 목록을 `cat_cols_lite`로 구성하고, CatBoost에 `cat_features=cat_cols_lite`로 전달.
- 모델/학습 설정:
  - 알고리즘: `CatBoostClassifier`(대칭 트리 기반 GBDT, 범주형은 내부 통계/순차 인코딩으로 처리).
  - 손실/평가지표: `loss_function='Logloss'`, `eval_metric='PRAUC'`.
  - 불균형 처리: `auto_class_weights='Balanced'`로 클래스 가중 자동 설정.
  - 조기 종료: `early_stopping_rounds=100` 적용.
  - 난수 고정: `random_seed=42`, `verbose=False`.
  - 하이퍼파라미터: 메인 모델의 Optuna 탐색 결과(`best_trial.params`)를 그대로 사용하여 일관된 학습 레시피 적용(별도의 Optuna 재탐색 없음).
- 저장 경로: `ML/outputs/01_Catboost/catboost_best_model_lite.joblib`
- 임계값: 기본 0.5 사용 권장. 필요 시 서비스 맥락에 맞춰 조정 가능(Precision/Recall 트레이드오프 고려).
- 기대/한계:
  - 장점: 입력이 단순해 빠른 통합과 수집 비용 절감.
  - 한계: 메인 모델 대비 정보 손실로 인해 PR-AUC, Recall 등 성능 저하 가능. 필요 시 비즈니스 임계값 튜닝 또는 피처 확장을 검토.
  - 카테고리 값 미스매치(새로운 코드/철자)는 자동 처리되지만 예측 안정성 저하 가능. 운영 시 허용 가능한 도메인 값 사전 정의를 권장.

### 13) 사용 방법 요약(Quick Start)

- 환경 준비

  - `python -m venv .venv && source .venv/bin/activate`
  - `pip install --upgrade pip && pip install -r requirements.txt`

- 모델 파일 준비(둘 중 하나)

  - 이미 저장된 모델 사용: `ML/outputs/01_Catboost/catboost_best_model.joblib`(Full), `ML/outputs/01_Catboost/catboost_best_model_lite.joblib`(Lite) 존재 확인
  - 또는 노트북 실행해 생성: `jupyter lab` → `ML/01_CatBoost.ipynb` 실행(마지막 셀에서 자동 저장)

- 단일 예측(CLI, Lite 모델)

  - 기본: `python model_test.py`
  - 인자 전달: `python model_test.py --trip-days 2 --gender M --age-grp 40대 --activity-type A03 --threshold 0.5`

- 파이썬에서 직접 사용(Full 모델)

  - `joblib.load('ML/outputs/01_Catboost/catboost_best_model.joblib')`
  - 입력은 `BINARY_CLASSIFICATION_FEATURES` 스키마와 동일해야 하며, 범주형 컬럼은 문자열로 캐스팅 권장

- 파이썬에서 직접 사용(Lite 모델, 4피처)

  - `joblib.load('ML/outputs/01_Catboost/catboost_best_model_lite.joblib')`
  - 입력 컬럼: `['TRIP_DAYS','GENDER','AGE_GRP','ACTIVITY_TYPE_CD']`
  - `predict_proba(X)[:, 1]` → 실패(1) 확률, `(proba >= 0.5).astype(int)` → 레이블

- 출력 해석

  - 확률: `class=1(실패)`의 추정 확률
  - 레이블: `threshold` 이상이면 1(실패), 미만이면 0(성공)
  - 서비스 목적에 따라 `threshold` 조정 가능(Precision/Recall 트레이드오프)

- 자주 발생하는 오류와 대응
  - 모델 경로 오류: 경로 확인 또는 노트북 재실행하여 모델 생성
  - 누락/오탈자 컬럼: 입력 DataFrame에 요구 컬럼이 정확히 존재해야 함
  - dtype 이슈(범주형): 문자열로 캐스팅하여 전달(`X[obj_cols] = X[obj_cols].astype(str)`)
