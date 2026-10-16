(function(){'use strict';
 let snapshot=null,pending=false,failed=false;
 const h=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const cards={
  score_inventory:{label:'점수는 있음 · 당시 사용 가능성은 미검증',state:'가용시각 증빙 필요',detail:'동결한 {factor_count}개 정의의 {signal_months}개 월별 점수 존재를 읽기 전용으로 확인했습니다. 값의 존재와 월말까지 실제로 알 수 있었음은 다릅니다. 점수·종목군·시총의 원천 가용시각과 정의 결합이 남았습니다.'},
  raw_opens:{label:'시가 후보 확보 · 총수익 인증 전',state:'미인증 로컬 자료',detail:'월초 관측 시가 후보를 로컬에서 준비했습니다. 0·결측을 삭제하거나 수익률로 채우지 않았습니다. 첫 관측 거래일이 공식 첫 정규 세션이라는 증빙과 기업행사·종목 식별 검증이 필요합니다.'},
  stock_accounting:{label:'주식 총수익 계산 부품',state:'합성 테스트 통과',detail:'배당·분할 등의 회계 처리와 미래 정보 차단 검사를 구현했습니다. 실제 원천의 완전한 기업행사 목록·PIT 입력 연결과 독립 대사는 아직입니다. 상폐·합병·거래정지 등 미지원 상황은 통과시키지 않습니다.'},
  calendar:{label:'공식 개장일과 개장시각',state:'필수 자료 미충족',detail:'휴장과 지연 개장을 포함하는 공식 달력이 필요합니다. 일별 시가만으로 09:00 체결을 입증하지 않습니다. 정규 개장시각·주식 첫 거래·지수 발표 시가는 서로 다른 값입니다.'},
  benchmark:{label:'KRX300 총수익 지수의 월초 값',state:'필수 자료 미충족',detail:'동일 진입·평가 시점의 공식 원화 총수익 지수와 정정·시각 증빙이 필요합니다. 기존 로컬 원천에서 명시적인 TR 계열은 확인하지 못했습니다. 지수는 2018년 12월에 출시돼 초기 구간의 공식 소급 산출 여부도 검토해야 합니다.'},
  execution_bundle:{label:'196개 성과 계산',state:'실행 전',detail:'입력 전체를 고정 계획에 결합해 인증하는 최종 어댑터·대사 단계가 남았습니다. 필수 입력이 빠진 현재 상태는 실행을 막습니다. 종가 수익이나 합성 테스트를 실제 월초 성과로 대신 표시하지 않습니다.'}
 };
 const expected={score_inventory:'VALUES_OBSERVED_PIT_UNVERIFIED',raw_opens:'LOCAL_CANDIDATES_UNCERTIFIED',stock_accounting:'COMPONENT_TESTED_ADAPTERS_REQUIRED',calendar:'OFFICIAL_SESSION_TIMES_REQUIRED',benchmark:'OFFICIAL_OPEN_TR_SOURCE_REQUIRED',execution_bundle:'NOT_CERTIFIED_NOT_RUN'};
 function bind(s,c){
  if(c.real_performance_computed!==false||c.actual_fill_verified!==false||c.independent_oos!==false)throw Error('Not an unexecuted comparison');
  if(s.schema_version!=='public-monthly-preparation-v1'||s.evidence_kind!=='MANUALLY_REVIEWED_LOCAL_READINESS')throw Error('Unsupported preparation');
  for(const key of ['comparison_id','plan_sha256','catalog_sha256','planned_comparisons','completed_comparisons'])if(s[key]!==c[key])throw Error('Stale preparation');
  if(s.real_performance_computed!==false||s.execution_certified!==false||s.actual_fill_verified!==false||s.independent_oos!==false||s.completed_comparisons!==0||s.source_data_refreshed!==false)throw Error('Uncertified performance claim');
  if(!Array.isArray(s.observations)||s.observations.length!==6||new Set(s.observations.map(x=>x.id)).size!==6||s.observations.some(x=>expected[x.id]!==x.status))throw Error('Invalid preparation states');
  const n=v=>{const [y,m]=v.split('-').map(Number);return y*12+m-1;},p=s.period;
  if(p.signal_start!==c.decision_start||p.signal_end!==c.decision_end||p.signal_months!==n(c.decision_end)-n(c.decision_start)+1||p.required_opening_months!==p.signal_months+1||n(p.first_opening_month)!==n(c.decision_start)+1||n(p.final_opening_month)!==n(c.decision_end)+2)throw Error('Invalid preparation period');
  return s;
 }
 function render(comparison,rerender){
  if(snapshot)try{bind(snapshot,comparison);}catch{snapshot=null;failed=true;}
  if(!snapshot&&!pending&&!failed){pending=true;fetch('./data/monthly-preparation.json').then(r=>{if(!r.ok)throw Error('Unavailable');return r.json();}).then(s=>{snapshot=bind(s,comparison);pending=false;rerender();}).catch(()=>{pending=false;failed=true;rerender();});}
  if(!snapshot)return `<section class="panel section-gap"><h2>입력 준비 점검</h2><p>${failed?'현재 계획에 결합된 추가 점검을 불러오지 못했습니다. 준비 완료나 성과를 추정하지 않습니다.':'계획에 결합된 입력 준비 점검을 확인하고 있습니다.'}</p></section>`;
  const p=snapshot.period;
  return `<section class="section-gap" id="comparison-preparation"><div class="section-head"><div><span class="eyebrow">PREPARATION ≠ PERFORMANCE</span><h2>계산을 막는 입력을 하나씩 확인합니다.</h2></div></div><p class="lede">신호 ${h(p.signal_start)}–${h(p.signal_end)} · ${p.signal_months}개월. 매수·최종 평가에 필요한 월초 값은 ${h(p.first_opening_month)}–${h(p.final_opening_month)}, 총 ${p.required_opening_months}개입니다.</p><p class="chart-note">점검 ${h(new Date(snapshot.reviewed_at).toLocaleString('ko-KR',{timeZone:'Asia/Seoul'}))+' KST'} · 수작업으로 검토한 준비 상태입니다. 자동 자료 수집·수익률 갱신이 아닙니다.</p><p class="chart-note">마지막 시가로 보유 자산을 평가하며, 강제 청산 매도·그 청산 비용은 계획에 포함하지 않습니다.</p><div class="two-grid">${snapshot.observations.map(x=>{const c=cards[x.id];return `<article class="panel" data-preparation-stage="${h(x.id)}"><span class="badge ${x.id==='stock_accounting'?'blue':'amber'}">${c.state}</span><h3>${c.label}</h3><p>${c.detail.replace('{factor_count}',comparison.factor_count).replace('{signal_months}',p.signal_months)}</p></article>`;}).join('')}</div><details class="panel source section-gap"><summary>자료 확보 경로와 아직 결정하지 않은 조건</summary><p>공식 KRX 자료의 현재 이용 권한·다운로드 범위 확인이 필요합니다. 로그인·가입·유료 구매·새 API 키를 진행하지 않았습니다. 공식 무료 FSC API는 2020년부터여서 초기 구간을 채우지 못합니다. 무료 열람이 원자료 공개 권한을 뜻하지 않습니다.</p><p>가능한 경로는 공식 월초 TR 관측값 또는 전일 TR·가격지수 종가, 당일 가격지수 시가와 시점이 맞는 배당 지수 포인트의 검증된 결합입니다. 종가 TR/가격지수 비율을 시가에 단순 곱하면 배당일에 같은 정의가 되지 않습니다.</p><p>기간·벤치마크·매매 시점을 바꾸는 대안은 현재 계획의 결과로 합치지 않고 별도 사전등록이 필요합니다. 원천 파일·종목별 값·접속 정보는 이 사이트에 포함하지 않습니다.</p><p><a href="https://download.kiwoom.com/web/KiwoomEtnRuleBook7.pdf" target="_blank" rel="noopener">KRX 총수익지수 방법론 ↗</a> · <a href="https://www.data.go.kr/data/15094807/openapi.do" target="_blank" rel="noopener">공식 금융위원회 지수시세 API ↗</a></p><div class="download-row"><a class="small-button" href="./data/monthly-preparation.json" download>입력 준비 상태 JSON ↓</a></div><p class="chart-note">계획·카탈로그 해시가 다르면 이 보조 점검은 표시하지 않습니다. 계산 부품의 테스트 통과는 실제 입력의 인증이 아닙니다.</p></details></section>`;
 }
 window.MonthlyReadiness=Object.freeze({render,bind});
})();
