import React from 'react';

// Gerak kepala, telinga, dan ekor dihitung murni dari frame; aman dirender acak/paralel.
export const Puppy: React.FC<{frame: number}> = ({frame}) => {
  const tilt = Math.sin(frame / 8) * 3.5;
  const bob = Math.sin(frame / 6) * 8;
  const earFlap = Math.sin(frame / 5) * 6;
  const wag = Math.sin(frame * 0.7) * 18;
  return <svg data-puppy="true" width={880} height={840} viewBox="0 0 900 860" role="img" aria-label="Animated happy golden puppy wagging its tail" style={{overflow: 'visible', filter: 'drop-shadow(0 22px 28px #0007)'}}>
    <defs>
      <linearGradient id="cta-puppy-fur" x1="0" y1="0" x2="1" y2="1">
        <stop stopColor="#ffe39f"/><stop offset=".55" stopColor="#f2b45c"/><stop offset="1" stopColor="#c77d28"/>
      </linearGradient>
      <linearGradient id="cta-puppy-ear" x1="0" y1="0" x2="0" y2="1">
        <stop stopColor="#d98b32"/><stop offset="1" stopColor="#995614"/>
      </linearGradient>
      <linearGradient id="cta-puppy-belly" x1="0" y1="0" x2="0" y2="1">
        <stop stopColor="#fff7df"/><stop offset="1" stopColor="#f5d393"/>
      </linearGradient>
      <radialGradient id="cta-puppy-glow">
        <stop stopColor="#ffd778" stopOpacity=".42"/><stop offset="1" stopColor="#ffd778" stopOpacity="0"/>
      </radialGradient>
    </defs>
    <ellipse cx={450} cy={450} rx={395} ry={370} fill="url(#cta-puppy-glow)"/>
    <ellipse cx={450} cy={762} rx={255 + Math.sin(frame / 6) * 7} ry={28} fill="#140c04" opacity={.24}/>
    <g data-puppy-tail="true" transform={`rotate(${wag} 615 655)`} stroke="#78420e" strokeWidth={8} strokeLinecap="round" strokeLinejoin="round">
      <path d="M590 660 C685 615 745 535 720 455 C695 495 655 545 575 615 Z" fill="url(#cta-puppy-fur)"/>
      <path d="M675 520 Q712 490 715 462" fill="none" stroke="#fff3cf" strokeWidth={7}/>
    </g>
    <g stroke="#78420e" strokeWidth={8} strokeLinejoin="round" strokeLinecap="round">
      <path d="M315 485 C275 565 280 685 315 740 L585 740 C620 685 625 565 585 485 Z" fill="url(#cta-puppy-fur)"/>
      <path d="M365 525 C345 600 350 695 380 738 L520 738 C550 695 555 600 535 525 Z" fill="url(#cta-puppy-belly)" stroke="none"/>
      <g data-puppy-collar="true">
        <path d="M322 495 Q450 545 578 495 L566 534 Q450 582 334 534 Z" fill="#e63946"/>
        <circle cx={450} cy={558} r={24} fill="#ffd166" stroke="#8a5a00" strokeWidth={6}/>
        <path d="M438 558 H462" stroke="#8a5a00" strokeWidth={5}/>
      </g>
      <g data-puppy-paws="true">
        <ellipse cx={355} cy={742} rx={58} ry={34} fill="url(#cta-puppy-belly)"/>
        <ellipse cx={545} cy={742} rx={58} ry={34} fill="url(#cta-puppy-belly)"/>
        <path d="M335 735 V758 M355 732 V760 M375 735 V758 M525 735 V758 M545 732 V760 M565 735 V758" stroke="#78420e" strokeWidth={5}/>
      </g>
    </g>
    <g data-puppy-head="true" transform={`translate(0 ${bob}) rotate(${tilt} 450 355)`} stroke="#78420e" strokeWidth={8} strokeLinejoin="round" strokeLinecap="round">
      <g data-puppy-ears="true" transform={`rotate(${earFlap} 450 265)`}>
        <path d="M295 235 C215 245 182 365 215 445 C242 485 292 455 310 385 Z" fill="url(#cta-puppy-ear)"/>
        <path d="M605 235 C685 245 718 365 685 445 C658 485 608 455 590 385 Z" fill="url(#cta-puppy-ear)"/>
      </g>
      <path d="M285 295 C275 185 355 135 450 135 C545 135 625 185 615 295 C635 385 575 495 450 495 C325 495 265 385 285 295 Z" fill="url(#cta-puppy-fur)"/>
      <path d="M420 138 Q445 102 465 132 Q482 110 495 140" fill="none" stroke="#78420e" strokeWidth={8}/>
      <ellipse cx={385} cy={275} rx={36} ry={40} fill="url(#cta-puppy-belly)" stroke="none"/>
      <ellipse cx={515} cy={275} rx={36} ry={40} fill="url(#cta-puppy-belly)" stroke="none"/>
      <ellipse cx={375} cy={312} rx={24} ry={28} fill="#261709" stroke="none"/>
      <ellipse cx={525} cy={312} rx={24} ry={28} fill="#261709" stroke="none"/>
      <circle cx={367} cy={302} r={9} fill="white" stroke="none"/>
      <circle cx={517} cy={302} r={9} fill="white" stroke="none"/>
      <ellipse cx={335} cy={365} rx={26} ry={15} fill="#ff8fa3" opacity={.55} stroke="none"/>
      <ellipse cx={565} cy={365} rx={26} ry={15} fill="#ff8fa3" opacity={.55} stroke="none"/>
      <ellipse cx={450} cy={392} rx={92} ry={66} fill="url(#cta-puppy-belly)"/>
      <path data-puppy-tongue="true" d={`M424 426 Q450 ${488 + Math.sin(frame / 4) * 8} 476 426 Z`} fill="#ff6b8b" stroke="#9e2a47" strokeWidth={6}/>
      <path d="M402 415 Q426 442 450 418 Q474 442 498 415" fill="none" stroke="#78420e" strokeWidth={8}/>
      <ellipse cx={450} cy={368} rx={34} ry={24} fill="#2b190b" stroke="none"/>
      <ellipse cx={440} cy={360} rx={11} ry={6} fill="#fff" opacity={.65} stroke="none"/>
    </g>
  </svg>;
};
