import React from 'react';
import {AbsoluteFill, Sequence} from 'remotion';
import {SlidePortada} from './SlidePortada';
import {SlideContenido} from './SlideContenido';
import {SlideCierre} from './SlideCierre';

export const SLIDE_FRAMES = 90; // 3 segundos a 30fps

export type Slide =
  | {tipo: 'portada'; titulo: string; copy: string}
  | {tipo: 'contenido'; numero: number; titulo: string; copy: string}
  | {tipo: 'cierre'; titulo: string; copy: string; cta: string};

type Props = {
  slides: Slide[];
  tema: string;
};

export const AgenciaReel: React.FC<Props> = ({slides}) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#0a0a0a'}}>
      {slides.map((slide, index) => (
        <Sequence
          key={index}
          from={index * SLIDE_FRAMES}
          durationInFrames={SLIDE_FRAMES}
        >
          {slide.tipo === 'portada' && (
            <SlidePortada titulo={slide.titulo} copy={slide.copy} />
          )}
          {slide.tipo === 'contenido' && (
            <SlideContenido
              numero={slide.numero}
              titulo={slide.titulo}
              copy={slide.copy}
            />
          )}
          {slide.tipo === 'cierre' && (
            <SlideCierre
              titulo={slide.titulo}
              copy={slide.copy}
              cta={slide.cta}
            />
          )}
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
