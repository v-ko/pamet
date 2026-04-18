import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import '@/views/menu/Menu.css';

export type MenuItem = {
  label: string;
  onClick?: () => void;
  disabled?: boolean;
  submenu?: MenuItem[];
  type?: 'item' | 'separator';
  shortcut?: string; // optional, pre-resolved display label from parent
};

export type MenuProps = {
  items: MenuItem[];
  x: number;
  y: number;
  onDismiss: () => void;
  variant?: 'main' | 'context';
  alignX?: 'left' | 'right';
  embedded?: boolean; // if true, don't clamp/position to viewport; let parent handle
};

export function Menu({ items, x, y, onDismiss, variant = 'main', alignX = 'left', embedded = false }: MenuProps) {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const [submenuOpenIndex, setSubmenuOpenIndex] = useState<number | null>(null);

  // Close on outside click or Escape
  useEffect(() => {
    function onDocMouseDown(ev: MouseEvent) {
      const path = (ev.composedPath && ev.composedPath()) as (EventTarget[]) | undefined;
      if (Array.isArray(path)) {
        // If click lands within any menu root, do not dismiss
        for (const t of path) {
          if ((t as HTMLElement)?.classList?.contains('MenuRoot')) {
            return;
          }
        }
      } else {
        const target = ev.target as HTMLElement | null;
        if (target && target.closest && target.closest('.MenuRoot')) {
          return;
        }
      }
      onDismiss();
    }
    function onDocKeyDown(ev: KeyboardEvent) {
      if (ev.key === 'Escape') onDismiss();
    }
    document.addEventListener('mousedown', onDocMouseDown);
    document.addEventListener('keydown', onDocKeyDown);
    return () => {
      document.removeEventListener('mousedown', onDocMouseDown);
      document.removeEventListener('keydown', onDocKeyDown);
    };
  }, [onDismiss]);

  // Keep menu within viewport bounds, accounting for actual rendered size
  const [adjustedPos, setAdjustedPos] = useState<{ left: number; top: number }>({ left: x, top: y });

  useLayoutEffect(() => {
    if (embedded) return;
    const el = rootRef.current;
    if (!el) {
      setAdjustedPos({ left: x, top: y });
      return;
    }
    const pad = 8;
    const rect = el.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    let adjX = x;
    let adjY = y;

    // If menu overflows right edge, shift left
    if (adjX + rect.width > vw - pad) {
      adjX = vw - rect.width - pad;
    }
    // If menu overflows bottom edge, shift up
    if (adjY + rect.height > vh - pad) {
      adjY = vh - rect.height - pad;
    }
    // Ensure it doesn't go off the left/top edges
    adjX = Math.max(pad, adjX);
    adjY = Math.max(pad, adjY);

    setAdjustedPos({ left: adjX, top: adjY });
  }, [x, y, embedded, items]);

  const style: React.CSSProperties = embedded
    ? { left: '0px', top: '0px', ...(alignX === 'right' ? { transform: 'translateX(-100%)' } : {}) }
    : { left: adjustedPos.left + 'px', top: adjustedPos.top + 'px', ...(alignX === 'right' ? { transform: 'translateX(-100%)' } : {}) };

  return (
    <div ref={rootRef} className={`MenuRoot ${variant}`} style={style}>
      <ul className="MenuList" role="menu">
        {items.map((item, idx) => {
          if (item.type === 'separator') {
            return <li key={idx} className="Separator" role="separator" />
          }
          const hasSub = !!item.submenu && item.submenu.length > 0;
          const disabled = !!item.disabled;
          const shortcut = item.shortcut;
          return (
            <li
              key={idx}
              className={`MenuItem${disabled ? ' disabled' : ''}${hasSub && submenuOpenIndex === idx ? ' open' : ''}`}
              role="menuitem"
              aria-haspopup={hasSub || undefined}
              aria-expanded={hasSub ? (submenuOpenIndex === idx) : undefined}
              tabIndex={disabled ? -1 : 0}
              onMouseEnter={() => setSubmenuOpenIndex(hasSub ? idx : null)}
              onClick={(e) => {
                if (disabled) return;
                if (hasSub) {
                  e.preventDefault();
                  e.stopPropagation();
                  setSubmenuOpenIndex((cur) => (cur === idx ? null : idx));
                  return;
                }
                try {
                  item.onClick?.();
                } finally {
                  onDismiss();
                }
              }}
              style={{ position: 'relative' }}
            >
              <span>{item.label}</span>
              <span className="MenuRight">
                {shortcut && <span className="Shortcut">{shortcut}</span>}
                {hasSub && <span className="MenuRightIcon">▶</span>}
              </span>
              {hasSub && submenuOpenIndex === idx && (
                <div className="Submenu">
                  <Menu
                    items={item.submenu!}
                    x={0}
                    y={0}
                    onDismiss={onDismiss}
                    variant={variant}
                    embedded={true}
                  />
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default Menu;
