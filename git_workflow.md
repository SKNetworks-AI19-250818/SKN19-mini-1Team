### **EDA 프로젝트를 위한 추천 Git 워크플로우 feat. gemini**

두 개의 핵심 브랜치와, 작업 단위를 명확히 하는 피쳐 브랜치로 구성합니다.

  * `main`: **최종 결과물 브랜치**. 1차 프로젝트(EDA)가 완전히 끝나고 팀원 모두가 동의한 최종 버전의 코드와 결과물만 존재하는 곳입니다.
  * `develop`: **중간 통합 브랜치**. 각자 작업한 내용들이 1차적으로 통합되는 공간입니다. 이 브랜치의 코드는 항상 실행 가능해야 합니다.
  * `feature/{기능}`: **개인 작업 브랜치**. 실제 모든 코드 작성과 수정은 이 브랜치에서 이루어집니다.

-----

### **브랜치 명명 규칙 및 선언**

명확한 브랜치 이름은 작업 내용을 한눈에 파악하게 해 협업 효율을 높입니다. 다음과 같은 규칙을 제안합니다.

#### **1. 개인 작업 브랜치 (Feature Branches)**

`feature/[작업내용]-[작업자이니셜]` 형태로 생성합니다.

  * **데이터 로딩 및 전처리:**
      * `feature/load-and-clean-data-kjw` (강지완)
-----

### **작업 프로세스 (Step-by-Step)**

팀원 A (강지완)가 '데이터 로딩 및 전처리' 작업을 맡았다고 가정하고 전체 흐름을 설명하겠습니다.

#### **1단계: 작업 브랜치 생성**

모든 작업은 최신 `develop` 브랜치에서 시작합니다.

1.  로컬 `develop` 브랜치를 최신 상태로 업데이트합니다.
    ```bash
    git checkout develop
    git pull origin develop
    ```
2.  자신의 작업을 위한 새로운 `feature` 브랜치를 생성하고 이동합니다.
    ```bash
    git checkout -b feature/load-and-clean-data-kjw
    ```

#### **2단계: EDA 코드 작업 및 커밋**

새로 만든 `feature/load-and-clean-data-kjw` 브랜치에서 Jupyter Notebook이나 Python 스크립트로 시각화 코드를 작성하고, 의미 있는 단위로 작업을 나누어 커밋(Commit)합니다.

  * **좋은 커밋 메시지 예시:**
      * `feat: 전처리 기능 추가` (기능 추가)
      * `fix: 결측치 처리 부분 수정` (수정)
      * `refactor: 결측치 처리 부분 코드 개선` (코드 개선)

#### **3단계: 원격 저장소에 Push**

로컬에서 작업이 어느 정도 완료되면, 다른 팀원들이 볼 수 있도록 원격 저장소(GitHub)에 Push 합니다.

```bash
git push origin feature/load-and-clean-data-kjw
```

#### **4단계: Pull Request (PR) 생성**

Push가 완료되면 GitHub 리포지토리 페이지에 가서 **Pull Request (PR)** 를 생성합니다.

  * **PR 방향:** `feature/load-and-clean-data-kjw` → `develop`
  * **내용 작성:** 내가 어떤 작업을 했는지, 다른 팀원들이 무엇을 중점적으로 봐주면 좋은지 상세히 작성합니다. (예: "데이터 로딩 및 전처리 작업을 완료하였습니다. 전처리 과정에서의 이상치, 결측치가 있는지 확인해주세요.")

#### **5단계: 코드 리뷰 및 Merge**(필요시)

  * **리뷰:** 
  * **수정:** 
  * **Merge:** 현재 feat 브랜치를 `develop` 브랜치로 병합(Merge)합니다.

#### **6단계: 브랜치 삭제**

Merge가 완료되어 더 이상 필요 없어진 작업 브랜치는 삭제하여 저장소를 깔끔하게 유지합니다.

  * **원격 브랜치 삭제:** GitHub의 PR 페이지에서 Merge 후 바로 삭제할 수 있습니다.
  * **로컬 브랜치 삭제:**
    ```bash
    git checkout develop
    git fetch -p
    git pull
    git branch -d feature/load-and-clean-data-kjw
    ```

**모든 팀원이 위 1\~6단계를 각자의 작업에 맞춰 반복합니다.**

-----

### **1차 프로젝트 최종 마무리**

모든 EDA 작업이 끝나고 `develop` 브랜치에 결과물이 성공적으로 통합되었다면, 이를 `main` 브랜치에 병합하여 1차 프로젝트를 공식적으로 마무리합니다.

1.  `develop` 브랜치에서 `main` 브랜치로 향하는 PR을 생성합니다.
2.  팀원 전체가 마지막으로 코드를 리뷰하고, 이상이 없으면 `main`으로 Merge합니다.
3.  프로젝트의 중요한 기점을 표시하는 **태그(Tag)** 를 생성하면 더욱 좋습니다.
    ```bash
    git checkout main
    git pull origin main
    git tag -a v1.0-EDA -m "EDA phase completed"
    git push origin v1.0-EDA
    ```