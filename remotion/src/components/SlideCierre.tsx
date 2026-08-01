import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

const VERDE = '#1ae82f';
const CELESTE = '#22cfff';

type Props = {
  titulo: string;
  copy: string;
  cta: string;
};

export const SlideCierre: React.FC<Props> = ({titulo, copy, cta}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const titleOpacity = spring({frame, fps, from: 0, to: 1, config: {damping: 18}});
  const titleY = interpolate(
    spring({frame, fps, config: {damping: 14}}),
    [0, 1], [50, 0]
  );

  const copyOpacity = interpolate(frame, [20, 45], [0, 1], {extrapolateRight: 'clamp'});
  const copyY = interpolate(frame, [20, 45], [30, 0], {extrapolateRight: 'clamp'});

  const ctaOpacity = interpolate(frame, [50, 75], [0, 1], {extrapolateRight: 'clamp'});
  const ctaScale = interpolate(frame, [50, 75], [0.9, 1], {extrapolateRight: 'clamp'});

  const barWidth = interpolate(frame, [70, 110], [0, 100], {extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill style={{
      background: 'linear-gradient(160deg, #0a0a0a 60%, #0f1a0f 100%)',
      padding: '100px 80px',
      justifyContent: 'center',
      alignItems: 'flex-start',
    }}>
      {/* Título */}
      <div style={{
        opacity: titleOpacity,
        transform: `translateY(${titleY}px)`,
        marginBottom: 48,
      }}>
        <h2 style={{
          color: '#ffffff',
          fontSize: 80,
          fontFamily: 'sans-serif',
          fontWeight: 900,
          lineHeight: 1.1,
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
        marginBottom: 80,
      }}>
        {copy.split('\n').map((line, i) => (
          <p key={i} style={{
            color: '#cccccc',
            fontSize: 42,
            fontFamily: 'sans-serif',
            fontWeight: 400,
            lineHeight: 1.5,
            margin: '0 0 12px 0',
          }}>
            {line}
          </p>
        ))}
      </div>

      {/* CTA pill */}
      <div style={{
        opacity: ctaOpacity,
        transform: `scale(${ctaScale})`,
        backgroundColor: VERDE,
        paddingTop: 28,
        paddingBottom: 28,
        paddingLeft: 56,
        paddingRight: 56,
        borderRadius: 100,
        display: 'inline-flex',
        alignItems: 'center',
        gap: 16,
      }}>
        <span style={{
          color: '#000000',
          fontSize: 38,
          fontFamily: 'sans-serif',
          fontWeight: 800,
          letterSpacing: 0.5,
        }}>
          {cta}
        </span>
      </div>

      {/* Barra gradiente abajo */}
      <div style={{position: 'absolute', bottom: 0, left: 0, right: 0, height: 8}}>
        <div style={{
          width: `${barWidth}%`,
          height: '100%',
          background: `linear-gradient(90deg, ${VERDE}, ${CELESTE})`,
        }} />
      </div>

      {/* Handle Instagram */}
      <div style={{
        position: 'absolute',
        bottom: 48, right: 80,
        opacity: ctaOpacity,
      }}>
        <span style={{
          color: VERDE,
          fontSize: 32,
          fontFamily: 'sans-serif',
          fontWeight: 600,
          letterSpacing: 1,
        }}>
          @impulseagency
        </span>
      </div>
    </AbsoluteFill>
  );
};
