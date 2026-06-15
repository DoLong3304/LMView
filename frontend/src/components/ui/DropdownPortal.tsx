import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

interface DropdownPortalProps {
  anchorRef: React.RefObject<HTMLElement | null>;
  children: React.ReactNode;
  className?: string;
  maxWidth?: number;
  minWidth?: number;
  onClose: () => void;
  open: boolean;
  placement?: "left" | "right";
  width?: number;
}

const VIEWPORT_MARGIN = 8;

export default function DropdownPortal({
  anchorRef,
  children,
  className = "",
  maxWidth = 320,
  minWidth = 96,
  onClose,
  open,
  placement = "left",
  width,
}: DropdownPortalProps) {
  const portalRef = useRef<HTMLDivElement>(null);
  const [style, setStyle] = useState<React.CSSProperties>({});

  useEffect(() => {
    if (!open) return;

    const updatePosition = () => {
      const anchor = anchorRef.current;
      if (!anchor) return;
      const rect = anchor.getBoundingClientRect();
      const dropdownWidth = Math.min(
        width ?? maxWidth,
        window.innerWidth - VIEWPORT_MARGIN * 2,
      );
      const minClampedWidth = Math.min(minWidth, window.innerWidth - VIEWPORT_MARGIN * 2);
      const preferredLeft = placement === "right"
        ? rect.right - dropdownWidth
        : rect.left;
      const left = Math.min(
        Math.max(VIEWPORT_MARGIN, preferredLeft),
        Math.max(VIEWPORT_MARGIN, window.innerWidth - dropdownWidth - VIEWPORT_MARGIN),
      );
      const top = Math.min(
        rect.bottom + 6,
        Math.max(VIEWPORT_MARGIN, window.innerHeight - VIEWPORT_MARGIN),
      );

      setStyle({
        left,
        minWidth: minClampedWidth,
        position: "fixed",
        top,
        width: dropdownWidth,
        zIndex: 1000,
      });
    };

    updatePosition();
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    return () => {
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
    };
  }, [anchorRef, maxWidth, minWidth, open, placement, width]);

  useEffect(() => {
    if (!open) return;

    const handlePointerDown = (event: MouseEvent) => {
      const target = event.target as Node;
      if (portalRef.current?.contains(target)) return;
      if (anchorRef.current?.contains(target)) return;
      onClose();
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [anchorRef, onClose, open]);

  if (!open || typeof document === "undefined") return null;

  return createPortal(
    <div ref={portalRef} className={className} style={style}>
      {children}
    </div>,
    document.body,
  );
}
