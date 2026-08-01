import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

const VERDE = '#1ae82f';

type Props = {
  numero: number;
  titulo: string;
  copy: string;
};

export const SlideContenido: React.FC<Props> = ({numero, titulo, copy}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const numOpacity = spring({frame, fps, from: 0, to: 1, config: {damping: 12}});
  const numX = interpolate(
    spring({frame, fps, config: {damping: 12}}),
    [0, 1], [-80, 0]
  );

  const titleOpacity = interpolate(frame, [15, 35], [0, 1], {extrapolateRight: 'clamp'});
  const titleY = interpolate(frame, [15, 35], [40, 0], {extrapolateRight: 'clamp'});

  const copyOpacity = interpolate(frame, [35, 60], [0, 1], {extrapolateRight: 'clamp'});
  const copyY = interpolate(frame, [35, 60], [30, 0], {extrapolateRight: 'clamp'});

  const numStr = String(numero).padStart(2, '0');

  return (
    <AbsoluteFill style={{backgroundColor: '#0a0a0a', padding: '100px 80px', justifyContent: 'center'}}>
      {/* Número */}
      <div style={{
        opacity: numOpacity,
        transform: `translateX(${numX}px)`,
        marginBottom: 32,
      }}>
        <span style={{
          color: VERDE,
          fontSize: 140,
          fontFamily: 'sans-serif',
          fontWeight: 900,
          lineHeight: 1,
          letterSpacing: -4,
        }}>
          {numStr}
        </span>
      </div>

      {/* Línea divisoria */}
      <div style={{
        width: 80, height: 4,
        backgroundColor: VERDE,
        marginBottom: 48,
        opacity: titleOpacity,
      }} />

      {/* Título */}
      <div style={{
        opacity: titleOpacity,
        transform: `translateY(${titleY}px)`,
        marginBottom: 48,
      }}>
        <h2 style={{
          color: '#ffffff',
          fontSize: 72,
          fontFamily: 'sans-serif',
          fontWeight: 800,
          lineHeight: 1.15,
          margin: 0,
          letterSpacing: -1,
        }}>
          {titulo}
        </h2>
      </div>

      {/* Copy */}
      <div style={{
        opacity: copyOpacity,
        transform: `translateY(${copyY}px)`,
      }}>
        <p style={{
          color: '#cccccc',
          fontSize: 44,
          fontFamily: 'sans-serif',
          fontWeight: 400,
          lineHeight: 1.5,
          margin: 0,
        }}>
          {copy}
        </p>
      </div>

      {/* Dot decorativo esquina inferior derecha */}
      <div style={{
        position: 'absolute',
        bottom: 80, right: 80,
        width: 16, height: 16,
        borderRadius: '50%',
        backgroundColor: VERDE,
        opacity: copyOpacity,
      }} />
    </AbsoluteFill>
  );
};
