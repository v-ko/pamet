import React, { ReactNode } from 'react';
import "@/components/Panel.css";

interface PanelProps {
  align: 'top-left' | 'top-right';
  children: ReactNode;
}

const Panel: React.FC<PanelProps> = ({ align, children }) => {
    const stopPropagation = (event: React.MouseEvent<HTMLDivElement>) => {
    // Prevents the event from bubbling up to the parent elements
    event.stopPropagation();
  };
  const stopTouchPropagation = (event: React.TouchEvent<HTMLDivElement>) => {
    // Prevents the event from bubbling up to the parent elements
    event.stopPropagation();
  };

  const alignClass = align === 'top-left' ? 'panel-top-left' : 'panel-top-right';

  return (
    <div
      className={`panel ${alignClass}`}
      onClick={stopPropagation}
      onMouseDown={stopPropagation}
      onMouseUp={stopPropagation}
      onMouseMove={stopPropagation}
      onMouseEnter={stopPropagation}
      onMouseLeave={stopPropagation}
      onContextMenu={stopPropagation}
      onTouchStart={stopTouchPropagation}
      onTouchEnd={stopTouchPropagation}
      onTouchMove={stopTouchPropagation}
    >
      {children}
    </div>
  );
};

export default Panel;
