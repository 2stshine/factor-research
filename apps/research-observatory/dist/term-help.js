'use strict';
// Presentation-only glossary. Never changes snapshot values, research gates or calculations.
(() => {
  const terms = [
    {key:'net', title:'비용 후 초과수익', aliases:['비용 후 초과수익','비용후 초과수익'], text:'전략 수익에서 비교 기준의 수익과 모형 거래비용을 뺀 값입니다. 양수면 비용을 내고도 기준보다 앞섰다는 뜻입니다. 음수라도 전략 자체가 손실이었다는 뜻은 아닙니다.', example:'같은 기간에 전략 +12%, 기준 +8%, 비용 1%라면 +3%p입니다.', note:'여기서는 Discovery 월평균 × 12인 연율화 진단값입니다. 복리 수익률(CAGR), OOS 수익률, 실제 계좌 수익이 아닙니다.'},
    {key:'gross', title:'비용 전 초과수익', aliases:['비용 전 초과수익'], text:'거래비용을 빼기 전, 전략 수익이 비교 기준의 수익보다 얼마나 높거나 낮았는지를 나타냅니다.', example:'전략 +12%, 기준 +8%이면 초과수익은 +4%p입니다.', note:'이 화면에서는 Discovery 월평균 × 12로 표시하며, 전략 자체의 절대 수익률이 아닙니다.'},
    {key:'cost', title:'모형 거래비용', aliases:['모형 거래비용'], text:'매수·매도 때 발생할 수수료, 세금, 시장 충격 등을 정해 둔 모형으로 추정한 비용입니다. 실제 체결 내역으로 확인한 지출은 아닙니다.', note:'비용 전 초과수익에서 이 값을 빼면 비용 후 초과수익이 됩니다. 여기서는 연율화한 %p/년입니다.'},
    {key:'icir', title:'Rank ICIR · 예측 관계의 안정성', aliases:['Rank ICIR','ICIR'], text:'월평균 IC를 월별 IC의 표준편차로 나눈 값입니다. 순위 예측 관계가 달마다 얼마나 일관적인지 봅니다.', note:'이 화면의 ICIR은 연율화하지 않습니다. 수익률이나 수익률 기반 샤프지수와 다릅니다.'},
    {key:'discovery-ic', title:'Discovery IC · 개발 구간의 순위 예측력', aliases:['Discovery Rank IC','DISCOVERY RANK IC','Discovery IC'], text:'팩터를 처음 탐색·평가한 과거 구간에서, 점수 순위와 다음 달 수익률 순위가 얼마나 함께 움직였는지 측정한 평균입니다.', note:'개발에 사용한 구간의 결과입니다. 독립적인 미래 검증이나 수익률 %로 읽으면 안 됩니다.'},
    {key:'oos-ic', title:'OOS IC · 분리한 검증 구간의 순위 예측력', aliases:['CONFIRMATION RANK IC','OOS Rank IC','OOS IC'], text:'개발 구간과 따로 떼어 둔 과거 검증 구간에서 측정한 평균 순위 상관입니다. 개발에 쓰지 않은 기간에도 예측 관계가 이어졌는지 확인합니다.', note:'IC 0.05는 수익률 5%라는 뜻이 아닙니다. 한 번 열어 본 검증 구간을 다시 쓰면 새로운 독립 검증으로 볼 수 없습니다.'},
    {key:'neutral-ic', title:'중립화 IC', aliases:['중립화 IC'], text:'연구에서 정한 시장·규모·유동성 등의 영향을 통계적으로 걷어 낸 뒤에도 순위 예측 관계가 남는지 보는 지표입니다.', note:'모든 위험을 제거했다는 뜻도, 팩터가 수익의 원인임을 증명했다는 뜻도 아닙니다.'},
    {key:'gold-corr', title:'Gold 최대 상관', aliases:['Gold 최대 상관'], text:'기존 승인 팩터와 점수 순위가 얼마나 겹치는지 확인합니다. 월별 절대 순위 상관의 중앙값을 기존 팩터별로 구한 뒤 가장 큰 값을 봅니다.', note:'값이 높을수록 기존 신호와 비슷할 수 있습니다. 수익률 간 상관이나 경제적 원인의 동일성을 뜻하지는 않습니다.'},
    {key:'ic', title:'IC / Rank IC · 순위 예측력', aliases:['Rank IC','IC','순위 상관계수'], text:'팩터 점수가 높은 종목이 다음 달 수익률도 높은 순서에 놓이는지 보는 상관계수입니다. 범위는 −1부터 +1이며, 양수는 같은 방향, 음수는 반대 방향입니다.', example:'IC 0.05는 “수익률 5%”가 아닙니다.', note:'집계값은 월별 Spearman 순위 상관의 평균입니다. 좋은 IC가 비용 후 수익을 보장하지는 않습니다.'},
    {key:'net-ir', title:'Net IR · 비용 후 정보비율', aliases:['Net IR'], text:'비용 후 초과수익의 평균을 그 변동성으로 나눈 뒤 연율화한 값입니다. 비교 기준을 얼마나 안정적으로 앞섰는지 봅니다.', note:'월별 기준 평균 ÷ 표준편차 × √12입니다. 무위험 수익률을 기준으로 하는 샤프지수와 다릅니다.'},
    {key:'sharpe', title:'Sharpe · 샤프지수', aliases:['Sharpe','샤프지수'], text:'무위험 수익률보다 더 얻은 수익을 전략 수익률의 변동성으로 나눈 지표입니다. 감수한 흔들림에 비해 보상이 얼마나 있었는지 봅니다.', note:'계산 기간, 연율화와 비용 반영 여부를 확인해야 합니다. IC나 벤치마크 대비 Net IR과 같은 숫자로 비교하면 안 됩니다.'},
    {key:'spread', title:'상위−하위 수익 차이', aliases:['상위−하위 수익','상위−하위'], text:'팩터 점수가 높은 그룹의 평균 수익률에서 낮은 그룹의 평균 수익률을 뺀 값입니다. 매월 그룹을 다시 구성하고 종목별 비중을 같게 둡니다.', note:'국면 화면에서는 %p/월이며 거래비용을 반영하지 않습니다. 실제로 실행한 롱숏 전략의 손익이 아닙니다.'},
    {key:'pp', title:'%p / pp · 퍼센트포인트', aliases:['pp/년','%p/년','%p/월'], text:'두 비율의 차이를 나타내는 단위입니다. 12%와 8%의 차이는 4%p(4 pp)입니다.', note:'%p/월은 월별 차이, %p/년은 연간 기준 차이입니다. 이 대시보드의 연간 초과수익은 월평균 × 12이며 복리가 아닙니다.'},
    {key:'cagr', title:'CAGR · 연평균 복리 수익률', aliases:['CAGR'], text:'처음 투자금이 마지막 금액이 되기까지, 매년 같은 복리 수익률을 냈다고 환산한 값입니다.', note:'월별 수익률의 평균에 12를 곱한 값과 다릅니다. 이 화면의 비용 전후 초과수익은 CAGR이 아닙니다.'},
    {key:'benchmark', title:'벤치마크 · 비교 기준', aliases:['벤치마크'], text:'전략이 잘했는지 비교하기 위해 미리 정한 기준 수익률입니다. 초과수익은 전략 수익률에서 이 기준 수익률을 빼서 계산합니다.', note:'반드시 KOSPI 수익률이라는 뜻은 아닙니다. 해당 연구가 정한 비교 대상과 기간을 함께 확인해야 합니다.'},
    {key:'discovery', title:'Discovery · 탐색·개발 구간', aliases:['Discovery'], text:'팩터의 아이디어를 처음 평가하고 사전에 정한 연구 기준을 검사하는 과거 구간입니다.', note:'이 구간의 좋은 성과만으로 일반화할 수 없어 별도 OOS 검증을 둡니다.'},
    {key:'oos', title:'OOS / Confirmation · 별도 확인 구간', aliases:['OOS','Confirmation'], text:'팩터 개발에 사용하지 않도록 분리해 둔 과거 구간입니다. 정해진 후보를 한 번 확인하는 데 사용합니다.', note:'이미 결과를 본 구간으로 팩터를 고치고 다시 검증하면 독립성이 훼손됩니다. 표의 —는 0이 아니라 미수집·미실시 등 원인 확인이 필요한 상태입니다.'},
    {key:'embargo', title:'Embargo · 구간 사이의 빈 기간', aliases:['Embargo'], text:'개발 구간과 검증 구간 사이에 일부 기간을 비워 두는 장치입니다. 수익률 측정 기간이 겹쳐 정보가 새어 들어가는 문제를 줄입니다.', note:'모든 종류의 미래 정보 누출을 자동으로 해결하는 것은 아닙니다.'},
    {key:'pit-assumed', title:'PIT_ASSUMED · 당시 정보라고 가정', aliases:['PIT_ASSUMED','PIT 가정'], text:'과거 그 시점에 알 수 있었던 값·발표 시각이라고 가정하고 사용한다는 표시입니다. 당시 최초 발표본과 정확히 일치한다고 인증된 것은 아닙니다.', note:'나중에 수정된 값이 섞일 가능성이 남습니다. 사용자가 수용한 가정이며 레짐 보조 설명 범위를 확인해야 합니다.'},
    {key:'pit', title:'PIT · 당시 알 수 있었던 정보', aliases:['PIT'], text:'백테스트의 각 시점에 실제로 이용 가능했을 정보만 사용한다는 뜻입니다. 통계 기준일과 발표일은 다르며, 나중에 수정된 값도 구분해야 합니다.', example:'1월 통계가 2월에 발표됐다면 1월 말 판단에 사용하면 안 됩니다.'},
    {key:'verified', title:'VERIFIED_INPUT · 확인된 입력 근거', aliases:['VERIFIED_INPUT'], text:'이 연구에서는 정책금리의 공식 발표일을 확인한 입력입니다. 보수적으로 발표일이 끝난 뒤부터 알 수 있었다고 처리합니다.', note:'정확한 장중 발표 시각까지 인증했다는 뜻은 아닙니다.'},
    {key:'regime', title:'레짐 / 국면 · 시장 환경의 분류', aliases:['레짐','국면'], text:'시장을 정해진 규칙으로 나눈 상태입니다. 기본 4국면은 장기 추세의 상승·하락과 변동성의 높음·낮음을 조합합니다.', note:'어떤 환경에서 팩터가 달랐는지 설명하는 보조 도구입니다. 유리했던 국면만 골라 매매해도 된다는 검증은 아닙니다.'},
    {key:'volatility', title:'변동성', aliases:['변동성','고변동','저변동'], text:'측정하는 값이 얼마나 크게 흔들리는지 나타냅니다. 시장 국면에서는 수익률의 흔들림을 봅니다. 높으면 움직임이 크고, 낮으면 상대적으로 작다는 뜻입니다.', note:'높음·낮음은 해당 분류 규칙의 기준에 따른 상대적 상태입니다. 저변동이 손실이 없거나 안전함을 뜻하지는 않습니다.'},
    {key:'sma', title:'SMA · 단순 이동평균', aliases:['SMA'], text:'최근 일정 기간의 가격을 같은 비중으로 평균한 값입니다. 단기 흔들림을 줄여 추세를 비교할 때 씁니다.', example:'10개월 SMA는 최근 10개 월별 가격의 단순 평균입니다.'},
    {key:'high-low', title:'HIGH / LOW · 과거 기준 대비 수준', aliases:['HIGH/LOW'], text:'매크로 수준 분류에서는 자기 과거 기준에 비해 높은지 낮은지를 뜻합니다.', note:'높아지는 중·낮아지는 중이라는 변화 방향이나 호황·불황을 곧바로 뜻하지 않습니다. 금리·생산·물가의 방향 분류는 별도 규칙을 봅니다.'},
    {key:'hac', title:'95% HAC 구간 · 평균의 불확실성', aliases:['95% HAC 구간','95% 구간','HAC'], text:'관측한 평균이 얼마나 불확실한지 보여 주는 통계 구간입니다. 이 연구는 월별 값의 연속적인 의존성과 들쭉날쭉한 변동을 고려하는 HAC 방식으로 계산합니다.', note:'넓을수록 해석이 불확실합니다. 국면 간 차이나 인과관계를 증명하지 않으며, 표본 부족이면 구간을 산출하지 않습니다.'},
    {key:'joint', title:'공동 유효 개월', aliases:['공동 유효 개월'], text:'해당 국면에서 IC와 그룹 수익 차이를 함께 계산할 수 있었던 달의 수입니다.', note:'전체 관측 개월과 다를 수 있습니다. 빠진 성과 자료가 있으면 공동 유효 개월은 줄어듭니다.'},
    {key:'episodes', title:'발생 구간', aliases:['발생 구간'], text:'같은 국면이 연속해서 나타난 한 덩어리를 말합니다. 중간에 다른 국면 등이 끼고 다시 나타나면 별도 발생 구간으로 셉니다.', example:'상승 국면이 6개월 연속이면 6개월·1구간입니다.', note:'구간이 여러 개여도 서로 독립적인 실험이라는 뜻은 아닙니다.'},
    {key:'support', title:'표본 부족 / 설명 표본 요건', aliases:['표본 부족','설명 표본 충족','설명 표본 요건 충족'], text:'국면 해석에 쓸 관측량이 충분한지 보는 최소 요건입니다. 이 연구에서는 IC·수익이 함께 있는 12개월과 3발생 구간이 필요합니다.', note:'요건을 충족해도 성과가 좋거나 통계적으로 입증됐다는 뜻은 아닙니다. 팩터 승격 기준과도 별개입니다.'},
    {key:'unknown', title:'UNKNOWN · 국면 미분류', aliases:['UNKNOWN'], text:'필요한 입력이 없거나 과거 관측이 충분히 쌓이지 않아 국면을 정하지 못한 상태입니다.', note:'중립 국면이나 성과 0을 뜻하지 않습니다. 미분류도 전체 관측에서 숨기지 않고 보존합니다.'},
    {key:'pairs', title:'유효 종목 쌍', aliases:['유효 종목 쌍'], text:'그 달에 팩터 점수와 다음 달 수익률이 모두 있어 계산에 사용한 종목별 관측 수입니다.', note:'서로 다른 두 종목을 묶은 개수가 아니라, 한 종목의 점수·수익률 한 쌍을 셉니다.'},
    {key:'promote', title:'PROMOTE · 연구 승격 판정', aliases:['PROMOTE'], text:'해당 연구 규칙에서 승격 판정을 받았다는 뜻입니다.', note:'운영용 Gold에 승인·적재됐다는 뜻은 아닙니다. 운영 등록 상태는 별도 근거로 확인합니다.'},
    {key:'approved', title:'APPROVED / Gold · 승인 팩터', aliases:['APPROVED','Gold'], text:'운영 승인 목록에 등록된 팩터를 가리킵니다. 이 화면의 목록은 표시된 기준일의 스냅샷입니다.', note:'현재 DB와 자동 동기화되지 않으며, 승인이 미래 수익이나 수익성을 보장하지 않습니다.'},
    {key:'provisional', title:'PROVISIONAL · 조건부 판정', aliases:['PROVISIONAL'], text:'연구 결과에 추가 확인이 필요한 조건이나 제한이 남아 있다는 판정입니다.', note:'무조건 통과나 운영 승인을 뜻하지 않습니다. 연구 상세의 판정 근거를 확인하세요.'},
    {key:'reject', title:'REJECT · 연구 기준 탈락', aliases:['REJECT'], text:'해당 연구에서 미리 정한 기준을 통과하지 못했다는 뜻입니다.', note:'어떤 검사에서 왜 탈락했는지 확인해야 합니다. 모든 기간·시장에 경제적 효과가 전혀 없다는 증명은 아닙니다.'},
    {key:'rebalance', title:'리밸런싱 · 보유 비중 재조정', aliases:['리밸런싱','MONTHLY REBALANCE'], text:'정해진 주기마다 새 점수와 규칙에 맞춰 종목과 비중을 다시 맞추는 일입니다. 이 연구는 월 단위입니다.', note:'매매가 발생하면 비용이 듭니다. 월말 정보 마감 시점과 실제 주문·체결 시점도 구분해야 합니다.'},
    {key:'cot', title:'COT · 선물시장 참여자 포지션', aliases:['COT'], text:'선물시장에서 참여자 집단이 매수·매도 계약을 얼마나 보유하는지 집계한 보고 자료입니다.', note:'현물 가격 자체가 아닙니다. 집계 기준일과 발표일이 다르므로 당시 이용 가능 시점을 따로 봐야 합니다.'},
    {key:'diagnostic', title:'진단용 · 설명을 돕는 자료', aliases:['DIAGNOSTIC ONLY'], text:'팩터 결과를 이해하기 위한 보조 분석이라는 뜻입니다.', note:'이 분석만으로 새 매매 규칙을 검증했거나 팩터 승격 기준을 통과했다고 주장할 수 없습니다.'},
  ];
  const byKey = new Map(terms.map(term => [term.key, term]));
  const aliases = new Map(terms.flatMap(term => term.aliases.map(alias => [alias.toLowerCase(), term.key])));
  const escapeRegex = value => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const pattern = new RegExp(`(?<![A-Za-z0-9_])(?:${[...aliases.keys()].sort((a,b) => b.length-a.length).map(escapeRegex).join('|')})(?![A-Za-z0-9_])`, 'gi');
  const targets = 'th,h2,h3,h4,.metric>span,.stat>span,.feature-stats>div>span,.cost-row>span,.badge,.chart-note,.legend>span,.regime-tile small,.regime-tile em,.data-dl>dt,.research-timeline>div>span,.tag,td:first-child';
  const excluded = 'button,a,input,select,option,textarea,svg,code,pre,summary,.term-help,.raw-value';
  let sequence = 0;

  function decorate(root) {
    root.querySelectorAll(targets).forEach(element => {
      if (element.closest(excluded)) return;
      const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
      const texts = [];
      while (walker.nextNode()) {
        if (!walker.currentNode.parentElement.closest(excluded)) texts.push(walker.currentNode);
      }
      for (const node of texts) {
        const matches = [...node.textContent.matchAll(pattern)];
        if (!matches.length) continue;
        const fragment = document.createDocumentFragment();
        let cursor = 0;
        for (const match of matches) {
          const term = byKey.get(aliases.get(match[0].toLowerCase()));
          fragment.append(document.createTextNode(node.textContent.slice(cursor, match.index)));
          const wrap = document.createElement('span');
          wrap.className = 'term-help';
          wrap.append(document.createTextNode(match[0]));
          const trigger = document.createElement('button');
          const description = document.createElement('span');
          description.id = `term-description-${++sequence}`;
          description.hidden = true;
          description.textContent = [term.text, term.example, term.note].filter(Boolean).join(' ');
          trigger.type = 'button';
          trigger.className = 'term-help-trigger';
          trigger.dataset.helpKey = term.key;
          trigger.setAttribute('aria-label', `${match[0]} 뜻 보기`);
          trigger.setAttribute('aria-describedby', description.id);
          trigger.setAttribute('aria-expanded', 'false');
          trigger.textContent = '?';
          wrap.append(trigger, description);
          fragment.append(wrap);
          cursor = match.index + match[0].length;
        }
        fragment.append(document.createTextNode(node.textContent.slice(cursor)));
        node.replaceWith(fragment);
      }
    });
  }

  // A top-layer popover avoids clipping inside scrollable tables and modal details.
  // Older browsers fall back to a fixed panel in the active dialog/body.
  const popup = document.createElement('div');
  popup.className = 'term-tooltip';
  popup.id = 'term-tooltip';
  popup.setAttribute('role', 'tooltip');
  popup.setAttribute('popover', 'manual');
  popup.hidden = true;
  document.body.append(popup);
  const nativePopover = typeof popup.showPopover === 'function';
  let active = null, pinned = false, hideTimer;

  function position() {
    if (!active) return;
    const rect = active.getBoundingClientRect();
    const box = popup.getBoundingClientRect();
    const viewport = window.visualViewport;
    const leftEdge = (viewport?.offsetLeft || 0) + 12;
    const topEdge = (viewport?.offsetTop || 0) + 12;
    const width = viewport?.width || window.innerWidth;
    const height = viewport?.height || window.innerHeight;
    popup.style.left = `${Math.max(leftEdge, Math.min(rect.left, leftEdge + width - box.width - 24))}px`;
    const below = rect.bottom + 8;
    const top = below + box.height <= topEdge + height - 24 ? below : rect.top - box.height - 8;
    popup.style.top = `${Math.max(topEdge, Math.min(top, topEdge + height - box.height - 24))}px`;
  }
  function close() {
    clearTimeout(hideTimer);
    if (nativePopover && popup.matches(':popover-open')) popup.hidePopover();
    popup.hidden = true;
    active?.setAttribute('aria-expanded', 'false');
    active = null;
    pinned = false;
  }
  function show(trigger) {
    clearTimeout(hideTimer);
    if (active === trigger) return;
    close();
    active = trigger;
    const term = byKey.get(trigger.dataset.helpKey);
    popup.replaceChildren();
    for (const [tag, className, content] of [['strong','term-tooltip-title',term.title],['p','',term.text],['p','term-tooltip-example',term.example],['p','term-tooltip-note',term.note],['small','term-tooltip-hint','다시 누르거나 Esc로 닫기']]) {
      if (!content) continue;
      const child = document.createElement(tag);
      child.className = className;
      child.textContent = content;
      popup.append(child);
    }
    // Keeping the node inside the open dialog also preserves its accessibility.
    (trigger.closest('dialog') || document.body).append(popup);
    popup.hidden = false;
    if (nativePopover) popup.showPopover();
    trigger.setAttribute('aria-expanded', 'true');
    position();
  }
  function scheduleClose() {
    clearTimeout(hideTimer);
    hideTimer = setTimeout(() => {
      if (!pinned && document.activeElement !== active && !popup.matches(':hover') && !active?.matches(':hover')) close();
    }, 160);
  }
  document.addEventListener('pointerover', event => {
    if (event.pointerType === 'touch') return;
    const trigger = event.target.closest('.term-help-trigger');
    if (trigger) show(trigger);
    else if (popup.contains(event.target)) clearTimeout(hideTimer);
  });
  document.addEventListener('pointerout', event => {
    if (event.target.closest('.term-help-trigger') || popup.contains(event.target)) scheduleClose();
  });
  document.addEventListener('focusin', event => {
    const trigger = event.target.closest('.term-help-trigger');
    if (trigger) show(trigger);
    else if (!popup.contains(event.target)) close();
  });
  document.addEventListener('focusout', scheduleClose);
  document.addEventListener('click', event => {
    const trigger = event.target.closest('.term-help-trigger');
    if (trigger) {
      event.preventDefault();
      if (active === trigger && pinned) close();
      else { show(trigger); pinned = true; }
    } else if (!popup.contains(event.target)) close();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && active) {
      event.preventDefault();
      event.stopImmediatePropagation(); // First Esc closes help, not the research detail dialog.
      close();
    }
  }, true);
  document.addEventListener('scroll', event => {
    if (!popup.contains(event.target)) position();
  }, true);
  window.addEventListener('resize', position);
  window.visualViewport?.addEventListener('resize', position);
  window.addEventListener('hashchange', close);
  document.querySelector('#detail-dialog').addEventListener('close', close);

  const roots = ['#main','#detail-content','.topbar'].map(selector => document.querySelector(selector));
  const observer = new MutationObserver(() => {
    observer.disconnect();
    if (active && !active.isConnected) close();
    roots.forEach(decorate);
    observe();
  });
  function observe() {
    roots.forEach(root => observer.observe(root, {childList:true, subtree:true}));
  }
  roots.forEach(decorate);
  observe();
})();
