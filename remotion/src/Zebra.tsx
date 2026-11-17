import React from 'react';

// Zebra tampak samping berdiri di atas zebra cross. Semua gerak dihitung dari frame (deterministik).
export const Zebra: React.FC<{frame: number}> = ({frame}) => {
  const bob = Math.sin(frame / 7) * 5;
  const tilt = Math.sin(frame / 9) * 2;
  const earTwitch = Math.sin(frame / 5) * 10;
  const tailSwish = Math.sin(frame * 0.7) * 16;
  const maneSway = Math.sin(frame / 6) * 5;
  const legSwing = Math.sin(frame / 6) * 4;
  const cycle = frame % 96;
  const blink = cycle > 84 ? Math.sin(((cycle - 84) / 12) * Math.PI) : 0;
  const lidRy = 26 * blink;
  const crossShift = Math.sin(frame / 11) * 7;
  return <svg data-zebra="true" width={880} height={840} viewBox="0 0 900 860" role="img"
    aria-label="Animated zebra standing on a zebra crossing" style={{overflow: 'visible', filter: 'drop-shadow(0 22px 28px #0007)'}}>
    <defs>
      <linearGradient id="cta-zebra-coat" x1="0" y1="0" x2=".3" y2="1">
        <stop stopColor="#ffffff"/><stop offset=".62" stopColor="#f3eee4"/><stop offset="1" stopColor="#ded6c8"/>
      </linearGradient>
      <linearGradient id="cta-zebra-muzzle" x1="0" y1="0" x2="0" y2="1">
        <stop stopColor="#bdb6b1"/><stop offset="1" stopColor="#8d8683"/>
      </linearGradient>
      <linearGradient id="cta-zebra-road" x1="0" y1="0" x2="0" y2="1">
        <stop stopColor="#3f424d"/><stop offset="1" stopColor="#22242c"/>
      </linearGradient>
      <radialGradient id="cta-zebra-glow">
        <stop stopColor="#ffffff" stopOpacity=".26"/><stop offset="1" stopColor="#ffffff" stopOpacity="0"/>
      </radialGradient>
      <clipPath id="cta-zebra-body-clip">
        <rect x={258} y={292} width={392} height={232} rx={70}/>
        <path d="M540 344 L678 196 L768 236 L640 372 Z"/>
        <ellipse cx={712} cy={214} rx={78} ry={66}/>
        <ellipse cx={782} cy={238} rx={44} ry={34}/>
      </clipPath>
    </defs>
    <ellipse cx={470} cy={420} rx={410} ry={360} fill="url(#cta-zebra-glow)"/>

    <g data-zebra-crossing="true" transform={`translate(${crossShift} 0)`}>
      <rect x={30} y={700} width={840} height={130} rx={26} fill="url(#cta-zebra-road)"/>
      {[0, 1, 2, 3, 4, 5].map((i) => (
        <rect key={i} x={52 + i * 136} y={714} width={78} height={102} rx={10} fill="#f7f4ee" opacity={.95}/>
      ))}
    </g>
    <ellipse cx={460} cy={846} rx={260} ry={22} fill="#0b0b10" opacity={.24}/>

    <g data-zebra-tail="true" transform={`rotate(${tailSwish} 274 330)`} fill="none" strokeLinecap="round">
      <path d="M272 326 C214 320 176 366 182 424" stroke="#f3eee4" strokeWidth={26}/>
      <path d="M184 406 C176 424 178 440 188 452" stroke="#2f2f36" strokeWidth={16}/>
    </g>

    <g data-zebra-legs="true" stroke="#2f2f36" strokeWidth={9} strokeLinejoin="round">
      <g transform={`translate(${-legSwing} 0)`}>
        <path d="M292 496 L288 700 L340 700 L344 496 Z" fill="#f3eee4"/>
        <path d="M292 560 H344 M292 624 H344" strokeWidth={12}/>
        <path d="M352 500 L348 700 L400 700 L404 500 Z" fill="#e8e2d6"/>
        <path d="M352 566 H404" strokeWidth={12}/>
      </g>
      <g transform={`translate(${legSwing} 0)`}>
        <path d="M560 496 L556 700 L608 700 L612 496 Z" fill="#f3eee4"/>
        <path d="M560 560 H612 M560 624 H612" strokeWidth={12}/>
        <path d="M620 500 L616 700 L668 700 L672 500 Z" fill="#e8e2d6"/>
        <path d="M620 566 H672" strokeWidth={12}/>
      </g>
    </g>

    <g data-zebra-body="true" stroke="#2f2f36" strokeWidth={9} strokeLinejoin="round" strokeLinecap="round">
      <rect x={258} y={292} width={392} height={232} rx={70} fill="#f3eee4"/>
      <path d="M540 344 L678 196 L768 236 L640 372 Z" fill="#f3eee4"/>
      <ellipse cx={712} cy={214} rx={78} ry={66} fill="#f3eee4"/>
      <g data-zebra-stripes="true" clipPath="url(#cta-zebra-body-clip)" fill="#2f2f36" stroke="none">
        {[0, 1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
          <rect key={i} x={272 + i * 62} y={150} width={30} height={430} rx={14} transform={`rotate(-16 ${287 + i * 62} 370)`}/>
        ))}
      </g>
    </g>

    <g data-zebra-head="true" transform={`translate(0 ${bob}) rotate(${tilt} 712 232)`} stroke="#2f2f36" strokeWidth={8}
      strokeLinejoin="round" strokeLinecap="round">
      <g data-zebra-ears="true" transform={`rotate(${earTwitch} 712 168)`}>
        <path d="M676 178 L668 106 L734 152 Z" fill="#f3eee4"/>
        <path d="M752 172 L762 100 L800 158 Z" fill="#f3eee4"/>
      </g>
      <g data-zebra-mane="true" transform={`rotate(${maneSway} 640 400)`} fill="#2f2f36" stroke="none">
        {[0, 1, 2, 3, 4].map((i) => {
          const x = 556 + i * 34;
          const y = 322 - i * 30;
          return <path key={i} d={`M${x} ${y} L${x + 12} ${y - 46} L${x + 26} ${y + 4} Z`}/>;
        })}
      </g>
      <g data-zebra-eyes="true">
        <ellipse cx={734} cy={196} rx={21} ry={20} fill="#ffffff" strokeWidth={6}/>
        <ellipse cx={738} cy={200} rx={12} ry={13} fill="#20222a" stroke="none"/>
        <circle cx={733} cy={193} r={4.5} fill="#ffffff" stroke="none"/>
        <ellipse cx={734} cy={196 - 19 + lidRy} rx={22} ry={lidRy} fill="#f3eee4" stroke="none"/>
      </g>
      <path d="M690 214 Q712 234 690 254" fill="none" strokeWidth={7} opacity={.8}/>
      <g data-zebra-muzzle="true" stroke="#4a4744" strokeWidth={6}>
        <ellipse cx={784} cy={240} rx={46} ry={36} fill="url(#cta-zebra-muzzle)"/>
        <ellipse cx={764} cy={234} rx={7} ry={9} fill="#3b3835" stroke="none"/>
        <path d="M800 256 Q812 262 806 272" fill="none" strokeWidth={5}/>
      </g>
    </g>
  </svg>;
};
