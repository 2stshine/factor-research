# Asset identity 재구축 기록

## 결론

기존 연구 캐시는 현재 RDS의 종목 식별자 계약을 재현하지 못하므로 더 이상 연구 입력으로
사용하지 않는다. 현재 RDS에서 패널을 전량 재구축했고, 새 캐시와 live RDS의
`krx_month_end_asset_ticker_v1` digest가 정확히 일치했다. Gold에는 쓰지 않았다.

## 원인

2026-08-10 Silver KRX 이력 재구축이 `public.asset`을 `TRUNCATE ... RESTART IDENTITY`한 뒤
다시 적재했다. `asset_id`는 내부 surrogate key이므로 기존 캐시와 현재 RDS에서 같은 숫자가
서로 다른 ticker를 가리키게 됐다. 기존 cache↔campaign snapshot digest 검사는 캐시 내부
재현성만 확인했기 때문에 live RDS의 재키잉을 조기에 잡지 못했다.

## 조치

- 기존 `.cache/panel.pkl`을 파일 SHA-256 경로에 보존했다.
- 현재 인증 RDS Silver로 1995-05-24~2026-08-10 패널을 다시 만들었다.
- 월말 `(trade_date, asset_id, ticker)`를 정렬해 SHA-256으로 묶었다.
- cache self-check와 live RDS audit을 모두 통과한 파일만 활성화했다.
- campaign 시작, discovery 평가, Gold SQL parity, OOS 공개 전에 동일한 read-only
  `REPEATABLE READ` snapshot에서 같은 cutoff identity를 대조한다.
- OOS 비활성 종목 판정에 쓰는 closure월 관측도 별도 identity digest로 동결·대조한다.
- ticker 유효기간 누락·중복 또는 ID 재배정은 팩터 계산 전에 중단한다.

## 기존 campaign 처리

`campaign-20260811-001`의 discovery 결과, epoch reflection, BY 결과와 parity 실패 시도는 원래
기록대로 보존한다. 다만 입력 identity를 인증할 수 없으므로 campaign은
`CLOSED_INVALIDATED_INPUT_IDENTITY`, OOS는 `NOT_USED`로 종료한다. OOS 공개 원장은 만들지
않는다. 이번 migration은 후보 자동 재평가 권한을 부여하지 않는다.

## 핵심 수치

| 구분 | 기존 캐시 | 현재 RDS 재구축 |
|---|---:|---:|
| 시작일 | 2015-01-06 | 1995-05-24 |
| 종료일 | 2026-08-06 | 2026-08-10 |
| 월말 행 | 334,354 | 733,897 |
| 종목 ID | 3,301 | 6,675 |
| 월 | 140 | 376 |
| 전체 identity digest | `eb894b87…` | `9a1a3dca…` |
| live RDS 일치 | 미검증 | MATCH |
