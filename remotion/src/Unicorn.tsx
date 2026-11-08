import React from 'react';

// Semua gerak berasal dari frame stage; aman dirender acak/paralel tanpa timer atau random.
export const Unicorn: React.FC<{frame: number}> = ({frame}) => {
  const nod = Math.sin(frame / 9) * 3;
  const bob = Math.sin(frame / 7) * 9;
  const maneColors = ['#b398ff', '#66d9ff', '#65e6ce', '#ffe58d', '#ff9ccf'];
  return <svg data-unicorn="true" width={880} height={840} viewBox="0 0 900 860" role="img" aria-label="Animated unicorn" style={{overflow: 'visible', filter: 'drop-shadow(0 22px 28px #0007)'}}>
    <defs>
      <linearGradient id="cta-unicorn-coat" x1="0" y1="0" x2="1" y2="1">
        <stop stopColor="#fffefc"/><stop offset=".65" stopColor="#f4efff"/><stop offset="1" stopColor="#cfc3f4"/>
      </linearGradient>
      <linearGradient id="cta-unicorn-horn" x1="0" y1="0" x2="1" y2="1">
        <stop stopColor="#fff9c1"/><stop offset=".5" stopColor="#ffd15c"/><stop offset="1" stopColor="#ee9a39"/>
      </linearGradient>
      <radialGradient id="cta-unicorn-aura">
        <stop stopColor="#dea2ff" stopOpacity=".48"/><stop offset="1" stopColor="#dea2ff" stopOpacity="0"/>
      </radialGradient>
    </defs>
    <ellipse cx={450} cy={440} rx={410} ry={390} fill="url(#cta-unicorn-aura)"/>
    <ellipse cx={455} cy={748} rx={260 + Math.sin(frame / 7) * 8} ry={28} fill="#100826" opacity={.22}/>
    <g data-unicorn-head="true" transform={`translate(0 ${bob}) rotate(${nod} 460 650)`} stroke="#68508e" strokeWidth={8} strokeLinejoin="round" strokeLinecap="round">
      <g data-unicorn-mane="true">
        {maneColors.map((color, i) => {
          const sway = Math.sin(frame / 8 + i * .7) * 12;
          return <path key={color} d={`M${455 + i * 12} ${265 + i * 14} C${220 + i * 17} 170 ${242 + sway} 424 ${188 + i * 25} 515 C${115 + i * 26 + sway} 632 ${190 + i * 24} 742 ${310 + i * 38} 727 C${255 + i * 23} 623 ${380 + sway} 567 ${362 + i * 23} 472 Z`} fill={color}/>;
        })}
      </g>
      <path d="M414 437 C373 524 388 603 323 707 Q435 771 613 716 C560 633 590 563 600 493 Z" fill="url(#cta-unicorn-coat)"/>
      <path data-unicorn-horn="true" d="M520 287 L548 88 Q556 77 561 92 L594 291 Z" fill="url(#cta-unicorn-horn)"/>
      <path d="M535 219 L581 239 M539 183 L573 201 M543 147 L566 160" fill="none" stroke="#c4863e" strokeWidth={6}/>
      <path d="M421 326 Q383 270 405 200 Q470 220 491 296" fill="url(#cta-unicorn-coat)"/>
      <path d="M427 283 Q415 254 421 235 L459 291" fill="#f4b5d8" stroke="none"/>
      <path d="M424 314 C474 270 555 267 597 315 Q624 345 619 392 L714 444 Q757 464 743 503 Q731 549 669 545 L601 526 Q553 577 494 537 C438 516 402 447 415 384 Z" fill="url(#cta-unicorn-coat)"/>
      <path d="M682 439 Q753 455 743 503 Q731 549 669 545 L646 522 Q679 500 682 439 Z" fill="#efc5e5" stroke="none"/>
      <ellipse cx={705} cy={484} rx={10} ry={15} fill="#68508e" stroke="none"/>
      <path d="M661 517 Q688 529 709 518" fill="none" strokeWidth={6}/>
      <ellipse cx={576} cy={389} rx={22} ry={29} fill="#332747" stroke="none"/>
      <circle cx={583} cy={379} r={8} fill="white" stroke="none"/>
      <path d="M558 369 L548 360 M571 361 L568 350" fill="none" strokeWidth={6}/>
      <ellipse cx={590} cy={446} rx={27} ry={16} fill="#f59fc9" opacity={.65} stroke="none"/>
      <path d={`M413 325 C426 262 501 245 549 282 Q590 310 594 346 C552 323 534 319 507 338 Q482 ${361 + Math.sin(frame / 8) * 9} 458 344 L466 310 Q437 340 413 325 Z`} fill="#ff9ccf"/>
      <path d="M430 310 Q463 274 511 285" fill="none" stroke="#ffd2ec" strokeWidth={10}/>
      <path d="M409 626 Q440 657 482 659" fill="none" stroke="#fff" strokeWidth={12} opacity={.7}/>
    </g>
    <g data-unicorn-sparkles="true" transform={`rotate(${Math.sin(frame / 13) * 3} 450 420)`}>
      {Array.from({length: 10}, (_, i) => {
        const angle = i * Math.PI * 2 / 10;
        const twinkle = .45 + .55 * (Math.sin(frame / 4 + i * 1.8) + 1) / 2;
        const x = 450 + Math.cos(angle) * (310 + i % 3 * 20);
        const y = 420 + Math.sin(angle) * 316;
        return <g key={i} transform={`translate(${x} ${y + Math.sin(frame / 6 + i) * 12}) scale(${twinkle})`} opacity={twinkle}>
          <path d="M0 -25 Q5 -5 22 0 Q5 5 0 25 Q-5 5 -22 0 Q-5 -5 0 -25 Z" fill={i % 2 ? '#fff2a8' : '#c2edff'} stroke="#fff" strokeWidth={3}/>
          <circle cx={30} cy={-24} r={4} fill="#fff"/>
        </g>;
      })}
    </g>
  </svg>;
};
