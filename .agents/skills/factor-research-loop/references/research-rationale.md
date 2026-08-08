# 연구 설계 근거

이 문서는 `factor-research-loop`의 절차를 바꾸거나 사람에게 설계 이유를 설명할 때만 읽는다.
일반 연구 루프의 입력은 아니며, 현재 데이터 상태나 개별 팩터 결과를 저장하지 않는다.

## 목차

- [결론](#결론)
- [설계 판단과 근거](#설계-판단과-근거)
- [파일별로 넣지 말아야 할 내용](#파일별로-넣지-말아야-할-내용)
- [참고 문헌](#참고-문헌)

## 결론

효율적인 Agent 연구 루프는 다음 세 종류의 정보를 분리해야 한다.

1. **절차 기억**: `SKILL.md`의 고정 실행 순서와 금지사항
2. **에피소드 기억**: `latest.md`의 현재 snapshot과 과거 시행 요약
3. **감사 증거**: 각 사이클의 `report.md`, `result.json`, 후보 소스

이 분리는 매번 모든 과거 문서를 읽는 비용을 줄이면서도 실패 기록과 시행 횟수를 잃지 않게 한다.

## 설계 판단과 근거

### 프롬프트는 짧은 지도와 상태 기반 행동으로 구성한다

`SKILL.md`에는 목표, 권위 있는 정보 출처, 불변조건, 상태별 다음 행동과 종료 조건만 둔다.
현재 컬럼·성과·임계값처럼 변하는 정보는 코드와 생성 컨텍스트에 남긴다. OpenAI의 Codex
harness 사례는 거대한 단일 지침서가 컨텍스트를 잠식하고 빠르게 낡으므로 짧은 지도와 검증 가능한
저장소 문서를 권한다. OpenAI의 agent 지침은 각 단계가 구체적인 행동·출력에 대응하고 흔한
예외를 조건 분기로 다루도록 권하며, Anthropic은 복잡한 프레임워크보다 단순하고 합성 가능한
workflow와 programmatic gate에서 시작하라고 제안한다.

Agent의 실행은 `상태 확인 → 행동 → 도구 결과 관찰 → 검증 또는 다음 행동`으로 표현한다.
이는 추론과 외부 행동을 교차시키는 ReAct의 운영 형태와 맞지만, 긴 사고과정의 출력을 요구하지
않는다. 핵심 연구 판정은 자연어 추론이 아니라 `engine/gate.py`가 담당한다.

Few-shot은 아이디어나 성과 숫자를 예시로 주입하지 않고, 자주 혼동되는 의사결정 경계를 짧은
대조 예시로만 제공한다. In-context example은 행동 패턴을 학습시키는 데 유용하지만, 예시의 선택과
순서에 따라 결과가 크게 달라질 수 있다. 따라서 단일 신호/합성, 데이터 공백/대체, 운영 재시도/
결과 튜닝, SEALED/reveal처럼 안정적인 정책 경계만 소수의 균형 잡힌 예시로 둔다.

### 가설을 먼저 고정한다

팩터 정의, 방향, 파라미터와 반증 조건을 평가 전에 기록한다. 결과를 본 뒤 lookback이나 산식을
고치는 행위는 확인 연구가 아니라 새 가설 생성이므로 새 파일과 새 시행으로 남긴다.

- Nosek 외의 사전등록 논의는 예측과 사후 설명을 분리하는 것이 선택적 보고와 결과 의존적
  의사결정을 드러내는 핵심이라고 정리한다.
- Harvey·Liu·Zhu는 수많은 팩터가 시험되는 자산가격 연구에서 통상적인 단일 검정 기준이
  충분하지 않다고 보여준다.

### 한 사이클에는 한 정의만 평가한다

Agent가 한 사이클 안에서 여러 변형을 시험하고 가장 좋은 것만 남기면 시행 횟수가 숨겨진다.
따라서 후보 하나를 한 번 평가하고, 모든 고유 정의를 원장과 히스토리에 보존한다. 다중검정과
귀무 보정은 결정론적 엔진에 맡기고 Agent가 유리한 통계만 선택하지 못하게 한다.

- White의 Reality Check와 Harvey·Liu·Zhu의 연구는 데이터 스누핑과 다중 시행을 성과 해석에
  포함해야 한다는 근거를 제공한다.
- Bailey 외의 백테스트 과적합 연구는 같은 표본에서 많은 설정을 고른 최적 전략의 OOS 성능이
  크게 악화될 수 있음을 다룬다.

### 표본과 구현을 표준화하고 OOS를 고정한다

유니버스, PIT 가용일, 미래수익 레이블, OOS 경계와 평가 코드를 후보마다 바꾸지 않는다.
경제적 아이디어의 차이와 구현 선택의 차이를 분리하기 위해 모든 후보에 같은 엔진을 적용한다.

- Hou·Xue·Zhang은 미세주식 완화와 일관된 재검증을 적용하면 다수의 기존 이상현상이 약해짐을
  보고한다.
- Jensen·Kelly·Pedersen은 통일된 팩터 구성과 시간·국가 OOS 검증을 통해 내부·외부 타당성을
  함께 평가한다. 두 연구의 결론은 다르지만, 표준화와 외부 검증이 필요하다는 점은 공통적이다.
- McLean·Pontiff는 예측변수 수익률이 원 논문 표본 밖과 발표 이후에 감소함을 보여주므로,
  고정 OOS를 개발 표본과 분리해야 한다.

연구 Python과 생산 Gold SQL은 같은 정의의 서로 다른 구현이다. 연구 결과가 좋아도 SQL의 join,
시점 조건, 결측 처리나 `predicted_sign`이 다르면 실제 Gold 신호는 다른 팩터가 된다. 따라서
discovery를 통과한 모든 후보의 definition hash와 SQL SHA256을 먼저 결박하고, 봉인 OOS를 열기
전에 discovery 구간에서 key·raw value·rank parity를 검증한다. 이 검증은 구현 오류를 찾기 위한
것이며 Gold write나 발행 승인이 아니다.

IC의 정의·효과크기·시간 안정성·다중검정 임계값에 관한 구체적인 판단과 출처는 활성
`factor-research/docs/factor-promotion-criteria.md`에 분리해 둔다.

### 최종 OOS는 campaign 단위로 봉인한다

고정된 구간도 반복해서 결과를 보고 다음 가설을 고르면 연구자의 선택을 통해 개발 데이터가 된다.
따라서 여러 후보를 epoch 시작 전에 동결하고, discovery 성찰에는 구조적 실패와 중복만 전달한다.
모든 epoch을 닫으면 `비REJECT ∩ discovery BY PASS` 후보 전부를 자동 확인 대상으로 확정한다.
사람이 좋아 보이는 후보만 고르는 자유도를 없애야 시행 원장에 드러나지 않는 선택 편향을 막을 수
있다. 최종 OOS는 이 전체 family에 정확히 한 번 공개하고 campaign을 종료한다. Bailey 외의
백테스트 과적합과 McLean·Pontiff의 표본 밖 성능 감소는 단순한 시간 분할뿐 아니라 holdout을
반복적인 모델 선택에서 보호해야 한다는 운영 근거가 된다.

역사 데이터도 후보 정의·선택 전에 접근을 차단하면 시간 순서가 지켜진 holdout이 될 수 있다.
현재 reveal-ready 수익률월에서 36 signal개월을 역산해 봉인하면 수년을 새로 기다리지 않고 시간 강건성을
확인할 수 있지만, 이미 그 구간의 결과를 본 후보에 소급 적용해서 독립성이 생기지는 않는다.
그런 결과는 `retrospective-only`로만 남긴다. 같은 달력 구간을 새 정의에 재사용하면 완전한
program-wide 미관측 표본은 아니므로 `HISTORICAL_REUSED_WINDOW`와 이전 exposure id를 남긴다.
이는 지금 판단 가능한 표준 시간분할을 제공하지만 증거의 독립성을 복원하지는 않는다. 36개월과 IC 임계값의 정량 근거는 활성
`factor-research/docs/factor-promotion-criteria.md`에만 둔다.

### 거래 가능성은 보되 가설 검정과 혼동하지 않는다

유동성, 회전율, 비용과 AUM은 실제 구현에 중요하다. 다만 이 레포의 현재 ruleset에서는 절대
포트폴리오 수익률 컷이 아니라 IC 기반 판정과 별도 진단으로 관리한다. Agent는 진단값을 임의의
탈락 기준으로 승격하지 않는다.

- Novy-Marx·Velikov은 거래비용이 이상현상의 수익성과 통계적 유의성을 낮추며, 특히 회전율이
  높은 전략의 구현 가능성이 약함을 보여준다.

### 다음 루프에는 압축된 교훈만 전달한다

`latest.md`에는 현재 입력, 등록 팩터 식별자, 시행별 판정·실패 항목과 가장 강한 관계만 둔다.
성과 수치와 상세 표는 불변 report/result에 남기고 필요할 때만 연다. Agent가 성공·실패 피드백을 짧은 언어
메모로 다음 시행에 전달하는 방식은 LLM Agent의 episodic memory 연구와도 방향이 맞는다.

- Reflexion은 시행 피드백을 언어 형태의 episodic memory로 유지하는 Agent가 후속 의사결정을
  개선할 수 있음을 보인다. 이 레포에서는 자유형 자기반성 대신 결정론적으로 생성한
  `latest.md`를 사용해 기억 왜곡을 줄인다.

## 파일별로 넣지 말아야 할 내용

- `SKILL.md`: 현재 날짜, 데이터 기간, 팩터 목록, 과거 판정, 임계값, 개별 결과 수치
- `latest.md`: 고정 실행 절차, 후보 코드 계약, 전체 보고서 표
- `report.md`: 다음 루프 전체 상태, 다른 모든 시행의 상세 기록
- `reflection.md`: 보고서 수치 복사, 동일 후보의 튜닝 제안, 봉인 OOS 결과
- 자유형 메모: 이미 history/report/result에 존재하는 내용의 수동 복사본

## 참고 문헌

- Nosek, Ebersole, DeHaven, Mellor (2018), [The Preregistration Revolution](https://doi.org/10.1073/pnas.1708274114)
- Harvey, Liu, Zhu (2016), [… and the Cross-Section of Expected Returns](https://academic.oup.com/rfs/article-abstract/29/1/5/1843824)
- White (2000), [A Reality Check for Data Snooping](https://doi.org/10.1111/1468-0262.00152)
- Bailey, Borwein, López de Prado, Zhu (2016), [The Probability of Backtest Overfitting](https://doi.org/10.21314/JCF.2016.322)
- Hou, Xue, Zhang (2020), [Replicating Anomalies](https://doi.org/10.1093/rfs/hhy131)
- McLean, Pontiff (2016), [Does Academic Research Destroy Stock Return Predictability?](https://doi.org/10.1111/jofi.12365)
- Jensen, Kelly, Pedersen (2023), [Is There a Replication Crisis in Finance?](https://doi.org/10.1111/jofi.13249)
- Novy-Marx, Velikov (2016), [A Taxonomy of Anomalies and Their Trading Costs](https://doi.org/10.1093/rfs/hhv063)
- Shinn 외 (2023), [Reflexion: Language Agents with Verbal Reinforcement Learning](https://proceedings.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html)
- Brown 외 (2020), [Language Models are Few-Shot Learners](https://arxiv.org/abs/2005.14165)
- Lu 외 (2022), [Fantastically Ordered Prompts and Where to Find Them](https://aclanthology.org/2022.acl-long.556/)
- Min 외 (2022), [Rethinking the Role of Demonstrations](https://aclanthology.org/2022.emnlp-main.759/)
- Yao 외 (2023), [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)
- Liu 외 (2024), [Lost in the Middle](https://aclanthology.org/2024.tacl-1.9/)
- Wallace 외 (2024), [The Instruction Hierarchy](https://arxiv.org/abs/2404.13208)
- OpenAI (2026), [Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/)
- OpenAI (2026), [Inside OpenAI's in-house data agent](https://openai.com/index/inside-our-in-house-data-agent/)
- OpenAI (2025), [A practical guide to building AI agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)
- Anthropic (2024), [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- Anthropic (2025), [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
