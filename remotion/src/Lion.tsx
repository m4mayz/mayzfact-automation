import React from 'react';

// Gerak rahang, kumis, telinga, dan harimau/surai dihitung murni dari frame; aman dirender acak/paralel.
export const Lion: React.FC<{frame: number}> = ({frame}) => {
  const nod = Math.sin(frame / 7) * 3.2;
  const bob = Math.sin(frame / 6) * 7;
  const roar = (Math.sin(frame * 0.45) + 1) / 2;
  const jawOpen = 14 + roar * 26;
  const manePulse = 1 + Math.sin(frame / 5) * 0.03;
  const whiskerTilt = Math.sin(frame / 4) * 5;
  return <svg data-lion="true" width={880} height={840} viewBox="0 0 900 860" role="img" aria-label="Animated roaring lion with golden mane" style={{overflow: 'visible', filter: 'drop-shadow(0 22px 28px #0007)'}}>
    <defs>
      <radialGradient id="cta-lion-glow">
        <stop stopColor="#ffb703" stopOpacity=".45"/><stop offset="1" stopColor="#ffb703" stopOpacity="0"/>
      </radialGradient>
      <linearGradient id="cta-lion-mane" x1="0" y1="0" x2="1" y2="1">
        <stop stopColor="#b5481a"/><stop offset=".55" stopColor="#7f2b0a"/><stop offset="1" stopColor="#4a1604"/>
      </linearGradient>
      <linearGradient id="cta-lion-fur" x1="0" y1="0" x2="0" y2="1">
        <stop stopColor="#ffe18c"/><stop offset=".55" stopColor="#f5b242"/><stop offset="1" stopColor="#cc7b19"/>
      </linearGradient>
      <linearGradient id="cta-lion-muzzle" x1="0" y1="0" x2="0" y2="1">
        <stop stopColor="#fff8df"/><stop offset="1" stopColor="#f2d08b"/>
      </linearGradient>
    </defs>
    <ellipse cx={450} cy={440} rx={400} ry={380} fill="url(#cta-lion-glow)"/>
    <ellipse cx={450} cy={765} rx={255 + Math.sin(frame / 6) * 8} ry={28} fill="#140b03" opacity={.26}/>
    <g data-lion-roar-waves="true" opacity={0.35 + roar * 0.55} fill="none" stroke="#ffd166" strokeLinecap="round">
      {[0, 1].map((i) => {
        const s = 1 + ((frame + i * 10) % 20) / 22;
        return <path key={i} d={`M${255 - i * 35} ${455 - i * 15} Q${195 - i * 40} 505 ${255 - i * 35} ${555 + i * 15} M${645 + i * 35} ${455 - i * 15} Q${705 + i * 40} 505 ${645 + i * 35} ${555 + i * 15}`} strokeWidth={10 - i * 3} transform={`scale(${s}) translate(${(1 - s) * 450} ${(1 - s) * 505})`}/>;
      })}
    </g>
    <g data-lion-head="true" transform={`translate(0 ${bob}) rotate(${nod} 450 430)`} stroke="#4a1c06" strokeWidth={8} strokeLinejoin="round" strokeLinecap="round">
      <g data-lion-mane="true" transform={`translate(450 415) scale(${manePulse}) translate(-450 -415)`}>
        <path d="M450 95 L515 130 L595 115 L635 175 L710 195 L715 270 L775 330 L745 405 L780 480 L725 540 L730 615 L655 645 L620 715 L540 705 L450 750 L360 705 L280 715 L245 645 L170 615 L175 540 L120 480 L155 405 L125 330 L185 270 L190 195 L265 175 L305 115 L385 130 Z" fill="url(#cta-lion-mane)"/>
      </g>
      <g data-lion-ears="true">
        <circle cx={295} cy={220} r={54} fill="url(#cta-lion-fur)"/>
        <circle cx={295} cy={220} r={28} fill="#d67c2c" stroke="none"/>
        <circle cx={605} cy={220} r={54} fill="url(#cta-lion-fur)"/>
        <circle cx={605} cy={220} r={28} fill="#d67c2c" stroke="none"/>
      </g>
      <path d="M275 335 C265 220 345 175 450 175 C555 175 635 220 625 335 C640 445 585 565 450 565 C315 565 260 445 275 335 Z" fill="url(#cta-lion-fur)"/>
      <path d="M340 275 L410 305 M560 275 L490 305" stroke="#4a1c06" strokeWidth={11}/>
      <ellipse cx={375} cy={335} rx={26} ry={30} fill="#261205" stroke="none"/>
      <ellipse cx={525} cy={335} rx={26} ry={30} fill="#261205" stroke="none"/>
      <circle cx={367} cy={325} r={9} fill="white" stroke="none"/>
      <circle cx={517} cy={325} r={9} fill="white" stroke="none"/>
      <g data-lion-jaw="true" transform={`translate(0 ${jawOpen})`}>
        <path d="M355 465 C355 565 545 565 545 465 Z" fill="#6e1423"/>
        <path d="M405 510 Q450 548 495 510 Q475 480 450 485 Q425 480 405 510 Z" fill="#ff758f" stroke="none"/>
        <path d="M380 475 L392 508 L405 478 Z M520 475 L508 508 L495 478 Z" fill="#fffdf7" stroke="#4a1c06" strokeWidth={5}/>
      </g>
      <ellipse cx={410} cy={435} rx={68} ry={48} fill="url(#cta-lion-muzzle)"/>
      <ellipse cx={490} cy={435} rx={68} ry={48} fill="url(#cta-lion-muzzle)"/>
      <path d="M412 382 L488 382 L450 425 Z" fill="#8c2f1b"/>
      <g data-lion-whiskers="true" transform={`rotate(${whiskerTilt} 450 435)`} stroke="#4a1c06" strokeWidth={6}>
        <path d="M345 425 L260 410 M345 445 L255 450 M555 425 L640 410 M555 445 L645 450"/>
      </g>
    </g>
  </svg>;
};
