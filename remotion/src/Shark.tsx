import React from 'react';

// Gerak sirip, ekor, rahang menggigit, dan gelembung dihitung murni dari frame; aman dirender acak/paralel.
export const Shark: React.FC<{frame: number}> = ({frame}) => {
  const swim = Math.sin(frame / 6) * 8;
  const tilt = Math.sin(frame / 7) * 3.5;
  const tailSwing = Math.sin(frame * 0.45) * 14;
  const finWave = Math.sin(frame * 0.35) * 6;
  const chomp = (Math.sin(frame * 0.5) + 1) / 2;
  const jawDrop = 6 + chomp * 22;
  return <svg data-shark="true" width={880} height={840} viewBox="0 0 900 860" role="img" aria-label="Animated great white shark with snapping jaws" style={{overflow: 'visible', filter: 'drop-shadow(0 22px 28px #0007)'}}>
    <defs>
      <radialGradient id="cta-shark-glow">
        <stop stopColor="#38bdf8" stopOpacity=".45"/><stop offset="1" stopColor="#0284c7" stopOpacity="0"/>
      </radialGradient>
      <linearGradient id="cta-shark-body" x1="0" y1="0" x2="0" y2="1">
        <stop stopColor="#334155"/><stop offset=".55" stopColor="#64748b"/><stop offset="1" stopColor="#cbd5e1"/>
      </linearGradient>
      <linearGradient id="cta-shark-belly" x1="0" y1="0" x2="0" y2="1">
        <stop stopColor="#f8fafc"/><stop offset="1" stopColor="#e2e8f0"/>
      </linearGradient>
    </defs>
    <ellipse cx={450} cy={430} rx={400} ry={370} fill="url(#cta-shark-glow)"/>
    <ellipse cx={450} cy={765} rx={250 + Math.sin(frame / 6) * 8} ry={28} fill="#082f49" opacity={.28}/>
    <g data-shark-bubbles="true" fill="#bae6fd" opacity={.75}>
      {[0, 1, 2, 3, 4].map((i) => {
        const t = ((frame * 1.6 + i * 11) % 45) / 45;
        return <circle key={i} cx={220 + i * 115 + Math.sin(frame / 5 + i) * 14} cy={620 - t * 440} r={10 + (i % 3) * 6} opacity={(1 - t) * .8}/>;
      })}
    </g>
    <g data-shark-body="true" transform={`translate(0 ${swim}) rotate(${tilt} 450 430)`} stroke="#0f172a" strokeWidth={8} strokeLinejoin="round" strokeLinecap="round">
      <g data-shark-tail="true" transform={`translate(700 430) rotate(${tailSwing}) translate(-700 -430)`}>
        <path d="M650 410 L820 265 L765 425 L805 565 L650 455 Z" fill="url(#cta-shark-body)"/>
      </g>
      <g data-shark-fin="true" transform={`translate(455 240) rotate(${finWave}) translate(-455 -240)`}>
        <path d="M365 260 C395 135 470 105 535 95 C500 165 495 220 515 265 Z" fill="url(#cta-shark-body)"/>
      </g>
      <path d="M125 395 C195 255 375 215 555 255 C645 275 700 355 705 425 C695 495 625 555 515 570 C355 590 205 535 125 395 Z" fill="url(#cta-shark-body)"/>
      <path d="M150 415 C245 455 415 470 635 445 C585 545 435 585 285 555 C205 535 165 475 150 415 Z" fill="url(#cta-shark-belly)"/>
      <path d="M515 355 C508 385 508 415 515 440 M545 360 C538 388 538 414 545 436 M575 366 C569 390 569 412 575 432" fill="none" stroke="#1e293b" strokeWidth={6}/>
      <circle cx={265} cy={355} r={22} fill="#0f172a" stroke="none"/>
      <circle cx={258} cy={348} r={7} fill="#ffffff" stroke="none"/>
      <path d="M240 322 L292 336" stroke="#0f172a" strokeWidth={10}/>
      <g data-shark-jaw="true" transform={`translate(0 ${jawDrop})`}>
        <path d="M175 430 C235 525 375 530 435 445 Z" fill="#881337"/>
        <path d="M225 475 Q305 515 385 475 Q345 450 305 455 Q265 450 225 475 Z" fill="#fb7185" stroke="none"/>
        <path d="M195 432 L212 465 L230 435 L248 468 L266 436 L284 468 L302 436 L320 468 L338 436 L356 465 L374 435 Z" fill="#ffffff" stroke="#0f172a" strokeWidth={4}/>
        <path d="M210 485 L225 455 L242 488 L260 458 L278 490 L296 458 L314 490 L332 458 L350 485 Z" fill="#ffffff" stroke="#0f172a" strokeWidth={4}/>
      </g>
      <path d="M355 485 L445 615 L495 515 Z" fill="url(#cta-shark-body)"/>
    </g>
  </svg>;
};
