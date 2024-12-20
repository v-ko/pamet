import React, { ReactNode } from 'react';
import styled from 'styled-components';

// Define the styled component with TypeScript
const StyledPanel = styled.div<{ align: 'top-left' | 'top-right' }>`
  position: absolute;
  top: 6px;
  left: ${(props) => (props.align === 'top-left' ? '6px' : 'auto')};
  right: ${(props) => (props.align === 'top-right' ? '6px' : 'auto')};
  padding: 10px;
  background: rgba(255, 255, 255, 1);
  display: flex;
  flex-direction: row;
  gap: 10px;
  z-index: 1002;
  box-shadow: 0px 0px 15px rgba(0,0,0,0.2);
  border: 1px solid rgba(0,0,0,0.2);
  border-radius: 3px;
  justify-content: center;
  align-items: center;
  font-size: 1.2em;
`;

interface PanelProps {
  align: 'top-left' | 'top-right';
  children: ReactNode;
}

// Functional React component that utilizes StyledPanel with type annotations
const Panel: React.FC<PanelProps> = ({ align, children }) => {
  const stopPropagation = (event: React.MouseEvent<HTMLDivElement>) => {
    // Prevents the event from bubbling up to the parent elements
    event.stopPropagation();
  };
  const stopTouchPropagation = (event: React.TouchEvent<HTMLDivElement>) => {
    // Prevents the event from bubbling up to the parent elements
    event.stopPropagation();
  };

  return (
    <StyledPanel align={align}
      onClick={stopPropagation}
      onMouseDown={stopPropagation}
      onMouseUp={stopPropagation}
      onMouseMove={stopPropagation}
      onMouseEnter={stopPropagation}
      onMouseLeave={stopPropagation}
      onContextMenu={stopPropagation}
      onTouchStart={stopTouchPropagation}
      onTouchEnd={stopTouchPropagation}
      onTouchMove={stopTouchPropagation}>
      {children}
    </StyledPanel>
  );
};

export default Panel;
