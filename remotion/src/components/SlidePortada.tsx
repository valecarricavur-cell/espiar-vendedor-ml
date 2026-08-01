import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

const VERDE = '#1ae82f';
const CELESTE = '#22cfff';

type Props = {
  titulo: string;
  copy: string;
};

export const SlidePortada: React.FC<Props> = ({titulo, copy}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const logoOpacity = spring({frame, fps, from: 0, to: 1, config: {damping: 20}});

  const titleY = interpolate(
    spring({frame: Math.max(0, frame - 8), fps, config: {damping: 14}}),
    [0, 1], [60, 0]
  );
  const titleOpacity = interpolate(frame, [8, 28], [0, 1], {extrapolateRight: 'clamp'});

  const copyOpacity = interpolate(frame, [30, 50], [0, 1], {extrapolateRight: 'clamp'});
  const copyY = interpolate(frame, [30, 50], [30, 0], {extrapolateRight: 'clamp'});

  const barWidth = interpolate(frame, [50, 90], [0, 100], {extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill style={{backgroundColor: '#0a0a0a', justifyContent: 'center', alignItems: 'center', padding: 80}}>
      {/* Logo arriba */}
      <div style={{
        position: 'absolute', top: 90, left: 80,
        opacity: logoOpacity,
        display: 'flex', alignItems: 'center', gap: 12,
      }}>
        <div style={{width: 10, height: 10, borderRadius: '50%', backgroundColor: VERDE}} />
        <span style={{color: '#ffffff', fontSize: 28, fontFamily: 'sans-serif', letterSpacing: 3, fontWeight: 600}}>
          IMPULSE AGENCY
        </span>
      </div>

      {/* Título principal */}
      <div style={{
        opacity: titleOpacity,
        transform: `translateY(${titleY}px)`,
        textAlign: 'center',
        marginBottom: 40,
      }}>
        <h1 style={{
          color: '#ffffff',
          fontSize: 88,
          fontFamily: 'sans-serif',
          fontWeight: 900,
          lineHeight: 1.1,
          margin: 0,
          letterSpacing: -1,
        }}>
          {titulo}
        </h1>
      </div>

      {/* Subtítulo */}
      <div style={{
        opacity: copyOpacity,
        transform: `translateY(${copyY}px)`,
        textAlign: 'center',
      }}>
        <p style={{
          color: '#999999',
          fontSize: 42,
          fontFamily: 'sans-serif',
          fontWeight: 400,
          margin: 0,
          lineHeight: 1.4,
        }}>
          {copy}
        </p>
      </div>

      {/* Barra verde animada abajo */}
      <div style={{position: 'absolute', bottom: 0, left: 0, right: 0, height: 8, backgroundColor: '#111'}}>
        <div style={{
          width: `${barWidth}%`,
          height: '100%',
          background: `linear-gradient(90deg, ${VERDE}, ${CELESTE})`,
        }} />
      </div>
    </AbsoluteFill>
  );
};
