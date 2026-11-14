import React from 'react';

// Gerak ekor, telinga, kumis, dan kelopak mata dihitung murni dari frame; aman dirender acak/paralel.
export const Cat: React.FC<{frame: number}> = ({frame}) => {
  const tilt = Math.sin(frame / 8) * 3;
  const bob = Math.sin(frame / 6) * 7;
  const earTwitch = Math.sin(frame / 5) * 7;
  const swish = Math.sin(frame * 0.8) * 16;
  const whiskerTilt = Math.sin(frame / 7) * 3;
  const eyePulse = Math.sin(frame / 9) * 2;
  const cycle = frame % 96;
  const blink = cycle > 84 ? Math.sin(((cycle - 84) / 12) * Math.PI) : 0;
  const lidRy = 50 * blink;
  return <svg data-cat="true" width={880} height={840} viewBox="0 0 900 860" role="img" aria-label="Animated orange cat swishing its tail" style={{overflow: 'visible', filter: 'drop-shadow(0 22px 28px #0007)'}}>
    <defs>
      <linearGradient id="cta-cat-fur" x1="0" y1="0" x2="1" y2="1">
        <stop stopColor="#ffc76b"/><stop offset=".55" stopColor="#f2912f"/><stop offset="1" stopColor="#c2610a"/>
      </linearGradient>
      <linearGradient id="cta-cat-belly" x1="0" y1="0" x2="0" y2="1">
        <stop stopColor="#fff6e6"/><stop offset="1" stopColor="#ffdca8"/>
      </linearGradient>
      <linearGradient id="cta-cat-ear" x1="0" y1="0" x2="0" y2="1">
        <stop stopColor="#ffa7b8"/><stop offset="1" stopColor="#e8708c"/>
      </linearGradient>
      <radialGradient id="cta-cat-glow">
        <stop stopColor="#ffbe63" stopOpacity=".40"/><stop offset="1" stopColor="#ffbe63" stopOpacity="0"/>
      </radialGradient>
    </defs>
    <ellipse cx={450} cy={450} rx={395} ry={370} fill="url(#cta-cat-glow)"/>
    <ellipse cx={450} cy={786} rx={250 + Math.sin(frame / 6) * 6} ry={26} fill="#140c04" opacity={.24}/>
    <g data-cat-tail="true" transform={`rotate(${swish} 556 706)`} fill="none" strokeLinecap="round">
      <path d="M540 706 C688 716 792 660 792 540 C792 468 736 430 698 466" stroke="url(#cta-cat-fur)" strokeWidth={48}/>
      <path d="M736 442 C720 452 712 468 716 484" stroke="#ffe1b4" strokeWidth={18}/>
    </g>
    <g data-cat-body="true" stroke="#a3520b" strokeWidth={8} strokeLinejoin="round" strokeLinecap="round">
      <path d="M330 470 C296 560 296 700 326 762 L574 762 C604 700 604 560 570 470 Z" fill="url(#cta-cat-fur)"/>
      <path d="M400 508 C378 600 382 720 402 760 L498 760 C518 720 522 600 500 508 Z" fill="url(#cta-cat-belly)" stroke="none"/>
      <path d="M342 566 Q376 584 400 570" fill="none" stroke="#b95c0c" strokeWidth={10}/>
      <path d="M338 628 Q372 646 400 632" fill="none" stroke="#b95c0c" strokeWidth={10}/>
      <path d="M336 690 Q370 708 398 694" fill="none" stroke="#b95c0c" strokeWidth={10}/>
      <path d="M558 566 Q524 584 500 570" fill="none" stroke="#b95c0c" strokeWidth={10} opacity={.65}/>
      <path d="M562 628 Q528 646 500 632" fill="none" stroke="#b95c0c" strokeWidth={10} opacity={.65}/>
    </g>
    <g data-cat-paws="true" stroke="#a3520b" strokeWidth={7} strokeLinecap="round">
      <ellipse cx={382} cy={768} rx={64} ry={36} fill="url(#cta-cat-belly)"/>
      <ellipse cx={518} cy={768} rx={64} ry={36} fill="url(#cta-cat-belly)"/>
      <path d="M356 760 V784 M382 756 V788 M408 760 V784 M492 760 V784 M518 756 V788 M544 760 V784" fill="none"/>
    </g>
    <g data-cat-head="true" transform={`translate(0 ${bob}) rotate(${tilt} 450 300)`} stroke="#a3520b" strokeWidth={8} strokeLinejoin="round" strokeLinecap="round">
      <g data-cat-ears="true" transform={`rotate(${earTwitch} 450 246)`}>
        <path d="M292 252 L328 104 L414 214 Z" fill="url(#cta-cat-fur)"/>
        <path d="M316 238 L340 148 L392 216 Z" fill="url(#cta-cat-ear)" stroke="none"/>
        <path d="M608 252 L572 104 L486 214 Z" fill="url(#cta-cat-fur)"/>
        <path d="M584 238 L560 148 L508 216 Z" fill="url(#cta-cat-ear)" stroke="none"/>
      </g>
      <path d="M286 300 C286 186 356 132 450 132 C544 132 614 186 614 300 C614 402 556 492 450 492 C344 492 286 402 286 300 Z" fill="url(#cta-cat-fur)"/>
      <path d="M420 172 Q450 204 480 172" fill="none" stroke="#b95c0c" strokeWidth={11}/>
      <path d="M392 202 Q450 244 508 202" fill="none" stroke="#b95c0c" strokeWidth={11}/>
      <path d="M362 238 Q450 288 538 238" fill="none" stroke="#b95c0c" strokeWidth={9} opacity={.7}/>
      <g data-cat-eyes="true" transform={`translate(0 ${eyePulse})`} stroke="none">
        <ellipse cx={386} cy={312} rx={46} ry={52} fill="#f8ffe9"/>
        <ellipse cx={514} cy={312} rx={46} ry={52} fill="#f8ffe9"/>
        <ellipse cx={386} cy={314} rx={31} ry={42} fill="#57cb74"/>
        <ellipse cx={514} cy={314} rx={31} ry={42} fill="#57cb74"/>
        <ellipse cx={386} cy={316} rx={13} ry={31} fill="#1d1206"/>
        <ellipse cx={514} cy={316} rx={13} ry={31} fill="#1d1206"/>
        <circle cx={374} cy={296} r={11} fill="#fff"/>
        <circle cx={502} cy={296} r={11} fill="#fff"/>
        <ellipse cx={386} cy={312 - 50 + lidRy} rx={48} ry={lidRy} fill="url(#cta-cat-fur)"/>
        <ellipse cx={514} cy={312 - 50 + lidRy} rx={48} ry={lidRy} fill="url(#cta-cat-fur)"/>
      </g>
      <ellipse cx={450} cy={410} rx={80} ry={54} fill="url(#cta-cat-belly)" stroke="none"/>
      <path d="M432 388 H468 L450 406 Z" fill="#ff7f9c" stroke="#c2556f" strokeWidth={5}/>
      <path d="M450 406 V418" fill="none" stroke="#a3520b" strokeWidth={6}/>
      <path d="M450 418 Q432 432 416 416 M450 418 Q468 432 484 416" fill="none" stroke="#a3520b" strokeWidth={6}/>
      <g data-cat-whiskers="true" transform={`rotate(${whiskerTilt} 450 410)`} fill="none" stroke="#fff6e6" strokeWidth={6} strokeLinecap="round">
        <path d="M304 384 Q246 368 204 352"/>
        <path d="M300 406 Q240 404 196 408"/>
        <path d="M306 428 Q248 442 208 462"/>
        <path d="M596 384 Q654 368 696 352"/>
        <path d="M600 406 Q660 404 704 408"/>
        <path d="M594 428 Q652 442 692 462"/>
      </g>
    </g>
  </svg>;
};
