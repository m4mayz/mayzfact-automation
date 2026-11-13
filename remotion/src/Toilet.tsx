import React from 'react';

// Kloset jongkok dari sudut depan: cekungan keramik dengan hood di belakang, air bergoyang dan
// percikan flush. Semua gerak dihitung dari frame, jadi render paralel tetap identik.
export const Toilet: React.FC<{frame: number}> = ({frame}) => {
  const ripple = (frame % 20) / 20;
  const wobble = Math.sin(frame / 6) * 5;
  return <svg data-toilet="true" width={880} height={840} viewBox="0 0 900 860" role="img" aria-label="Animated squat toilet with flushing water in the bowl" style={{overflow: 'visible', filter: 'drop-shadow(0 22px 28px #0007)'}}>
    <defs>
      <linearGradient id="cta-toilet-ceramic" x1="0" y1="0" x2=".6" y2="1">
        <stop stopColor="#ffffff"/><stop offset=".55" stopColor="#eaf1f5"/><stop offset="1" stopColor="#cddadf"/>
      </linearGradient>
      <linearGradient id="cta-toilet-water" x1="0" y1="0" x2="0" y2="1">
        <stop stopColor="#a7e2fb"/><stop offset="1" stopColor="#2f86c4"/>
      </linearGradient>
    </defs>
    <ellipse cx={450} cy={762} rx={330} ry={34} fill="#100d06" opacity={.22}/>
    <g data-toilet-bowl="true" strokeLinejoin="round">
      <path d="M600 700 Q470 742 300 700 L196 704 Q168 708 170 736 L186 762 Q450 800 714 762 L730 736 Q732 708 704 704 Z" fill="#d8e3e8" stroke="#b9cbd5" strokeWidth={6}/>
      <path d="M160 498 L740 498 Q772 498 770 532 L752 706 Q450 764 148 706 L130 532 Q128 498 160 498 Z" fill="url(#cta-toilet-ceramic)" stroke="#b9cbd5" strokeWidth={7}/>
      <ellipse cx={450} cy={576} rx={244} ry={92} fill="#c3d2da"/>
      <ellipse cx={450} cy={576 + wobble * .4} rx={214} ry={76} fill="url(#cta-toilet-water)" stroke="#f2fbff" strokeWidth={5}/>
      <ellipse cx={450} cy={524} rx={34} ry={16} fill="#3f7593" stroke="#e6f7ff" strokeWidth={4}/>
      <path d="M336 462 Q450 404 564 462 L556 512 Q450 476 344 512 Z" fill="#f3f8fb" stroke="#b9cbd5" strokeWidth={6}/>
      <ellipse cx={450} cy={458} rx={92} ry={30} fill="#9fb4bf"/>
      <ellipse cx={450} cy={452} rx={70} ry={20} fill="#8fa4ae"/>
      <path d="M356 512 Q450 542 544 512" fill="none" stroke="#b9cbd5" strokeWidth={5} strokeLinecap="round"/>
    </g>
    <g data-toilet-footprints="true">
      {[[214, 604], [686, 604]].map(([cx, cy], i) => (
        <g key={i} transform={`translate(${cx} ${cy})`}>
          <rect x={-58} y={-74} width={116} height={150} rx={28} fill="#cfdde4" stroke="#aebfc9" strokeWidth={5}/>
          {[-46, -22, 2, 26, 50].map((dy) => (
            <rect key={dy} x={-34} y={dy} width={68} height={9} rx={4.5} fill="#b3c6d1" opacity={.85}/>
          ))}
        </g>
      ))}
    </g>
    <g>
      <ellipse data-toilet-water="true" cx={450} cy={576 + wobble * .4} rx={30 + ripple * 170} ry={12 + ripple * 52} fill="none" stroke="#e6f7ff" strokeWidth={6} opacity={(1 - ripple) * .9}/>
      <ellipse cx={450} cy={576 + wobble * .4} rx={20 + ((ripple + .5) % 1) * 150} ry={8 + ((ripple + .5) % 1) * 46} fill="none" stroke="#ffffff" strokeWidth={4} opacity={(1 - ((ripple + .5) % 1)) * .55}/>
      {[0, 1, 2].map((i) => {
        const t = ((frame + i * 7) % 21) / 21;
        return <circle key={i} cx={420 + i * 30 + Math.sin(frame / 5 + i) * 6} cy={560 + wobble - t * 26} r={9 - t * 5} fill="#dff3ff" opacity={(1 - t) * .8}/>;
      })}
    </g>
    <g>
      <path data-toilet-flush="true" d={`M470 300 Q${520 + wobble} 360 500 430 Q${486 + wobble * .6} 470 462 442 Q${470 + wobble} 380 448 316 Z`} fill="#8fd6f5" opacity={.85}/>
      {[0, 1, 2, 3, 4].map((i) => {
        const t = ((frame * 1.2 + i * 9) % 40) / 40;
        return <circle key={i} cx={450 + (i - 2) * 26} cy={286 + t * t * 210} r={10 - t * 4} fill="#cdeefb" opacity={Math.sin(t * Math.PI)}/>;
      })}
      <path d="M402 268 Q450 236 498 268" fill="none" stroke="#cdeefb" strokeWidth={8} strokeLinecap="round" opacity={.7}/>
    </g>
  </svg>;
};
