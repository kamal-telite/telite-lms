import { useRef } from 'react';
import { useAutoHideScrollbar } from './useAutoHideScrollbar';
import './scroll-system.css';

/**
 * Base scroll container.
 * All overflow behavior is driven by semantic CSS classes —
 * no Tailwind utility classes are used.
 */
export function ScrollContainer({ 
  children, 
  className = '', 
  orientation = 'vertical', // 'vertical' | 'horizontal' | 'both'
  as: Component = 'div',
  autoHide = true,
  ...props 
}) {
  const scrollRef = useRef(null);
  
  // Only attach the scroll listener if autoHide is requested
  useAutoHideScrollbar(scrollRef, !autoHide);

  // Map orientation to a semantic CSS modifier class
  const orientationClass = `telite-scroll-container--${orientation}`;

  return (
    <Component 
      ref={scrollRef}
      className={`telite-scroll-container ${orientationClass} ${className}`}
      {...props}
    >
      {children}
    </Component>
  );
}

// ─── Semantic Wrappers ───

export function PageScroll({ children, className = '', ...props }) {
  return (
    <ScrollContainer 
      orientation="vertical" 
      className={`telite-page-scroll ${className}`} 
      {...props}
    >
      {children}
    </ScrollContainer>
  );
}

export function PanelScroll({ children, className = '', ...props }) {
  return (
    <ScrollContainer 
      orientation="vertical" 
      className={`telite-panel-scroll ${className}`} 
      {...props}
    >
      {children}
    </ScrollContainer>
  );
}

export function ModalScroll({ children, className = '', ...props }) {
  return (
    <ScrollContainer 
      orientation="vertical" 
      className={`telite-modal-scroll ${className}`} 
      {...props}
    >
      {children}
    </ScrollContainer>
  );
}

export function TableScroll({ children, className = '', ...props }) {
  return (
    <ScrollContainer 
      orientation="horizontal" 
      className={`telite-table-scroll ${className}`} 
      {...props}
    >
      {children}
    </ScrollContainer>
  );
}
