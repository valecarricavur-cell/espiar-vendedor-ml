import React from 'react';
import {Composition} from 'remotion';
import {AgenciaReel, SLIDE_FRAMES, type Slide} from './components/AgenciaReel';
import {ChatAutomatizado, CHAT_DURATION} from './components/ChatAutomatizado';
import {BarraEcosistema, BARRA_DURATION} from './components/BarraEcosistema';
import {CierreEcosistema, CIERRE_ECOSISTEMA_DURATION} from './components/CierreEcosistema';
import {BarraHoras, BARRA_HORAS_DURATION} from './components/BarraHoras';
import {ContadorVentas, CONTADOR_VENTAS_DURATION} from './components/ContadorVentas';

const DEFAULT_SLIDES: Slide[] = [
  {tipo: 'portada', titulo: 'Preview', copy: 'Ejecutá remotion_video.py con tu JSON'},
  {tipo: 'contenido', numero: 1, titulo: 'Slide de ejemplo', copy: 'El contenido se carga desde el JSON al renderizar.'},
  {tipo: 'cierre', titulo: 'Listo', copy: 'Impulse Agency', cta: 'Seguime para más'},
];

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="AgenciaReel"
        component={AgenciaReel}
        durationInFrames={DEFAULT_SLIDES.length * SLIDE_FRAMES}
        fps={30}
        width={720}
        height={1280}
        defaultProps={{slides: DEFAULT_SLIDES, tema: 'Preview'}}
        calculateMetadata={({props}) => ({
          durationInFrames: props.slides.length * SLIDE_FRAMES,
        })}
      />
      <Composition
        id="ChatAutomatizado"
        component={ChatAutomatizado}
        durationInFrames={CHAT_DURATION}
        fps={30}
        width={720}
        height={1280}
        defaultProps={{
          pregunta: '¿Tienen stock en talle M?',
          respuestaAutomatica: '¡Sí! Talle M disponible. Envío en 24-48hs.',
        }}
      />
      <Composition
        id="BarraEcosistema"
        component={BarraEcosistema}
        durationInFrames={BARRA_DURATION}
        fps={30}
        width={720}
        height={1280}
        defaultProps={{
          porcentajeMeli: 60,
          porcentajePropio: 40,
        }}
      />
      <Composition
        id="CierreEcosistema"
        component={CierreEcosistema}
        durationInFrames={CIERRE_ECOSISTEMA_DURATION}
        fps={30}
        width={720}
        height={1280}
      />
      <Composition
        id="BarraHoras"
        component={BarraHoras}
        durationInFrames={BARRA_HORAS_DURATION}
        fps={30}
        width={720}
        height={1280}
        defaultProps={{
          horasAntes: 3,
          horasDespues: 0,
          etiqueta: 'respondiendo consultas, por día',
        }}
      />
      <Composition
        id="ContadorVentas"
        component={ContadorVentas}
        durationInFrames={CONTADOR_VENTAS_DURATION}
        fps={30}
        width={720}
        height={1280}
        defaultProps={{
          desde: 0,
          hasta: 500,
          etiqueta: 'Ventas totales',
        }}
      />
    </>
  );
};
