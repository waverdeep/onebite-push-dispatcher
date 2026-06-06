# onebite-push-dispatcher

OneBite의 **적응형 데일리 리마인드**(웹 푸시)를 매시 발송하는 [Cloud Run Job](https://cloud.google.com/run/docs/create-jobs)입니다. (ADR 0002 — `onebite-web/docs/decisions/0002-web-push.md`)

매 실행(매시 정각)마다 **그 시각(KST hour) 슬롯에 알림을 받기로 한 유저**를 찾아
`sender.deliver()`로 ① Web Push 발송 + ② 인앱 알림(`notifications` 행) 적재를 함께
수행합니다. 발송 후엔 그 유저의 최근 풀이 시각으로부터 다음날 알림 시각을 재학습합니다
(`daily_push_hour_auto`인 유저만).

> 이 프로젝트는 `onebite-server`의 `app/`에서 **발송에 필요한 부분만** 복사해 단독
> 빌드/배포합니다. FastAPI·라우터 등 웹 계층은 포함하지 않습니다. **드리프트 주의**:
> `app/models/*`, `app/domains/notifications/sender.py`, `.../adaptive.py`, `app/core/*`는
> 서버 원본의 복사본입니다. 서버에서 이들이 바뀌면 이쪽도 함께 갱신하세요. (sender·adaptive는
> 서버에서 **fastapi 의존 0**으로 설계되어 무손실 복사됩니다.)

## 동작

1. **발송 슬롯(KST 시)** 결정 — 다음 순서로 (먼저 맞는 것):
   - CLI 인자 — `python job_main.py 14`
   - `PUSH_HOUR` 환경변수 — `PUSH_HOUR=14`
   - 기본값 — **현재 KST 시각의 시(hour)**
2. 대상 유저: `daily_push_enabled = true AND daily_push_hour == 슬롯 AND deleted_at IS NULL`.
3. **멱등**: 오늘(00:00 KST 이후) 같은 유저에게 `daily_reminder` 알림이 이미 있으면 건너뜀
   (스케줄러 재시도/중복 트리거 방지).
4. 각 유저 `sender.deliver(...)` → 푸시 + 알림 적재 + 만료(404/410) 구독 정리.
5. 발송 유저만 `adaptive.learn_push_hour()`로 다음날 `daily_push_hour` 갱신(`auto`만).

성공 시 exit 0, 실패 시 non-zero로 종료해 Cloud Run/스케줄러가 재시도합니다.

### 알림 시각 학습 (ADR 0002 결정 F)

- 신규 유저 디폴트 = **KST 13시**(`user_settings.daily_push_hour` server_default).
- 이후 **최근 7일 풀이 시각(`daily_attempts.completed_at`, KST 변환) 중앙값 → 가장 가까운
  정시 반올림**. 중앙값이라 우연한 새벽 풀이 등 일탈에 흔들리지 않습니다.
- 안 푼 주(데이터 0개) → 학습값 유지. 유저가 설정에서 수동 고정 시(`auto=false`) 학습 중단.

## 로컬 실행

```bash
uv sync
cp .env.example .env   # DB_PASSWORD / VAPID_* 채우기

# 현재 KST 시각 슬롯으로 발송
uv run python job_main.py

# 특정 슬롯(예: 14시) 강제 — dry-run/디버깅
uv run python job_main.py 14
```

## 배포 (Cloud Run Job)

서버와 같은 GCP 프로젝트/리전(`asia-northeast3`)을 가정합니다.

### 최초 1회 — env/secret 설정

`cloudbuild.yaml`은 env/secret을 건드리지 않으므로(재배포 시 보존) 처음 한 번만 설정합니다.
DB 비밀번호와 **VAPID 개인키**는 Secret Manager 권장입니다.

```bash
PROJECT_ID=$(gcloud config get-value project)
REGION=asia-northeast3

gcloud run jobs update dispatch-push \
  --region "$REGION" \
  --task-timeout=600s \
  --max-retries=1 \
  --set-env-vars=ENV=prod,SERVICE_TZ=Asia/Seoul,DB_HOST=...,DB_PORT=6543,DB_USER=...,DB_NAME=postgres,DB_SSL=true,DB_SCHEMA=onebite,VAPID_PUBLIC_KEY=...,VAPID_SUBJECT=mailto:onebite@example.com \
  --set-secrets=DB_PASSWORD=onebite-db-password:latest,VAPID_PRIVATE_KEY=onebite-vapid-private:latest
```

> ⚠️ VAPID 키쌍은 1회 생성 후 고정합니다. 키를 교체하면 **기존 모든 구독이 무효화**되어
> 전 사용자가 재구독해야 합니다(ADR 0002 결정 B).

### 빌드 & 배포 — cloudbuild.yaml

```bash
# 기본값(IMAGE=push-dispatcher, JOB=dispatch-push)으로 배포
gcloud builds submit --config cloudbuild.yaml

# 커밋 해시 태깅 (권장)
gcloud builds submit --config cloudbuild.yaml \
  --substitutions=_TAG=$(git rev-parse --short HEAD)
```

### 수동 실행 (테스트)

```bash
gcloud run jobs execute dispatch-push --region "$REGION"
# 특정 슬롯으로
gcloud run jobs execute dispatch-push --region "$REGION" --args=14
```

## 크론 스케줄 (Cloud Scheduler) — 매시

```bash
PROJECT_ID=$(gcloud config get-value project)
REGION=asia-northeast3
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
INVOKER_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud scheduler jobs create http dispatch-push-trigger \
  --location "$REGION" \
  --schedule="0 * * * *" \
  --time-zone="Asia/Seoul" \
  --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/dispatch-push:run" \
  --http-method=POST \
  --oauth-service-account-email="$INVOKER_SA"

# invoker 권한 부여
gcloud run jobs add-iam-policy-binding dispatch-push \
  --region "$REGION" \
  --member="serviceAccount:${INVOKER_SA}" \
  --role="roles/run.invoker"
```

- `--schedule="0 * * * *"` + `--time-zone="Asia/Seoul"` → **매시 정각(KST)** 실행.
  각 실행이 그 시각 슬롯의 유저에게 발송합니다.

## 구조

```
onebite-push-dispatcher/
├── app/
│   ├── core/            # config(+VAPID), db, errors(트림됨), text — 코어만
│   ├── models/          # ORM 모델 전체 (relationship 등록 위해 모두 필요)
│   └── domains/notifications/   # sender.py(발송), adaptive.py(학습) — 서버 복사본
├── job_main.py          # Cloud Run Job 진입점 (ENTRYPOINT, 매시 발송)
├── Dockerfile
├── cloudbuild.yaml      # 빌드 → 푸시 → Job 배포 파이프라인
├── pyproject.toml / uv.lock
└── .env.example
```

> `app/core/errors.py`는 onebite-server 원본에서 FastAPI 의존을 떼어낸 트림 버전입니다
> (에러 클래스 자체는 서버와 동일). `sender.py`/`adaptive.py`는 서버 원본 그대로입니다.
