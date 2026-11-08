import React from 'react';

// Aliran, tetesan dan riak cuma bergantung pada frame; render acak/paralel tetap identik.
export const Honey: React.FC<{frame: number}> = ({frame}) => {
  const flow = Math.sin(frame / 7) * 7;
  const ripple = (frame % 24) / 24;
  return <svg data-honey="true" width={880} height={840} viewBox="0 0 900 860" role="img" aria-label="Animated honey dripping from a dipper into a glass jar" style={{overflow: 'visible', filter: 'drop-shadow(0 22px 28px #0007)'}}>
    <defs>
      <linearGradient id="cta-honey-gold" x1="0" y1="0" x2="1" y2="1">
        <stop stopColor="#fff099"/><stop offset=".3" stopColor="#ffc52f"/><stop offset="1" stopColor="#d9780a"/>
      </linearGradient>
      <linearGradient id="cta-honey-wood" x1="0" y1="0" x2="0" y2="1">
        <stop stopColor="#f9d292"/><stop offset=".5" stopColor="#d89b53"/><stop offset="1" stopColor="#9a5828"/>
      </linearGradient>
      <linearGradient id="cta-honey-glass" x1="0" y1="0" x2="1" y2="0">
        <stop stopColor="#dcf7ff" stopOpacity=".42"/><stop offset=".35" stopColor="#e9fbff" stopOpacity=".08"/><stop offset="1" stopColor="#92d4ed" stopOpacity=".3"/>
      </linearGradient>
    </defs>
    <ellipse cx={450} cy={780} rx={245} ry={30} fill="#100d06" opacity={.24}/>
    <g data-honey-jar="true" strokeLinejoin="round">
      <path d="M330 430 L330 476 Q270 499 270 548 L270 710 Q270 766 326 766 L574 766 Q630 766 630 710 L630 548 Q630 499 570 476 L570 430 Z" fill="url(#cta-honey-glass)" stroke="#b9e5f4" strokeWidth={9}/>
      <g data-honey-fill="true">
        <path d="M286 570 Q450 597 614 570 L614 708 Q614 749 573 749 L327 749 Q286 749 286 708 Z" fill="url(#cta-honey-gold)"/>
        <ellipse cx={450} cy={570} rx={164} ry={29} fill="#ffcf48" stroke="#ffe88c" strokeWidth={5}/>
        <ellipse cx={450} cy={570} rx={14 + ripple * 90} ry={3 + ripple * 14} fill="none" stroke="#fff0a1" strokeWidth={5} opacity={1 - ripple}/>
        <circle cx={340} cy={650} r={10} fill="#ffe592" opacity={.55}/>
        <circle cx={553} cy={702} r={7} fill="#ffe592" opacity={.45}/>
      </g>
    </g>
    <g data-honey-dipper="true" transform="rotate(-28 430 260)" stroke="#8d5126" strokeWidth={5}>
      <rect x={472} y={243} width={310} height={34} rx={17} fill="url(#cta-honey-wood)"/>
      <path d="M535 253 L749 253" stroke="#ffe0a9" strokeWidth={6} strokeLinecap="round"/>
      <rect x={334} y={205} width={180} height={110} rx={48} fill="url(#cta-honey-wood)"/>
      <g data-honey-grooves="true">
        {[351, 382, 413, 444, 475, 501].map((x) => <ellipse key={x} cx={x} cy={260} rx={15} ry={51} fill="url(#cta-honey-gold)" stroke="#a9661d" strokeWidth={6}/>)}
      </g>
      <path d="M345 275 Q421 298 501 273 L500 290 Q421 326 345 294 Z" fill="url(#cta-honey-gold)" stroke="none"/>
    </g>
    <path data-honey-stream="true" d={`M441 306 C${435 + flow} 382 ${455 - flow} 438 440 493 Q${431 + flow} 534 441 570 Q450 582 460 570 C${448 + flow} 515 ${471 - flow} 475 462 420 Q${451 + flow} 355 461 306 Z`} fill="url(#cta-honey-gold)" stroke="#ffe28a" strokeWidth={3}/>
    <g data-honey-drops="true" transform={`translate(${Math.sin(frame / 11) * 3} 0)`} fill="url(#cta-honey-gold)" stroke="#ffe28a" strokeWidth={3}>
      {[0, 1, 2].map((i) => {
        const t = ((frame + i * 13) % 40) / 40;
        return <path key={i} transform={`translate(${486 + i * 19} ${335 + t * t * 215}) scale(${.65 + t * .35})`} d="M0 -22 C-2 -12 -13 -3 -13 7 A13 13 0 0 0 13 7 C13 -3 2 -12 0 -22 Z" opacity={Math.sin(t * Math.PI)}/>;
      })}
    </g>
    <ellipse cx={450} cy={430} rx={120} ry={28} fill="none" stroke="#d9f5ff" strokeWidth={10}/>
    <path d="M330 452 Q450 480 570 452 M301 534 L301 701 Q301 729 326 729" fill="none" stroke="#f1fcff" strokeWidth={12} strokeLinecap="round" opacity={.75}/>
    <path d="M595 549 L595 692" fill="none" stroke="#e6faff" strokeWidth={7} strokeLinecap="round" opacity={.5}/>
  </svg>;
};
