const $ = selector => document.querySelector(selector);
const escapeHTML = value => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
let data, selected = 'confirmation', filter = 'all';
function sourceLink(id) {
  const source = data.sources[id];
  const url = `https://github.com/2stshine/factor-research/blob/${data.source_commit}/${source.path}${source.line ? '#L'+source.line : ''}`;
  return `<a class="source-link" href="${escapeHTML(url)}" target="_blank" rel="noopener noreferrer"><span class="external">↗</span>${escapeHTML(source.label)}<small>${escapeHTML(source.path.split('/').slice(-2).join('/'))}</small></a>`;
}
function renderGraph() {
  $('#nodes').innerHTML = data.nodes.map((node, i) => `<button class="node" data-id="${node.id}" data-type="${node.type}" style="left:${node.x}px;top:${node.y}px" aria-pressed="false" aria-controls="detail" aria-label="${escapeHTML(data.types[node.type].label + ': ' + node.title.replaceAll('\n',' ') + ' 상세 보기')}"><span class="node-kicker"><span>${data.types[node.type].symbol} ${data.types[node.type].label}</span><span>${String(i+1).padStart(2,'0')}</span></span><span class="node-title">${escapeHTML(node.title).replaceAll('\n','<br>')}</span>${node.stat ? `<span class="node-stat">${escapeHTML(node.stat)}</span>` : ''}<span class="node-note">${escapeHTML(node.note)}</span><span class="node-arrow" aria-hidden="true">↗</span></button>`).join('');
  $('#connections').innerHTML = `<defs><marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6" fill="none" stroke="#adbec7" stroke-width="1"/></marker></defs>` + data.edges.map(edge => {
    const width = edge.label.length * 9 + 12;
    return `<g class="edge ${edge.future ? 'future' : ''}" data-from="${edge.from}" data-to="${edge.to}"><path d="${edge.path}" marker-end="url(#arrow)"/><rect x="${edge.lx-width/2}" y="${edge.ly-9}" width="${width}" height="18"/><text x="${edge.lx}" y="${edge.ly+3}" text-anchor="middle">${escapeHTML(edge.label)}</text></g>`;
  }).join('');
}
function highlight() {
  document.querySelectorAll('.node').forEach(button => {
    button.classList.toggle('selected', button.dataset.id === selected);
    button.setAttribute('aria-pressed', String(button.dataset.id === selected));
    const active = filter === 'all' || (filter === 'evidence' ? button.dataset.type === 'evidence' : ['limit','question'].includes(button.dataset.type));
    button.classList.toggle('filtered', !active);
  });
  document.querySelectorAll('.edge').forEach(edge => {
    const connected = edge.dataset.from === selected || edge.dataset.to === selected;
    edge.classList.toggle('is-connected', connected);
    edge.classList.toggle('is-muted', filter !== 'all' && !connected);
  });
  document.querySelectorAll('[data-filter]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.filter === filter)));
}
function selectNode(id, {focus = false, reveal = false, announce = true} = {}) {
  const node = data.nodes.find(item => item.id === id);
  if (!node) return;
  selected = id;
  const type = data.types[node.type];
  const related = data.edges.filter(edge => edge.from === id || edge.to === id);
  $('#node-position').textContent = `${String(data.nodes.indexOf(node)+1).padStart(2,'0')} / ${String(data.nodes.length).padStart(2,'0')}`;
  $('#detail').innerHTML = `<span class="detail-kind ${node.type}">${type.symbol} ${type.label}</span><h3 tabindex="-1" id="detail-title">${escapeHTML(node.title).replaceAll('\n',' ')}</h3><p class="detail-summary">${escapeHTML(node.summary)}</p>${node.formula ? `<code class="formula">${escapeHTML(node.formula)}</code>` : ''}${node.metrics ? `<div class="detail-metrics">${node.metrics.map(metric => `<div class="detail-metric"><span>${escapeHTML(metric.label)}</span><strong>${escapeHTML(metric.value)}</strong><small>${escapeHTML(metric.note)}</small></div>`).join('')}</div>` : ''}${node.sections.map(section => `<section class="detail-section"><h4>${escapeHTML(section.title)}</h4><p>${escapeHTML(section.text)}</p></section>`).join('')}${node.callout ? `<div class="detail-callout">${escapeHTML(node.callout)}</div>` : ''}<section class="detail-section"><h4>연결된 근거와 질문</h4>${related.map(edge => {
    const other = data.nodes.find(item => item.id === (edge.from === id ? edge.to : edge.from));
    return `<button class="related-link" data-select="${other.id}"><span>${escapeHTML(other.title.replaceAll('\n',' '))}<small> · ${escapeHTML(edge.label)}</small></span><span aria-hidden="true">→</span></button>`;
  }).join('')}</section><section class="detail-section"><h4>코드와 기록에서 확인하기</h4>${node.sources.map(sourceLink).join('')}<p class="source-version">GitHub 원문 · ${data.source_commit.slice(0,7)} 기준<br>공개 완료 기록의 수동 스냅샷 · 실행 기능 없음</p></section>`;
  highlight();
  history.replaceState(null, '', `#${id}`);
  if (announce) $('#announcement').textContent = `${type.label}, ${node.title.replaceAll('\n',' ')}. 상세 패널이 갱신되었습니다.`;
  if (focus) document.querySelector(`[data-id="${id}"]`).focus({preventScroll:true});
  if (reveal && matchMedia('(max-width:900px)').matches) $('#detail-title').scrollIntoView({behavior:'smooth',block:'start'});
}
function moveSelection(event) {
  const direction = ['ArrowRight','ArrowDown'].includes(event.key) ? 1 : ['ArrowLeft','ArrowUp'].includes(event.key) ? -1 : 0;
  if (!direction && !['Home','End'].includes(event.key)) return;
  event.preventDefault();
  const index = data.nodes.findIndex(node => node.id === event.currentTarget.dataset.id);
  const next = event.key === 'Home' ? 0 : event.key === 'End' ? data.nodes.length-1 : (index + direction + data.nodes.length) % data.nodes.length;
  selectNode(data.nodes[next].id, {focus:true});
  document.querySelector(`[data-id="${selected}"]`).scrollIntoView({behavior:'smooth',block:'nearest',inline:'nearest'});
}
function fitGraph() {
  const viewport = $('#graph-viewport');
  const fit = matchMedia('(min-width:901px)').matches;
  // Preserve readable native-size cards on phones; fit all four lanes on desktop.
  $('#graph').style.zoom = fit ? Math.min(1, viewport.clientWidth / 1046) : 1;
  viewport.style.overflowX = fit ? 'hidden' : 'auto';
}
async function boot() {
  const response = await fetch('./case-0230.json');
  if (!response.ok) throw new Error('snapshot unavailable');
  data = await response.json();
  renderGraph();
  document.querySelectorAll('.node').forEach(button => {
    button.addEventListener('click', () => selectNode(button.dataset.id,{reveal:true}));
    button.addEventListener('keydown', moveSelection);
  });
  $('#detail').addEventListener('click', event => {
    const button = event.target.closest('[data-select]');
    if (button) {selectNode(button.dataset.select, {reveal:true}); $('#detail-title').focus({preventScroll:true});}
  });
  document.querySelectorAll('[data-filter]').forEach(button => button.addEventListener('click', () => {filter = button.dataset.filter; highlight(); $('#announcement').textContent = `${button.textContent} 강조. 모든 노드는 선택할 수 있습니다.`;}));
  $('#reset-map').addEventListener('click', () => {filter='all';selectNode('confirmation');$('#graph-viewport').scrollTo({left:0,top:0,behavior:'smooth'});});
  $('#back-to-map').addEventListener('click', () => {const button=document.querySelector(`[data-id="${selected}"]`);button.focus({preventScroll:true});button.scrollIntoView({behavior:'smooth',block:'center',inline:'center'});});
  const hash = location.hash.slice(1);
  selectNode(data.nodes.some(node=>node.id===hash) ? hash : selected,{announce:false});
  new ResizeObserver(fitGraph).observe($('#graph-viewport'));
  fitGraph();
}
boot().catch(() => {$('#detail').innerHTML='<h3>사례 데이터를 불러오지 못했습니다.</h3><p>로컬 미리보기 서버에서 다시 열어 주세요.</p><a href="./case-0230.json">사례 JSON 확인</a>';$('#announcement').textContent='사례 데이터 로드 실패';});
